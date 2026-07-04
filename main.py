#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import sys
import os
import random
import math
from datetime import datetime, timedelta, timezone
from pygame.locals import *

# 自作モジュールのインポート
from constants import *
from aws_icon import AWSIcon
from evolution_system import EvolutionSystem
from progress_system import ProgressSystem
from ui_panel import UIPanel

class Game:
    """ゲームのメインクラス"""
    
    # キーボードのアルファベットと生成するサービスの対応
    # （EBSはEがEC2と重複するため頭文字ではなくBlock storeのBを割り当て）
    KEY_TO_SERVICE = {
        K_e: "EC2",
        K_s: "S3",
        K_v: "VPC",
        K_l: "Lambda",
        K_b: "EBS",
        K_r: "RDS",
        K_i: "IAM",
        K_d: "DynamoDB",
        K_a: "API Gateway",
        K_c: "CloudFront",
    }

    # VPCのデフォルトクォータ（AWSアカウントのリージョンあたり5個）
    # これを超えて6個目を作ろうとすると即座に失敗することを表現する
    VPC_DEFAULT_QUOTA = 5
    # デフォルトクォータ超過時のAWS CreateVpcエラーメッセージを忠実に再現
    # （errorCode: VpcLimitExceeded）
    VPC_QUOTA_ERROR_MESSAGE = (
        "An error occurred (VpcLimitExceeded) when calling the CreateVpc "
        "operation: The maximum number of VPCs has been reached."
    )

    # EC2インスタンスのリタイア通知に使うリージョン（AWS公式メッセージの再現用）
    EC2_RETIREMENT_REGION = "us-east-1"

    # 相互作用に関する定数
    VELOCITY_SLOWDOWN_FACTOR = 0.9
    VELOCITY_INCREASE_FACTOR = 1.1
    VELOCITY_MAX_MULTIPLIER = 2
    HEALTH_RECOVERY_AMOUNT = 0.1
    VELOCITY_FOLLOW_FACTOR = 0.3
    
    def __init__(self):
        """初期化"""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        
        # アイコングループ
        self.all_icons = pygame.sprite.Group()
        
        # UIパネル
        self.ui_panel = UIPanel(GAME_AREA_WIDTH, 0, UI_PANEL_WIDTH, SCREEN_HEIGHT)
        
        # 選択中のアイコン
        self.selected_icon = None
        
        # 直接操作中のアイコン
        self.direct_control_icon = None
        
        # 進行システム
        self.progress_system = ProgressSystem()

        # 進化システム
        self.evolution_system = EvolutionSystem()

        # EC2リタイア通知に使うAWSアカウントID（12桁、公式メッセージの再現用）
        self.aws_account_id = f"{random.randint(0, 10 ** 12 - 1):012d}"
        
        # 初期アイコンの生成
        self._create_initial_icons()
    
    def _create_initial_icons(self):
        """初期アイコンを生成"""
        # 起動時には何もアイコンを配置しない
        pass

    def _spawn_icon(self, service, position=None):
        """指定サービスのアイコンを生成して追加する（位置未指定ならランダム配置）"""
        if position is None:
            position = (random.randint(50, GAME_AREA_WIDTH - 50),
                        random.randint(50, SCREEN_HEIGHT - 50))
        icon = AWSIcon(service, position)

        # VPCはデフォルトクォータ（5個）を超えると6個目以降は即死する。
        # AWSアカウントでデフォルトでは5個までしかVPCを作れないことの表現。
        if service == "VPC":
            existing_vpcs = sum(
                1 for i in self.all_icons
                if i.service_type == "VPC" and i.health > 0
            )
            if existing_vpcs >= self.VPC_DEFAULT_QUOTA:
                icon.health = 0  # 即死（次の更新で除去される）
                self.progress_system.add_notification(self.VPC_QUOTA_ERROR_MESSAGE)

        self.all_icons.add(icon)
        return icon

    def _ec2_retirement_message(self, icon):
        """AWSのEC2インスタンスリタイア通知メール本文を忠実に再現する

        公式メッセージ:
        "EC2 has detected degradation of the underlying hardware hosting your
        Amazon EC2 instance (instance-ID: ...) associated with your AWS account
        (AWS Account ID: ...) in the ... region. Due to this degradation your
        instance could already be unreachable. We will stop your instance
        after ... UTC."
        """
        stop_time = (datetime.now(timezone.utc) + timedelta(days=14)).strftime(
            "%Y-%m-%d %H:%M:%S")
        return (
            f"EC2 has detected degradation of the underlying hardware hosting "
            f"your Amazon EC2 instance (instance-ID: {icon.instance_id}) "
            f"associated with your AWS account (AWS Account ID: "
            f"{self.aws_account_id}) in the {self.EC2_RETIREMENT_REGION} region. "
            f"Due to this degradation your instance could already be "
            f"unreachable. We will stop your instance after {stop_time} UTC."
        )

    def handle_events(self):
        """イベント処理"""
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                elif event.key == K_SPACE:
                    # スペースキーで新しいランダムなアイコンを追加
                    self._spawn_icon(random.choice(AWS_ICONS))
                elif event.key in self.KEY_TO_SERVICE and not (event.mod & KMOD_SHIFT):
                    # アルファベットキーで対応するサービスのアイコンを生成
                    # （ShiftはShift+Aの実績オーバーレイ用に予約し、生成はしない）
                    self._spawn_icon(self.KEY_TO_SERVICE[event.key])
            elif event.type == MOUSEBUTTONDOWN:
                # UIパネル外（ゲームエリア内）のみ処理
                if event.pos[0] < GAME_AREA_WIDTH:
                    if event.button == 1:  # 左クリック
                        # アイコンがあればドラッグ操作を開始、なければ新しいアイコンを配置
                        if not self._start_drag_control(event.pos):
                            # クリック位置にアイコンがなければ新しいアイコンを追加
                            self._spawn_icon(random.choice(AWS_ICONS), event.pos)
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:  # 左クリックリリース
                    # ドラッグ操作の終了
                    self.direct_control_icon = None
            elif event.type == MOUSEMOTION:
                # ドラッグ操作中のアイコン移動
                if self.direct_control_icon:
                    self.direct_control_icon.rect.center = event.pos
    def _start_drag_control(self, position):
        """指定位置のアイコンを選択してドラッグ操作を開始。アイコンがあればTrue、なければFalseを返す"""
        # 以前の選択をクリア
        if self.selected_icon:
            self.selected_icon.selected = False
        
        self.selected_icon = None
        self.direct_control_icon = None
        
        # 位置にあるアイコンを探す
        for icon in self.all_icons:
            if icon.rect.collidepoint(position):
                icon.selected = True
                self.selected_icon = icon
                # ドラッグ操作のために直接操作対象として設定
                self.direct_control_icon = icon
                return True
        return False
    
    def update(self):
        """ゲームの状態を更新"""
        # アイコンの更新とHealthが0になったアイコンを削除
        dead_icons = set()
        for icon in self.all_icons:
            icon.update(self.all_icons)
            if icon.health <= 0:
                dead_icons.add(icon)
            # EC2リタイア発動時に通知を出す（発動した瞬間のみ）
            if getattr(icon, 'retiring', False) and not icon.retirement_announced:
                icon.retirement_announced = True
                self.progress_system.add_notification(
                    self._ec2_retirement_message(icon)
                )
        
        # 削除対象のアイコンを処理
        if dead_icons:
            # 選択中のアイコンが削除される場合は選択を解除
            if self.selected_icon in dead_icons:
                self.selected_icon = None
            # 直接操作中のアイコンが削除される場合は操作を解除
            if self.direct_control_icon in dead_icons:
                self.direct_control_icon = None
            # アイコンをグループから効率的に削除
            for icon in dead_icons:
                if icon in self.all_icons:
                    self.all_icons.remove(icon)

        # AutoScalingのスケールアウトによるアイコン起動リクエストを処理
        for icon in list(self.all_icons):
            requests = getattr(icon, 'spawn_requests', None)
            if requests:
                for service_type, position in requests:
                    self.all_icons.add(AWSIcon(service_type, position))
                icon.spawn_requests = []

        # 進行状況の更新
        self.progress_system.check_achievements(self.all_icons)
        self.progress_system.update_notifications()
        
        # UIパネルの更新
        self.ui_panel.update(self.all_icons, self.selected_icon)
        
        # アイコン間の相互作用を処理
        self._handle_interactions()

        # アイコンの進化を処理
        self._handle_evolutions()

    def _handle_evolutions(self):
        """アイコンの進化を処理"""
        for evolution in self.evolution_system.update(self.all_icons):
            # 進化元のアイコンを削除（選択中・操作中の場合は参照も解除）
            for icon in evolution.icons:
                if self.selected_icon is icon:
                    self.selected_icon = None
                if self.direct_control_icon is icon:
                    self.direct_control_icon = None
                self.all_icons.remove(icon)

            # 進化後のアイコンを重心位置に生成
            self.all_icons.add(
                AWSIcon(evolution.target_type, evolution.position, evolution.velocity)
            )
            # 進化発動を実績として記録（通知＋Shift+Aオーバーレイに反映）
            self.progress_system.record_evolution(
                evolution.source_type, evolution.target_type
            )

    def _handle_interactions(self):
        """アイコン間の相互作用を処理"""
        # すべてのアイコンペアをチェック
        for i, icon1 in enumerate(self.all_icons):
            for icon2 in list(self.all_icons)[i+1:]:
                # 近接しているかチェック
                if icon1._is_near(icon2, 70):  # 70pxの距離内にある場合
                    # 相互作用を記録
                    icon1.last_interaction = icon2
                    icon2.last_interaction = icon1
                    icon1.interaction_timer = 30  # 30フレーム（約0.5秒）
                    icon2.interaction_timer = 30
                    
                    # 依存関係の処理
                    if icon2.service_type in icon1.dependencies:
                        # 依存関係が満たされた場合、体力回復を加速
                        icon1.recover(5)
                    
                    # 補完関係の処理
                    self._handle_complementary_relations(icon1, icon2)
                    
                    # 重なり防止のための位置調整
                    self._adjust_overlapping_positions(icon1, icon2)
    
    def _adjust_overlapping_positions(self, icon1, icon2):
        """重なっているアイコンの位置を調整"""
        # アイコン間のベクトルを計算
        dx = icon2.rect.centerx - icon1.rect.centerx
        dy = icon2.rect.centery - icon1.rect.centery
        
        # ベクトルの長さ（距離）を計算
        distance = math.sqrt(dx*dx + dy*dy)
        
        # 最小距離は両方のアイコンの半径の合計（サイズが異なるアイコンにも対応）
        min_distance = icon1.rect.width / 2 + icon2.rect.width / 2
        
        # 重なっている場合のみ調整
        if distance < min_distance and distance > 0:  # 0除算を防ぐ
            # 重なりの度合いを計算
            overlap = min_distance - distance
            
            # 正規化したベクトル
            if distance > 0:
                dx /= distance
                dy /= distance
            
            # 重なりを解消するための移動量
            move_x = dx * overlap / 2
            move_y = dy * overlap / 2
            
            # 両方のアイコンを反対方向に移動
            icon1.rect.x -= move_x
            icon1.rect.y -= move_y
            icon2.rect.x += move_x
            icon2.rect.y += move_y
            
            # ゲームエリア内に収める
            icon1.rect.left = max(0, min(icon1.rect.left, GAME_AREA_WIDTH - icon1.rect.width))
            icon1.rect.top = max(0, min(icon1.rect.top, SCREEN_HEIGHT - icon1.rect.height))
            icon2.rect.left = max(0, min(icon2.rect.left, GAME_AREA_WIDTH - icon2.rect.width))
            icon2.rect.top = max(0, min(icon2.rect.top, SCREEN_HEIGHT - icon2.rect.height))
    
    def _cap_velocity(self, velocity, increase_factor, max_multiplier):
        """速度成分を増加させつつ、元の速度の max_multiplier 倍を超えないようキャップする"""
        capped = []
        for v in velocity:
            candidate = v * increase_factor
            limit = v * max_multiplier
            if v > 0:
                capped.append(min(candidate, limit))
            elif v < 0:
                capped.append(max(candidate, limit))
            else:
                capped.append(candidate)
        return capped

    def _handle_complementary_relations(self, icon1, icon2):
        """補完関係の処理"""
        # EC2とEBSの補完関係
        if (icon1.service_type == "EC2" and icon2.service_type == "EBS") or \
           (icon1.service_type == "EBS" and icon2.service_type == "EC2"):
            # 両方のアイコンの速度を少し遅くする（安定性を表現）
            icon1.velocity = [v * self.VELOCITY_SLOWDOWN_FACTOR for v in icon1.velocity]
            icon2.velocity = [v * self.VELOCITY_SLOWDOWN_FACTOR for v in icon2.velocity]
            # 体力を少し回復（過度な回復を防ぐ）
            icon1.recover(self.HEALTH_RECOVERY_AMOUNT)
            icon2.recover(self.HEALTH_RECOVERY_AMOUNT)
            
            # EC2とEBSが近くにいる場合、EBSはEC2に追従する傾向を強める
            if icon1.service_type == "EC2" and icon2.service_type == "EBS":
                # EC2の動きにEBSを追従させる
                icon2.velocity = [
                    (1 - self.VELOCITY_FOLLOW_FACTOR) * icon2.velocity[0] + self.VELOCITY_FOLLOW_FACTOR * icon1.velocity[0],
                    (1 - self.VELOCITY_FOLLOW_FACTOR) * icon2.velocity[1] + self.VELOCITY_FOLLOW_FACTOR * icon1.velocity[1]
                ]
            elif icon1.service_type == "EBS" and icon2.service_type == "EC2":
                # EC2の動きにEBSを追従させる
                icon1.velocity = [
                    (1 - self.VELOCITY_FOLLOW_FACTOR) * icon1.velocity[0] + self.VELOCITY_FOLLOW_FACTOR * icon2.velocity[0],
                    (1 - self.VELOCITY_FOLLOW_FACTOR) * icon1.velocity[1] + self.VELOCITY_FOLLOW_FACTOR * icon2.velocity[1]
                ]
        
        # LambdaとDynamoDBの補完関係
        if (icon1.service_type == "Lambda" and icon2.service_type == "DynamoDB") or \
           (icon1.service_type == "DynamoDB" and icon2.service_type == "Lambda"):
            # 両方のアイコンの速度を少し速くする（効率性を表現）- 上限あり
            icon1.velocity = self._cap_velocity(icon1.velocity, self.VELOCITY_INCREASE_FACTOR, self.VELOCITY_MAX_MULTIPLIER)
            icon2.velocity = self._cap_velocity(icon2.velocity, self.VELOCITY_INCREASE_FACTOR, self.VELOCITY_MAX_MULTIPLIER)
            # 体力を少し回復（過度な回復を防ぐ）
            icon1.recover(self.HEALTH_RECOVERY_AMOUNT)
            icon2.recover(self.HEALTH_RECOVERY_AMOUNT)

        # S3とCloudFrontの補完関係
        if (icon1.service_type == "S3" and icon2.service_type == "CloudFront") or \
           (icon1.service_type == "CloudFront" and icon2.service_type == "S3"):
            # 速度を少し速くする（効率性を表現）- 上限あり
            icon1.velocity = self._cap_velocity(icon1.velocity, self.VELOCITY_INCREASE_FACTOR, self.VELOCITY_MAX_MULTIPLIER)
            icon2.velocity = self._cap_velocity(icon2.velocity, self.VELOCITY_INCREASE_FACTOR, self.VELOCITY_MAX_MULTIPLIER)
            # 体力を少し回復（過度な回復を防ぐ）
            icon1.recover(self.HEALTH_RECOVERY_AMOUNT)
            icon2.recover(self.HEALTH_RECOVERY_AMOUNT)

            # CloudFrontの場合は追加で速度を上げる（配信の高速化を表現）
            cloudfront_boost_factor = 1.2
            if icon1.service_type == "CloudFront":
                icon1.velocity = self._cap_velocity(icon1.velocity, cloudfront_boost_factor, self.VELOCITY_MAX_MULTIPLIER)
            elif icon2.service_type == "CloudFront":
                icon2.velocity = self._cap_velocity(icon2.velocity, cloudfront_boost_factor, self.VELOCITY_MAX_MULTIPLIER)
    
    def render(self):
        """描画処理"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # ゲームエリアとUIの区切り線
        pygame.draw.line(
            self.screen,
            UI_BORDER_COLOR,
            (GAME_AREA_WIDTH, 0),
            (GAME_AREA_WIDTH, SCREEN_HEIGHT),
            2
        )
        
        # アイコンの描画（カスタム描画メソッドを使用）
        for icon in self.all_icons:
            icon.draw(self.screen)
        
        # 進行システムの描画
        font = pygame.font.SysFont(None, 24)
        self.progress_system.draw(self.screen, font)
        
        # UIパネルの描画
        self.ui_panel.draw(self.screen)

        # Shift+A押下中は全実績の状況を最前面にオーバーレイ表示
        keys = pygame.key.get_pressed()
        if keys[K_a] and (keys[K_LSHIFT] or keys[K_RSHIFT]):
            self.progress_system.draw_overlay(self.screen)

        pygame.display.flip()
    
    def run(self):
        """ゲームのメインループ"""
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    # assets/iconsディレクトリが存在しない場合は作成
    os.makedirs("assets/icons", exist_ok=True)
    
    game = Game()
    game.run()

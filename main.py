#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import sys
import os
import random
import math
from pygame.locals import *

# 自作モジュールのインポート
from constants import *
from aws_icon import AWSIcon
from progress_system import ProgressSystem
from ui_panel import UIPanel

class Game:
    """ゲームのメインクラス"""
    
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
        
        # 初期アイコンの生成
        self._create_initial_icons()
    
    def _create_initial_icons(self):
        """初期アイコンを生成"""
        # 起動時には何もアイコンを配置しない
        pass
    
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
                    service = random.choice(AWS_ICONS)
                    position = (random.randint(50, GAME_AREA_WIDTH - 50), 
                                random.randint(50, SCREEN_HEIGHT - 50))
                    icon = AWSIcon(service, position)
                    self.all_icons.add(icon)
            elif event.type == MOUSEBUTTONDOWN:
                # UIパネル外（ゲームエリア内）のみ処理
                if event.pos[0] < GAME_AREA_WIDTH:
                    if event.button == 1:  # 左クリック
                        # アイコンがあればドラッグ操作を開始、なければ新しいアイコンを配置
                        if not self._start_drag_control(event.pos):
                            # クリック位置にアイコンがなければ新しいアイコンを追加
                            service = random.choice(AWS_ICONS)
                            icon = AWSIcon(service, event.pos)
                            self.all_icons.add(icon)
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
        # アイコンの更新
        for icon in self.all_icons:
            icon.update(self.all_icons)
        
        # Healthが0になったアイコンを削除
        # アイコンの更新とHealthが0になったアイコンを削除
        dead_icons = set()
        for icon in self.all_icons:
            icon.update(self.all_icons)
            if icon.health <= 0:
                dead_icons.add(icon)
        
        # 削除対象のアイコンを処理
        if dead_icons:
            # 選択中のアイコンが削除される場合は選択を解除
            if self.selected_icon in dead_icons:
                self.selected_icon = None
            # 直接操作中のアイコンが削除される場合は操作を解除
            if self.direct_control_icon in dead_icons:
                self.direct_control_icon = None
            # アイコンをグループから削除
            for icon in dead_icons:
                self.all_icons.remove(icon)
        
        # 進行状況の更新
        self.progress_system.check_achievements(self.all_icons)
        self.progress_system.update_notifications()
        
        # UIパネルの更新
        self.ui_panel.update(self.all_icons, self.selected_icon)
        
        # アイコン間の相互作用を処理
        self._handle_interactions()
    
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
                        icon1.health = min(icon1.max_health, icon1.health + 5)
                    
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
        
        # アイコンの半径（サイズの半分）
        icon_radius = icon1.rect.width / 2
        min_distance = icon_radius * 2  # 最小距離は両方のアイコンの半径の合計
        
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
    
    def _handle_complementary_relations(self, icon1, icon2):
        """補完関係の処理"""
        # EC2とEBSの補完関係
        if (icon1.service_type == "EC2" and icon2.service_type == "EBS") or \
           (icon1.service_type == "EBS" and icon2.service_type == "EC2"):
            # 両方のアイコンの速度を少し遅くする（安定性を表現）
            # Constants for velocity and health adjustments
            VELOCITY_SLOWDOWN_FACTOR = 0.9
            HEALTH_RECOVERY_AMOUNT = 0.1
            VELOCITY_FOLLOW_FACTOR = 0.3
            # 両方のアイコンの速度を少し遅くする（安定性を表現）
            icon1.velocity = [v * VELOCITY_SLOWDOWN_FACTOR for v in icon1.velocity]
            icon2.velocity = [v * VELOCITY_SLOWDOWN_FACTOR for v in icon2.velocity]
            # 体力を少し回復（過度な回復を防ぐ）
            icon1.health = min(icon1.max_health, icon1.health + HEALTH_RECOVERY_AMOUNT)
            icon2.health = min(icon2.max_health, icon2.health + HEALTH_RECOVERY_AMOUNT)
            
            # EC2とEBSが近くにいる場合、EBSはEC2に追従する傾向を強める
            if icon1.service_type == "EC2" and icon2.service_type == "EBS":
                # EC2の動きにEBSを追従させる
                icon2.velocity = [
                    (1 - VELOCITY_FOLLOW_FACTOR) * icon2.velocity[0] + VELOCITY_FOLLOW_FACTOR * icon1.velocity[0],
                    (1 - VELOCITY_FOLLOW_FACTOR) * icon2.velocity[1] + VELOCITY_FOLLOW_FACTOR * icon1.velocity[1]
                ]
            elif icon1.service_type == "EBS" and icon2.service_type == "EC2":
                # EC2の動きにEBSを追従させる
                icon1.velocity = [
                    (1 - VELOCITY_FOLLOW_FACTOR) * icon1.velocity[0] + VELOCITY_FOLLOW_FACTOR * icon2.velocity[0],
                    (1 - VELOCITY_FOLLOW_FACTOR) * icon1.velocity[1] + VELOCITY_FOLLOW_FACTOR * icon2.velocity[1]
                ]
        
        # LambdaとDynamoDBの補完関係
            icon2.velocity = [v * 0.9 for v in icon2.velocity]
            # 体力を少し回復（過度な回復を防ぐ）
            icon1.health = min(icon1.max_health, icon1.health + 0.1)
            icon2.health = min(icon2.max_health, icon2.health + 0.1)
            
            # EC2とEBSが近くにいる場合、EBSはEC2に追従する傾向を強める
            if icon1.service_type == "EC2" and icon2.service_type == "EBS":
                # EC2の動きにEBSを追従させる
                icon2.velocity = [
                    0.7 * icon2.velocity[0] + 0.3 * icon1.velocity[0],
                    0.7 * icon2.velocity[1] + 0.3 * icon1.velocity[1]
                ]
            elif icon1.service_type == "EBS" and icon2.service_type == "EC2":
                # EC2の動きにEBSを追従させる
                icon1.velocity = [
                    0.7 * icon1.velocity[0] + 0.3 * icon2.velocity[0],
                    0.7 * icon1.velocity[1] + 0.3 * icon2.velocity[1]
                ]
        
        # LambdaとDynamoDBの補完関係
        if (icon1.service_type == "Lambda" and icon2.service_type == "DynamoDB") or \
           (icon1.service_type == "DynamoDB" and icon2.service_type == "Lambda"):
            # 両方のアイコンの速度を少し速くする（効率性を表現）- 上限あり
            VELOCITY_INCREASE_FACTOR = 1.1
            VELOCITY_MAX_MULTIPLIER = 2
            icon1.velocity = [min(v * VELOCITY_INCREASE_FACTOR, v * VELOCITY_MAX_MULTIPLIER if v > 0 else v * -VELOCITY_MAX_MULTIPLIER) for v in icon1.velocity]
            icon2.velocity = [min(v * VELOCITY_INCREASE_FACTOR, v * VELOCITY_MAX_MULTIPLIER if v > 0 else v * -VELOCITY_MAX_MULTIPLIER) for v in icon2.velocity]
            # 体力を少し回復（過度な回復を防ぐ）
            HEALTH_RECOVERY_AMOUNT = 0.1
            icon1.health = min(icon1.max_health, icon1.health + HEALTH_RECOVERY_AMOUNT)
            icon2.health = min(icon2.max_health, icon2.health + HEALTH_RECOVERY_AMOUNT)
        
        # S3とCloudFrontの補完関係
        if (icon1.service_type == "S3" and icon2.service_type == "CloudFront") or \
           (icon1.service_type == "CloudFront" and icon2.service_type == "S3"):
            # 速度を少し速くする（効率性を表現）- 上限あり
            VELOCITY_INCREASE_FACTOR = 1.1
            VELOCITY_MAX_MULTIPLIER = 2
            icon1.velocity = [min(v * VELOCITY_INCREASE_FACTOR, v * VELOCITY_MAX_MULTIPLIER if v > 0 else v * -VELOCITY_MAX_MULTIPLIER) for v in icon1.velocity]
            icon2.velocity = [min(v * VELOCITY_INCREASE_FACTOR, v * VELOCITY_MAX_MULTIPLIER if v > 0 else v * -VELOCITY_MAX_MULTIPLIER) for v in icon2.velocity]
            # 体力を少し回復（過度な回復を防ぐ）
            HEALTH_RECOVERY_AMOUNT = 0.1
            icon1.health = min(icon1.max_health, icon1.health + HEALTH_RECOVERY_AMOUNT)
            icon2.health = min(icon2.max_health, icon2.health + HEALTH_RECOVERY_AMOUNT)
        # S3とCloudFrontの補完関係
        if (icon1.service_type == "S3" and icon2.service_type == "CloudFront") or \
           (icon1.service_type == "CloudFront" and icon2.service_type == "S3"):
            # CloudFrontの速度を速くする（配信の高速化を表現）- 上限あり
            if icon1.service_type == "CloudFront":
                icon1.velocity = [min(v * 1.2, v * 2 if v > 0 else v * -2) for v in icon1.velocity]
            else:
                icon2.velocity = [min(v * 1.2, v * 2 if v > 0 else v * -2) for v in icon2.velocity]
    
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
import math

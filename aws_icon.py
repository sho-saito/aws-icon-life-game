#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import os
import random
import math
from constants import GAME_AREA_WIDTH, SCREEN_HEIGHT, ICON_COLORS

class AWSIcon(pygame.sprite.Sprite):
    """AWSサービスアイコンを表すクラス"""
    
    # 衝突と重なりに関する定数
    OVERLAP_THRESHOLD = 30  # 重なりすぎと判断する閾値（ピクセル）
    SEPARATION_FORCE = 0.5  # 分離力の基本強度
    STUCK_THRESHOLD = 60    # スタック状態と判断するフレーム数
    STUCK_FORCE_MULTIPLIER = 2.0  # スタック状態での分離力の倍率
    
    def __init__(self, service_type, position, velocity=None):
        super().__init__()
        self.service_type = service_type
        
        # アイコン画像の読み込み
        try:
            icon_path = f"assets/icons/{service_type.lower()}.png"
            if os.path.exists(icon_path):
                self.image = pygame.image.load(icon_path)
                self.image = pygame.transform.scale(self.image, (50, 50))
            else:
                raise pygame.error("Icon file not found")
        except pygame.error:
            # 画像が見つからない場合は代替の四角形を使用
            self.image = pygame.Surface((50, 50))
            self.image.fill(ICON_COLORS.get(service_type, (200, 200, 200)))
            font = pygame.font.SysFont(None, 20)
            text = font.render(service_type, True, (0, 0, 0))
            text_rect = text.get_rect(center=(25, 25))
            self.image.blit(text, text_rect)
        
        self.rect = self.image.get_rect()
        self.rect.center = position
        
        # 速度がない場合はランダムな速度を設定（最大速度を制限）
        self.max_velocity = 3.0  # 最大速度の設定
        if velocity is None:
            self.velocity = [random.uniform(-2, 2), random.uniform(-2, 2)]
        else:
            self.velocity = velocity
        
        # サービス固有の特性
        self.properties = {}
        
        # 相互作用可能なサービスリスト
        self.interactions = []
        
        # 体力（VPCがない場合のEC2など、依存関係の表現に使用）
        self.health = 100
        self.max_health = 100
        
        # 依存関係の設定
        self.dependencies = self._set_dependencies()
        
        # 選択状態
        self.selected = False
        
        # 依存関係が満たされているかのフラグ
        self.dependency_satisfied = False
        
        # 最後に相互作用したアイコン
        self.last_interaction = None
        self.interaction_timer = 0
        
        # 停止状態の管理
        self.is_stopped = False
        self.stop_timer = 0
        self.max_stop_time = 120  # 最大停止時間（フレーム数）
        
        # 重なり状態の管理
        self.overlapping_icons = {}  # {icon_id: icon} 形式で重なっているアイコンを追跡
        self.overlap_duration = {}   # {icon_id: frames} 形式で重なり継続フレーム数を追跡
        self.stuck = False           # スタック状態のフラグ
    
    def _set_dependencies(self):
        """サービスの依存関係を設定"""
        if self.service_type == "EC2":
            return ["VPC"]
        elif self.service_type == "Lambda":
            return ["IAM"]
        elif self.service_type == "RDS":
            return ["VPC"]
        elif self.service_type == "API Gateway":
            return ["Lambda"]
        elif self.service_type == "CloudFront":
            return ["S3"]
        elif self.service_type == "EBS":
            return ["EC2"]  # EBSはEC2に依存（EC2にアタッチされる）
        elif self.service_type == "AutoScaling":
            return ["EC2"]  # AutoScalingはEC2に依存
        return []
        
    def _handle_overlap(self, other_icon):
        """重なっているアイコンとの分離を処理する"""
        # 重なりの度合いを計算
        dx = self.rect.centerx - other_icon.rect.centerx
        dy = self.rect.centery - other_icon.rect.centery
        distance = math.sqrt(dx*dx + dy*dy)
        
        # アイコンの半径（簡易的に幅の半分を使用）
        radius = self.rect.width / 2
        
        # 重なりの度合いを計算（0なら完全に重なっている、radius*2なら接している）
        overlap = max(0, radius * 2 - distance)
        
        # 重なりが閾値を超えている場合、分離力を適用
        if overlap > self.OVERLAP_THRESHOLD:
            # 他のアイコンのIDを取得（Pythonのオブジェクトのidを使用）
            other_id = id(other_icon)
            
            # 重なり状態を記録
            if other_id not in self.overlapping_icons:
                self.overlapping_icons[other_id] = other_icon
                self.overlap_duration[other_id] = 0
            else:
                self.overlap_duration[other_id] += 1
            
            # スタック状態の判定（長時間重なっている場合）
            if self.overlap_duration[other_id] > self.STUCK_THRESHOLD:
                self.stuck = True
            
            # 分離力の計算（スタック状態ならより強い力で分離）
            separation_force = self.SEPARATION_FORCE
            if self.stuck:
                separation_force *= self.STUCK_FORCE_MULTIPLIER
            
            # 分離方向の計算（重なっているアイコンから離れる方向）
            if distance > 0:  # 0除算を防ぐ
                direction_x = dx / distance
                direction_y = dy / distance
            else:
                # 完全に重なっている場合はランダムな方向
                angle = random.uniform(0, 2 * math.pi)
                direction_x = math.cos(angle)
                direction_y = math.sin(angle)
            
            # 分離力を適用（速度に加算）
            self.velocity[0] += direction_x * separation_force * overlap / radius
            self.velocity[1] += direction_y * separation_force * overlap / radius
        else:
            # 重なりが解消された場合、記録から削除
            other_id = id(other_icon)
            if other_id in self.overlapping_icons:
                del self.overlapping_icons[other_id]
                del self.overlap_duration[other_id]
            
            # すべての重なりが解消されたらスタック状態を解除
            if not self.overlapping_icons:
                self.stuck = False
    def update(self, all_icons=None):
        """アイコンの状態を更新"""
        # サービスタイプ固有の動きパターンを適用
        self._apply_movement_pattern(all_icons)
        
        # 停止状態の管理
        if self.is_stopped:
            self.stop_timer += 1
            # 最大停止時間を超えたら再始動
            if self.stop_timer >= self.max_stop_time:
                self.is_stopped = False
                self.stop_timer = 0
                # ランダムな方向に再始動
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(0.5, 1.5)
                self.velocity = [
                    math.cos(angle) * speed,
                    math.sin(angle) * speed
                ]
        
        # 停止していない場合のみ移動
        if not self.is_stopped:
            # 移動
            self.rect.x += self.velocity[0]
            self.rect.y += self.velocity[1]
        
        # 速度の上限を制限
        self.velocity = [
            max(min(self.velocity[0], self.max_velocity), -self.max_velocity),
            max(min(self.velocity[1], self.max_velocity), -self.max_velocity)
        ]
        
        # 画面端での反射（ゲームエリア内のみ）
        if self.rect.left < 0 or self.rect.right > GAME_AREA_WIDTH:
            self.velocity[0] *= -1
        if self.rect.top < 0 or self.rect.bottom > SCREEN_HEIGHT:
            self.velocity[1] *= -1
        
        # ゲームエリア内に収める
        self.rect.left = max(0, min(self.rect.left, GAME_AREA_WIDTH - self.rect.width))
        self.rect.top = max(0, min(self.rect.top, SCREEN_HEIGHT - self.rect.height))
        
        # 重なっているアイコンとの分離処理
        if all_icons:
            for icon in all_icons:
                if icon != self and pygame.sprite.collide_rect(self, icon):
                    self._handle_overlap(icon)
        
        # 依存関係の確認と体力の更新
        if all_icons and self.dependencies:
            self.dependency_satisfied = False
            for icon in all_icons:
                if icon.service_type in self.dependencies and self._is_near(icon, 150):
                    self.dependency_satisfied = True
                    break
            
            # 依存関係が満たされていない場合、体力を減少
            if not self.dependency_satisfied:
                if self.service_type in ["EC2", "RDS", "API Gateway", "CloudFront"]:
                    self.health = max(0, self.health - 0.1)
            elif self.health < self.max_health:
                self.health = min(self.max_health, self.health + 0.05)
        
        # 相互作用タイマーの更新
        if self.interaction_timer > 0:
            self.interaction_timer -= 1

    def _is_near(self, other_icon, distance_threshold):
        """他のアイコンが近くにいるかを判定"""
        dx = self.rect.centerx - other_icon.rect.centerx
        dy = self.rect.centery - other_icon.rect.centery
        distance = math.sqrt(dx*dx + dy*dy)
        return distance < distance_threshold
    
    def draw(self, surface):
        """アイコンを描画"""
        # 通常の描画
        surface.blit(self.image, self.rect)
        
        # 選択状態の表示
        if self.selected:
            pygame.draw.rect(surface, (255, 255, 0), self.rect, 2)
        
        # 依存関係の表示
        if self.dependencies and not self.dependency_satisfied:
            pygame.draw.circle(surface, (255, 0, 0), self.rect.center, 30, 1)
        
        # 体力バーの表示
        if self.health < self.max_health:
            bar_width = 40
            bar_height = 5
            bar_x = self.rect.centerx - bar_width / 2
            bar_y = self.rect.bottom + 5
            
            # 背景（グレー）
            pygame.draw.rect(surface, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))
            
            # 体力（緑〜黄色〜赤）
            health_width = (self.health / self.max_health) * bar_width
            health_ratio = self.health / self.max_health
            
            if health_ratio > 0.6:
                color = (0, 255, 0)  # 緑
            elif health_ratio > 0.3:
                color = (255, 255, 0)  # 黄色
            else:
                color = (255, 0, 0)  # 赤
            
            pygame.draw.rect(surface, color, (bar_x, bar_y, health_width, bar_height))
        
        # 最近の相互作用の表示
        if self.last_interaction and self.interaction_timer > 0:
            pygame.draw.line(
                surface,
                (0, 0, 255),
                self.rect.center,
                self.last_interaction.rect.center,
                2
            )
    # API GatewayとLambdaの相互作用を管理するメソッド
    def _api_gateway_behavior(self, all_icons):
        """API Gatewayの振る舞いを管理する"""
        # API Gatewayの場合のみ実行
        if self.service_type != "API Gateway":
            return
            
        # API Gatewayの状態管理（初期化）
        if not hasattr(self, 'api_state'):
            self.api_state = 'patrol'  # 'patrol', 'connect', 'return'
            self.state_timer = 0
            self.target_lambda = None
            self.original_position = [self.rect.centerx, self.rect.centery]
            self.patrol_axis = random.choice(['x', 'y'])  # パトロール軸（x軸またはy軸）
            self.patrol_direction = random.choice([1, -1])  # パトロール方向（1: 正方向, -1: 負方向）
            self.patrol_range = [100, GAME_AREA_WIDTH - 100]  # パトロール範囲（x軸）
            if self.patrol_axis == 'y':
                self.patrol_range = [100, SCREEN_HEIGHT - 100]  # パトロール範囲（y軸）
            
        # 状態に応じた動作
        if self.api_state == 'patrol':
            # パトロール状態: 画面端付近を行き来する
            
            # 速度を中程度に保つ
            max_patrol_speed = 1.5
            
            # パトロール軸に沿って移動
            if self.patrol_axis == 'x':
                # x軸に沿ってパトロール
                self.velocity = [max_patrol_speed * self.patrol_direction, 0]
                
                # 範囲の端に到達したら方向転換
                if (self.rect.right >= self.patrol_range[1] and self.patrol_direction > 0) or \
                   (self.rect.left <= self.patrol_range[0] and self.patrol_direction < 0):
                    self.patrol_direction *= -1
            else:
                # y軸に沿ってパトロール
                self.velocity = [0, max_patrol_speed * self.patrol_direction]
                
                # 範囲の端に到達したら方向転換
                if (self.rect.bottom >= self.patrol_range[1] and self.patrol_direction > 0) or \
                   (self.rect.top <= self.patrol_range[0] and self.patrol_direction < 0):
                    self.patrol_direction *= -1
            
            # Lambdaを探して接続状態に移行
            if all_icons and random.random() < 0.02:  # 2%の確率でLambda探索
                lambda_icons = [icon for icon in all_icons if icon.service_type == "Lambda"]
                if lambda_icons:
                    # 制限を解除: 他のAPI Gatewayが接続しているLambdaも対象に含める
                    # ランダムにLambdaを選択
                    self.target_lambda = random.choice(lambda_icons)
                    self.api_state = 'connect'
                    self.state_timer = 0
                    # 現在位置を記憶
                    self.original_position = [self.rect.centerx, self.rect.centery]
        
        elif self.api_state == 'connect':
            # 接続状態: 選択したLambdaに向かって移動
            
            if self.target_lambda and self.target_lambda in all_icons:
                # Lambdaへの方向ベクトルを計算
                dx = self.target_lambda.rect.centerx - self.rect.centerx
                dy = self.target_lambda.rect.centery - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:  # 0除算を防ぐ
                    # 高速で移動（APIリクエストの転送を表現）
                    speed = 4.0
                    direction_x = dx / distance
                    direction_y = dy / distance
                    self.velocity = [direction_x * speed, direction_y * speed]
                
                # Lambdaに到達したら戻り状態に移行
                if distance < 30:
                    self.api_state = 'return'
                    self.state_timer = 0
                    
                    # Lambdaとの相互作用を記録
                    self.last_interaction = self.target_lambda
                    self.interaction_timer = 30
                    if hasattr(self.target_lambda, 'last_interaction'):
                        self.target_lambda.last_interaction = self
                        self.target_lambda.interaction_timer = 30
            else:
                # ターゲットのLambdaが見つからない場合、パトロール状態に戻る
                self.api_state = 'patrol'
                self.target_lambda = None
        
        elif self.api_state == 'return':
            # 戻り状態: 元の位置に戻る
            
            # 元の位置への方向ベクトルを計算
            dx = self.original_position[0] - self.rect.centerx
            dy = self.original_position[1] - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0:  # 0除算を防ぐ
                # 高速で移動（APIレスポンスの返送を表現）
                speed = 3.0
                direction_x = dx / distance
                direction_y = dy / distance
                self.velocity = [direction_x * speed, direction_y * speed]
            
            # 元の位置に到達したらパトロール状態に戻る
            if distance < 20:
                self.api_state = 'patrol'
                self.state_timer = 0
                self.target_lambda = None
                
                # パトロール方向をランダムに変更
                if random.random() < 0.5:
                    self.patrol_direction *= -1
                
                # 時々パトロール軸を変更
                if random.random() < 0.3:
                    self.patrol_axis = 'x' if self.patrol_axis == 'y' else 'y'
                    self.patrol_range = [100, GAME_AREA_WIDTH - 100]  # パトロール範囲（x軸）
                    if self.patrol_axis == 'y':
                        self.patrol_range = [100, SCREEN_HEIGHT - 100]  # パトロール範囲（y軸）


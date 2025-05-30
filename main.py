#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import sys
import os
import random
import math
from pygame.locals import *

# 定数
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
BACKGROUND_COLOR = (240, 240, 240)
TITLE = "AWS Icon Life"
UI_PANEL_WIDTH = 200  # 右側のUIパネル幅
GAME_AREA_WIDTH = SCREEN_WIDTH - UI_PANEL_WIDTH  # ゲームエリアの幅
UI_BACKGROUND_COLOR = (230, 230, 230)
UI_TEXT_COLOR = (50, 50, 50)
UI_BORDER_COLOR = (200, 200, 200)

# AWSアイコンの種類
AWS_ICONS = ["EC2", "S3", "VPC", "Lambda", "EBS", "RDS", "IAM", "DynamoDB", "API Gateway", "CloudFront"]

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
            color_map = {
                "EC2": (255, 153, 0),      # オレンジ
                "S3": (227, 86, 0),        # 赤っぽいオレンジ
                "VPC": (138, 180, 248),    # 水色
                "Lambda": (250, 146, 3),   # 濃いオレンジ
                "EBS": (255, 153, 153),    # ピンク
                "RDS": (0, 128, 128),      # ティール
                "IAM": (255, 215, 0),      # 金色
                "DynamoDB": (54, 150, 215),# 青
                "API Gateway": (150, 0, 150), # 紫
                "CloudFront": (255, 99, 71)  # トマト色
            }
            self.image.fill(color_map.get(service_type, (200, 200, 200)))
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
            
            # スタック状態の判定
            is_stuck = self.overlap_duration[other_id] > self.STUCK_THRESHOLD
            
            # 分離力の計算（重なりが大きいほど強い力を適用）
            force_magnitude = self.SEPARATION_FORCE * (overlap / radius)
            
            # スタック状態の場合、より強い分離力を適用
            if is_stuck:
                force_magnitude *= self.STUCK_FORCE_MULTIPLIER
                self.stuck = True
            
            # 方向ベクトルの計算（自分から相手への方向）
            if distance > 0:  # 0除算を防ぐ
                direction_x = dx / distance
                direction_y = dy / distance
            else:
                # 完全に重なっている場合はランダムな方向に分離
                angle = random.uniform(0, 2 * math.pi)
                direction_x = math.cos(angle)
                direction_y = math.sin(angle)
            
            # 分離力を適用（自分は相手から離れる方向、相手は自分から離れる方向）
            self.velocity[0] += direction_x * force_magnitude
            self.velocity[1] += direction_y * force_magnitude
            other_icon.velocity[0] -= direction_x * force_magnitude
            other_icon.velocity[1] -= direction_y * force_magnitude
            
            # スタック状態を脱するためのランダム要素を追加
            if is_stuck:
                random_angle = random.uniform(0, 2 * math.pi)
                random_force = random.uniform(0.1, 0.5)
                self.velocity[0] += math.cos(random_angle) * random_force
                self.velocity[1] += math.sin(random_angle) * random_force
                
                random_angle = random.uniform(0, 2 * math.pi)
                random_force = random.uniform(0.1, 0.5)
                other_icon.velocity[0] += math.cos(random_angle) * random_force
                other_icon.velocity[1] += math.sin(random_angle) * random_force
        else:
            # 重なりが閾値以下の場合、重なり状態をリセット
            other_id = id(other_icon)
            if other_id in self.overlapping_icons:
                del self.overlapping_icons[other_id]
                del self.overlap_duration[other_id]
                
                # すべての重なりが解消されたらスタック状態をリセット
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
    
    def _apply_movement_pattern(self, all_icons):
        """サービスタイプ固有の動きパターンを適用"""
        if self.service_type == "EC2":
            # EC2: 比較的直線的な動き、VPCの近くに留まろうとする傾向
            
            # 方向転換の確率を低く設定（直線的な動きを維持）
            if random.random() < 0.02:  # 2%の確率で方向転換
                angle = random.uniform(0, 2 * math.pi)
                speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                self.velocity = [
                    math.cos(angle) * speed,
                    math.sin(angle) * speed
                ]
            
            # VPCの近くに留まろうとする動き
            if all_icons:
                for icon in all_icons:
                    if icon.service_type == "VPC":
                        # VPCとの距離を計算
                        dx = icon.rect.centerx - self.rect.centerx
                        dy = icon.rect.centery - self.rect.centery
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance > 0:  # 0除算を防ぐ
                            # 距離が300px以上の場合、VPCに向かって強く引き寄せられる
                            if distance > 300:
                                # 引力の強さ（距離に反比例）- より強く
                                attraction = 0.15
                                # 正規化した方向ベクトル
                                direction_x = dx / distance
                                direction_y = dy / distance
                                
                                # 速度に引力を加える
                                self.velocity[0] += direction_x * attraction
                                self.velocity[1] += direction_y * attraction
                            # 距離が100px〜300pxの場合、弱い引力
                            elif distance > 100:
                                # 弱い引力
                                attraction = 0.08
                                direction_x = dx / distance
                                direction_y = dy / distance
                                self.velocity[0] += direction_x * attraction
                                self.velocity[1] += direction_y * attraction
        
        elif self.service_type == "S3":
            # S3: ゆっくりとした動き、あまり移動しない
            
            # 速度を常に低く保つ
            max_s3_speed = 1.0  # S3の最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_s3_speed and current_speed > 0:
                ratio = max_s3_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # ランダムに減速する確率
            if random.random() < 0.05:  # 5%の確率で減速
                self.velocity = [v * 0.9 for v in self.velocity]
            
            # 長時間同じ方向に動かないように、時々わずかに方向を変える
            if random.random() < 0.1:  # 10%の確率で方向微調整
                angle_change = random.uniform(-0.2, 0.2)  # 小さな角度変化
                speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                if speed > 0:
                    current_angle = math.atan2(self.velocity[1], self.velocity[0])
                    new_angle = current_angle + angle_change
                    self.velocity = [
                        math.cos(new_angle) * speed,
                        math.sin(new_angle) * speed
                    ]
            
            # 時々完全に停止する（停止状態管理を使用）
            if not self.is_stopped and random.random() < 0.01:  # 1%の確率で停止
                self.is_stopped = True
                self.stop_timer = 0
                self.velocity = [0, 0]
        
        elif self.service_type == "EBS":
            # EBS: EC2の近くに留まろうとする動き
            
            # 基本的な動きはS3と似ているが、より積極的にEC2を追いかける
            
            # 速度を中程度に保つ
            max_ebs_speed = 1.5  # EBSの最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_ebs_speed and current_speed > 0:
                ratio = max_ebs_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # EC2を探して近くに留まろうとする動き
            if all_icons:
                # 最も近いEC2を探す
                closest_ec2 = None
                min_distance = float('inf')
                
                for icon in all_icons:
                    if icon.service_type == "EC2":
                        dx = icon.rect.centerx - self.rect.centerx
                        dy = icon.rect.centery - self.rect.centery
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance < min_distance:
                            min_distance = distance
                            closest_ec2 = icon
                
                # 最も近いEC2が見つかった場合
                if closest_ec2:
                    dx = closest_ec2.rect.centerx - self.rect.centerx
                    dy = closest_ec2.rect.centery - self.rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance > 0:  # 0除算を防ぐ
                        # 距離に応じた引力の調整
                        if distance > 200:
                            # 遠い場合は強い引力
                            attraction = 0.2
                        elif distance > 100:
                            # 中距離の場合は中程度の引力
                            attraction = 0.1
                        elif distance > 50:
                            # 近い場合は弱い引力
                            attraction = 0.05
                        else:
                            # とても近い場合は引力なし（すでに十分近い）
                            attraction = 0
                        
                        # 引力を適用
                        if attraction > 0:
                            direction_x = dx / distance
                            direction_y = dy / distance
                            self.velocity[0] += direction_x * attraction
                            self.velocity[1] += direction_y * attraction
                            
                            # EC2の近くにいる場合、EC2と似た動きをする
                            if distance < 100:
                                # EC2の速度に少し影響される
                                self.velocity[0] = 0.8 * self.velocity[0] + 0.2 * closest_ec2.velocity[0]
                                self.velocity[1] = 0.8 * self.velocity[1] + 0.2 * closest_ec2.velocity[1]
            
            # 時々方向を変える（S3よりも頻度は低い）
            if random.random() < 0.05:  # 5%の確率で方向微調整
                angle_change = random.uniform(-0.3, 0.3)
                speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                if speed > 0:
                    current_angle = math.atan2(self.velocity[1], self.velocity[0])
                    new_angle = current_angle + angle_change
                    self.velocity = [
                        math.cos(new_angle) * speed,
                        math.sin(new_angle) * speed
                    ]
        
        elif self.service_type == "VPC":
            # VPC: 広い範囲をゆっくり移動、他のサービスを引き寄せる
            
            # 速度を低めに保つ（安定したネットワーク基盤を表現）
            max_vpc_speed = 0.8  # VPCの最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_vpc_speed and current_speed > 0:
                ratio = max_vpc_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # 円を描くような動きを強化
            # 毎フレームで少しずつ角度を変える（一定方向に）
            if not hasattr(self, 'rotation_direction'):
                # 初回のみ回転方向をランダムに決定（1: 時計回り, -1: 反時計回り）
                self.rotation_direction = random.choice([1, -1])
            
            # 角度変化量を調整（大きくして円運動を明確に）
            angle_change = 0.02 * self.rotation_direction  # 一定方向に回転
            
            speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            if speed > 0:
                current_angle = math.atan2(self.velocity[1], self.velocity[0])
                new_angle = current_angle + angle_change
                self.velocity = [
                    math.cos(new_angle) * speed,
                    math.sin(new_angle) * speed
                ]
            
            # 画面中央に向かう傾向（ネットワークの中心性を表現）
            center_x = GAME_AREA_WIDTH / 2
            center_y = SCREEN_HEIGHT / 2
            dx = center_x - self.rect.centerx
            dy = center_y - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0:  # 0除算を防ぐ
                # 中央からの距離に応じた引力
                if distance > 300:
                    # 遠い場合は強い引力
                    attraction = 0.02
                    direction_x = dx / distance
                    direction_y = dy / distance
                    self.velocity[0] += direction_x * attraction
                    self.velocity[1] += direction_y * attraction
            
            # 他のサービスを引き寄せる効果はEC2、RDS、Lambda側で実装
    
    def _is_near(self, other_icon, distance):
        """他のアイコンが指定した距離内にあるかを確認"""
        dx = self.rect.centerx - other_icon.rect.centerx
        dy = self.rect.centery - other_icon.rect.centery
        return (dx * dx + dy * dy) <= distance * distance
    
    def draw(self, surface):
        """アイコンを描画（選択状態や体力バーを含む）"""
        # 通常の描画
        surface.blit(self.image, self.rect)
        
        # 選択状態の表示
        if self.selected:
            pygame.draw.rect(surface, (255, 255, 0), self.rect.inflate(4, 4), 2)
        
        # スタック状態の視覚化（デバッグ用）
        if self.stuck:
            pygame.draw.rect(surface, (255, 0, 255), self.rect.inflate(8, 8), 1)  # マゼンタの枠
        
        # 依存関係の視覚化
        if self.dependencies:
            if self.dependency_satisfied:
                status_color = (0, 255, 0)  # 緑：依存関係満たされている
            else:
                status_color = (255, 0, 0)  # 赤：依存関係満たされていない
            pygame.draw.circle(surface, status_color, (self.rect.right - 5, self.rect.top + 5), 5)
        
        # 体力バーの表示（EC2など、依存関係のあるアイコンのみ）
        if self.dependencies:
            bar_width = 40
            bar_height = 5
            bar_x = self.rect.centerx - bar_width // 2
            bar_y = self.rect.bottom + 2
            
            # 背景（グレー）
            pygame.draw.rect(surface, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))
            
            # 体力（緑〜黄色〜赤）
            health_ratio = self.health / self.max_health
            if health_ratio > 0:
                health_width = int(bar_width * health_ratio)
                
                # 体力に応じた色（緑→黄色→赤）
                if health_ratio > 0.7:
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

class UIPanel:
    """ゲームのUIパネルを管理するクラス"""
    
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = pygame.font.SysFont(None, 24)
        self.small_font = pygame.font.SysFont(None, 20)
        self.selected_icon = None
        self.icon_counts = {icon_type: 0 for icon_type in AWS_ICONS}
    
    def update(self, all_icons, selected_icon):
        """UIパネルの状態を更新"""
        self.selected_icon = selected_icon
        
        # アイコン数のカウント
        self.icon_counts = {icon_type: 0 for icon_type in AWS_ICONS}
        for icon in all_icons:
            if icon.service_type in self.icon_counts:
                self.icon_counts[icon.service_type] += 1
    
    def draw(self, surface):
        """UIパネルを描画"""
        # パネル背景
        pygame.draw.rect(surface, UI_BACKGROUND_COLOR, self.rect)
        pygame.draw.rect(surface, UI_BORDER_COLOR, self.rect, 2)
        
        # タイトル
        title_text = self.font.render("AWS Icon Life", True, UI_TEXT_COLOR)
        surface.blit(title_text, (self.rect.x + 10, self.rect.y + 10))
        
        # 区切り線
        pygame.draw.line(
            surface,
            UI_BORDER_COLOR,
            (self.rect.x, self.rect.y + 40),
            (self.rect.right, self.rect.y + 40),
            2
        )
        
        # アイコン統計
        stats_title = self.font.render("Icon Statistics", True, UI_TEXT_COLOR)
        surface.blit(stats_title, (self.rect.x + 10, self.rect.y + 50))
        
        y_offset = 80
        for icon_type, count in self.icon_counts.items():
            text = self.small_font.render(f"{icon_type}: {count}", True, UI_TEXT_COLOR)
            surface.blit(text, (self.rect.x + 20, self.rect.y + y_offset))
            y_offset += 25
        
        # 区切り線
        pygame.draw.line(
            surface,
            UI_BORDER_COLOR,
            (self.rect.x, self.rect.y + y_offset),
            (self.rect.right, self.rect.y + y_offset),
            2
        )
        
        # 選択中のアイコン情報
        y_offset += 10
        info_title = self.font.render("Selected Icon", True, UI_TEXT_COLOR)
        surface.blit(info_title, (self.rect.x + 10, self.rect.y + y_offset))
        
        y_offset += 30
        if self.selected_icon:
            # アイコンタイプ
            type_text = self.small_font.render(f"Type: {self.selected_icon.service_type}", True, UI_TEXT_COLOR)
            surface.blit(type_text, (self.rect.x + 20, self.rect.y + y_offset))
            y_offset += 25
            
            # 体力
            health_text = self.small_font.render(
                f"Health: {int(self.selected_icon.health)}/{self.selected_icon.max_health}",
                True, UI_TEXT_COLOR
            )
            surface.blit(health_text, (self.rect.x + 20, self.rect.y + y_offset))
            y_offset += 25
            
            # 依存関係
            if self.selected_icon.dependencies:
                deps_text = self.small_font.render(
                    f"Depends on: {', '.join(self.selected_icon.dependencies)}",
                    True, UI_TEXT_COLOR
                )
                surface.blit(deps_text, (self.rect.x + 20, self.rect.y + y_offset))
                y_offset += 25
                
                status_text = self.small_font.render(
                    f"Status: {'Satisfied' if self.selected_icon.dependency_satisfied else 'Not Satisfied'}",
                    True, (0, 255, 0) if self.selected_icon.dependency_satisfied else (255, 0, 0)
                )
                surface.blit(status_text, (self.rect.x + 20, self.rect.y + y_offset))
            else:
                deps_text = self.small_font.render("Depends on: None", True, UI_TEXT_COLOR)
                surface.blit(deps_text, (self.rect.x + 20, self.rect.y + y_offset))
        else:
            no_selection = self.small_font.render("No icon selected", True, UI_TEXT_COLOR)
            surface.blit(no_selection, (self.rect.x + 20, self.rect.y + y_offset))
        
        # 操作説明
        y_offset = self.rect.height - 120
        help_title = self.font.render("Controls", True, UI_TEXT_COLOR)
        surface.blit(help_title, (self.rect.x + 10, self.rect.y + y_offset))
        
        y_offset += 30
        controls = [
            "Left Click: Place icon",
            "Right Click: Select icon",
            "Space: Random placement",
            "ESC: Exit"
        ]
        
        for control in controls:
            control_text = self.small_font.render(control, True, UI_TEXT_COLOR)
            surface.blit(control_text, (self.rect.x + 20, self.rect.y + y_offset))
            y_offset += 20

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
        
        # 初期アイコンの生成
        self._create_initial_icons()
    
    def _create_initial_icons(self):
        """初期アイコンを生成"""
        for service in AWS_ICONS:
            position = (random.randint(50, GAME_AREA_WIDTH - 50), 
                        random.randint(50, SCREEN_HEIGHT - 50))
            icon = AWSIcon(service, position)
            self.all_icons.add(icon)
    
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
                        # クリック位置に新しいアイコンを追加
                        service = random.choice(AWS_ICONS)
                        icon = AWSIcon(service, event.pos)
                        self.all_icons.add(icon)
                    elif event.button == 3:  # 右クリック
                        # アイコンの選択
                        self._select_icon_at_position(event.pos)
    
    def _select_icon_at_position(self, position):
        """指定位置のアイコンを選択"""
        # 以前の選択をクリア
        if self.selected_icon:
            self.selected_icon.selected = False
        
        self.selected_icon = None
        
        # 位置にあるアイコンを探す
        for icon in self.all_icons:
            if icon.rect.collidepoint(position):
                icon.selected = True
                self.selected_icon = icon
                break
    
    def update(self):
        """ゲーム状態の更新"""
        # アイコンの更新（全アイコンのリストを渡す）
        for icon in self.all_icons:
            icon.update(self.all_icons)
        
        # 衝突検出と相互作用
        self._handle_collisions()
        
        # UIパネルの更新
        self.ui_panel.update(self.all_icons, self.selected_icon)
        
        # 体力が0になったアイコンを削除（EC2など）
        for icon in list(self.all_icons):
            if hasattr(icon, 'health') and icon.health <= 0:
                self.all_icons.remove(icon)
                if self.selected_icon == icon:
                    self.selected_icon = None
    
    def _handle_collisions(self):
        """アイコン同士の衝突と相互作用を処理"""
        # すべてのアイコンペアをチェック
        icons = list(self.all_icons)
        for i, icon1 in enumerate(icons):
            for icon2 in icons[i+1:]:
                if pygame.sprite.collide_rect(icon1, icon2):
                    # 衝突時の反応（速度交換に加えて、少しランダム性を追加）
                    icon1.velocity[0], icon2.velocity[0] = icon2.velocity[0], icon1.velocity[0]
                    icon1.velocity[1], icon2.velocity[1] = icon2.velocity[1], icon1.velocity[1]
                    
                    # 衝突後に少しランダムな速度成分を追加して対称性を崩す
                    random_factor = 0.3
                    icon1.velocity[0] += random.uniform(-random_factor, random_factor)
                    icon1.velocity[1] += random.uniform(-random_factor, random_factor)
                    icon2.velocity[0] += random.uniform(-random_factor, random_factor)
                    icon2.velocity[1] += random.uniform(-random_factor, random_factor)
                    
                    # 相互作用の記録
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
    
    def _handle_complementary_relations(self, icon1, icon2):
        """補完関係の処理"""
        # EC2とEBSの補完関係
        if (icon1.service_type == "EC2" and icon2.service_type == "EBS") or \
           (icon1.service_type == "EBS" and icon2.service_type == "EC2"):
            # 両方のアイコンの速度を少し遅くする（安定性を表現）
            icon1.velocity = [v * 0.9 for v in icon1.velocity]
            icon2.velocity = [v * 0.9 for v in icon2.velocity]
            # 体力を回復
            icon1.health = min(icon1.max_health, icon1.health + 2)
            icon2.health = min(icon2.max_health, icon2.health + 2)
        
        # LambdaとDynamoDBの補完関係
        if (icon1.service_type == "Lambda" and icon2.service_type == "DynamoDB") or \
           (icon1.service_type == "DynamoDB" and icon2.service_type == "Lambda"):
            # 両方のアイコンの速度を少し速くする（効率性を表現）- 上限あり
            icon1.velocity = [min(v * 1.1, v * 2 if v > 0 else v * -2) for v in icon1.velocity]
            icon2.velocity = [min(v * 1.1, v * 2 if v > 0 else v * -2) for v in icon2.velocity]
            # 体力を回復
            icon1.health = min(icon1.max_health, icon1.health + 2)
            icon2.health = min(icon2.max_health, icon2.health + 2)
        
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

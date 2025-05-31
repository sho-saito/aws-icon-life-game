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
            
            # 速度を低めに保つ
            max_s3_speed = 1.0  # S3の最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_s3_speed and current_speed > 0:
                ratio = max_s3_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # 時々方向を変える（ランダムな小さな変化）
            if random.random() < 0.1:  # 10%の確率で方向微調整
                angle_change = random.uniform(-0.5, 0.5)
                speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                if speed > 0:
                    current_angle = math.atan2(self.velocity[1], self.velocity[0])
                    new_angle = current_angle + angle_change
                    self.velocity = [
                        math.cos(new_angle) * speed,
                        math.sin(new_angle) * speed
                    ]
            
            # 時々停止する（データアクセスの待機を表現）
            if random.random() < 0.01 and not self.is_stopped:  # 1%の確率で停止
                self.is_stopped = True
                self.stop_timer = 0
                self.max_stop_time = random.randint(30, 90)  # 0.5〜1.5秒の停止
        
        elif self.service_type == "EBS":
            # EBS: EC2の近くに留まろうとする動き
            
            # 速度を低めに保つ
            max_ebs_speed = 1.2  # EBSの最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_ebs_speed and current_speed > 0:
                ratio = max_ebs_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # 時々方向を変える
            if random.random() < 0.05:  # 5%の確率で方向転換
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(0.5, 1.2)
                self.velocity = [
                    math.cos(angle) * speed,
                    math.sin(angle) * speed
                ]
            
            # 最も近いEC2を探し、その近くに留まろうとする
            if all_icons:
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
                
                # 最も近いEC2が見つかった場合、その方向に引き寄せられる
                if closest_ec2:
                    dx = closest_ec2.rect.centerx - self.rect.centerx
                    dy = closest_ec2.rect.centery - self.rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance > 0:  # 0除算を防ぐ
                        # 引力の強さ（距離に反比例）
                        attraction = min(0.2, 50 / distance)  # 最大0.2、距離が近いほど弱く
                        
                        # 正規化した方向ベクトル
                        direction_x = dx / distance
                        direction_y = dy / distance
                        self.velocity[0] += direction_x * attraction
                        self.velocity[1] += direction_y * attraction
                        
                        # EC2の近くにいる場合、EC2と似た動きをする
                        if distance < 100:
                            # EC2の速度に少し影響される
                            self.velocity[0] = 0.8 * self.velocity[0] + 0.2 * closest_ec2.velocity[0]
                            self.velocity[1] = 0.8 * self.velocity[1] + 0.2 * closest_ec2.velocity[1]
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

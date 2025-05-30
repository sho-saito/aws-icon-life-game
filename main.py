#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import sys
import os
import random
import math
from pygame.locals import *

# 定数
SCREEN_WIDTH = 850  # 画面の幅を800から850に増加
SCREEN_HEIGHT = 650  # 画面の高さを600から650に増加
FPS = 60
BACKGROUND_COLOR = (240, 240, 240)
TITLE = "AWS Icon Life"
UI_PANEL_WIDTH = 250  # 右側のUIパネル幅を200から250に増加
GAME_AREA_WIDTH = SCREEN_WIDTH - UI_PANEL_WIDTH  # ゲームエリアの幅
UI_BACKGROUND_COLOR = (230, 230, 230)
UI_TEXT_COLOR = (50, 50, 50)
UI_BORDER_COLOR = (200, 200, 200)
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
        
        elif self.service_type == "Lambda":
            # Lambda: 素早く不規則な動き、短い距離を素早く移動して停止するパターン
            
            # Lambdaの状態管理（初期化）
            if not hasattr(self, 'lambda_state'):
                self.lambda_state = 'idle'  # 'idle', 'burst', 'cooldown'
                self.state_timer = 0
                self.burst_direction = [0, 0]
                self.burst_duration = 0
                self.cooldown_duration = 0
            
            # 状態に応じた動作
            if self.lambda_state == 'idle':
                # アイドル状態: ゆっくり動く、バーストの準備
                
                # 速度を低めに保つ
                max_idle_speed = 0.8
                current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                if current_speed > max_idle_speed and current_speed > 0:
                    ratio = max_idle_speed / current_speed
                    self.velocity = [v * ratio for v in self.velocity]
                
                # 時々方向を変える
                if random.random() < 0.1:  # 10%の確率で方向転換
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(0.3, 0.8)
                    self.velocity = [
                        math.cos(angle) * speed,
                        math.sin(angle) * speed
                    ]
                
                # バースト状態に移行する確率
                if random.random() < 0.03:  # 3%の確率でバースト状態に移行
                    self.lambda_state = 'burst'
                    self.state_timer = 0
                    
                    # バーストの方向と速度を決定
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(3.0, 5.0)  # 高速
                    self.burst_direction = [
                        math.cos(angle) * speed,
                        math.sin(angle) * speed
                    ]
                    
                    # バーストの持続時間を決定（10〜20フレーム = 約0.2〜0.3秒）
                    self.burst_duration = random.randint(10, 20)
            
            elif self.lambda_state == 'burst':
                # バースト状態: 高速で直線移動
                
                # バースト方向に高速移動
                self.velocity = self.burst_direction.copy()
                
                # タイマー更新
                self.state_timer += 1
                
                # バースト終了判定
                if self.state_timer >= self.burst_duration:
                    self.lambda_state = 'cooldown'
                    self.state_timer = 0
                    self.velocity = [0, 0]  # 停止
                    
                    # クールダウン時間を決定（30〜60フレーム = 約0.5〜1秒）
                    self.cooldown_duration = random.randint(30, 60)
            
            elif self.lambda_state == 'cooldown':
                # クールダウン状態: 停止または非常に遅い動き
                
                # 速度を非常に低く保つ
                self.velocity = [v * 0.9 for v in self.velocity]
                
                # タイマー更新
                self.state_timer += 1
                
                # クールダウン終了判定
                if self.state_timer >= self.cooldown_duration:
                    self.lambda_state = 'idle'
                    self.state_timer = 0
                    
                    # アイドル状態に戻る際の初期速度
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(0.3, 0.8)
                    self.velocity = [
                        math.cos(angle) * speed,
                        math.sin(angle) * speed
                    ]
            
            # IAMを探して近くに留まろうとする動き（依存関係）
            if all_icons and not self.is_stopped:
                for icon in all_icons:
                    if icon.service_type == "IAM":
                        # IAMとの距離を計算
                        dx = icon.rect.centerx - self.rect.centerx
                        dy = icon.rect.centery - self.rect.centery
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance > 0:  # 0除算を防ぐ
                            # 距離が300px以上の場合、IAMに向かって引き寄せられる
                            if distance > 300:
                                # 引力の強さ（距離に反比例）
                                attraction = 0.1
                                # 正規化した方向ベクトル
                                direction_x = dx / distance
                                direction_y = dy / distance
                                
                                # 速度に引力を加える（バースト中は引力の影響を受けない）
                                if self.lambda_state != 'burst':
                                    self.velocity[0] += direction_x * attraction
                                    self.velocity[1] += direction_y * attraction
        
        elif self.service_type == "DynamoDB":
            # DynamoDB: ランダムな方向転換を頻繁に行い、高いスケーラビリティと分散性を表現
            
            # 速度を中程度に保つ
            max_dynamo_speed = 2.0  # DynamoDBの最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_dynamo_speed and current_speed > 0:
                ratio = max_dynamo_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # 頻繁に方向を変える（ランダムアクセスパターンを表現）
            if random.random() < 0.15:  # 15%の確率で方向転換
                # 方向転換の角度を決定（小さな変化から大きな変化まで）
                angle_change = random.uniform(-math.pi/2, math.pi/2)  # ±90度
                
                speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                if speed > 0:
                    current_angle = math.atan2(self.velocity[1], self.velocity[0])
                    new_angle = current_angle + angle_change
                    self.velocity = [
                        math.cos(new_angle) * speed,
                        math.sin(new_angle) * speed
                    ]
            
            # 時々速度を急に変える（バーストキャパシティを表現）
            if random.random() < 0.05:  # 5%の確率で速度変化
                # 速度の変化量を決定（加速または減速）
                speed_change = random.uniform(0.5, 2.0)
                
                # 加速または減速を決定
                if random.random() < 0.5:  # 50%の確率で加速
                    self.velocity = [v * speed_change for v in self.velocity]
                else:  # 50%の確率で減速
                    self.velocity = [v / speed_change for v in self.velocity]
            
            # 時々短い距離を素早く移動（読み取り/書き込みオペレーションを表現）
            if random.random() < 0.02:  # 2%の確率でバースト移動
                # 現在の速度を保存
                original_velocity = self.velocity.copy()
                
                # バースト方向と速度を決定
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(2.5, 4.0)  # 高速
                self.velocity = [
                    math.cos(angle) * speed,
                    math.sin(angle) * speed
                ]
                
                # 10フレーム後に元の速度に戻す処理を予約
                # （実際のゲームエンジンによっては異なる実装が必要）
                def restore_velocity():
                    self.velocity = original_velocity
                
                # 注意: この実装はタイマーを使用していないため、実際には機能しません
                # 実際の実装では、状態管理やタイマーを使用する必要があります
                
            # 画面全体に分散する傾向（分散データベースの特性を表現）
            # 画面の端に近づくと、中央方向への弱い引力が発生
            edge_margin = 100  # 画面端からの距離
            center_x = GAME_AREA_WIDTH / 2
            center_y = SCREEN_HEIGHT / 2
            
            # 画面端に近い場合、中央方向への弱い引力を加える
            if (self.rect.left < edge_margin or 
                self.rect.right > GAME_AREA_WIDTH - edge_margin or 
                self.rect.top < edge_margin or 
                self.rect.bottom > SCREEN_HEIGHT - edge_margin):
                
                dx = center_x - self.rect.centerx
                dy = center_y - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:  # 0除算を防ぐ
                    # 引力の強さ（弱い）
                    attraction = 0.03
                    # 正規化した方向ベクトル
                    direction_x = dx / distance
                    direction_y = dy / distance
                    
                    # 速度に引力を加える
                    self.velocity[0] += direction_x * attraction
                    self.velocity[1] += direction_y * attraction
        
        elif self.service_type == "API Gateway":
            # API Gateway: 入り口（画面端）付近を行き来する動き、Lambdaとの連携を表現
            
            # API Gatewayの状態管理（初期化）
            if not hasattr(self, 'api_state'):
                self.api_state = 'patrol'  # 'patrol', 'connect', 'return'
                self.state_timer = 0
                self.target_lambda = None
                self.original_position = [self.rect.centerx, self.rect.centery]
                self.patrol_direction = 1  # 1: 右/下方向, -1: 左/上方向
                self.patrol_axis = random.choice(['x', 'y'])  # x軸またはy軸に沿ってパトロール
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
                        # 他のAPI Gatewayが既に接続しているLambdaを除外
                        available_lambdas = []
                        for lambda_icon in lambda_icons:
                            # このLambdaに接近しているAPI Gatewayがあるか確認
                            has_approaching_gateway = False
                            for icon in all_icons:
                                if (icon != self and 
                                    icon.service_type == "API Gateway" and 
                                    hasattr(icon, 'api_state') and 
                                    icon.api_state in ['connect', 'return'] and 
                                    hasattr(icon, 'target_lambda') and 
                                    icon.target_lambda == lambda_icon):
                                    has_approaching_gateway = True
                                    break
                            
                            # 接近しているAPI Gatewayがなければ利用可能
                            if not has_approaching_gateway:
                                available_lambdas.append(lambda_icon)
                        
                        # 利用可能なLambdaがあれば選択
                        if available_lambdas:
                            self.target_lambda = random.choice(available_lambdas)
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
        
        elif self.service_type == "RDS":
            # RDS: 安定した円形の動き、VPCへの依存関係を表現
            
            # RDSの状態管理（初期化）
            if not hasattr(self, 'rds_state'):
                self.rds_state = 'normal'  # 'normal', 'backup'
                self.state_timer = 0
                self.orbit_center = None
                self.orbit_radius = random.randint(50, 100)
                self.orbit_speed = random.uniform(0.01, 0.02)  # 角速度（ラジアン/フレーム）
                self.orbit_angle = random.uniform(0, 2 * math.pi)
                self.orbit_direction = random.choice([1, -1])  # 1: 時計回り, -1: 反時計回り
            
            # 速度を低めに保つ（安定したデータベースを表現）
            max_rds_speed = 1.0  # RDSの最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_rds_speed and current_speed > 0:
                ratio = max_rds_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # VPCを探して近くに留まろうとする動き（依存関係）
            vpc_found = False
            if all_icons:
                for icon in all_icons:
                    if icon.service_type == "VPC":
                        vpc_found = True
                        # VPCを軌道の中心として設定
                        if self.orbit_center is None:
                            self.orbit_center = [icon.rect.centerx, icon.rect.centery]
                        
                        # 軌道中心の更新（VPCの位置に徐々に追従）
                        target_center = [icon.rect.centerx, icon.rect.centery]
                        self.orbit_center = [
                            self.orbit_center[0] + (target_center[0] - self.orbit_center[0]) * 0.01,
                            self.orbit_center[1] + (target_center[1] - self.orbit_center[1]) * 0.01
                        ]
                        
                        # 軌道上の目標位置を計算
                        self.orbit_angle += self.orbit_speed * self.orbit_direction
                        target_x = self.orbit_center[0] + math.cos(self.orbit_angle) * self.orbit_radius
                        target_y = self.orbit_center[1] + math.sin(self.orbit_angle) * self.orbit_radius
                        
                        # 目標位置への方向ベクトルを計算
                        dx = target_x - self.rect.centerx
                        dy = target_y - self.rect.centery
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance > 0:  # 0除算を防ぐ
                            # 目標位置に向かって移動
                            speed = min(distance * 0.1, max_rds_speed)  # 距離に応じた速度（最大値制限）
                            direction_x = dx / distance
                            direction_y = dy / distance
                            self.velocity = [direction_x * speed, direction_y * speed]
                        
                        # 依存関係の満足状態を更新
                        if self._is_near(icon, 150):
                            self.dependency_satisfied = True
                        break
            
            # VPCが見つからない場合、中央に向かう
            if not vpc_found:
                self.dependency_satisfied = False
                center_x = GAME_AREA_WIDTH / 2
                center_y = SCREEN_HEIGHT / 2
                
                # 軌道中心を画面中央に設定
                if self.orbit_center is None:
                    self.orbit_center = [center_x, center_y]
                
                # 軌道中心の更新（画面中央に徐々に移動）
                self.orbit_center = [
                    self.orbit_center[0] + (center_x - self.orbit_center[0]) * 0.01,
                    self.orbit_center[1] + (center_y - self.orbit_center[1]) * 0.01
                ]
                
                # 軌道上の目標位置を計算
                self.orbit_angle += self.orbit_speed * self.orbit_direction
                target_x = self.orbit_center[0] + math.cos(self.orbit_angle) * self.orbit_radius
                target_y = self.orbit_center[1] + math.sin(self.orbit_angle) * self.orbit_radius
                
                # 目標位置への方向ベクトルを計算
                dx = target_x - self.rect.centerx
                dy = target_y - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:  # 0除算を防ぐ
                    # 目標位置に向かって移動
                    speed = min(distance * 0.1, max_rds_speed)  # 距離に応じた速度（最大値制限）
                    direction_x = dx / distance
                    direction_y = dy / distance
                    self.velocity = [direction_x * speed, direction_y * speed]
            
            # 時々バックアップ状態に移行（データベースバックアップを表現）
            if self.rds_state == 'normal' and random.random() < 0.005:  # 0.5%の確率でバックアップ状態に移行
                self.rds_state = 'backup'
                self.state_timer = 0
                # バックアップ中は一時的に速度を下げる
                self.velocity = [v * 0.3 for v in self.velocity]
            
            # バックアップ状態の処理
            if self.rds_state == 'backup':
                # バックアップ中は速度を低く保つ
                self.velocity = [v * 0.95 for v in self.velocity]
                
                # タイマー更新
                self.state_timer += 1
                
                # バックアップ終了判定（約2秒）
                if self.state_timer >= 120:
                    self.rds_state = 'normal'
                    self.state_timer = 0
        
        elif self.service_type == "CloudFront":
            # CloudFront: 広範囲をカバーする動き、S3の近くに留まろうとする傾向
            
            # CloudFrontの状態管理（初期化）
            if not hasattr(self, 'cloudfront_state'):
                self.cloudfront_state = 'normal'  # 'normal', 'distribute'
                self.state_timer = 0
                self.target_s3 = None
                self.distribution_points = []
                self.current_point_index = 0
                self.point_reached = False
                self.distribution_speed = 3.0
                self.normal_speed = 1.8
            
            # 基本速度を中高速に保つ（CDNの高速性を表現）
            max_cf_speed = self.distribution_speed if self.cloudfront_state == 'distribute' else self.normal_speed
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_cf_speed and current_speed > 0:
                ratio = max_cf_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # 状態に応じた動作
            if self.cloudfront_state == 'normal':
                # 通常状態: 広範囲をカバーする動き、S3を探す
                
                # S3を探して近くに留まろうとする動き
                s3_found = False
                if all_icons:
                    for icon in all_icons:
                        if icon.service_type == "S3":
                            s3_found = True
                            self.target_s3 = icon
                            
                            # S3との距離を計算
                            dx = icon.rect.centerx - self.rect.centerx
                            dy = icon.rect.centery - self.rect.centery
                            distance = math.sqrt(dx*dx + dy*dy)
                            
                            if distance > 0:  # 0除算を防ぐ
                                # 距離に応じた引力の調整
                                if distance > 200:
                                    # 遠い場合は強い引力
                                    attraction = 0.1
                                    direction_x = dx / distance
                                    direction_y = dy / distance
                                    self.velocity[0] += direction_x * attraction
                                    self.velocity[1] += direction_y * attraction
                                elif distance > 100:
                                    # 中距離の場合は弱い引力
                                    attraction = 0.05
                                    direction_x = dx / distance
                                    direction_y = dy / distance
                                    self.velocity[0] += direction_x * attraction
                                    self.velocity[1] += direction_y * attraction
                            
                            # S3の近くにいる場合、時々配信状態に移行
                            if distance < 150 and random.random() < 0.01:  # 1%の確率で配信状態に移行
                                self.cloudfront_state = 'distribute'
                                self.state_timer = 0
                                
                                # 配信ポイントを生成（画面の四隅付近にランダムに配置）
                                self.distribution_points = []
                                num_points = random.randint(3, 5)  # 3〜5箇所の配信ポイント
                                
                                # 画面を4つの領域に分割し、各領域にポイントを配置
                                regions = [
                                    (0, 0, GAME_AREA_WIDTH/2, SCREEN_HEIGHT/2),  # 左上
                                    (GAME_AREA_WIDTH/2, 0, GAME_AREA_WIDTH, SCREEN_HEIGHT/2),  # 右上
                                    (0, SCREEN_HEIGHT/2, GAME_AREA_WIDTH/2, SCREEN_HEIGHT),  # 左下
                                    (GAME_AREA_WIDTH/2, SCREEN_HEIGHT/2, GAME_AREA_WIDTH, SCREEN_HEIGHT)  # 右下
                                ]
                                
                                # 使用する領域をランダムに選択
                                selected_regions = random.sample(regions, min(num_points, len(regions)))
                                
                                # 各領域内にランダムなポイントを生成
                                for region in selected_regions:
                                    x = random.uniform(region[0] + 50, region[2] - 50)
                                    y = random.uniform(region[1] + 50, region[3] - 50)
                                    self.distribution_points.append((x, y))
                                
                                # 最初のポイントへ向かう
                                self.current_point_index = 0
                                self.point_reached = False
                            break
                
                # S3が見つからない場合、広範囲をカバーする動き
                if not s3_found:
                    # 時々方向を変える（広範囲をカバー）
                    if random.random() < 0.03:  # 3%の確率で方向転換
                        angle_change = random.uniform(-math.pi/4, math.pi/4)  # ±45度
                        speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                        if speed > 0:
                            current_angle = math.atan2(self.velocity[1], self.velocity[0])
                            new_angle = current_angle + angle_change
                            self.velocity = [
                                math.cos(new_angle) * speed,
                                math.sin(new_angle) * speed
                            ]
                    
                    # 画面端に近づくと反射角度を大きくする（中央に戻りやすくする）
                    edge_margin = 100
                    if (self.rect.left < edge_margin or 
                        self.rect.right > GAME_AREA_WIDTH - edge_margin or 
                        self.rect.top < edge_margin or 
                        self.rect.bottom > SCREEN_HEIGHT - edge_margin):
                        
                        # 画面中央への方向ベクトル
                        center_x = GAME_AREA_WIDTH / 2
                        center_y = SCREEN_HEIGHT / 2
                        dx = center_x - self.rect.centerx
                        dy = center_y - self.rect.centery
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance > 0:  # 0除算を防ぐ
                            # 中央方向への引力
                            attraction = 0.05
                            direction_x = dx / distance
                            direction_y = dy / distance
                            self.velocity[0] += direction_x * attraction
                            self.velocity[1] += direction_y * attraction
            
            elif self.cloudfront_state == 'distribute':
                # 配信状態: 配信ポイントを順番に巡回
                
                if self.distribution_points and self.current_point_index < len(self.distribution_points):
                    # 現在の目標ポイント
                    target_x, target_y = self.distribution_points[self.current_point_index]
                    
                    # 目標ポイントへの方向ベクトルを計算
                    dx = target_x - self.rect.centerx
                    dy = target_y - self.rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance > 0:  # 0除算を防ぐ
                        # 高速で移動（コンテンツ配信の高速性を表現）
                        speed = self.distribution_speed
                        direction_x = dx / distance
                        direction_y = dy / distance
                        self.velocity = [direction_x * speed, direction_y * speed]
                    
                    # ポイントに到達したら次のポイントへ
                    if distance < 20:
                        self.current_point_index += 1
                        
                        # すべてのポイントを巡回したら、S3に戻る
                        if self.current_point_index >= len(self.distribution_points):
                            if self.target_s3 and self.target_s3 in all_icons:
                                # S3への方向ベクトルを計算
                                dx = self.target_s3.rect.centerx - self.rect.centerx
                                dy = self.target_s3.rect.centery - self.rect.centery
                                distance = math.sqrt(dx*dx + dy*dy)
                                
                                if distance > 0:  # 0除算を防ぐ
                                    # 高速で移動（コンテンツ取得の高速性を表現）
                                    speed = self.distribution_speed
                                    direction_x = dx / distance
                                    direction_y = dy / distance
                                    self.velocity = [direction_x * speed, direction_y * speed]
                            else:
                                # S3が見つからない場合、通常状態に戻る
                                self.cloudfront_state = 'normal'
                                self.state_timer = 0
                else:
                    # S3に戻った後、通常状態に移行
                    if self.target_s3 and self.target_s3 in all_icons:
                        dx = self.target_s3.rect.centerx - self.rect.centerx
                        dy = self.target_s3.rect.centery - self.rect.centery
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance < 50:  # S3に十分近づいたら通常状態に戻る
                            self.cloudfront_state = 'normal'
                            self.state_timer = 0
                            
                            # S3との相互作用を記録
                            self.last_interaction = self.target_s3
                            self.interaction_timer = 30
                            if hasattr(self.target_s3, 'last_interaction'):
                                self.target_s3.last_interaction = self
                                self.target_s3.interaction_timer = 30
                    else:
                        # S3が見つからない場合、通常状態に戻る
                        self.cloudfront_state = 'normal'
                        self.state_timer = 0
        
        elif self.service_type == "IAM":
            # IAM: 中央に留まる傾向、他のサービスとの接続はしない
            
            # IAMの状態管理（初期化）
            if not hasattr(self, 'iam_state'):
                self.iam_state = 'central'
                self.central_position = [GAME_AREA_WIDTH / 2, SCREEN_HEIGHT / 2]
                self.central_radius = random.randint(30, 80)  # 中央付近での移動半径
                self.central_angle = random.uniform(0, 2 * math.pi)
                self.central_speed = random.uniform(0.005, 0.015)  # 角速度（ラジアン/フレーム）
                self.central_direction = random.choice([1, -1])  # 1: 時計回り, -1: 反時計回り
            
            # 速度を低めに保つ（安定したサービスを表現）
            max_iam_speed = 1.2  # IAMの最大速度
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            
            # 現在の速度が最大速度を超えている場合、速度を下げる
            if current_speed > max_iam_speed and current_speed > 0:
                ratio = max_iam_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # 中央付近での軌道運動
            self.central_angle += self.central_speed * self.central_direction
            target_x = self.central_position[0] + math.cos(self.central_angle) * self.central_radius
            target_y = self.central_position[1] + math.sin(self.central_angle) * self.central_radius
            
            # 目標位置への方向ベクトルを計算
            dx = target_x - self.rect.centerx
            dy = target_y - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0:  # 0除算を防ぐ
                # 目標位置に向かって移動
                speed = min(distance * 0.1, max_iam_speed)  # 距離に応じた速度（最大値制限）
                direction_x = dx / distance
                direction_y = dy / distance
                self.velocity = [direction_x * speed, direction_y * speed]
            
            # 画面中央から大きく離れないようにする強い引力
            center_x = GAME_AREA_WIDTH / 2
            center_y = SCREEN_HEIGHT / 2
            dx = center_x - self.rect.centerx
            dy = center_y - self.rect.centery
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 200:  # 中央から200px以上離れた場合
                # 強い中央への引力
                attraction = 0.1
                direction_x = dx / distance
                direction_y = dy / distance
                self.velocity[0] += direction_x * attraction
                self.velocity[1] += direction_y * attraction
    
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
class ProgressSystem:
    """ゲームの進行状況を管理するクラス"""
    
    def __init__(self):
        # 依存関係の達成状況
        self.dependency_achievements = {
            "EC2-VPC": {"achieved": False, "description": "EC2 exists in VPC"},
            "Lambda-IAM": {"achieved": False, "description": "Lambda has IAM role"},
            "RDS-VPC": {"achieved": False, "description": "RDS exists in VPC"},
            "API Gateway-Lambda": {"achieved": False, "description": "API Gateway connected to Lambda"},
            "CloudFront-S3": {"achieved": False, "description": "CloudFront connected to S3"},
            "EBS-EC2": {"achieved": False, "description": "EBS attached to EC2"}
        }
        
        # 補完関係の達成状況
        self.complementary_achievements = {
            "EC2-EBS": {"achieved": False, "description": "EC2 and EBS integration"},
            "Lambda-DynamoDB": {"achieved": False, "description": "Lambda and DynamoDB integration"},
            "S3-CloudFront": {"achieved": False, "description": "S3 and CloudFront integration"}
        }
        
        # 通知メッセージのキュー
        self.notifications = []
        self.notification_duration = 180  # 通知表示フレーム数（約3秒）
        self.notification_timers = {}  # 通知ごとのタイマー
    
    def check_achievements(self, all_icons):
        """アイコン間の関係を確認し、達成状況を更新"""
        # 依存関係の確認
        self._check_dependencies(all_icons)
        
        # 補完関係の確認
        self._check_complementary_relations(all_icons)
    
    def _check_dependencies(self, all_icons):
        """依存関係の達成状況を確認"""
        # EC2-VPC
        self._check_dependency_pair(all_icons, "EC2", "VPC", "EC2-VPC")
        
        # Lambda-IAM
        self._check_dependency_pair(all_icons, "Lambda", "IAM", "Lambda-IAM")
        
        # RDS-VPC
        self._check_dependency_pair(all_icons, "RDS", "VPC", "RDS-VPC")
        
        # API Gateway-Lambda
        self._check_dependency_pair(all_icons, "API Gateway", "Lambda", "API Gateway-Lambda")
        
        # CloudFront-S3
        self._check_dependency_pair(all_icons, "CloudFront", "S3", "CloudFront-S3")
        
        # EBS-EC2
        self._check_dependency_pair(all_icons, "EBS", "EC2", "EBS-EC2")
    
    def _check_complementary_relations(self, all_icons):
        """補完関係の達成状況を確認"""
        # EC2-EBS
        self._check_complementary_pair(all_icons, "EC2", "EBS", "EC2-EBS")
        
        # Lambda-DynamoDB
        self._check_complementary_pair(all_icons, "Lambda", "DynamoDB", "Lambda-DynamoDB")
        
        # S3-CloudFront
        self._check_complementary_pair(all_icons, "S3", "CloudFront", "S3-CloudFront")
    
    def _check_dependency_pair(self, all_icons, service1, service2, achievement_key):
        """特定の依存関係が満たされているかを確認"""
        service1_icons = [icon for icon in all_icons if icon.service_type == service1]
        service2_icons = [icon for icon in all_icons if icon.service_type == service2]
        
        # 両方のサービスが存在する場合のみチェック
        if service1_icons and service2_icons:
            # 依存関係が満たされているかを確認（近接しているか）
            for icon1 in service1_icons:
                for icon2 in service2_icons:
                    if icon1._is_near(icon2, 150):  # 150pxの距離内にあるか
                        # まだ達成されていない場合、通知を追加
                        if not self.dependency_achievements[achievement_key]["achieved"]:
                            self.dependency_achievements[achievement_key]["achieved"] = True
                            description = self.dependency_achievements[achievement_key]["description"]
                            self.add_notification(f"Dependency Achieved: {description}")
                        return
            
            # 近接していない場合でも、達成状態はリセットしない
            # 一度達成したものは永続的に達成状態を維持
    
    def _check_complementary_pair(self, all_icons, service1, service2, achievement_key):
        """特定の補完関係が満たされているかを確認"""
        service1_icons = [icon for icon in all_icons if icon.service_type == service1]
        service2_icons = [icon for icon in all_icons if icon.service_type == service2]
        
        # 両方のサービスが存在する場合のみチェック
        if service1_icons and service2_icons:
            # 補完関係が満たされているかを確認（相互作用しているか）
            for icon1 in service1_icons:
                for icon2 in service2_icons:
                    if hasattr(icon1, 'last_interaction') and icon1.last_interaction == icon2:
                        # まだ達成されていない場合、通知を追加
                        if not self.complementary_achievements[achievement_key]["achieved"]:
                            self.complementary_achievements[achievement_key]["achieved"] = True
                            description = self.complementary_achievements[achievement_key]["description"]
                            self.add_notification(f"Complementary Relation Achieved: {description}")
                        return
                    if hasattr(icon2, 'last_interaction') and icon2.last_interaction == icon1:
                        # まだ達成されていない場合、通知を追加
                        if not self.complementary_achievements[achievement_key]["achieved"]:
                            self.complementary_achievements[achievement_key]["achieved"] = True
                            description = self.complementary_achievements[achievement_key]["description"]
                            self.add_notification(f"Complementary Relation Achieved: {description}")
                        return
            
            # 相互作用していない場合でも、達成状態はリセットしない
            # 一度達成したものは永続的に達成状態を維持
    
    def add_notification(self, message):
        """通知メッセージを追加"""
        if message not in self.notifications:
            self.notifications.append(message)
            self.notification_timers[message] = self.notification_duration
    
    def update_notifications(self):
        """通知の表示時間を更新"""
        for message in list(self.notification_timers.keys()):
            self.notification_timers[message] -= 1
            if self.notification_timers[message] <= 0:
                self.notifications.remove(message)
                del self.notification_timers[message]
    
    def get_dependency_achievement_rate(self):
        """依存関係の達成率を計算"""
        achieved = sum(1 for item in self.dependency_achievements.values() if item["achieved"])
        total = len(self.dependency_achievements)
        return achieved, total
    
    def get_complementary_achievement_rate(self):
        """補完関係の達成率を計算"""
        achieved = sum(1 for item in self.complementary_achievements.values() if item["achieved"])
        total = len(self.complementary_achievements)
        return achieved, total
    
    def get_total_achievement_rate(self):
        """全体の達成率を計算"""
        dep_achieved, dep_total = self.get_dependency_achievement_rate()
        comp_achieved, comp_total = self.get_complementary_achievement_rate()
        return dep_achieved + comp_achieved, dep_total + comp_total
    
    def draw(self, surface, font):
        """進行状況と通知を描画"""
        # 達成率の表示
        dep_achieved, dep_total = self.get_dependency_achievement_rate()
        comp_achieved, comp_total = self.get_complementary_achievement_rate()
        total_achieved, total_total = self.get_total_achievement_rate()
        
        # 達成率テキスト
        achievement_text = f"Total Achievement: {total_achieved}/{total_total}"
        dep_text = f"Dependencies: {dep_achieved}/{dep_total}"
        comp_text = f"Complementary: {comp_achieved}/{comp_total}"
        
        # テキスト描画
        text_color = (50, 50, 50)
        achievement_surface = font.render(achievement_text, True, text_color)
        dep_surface = font.render(dep_text, True, text_color)
        comp_surface = font.render(comp_text, True, text_color)
        
        # 位置調整（画面左上）
        margin = 10
        surface.blit(achievement_surface, (margin, margin))
        surface.blit(dep_surface, (margin, margin + 25))
        surface.blit(comp_surface, (margin, margin + 50))
        
        # 通知の表示
        self._draw_notifications(surface, font)
    
    def _draw_notifications(self, surface, font):
        """通知メッセージを描画"""
        if not self.notifications:
            return
        
        # 通知背景の設定
        notification_bg_color = (0, 0, 0, 180)  # 半透明の黒
        notification_text_color = (255, 255, 255)  # 白
        
        # 通知領域の設定
        notification_width = 600  # 幅を広くして文字が欠けないようにする
        notification_height = 30 * len(self.notifications)
        notification_x = (GAME_AREA_WIDTH - notification_width) // 2
        notification_y = 50
        
        # 通知背景の描画
        notification_surface = pygame.Surface((notification_width, notification_height), pygame.SRCALPHA)
        notification_surface.fill(notification_bg_color)
        
        # 通知テキストの描画
        for i, message in enumerate(self.notifications):
            text_surface = font.render(message, True, notification_text_color)
            text_rect = text_surface.get_rect(center=(notification_width // 2, 15 + 30 * i))
            notification_surface.blit(text_surface, text_rect)
        
        # 通知を画面に描画
        surface.blit(notification_surface, (notification_x, notification_y))

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
        y_offset = self.rect.height - 140  # 120から140に変更して上に移動
        help_title = self.font.render("Controls", True, UI_TEXT_COLOR)
        surface.blit(help_title, (self.rect.x + 10, self.rect.y + y_offset))
        
        y_offset += 30
        controls = [
            "Left Click (empty): Place icon",
            "Left Click (on icon): Select icon",
            "Left Click+Drag: Move icon",
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
                    elif event.button == 2:  # 中クリック（ホイールクリック）
                        # アイコンの選択と直接操作モードの開始
                        self._select_icon_for_direct_control(event.pos)
            elif event.type == MOUSEMOTION:
                # マウス移動時の処理
                buttons = pygame.mouse.get_pressed()
                if buttons[0] and self.selected_icon:  # 左ボタンが押されていて、アイコンが選択されている場合
                    # 直接操作モードを開始
                    self.direct_control_icon = self.selected_icon
                    # アイコンをマウス位置に移動
                    self.direct_control_icon.rect.center = event.pos
                    # 速度をリセット（マウスで直接操作中は自動移動しない）
                    self.direct_control_icon.velocity = [0, 0]
                elif hasattr(self, 'direct_control_icon') and self.direct_control_icon:
                    # 直接操作モードの場合、アイコンをマウス位置に移動
                    self.direct_control_icon.rect.center = event.pos
                    # 速度をリセット（マウスで直接操作中は自動移動しない）
                    self.direct_control_icon.velocity = [0, 0]
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1 or event.button == 2:  # 左クリックまたは中クリックリリース
                    # 直接操作モードの終了
                    if hasattr(self, 'direct_control_icon') and self.direct_control_icon:
                        # 新しいランダムな速度を設定
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(0.5, 1.5)
                        self.direct_control_icon.velocity = [
                            math.cos(angle) * speed,
                            math.sin(angle) * speed
                        ]
                        self.direct_control_icon = None
    
    def _select_icon_for_direct_control(self, position):
        """指定位置のアイコンを選択して直接操作モードを開始"""
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
                self.direct_control_icon = icon  # 直接操作対象として設定
                break
    
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
                # マウスが動いた場合のみ直接操作対象として設定（クリックのみの場合は情報表示のみ）
                return True
        return False
        
        self.selected_icon = None
        self.direct_control_icon = None
        
        # 位置にあるアイコンを探す
        for icon in self.all_icons:
            if icon.rect.collidepoint(position):
                icon.selected = True
                self.selected_icon = icon
                self.direct_control_icon = icon  # 直接操作対象として設定
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
        
        # 進行システムの更新
        self.progress_system.check_achievements(self.all_icons)
        self.progress_system.update_notifications()
        
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
            icon1.velocity = [v * 0.9 for v in icon1.velocity]
            icon2.velocity = [v * 0.9 for v in icon2.velocity]
            # 体力を回復
            icon1.health = min(icon1.max_health, icon1.health + 2)
            icon2.health = min(icon2.max_health, icon2.health + 2)
            
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

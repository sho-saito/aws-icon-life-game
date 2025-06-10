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
        
        # 動きの追跡（停滞時のHealth減少用）
        self.previous_position = list(position)  # 前フレームの位置
        self.stationary_frames = 0  # 停滞しているフレーム数
        self.movement_threshold = 3.0  # 動きと判断する最小距離（ピクセル）
        self.max_stationary_frames = 300  # 停滞許容フレーム数（約5秒）
    
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
        elif self.service_type == "DynamoDB":
            return ["Lambda"]  # DynamoDBはLambdaに依存
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
                if self.service_type in ["EC2", "RDS", "API Gateway", "CloudFront", "DynamoDB"]:
                    self.health = max(0, self.health - 0.05)  # 依存関係不満足時の減少を緩和
            elif self.health < self.max_health:
                self.health = min(self.max_health, self.health + 0.05)
        
        # 相互作用タイマーの更新
        if self.interaction_timer > 0:
            self.interaction_timer -= 1
        
        # 全アイコン共通の微細なHealth減少（生存コスト）
        self.health = max(0, self.health - 0.01)
        
        # Healthが黄色の域（30-60%）の場合、ランダムな動きを加えて停滞を防ぐ
        health_ratio = self.health / self.max_health
        if 0.3 < health_ratio <= 0.6:
            # 低確率でランダムな力を加える
            if random.random() < 0.05:  # 5%の確率
                angle = random.uniform(0, 2 * math.pi)
                force = random.uniform(0.3, 0.8)  # 適度な力
                self.velocity[0] += math.cos(angle) * force
                self.velocity[1] += math.sin(angle) * force
        
        # 動きの追跡と停滞時のHealth減少
        self._check_movement_and_health()
    
    def _check_movement_and_health(self):
        """動きを追跡し、停滞時にHealthを減少させる"""
        # 現在の位置と前フレームの位置の距離を計算
        current_pos = [self.rect.centerx, self.rect.centery]
        distance_moved = math.sqrt(
            (current_pos[0] - self.previous_position[0])**2 + 
            (current_pos[1] - self.previous_position[1])**2
        )
        
        # 動きが閾値以下の場合は停滞とみなす
        if distance_moved < self.movement_threshold:
            self.stationary_frames += 1
        else:
            self.stationary_frames = 0  # 動いた場合はカウンターをリセット
            
            # 依存関係を持たないアイコンは動いている間に回復
            if not self.dependencies and self.health < self.max_health:
                # 動きの速さに応じて回復量を調整（最大0.05/フレーム）
                recovery_amount = min(0.05, distance_moved * 0.01)
                self.health = min(self.max_health, self.health + recovery_amount)
        
        # 停滞時間が長すぎる場合はHealthを減少
        if self.stationary_frames > self.max_stationary_frames:
            self.health = max(0, self.health - 0.2)  # 停滞時の減少幅をさらに緩和
        
        # 前フレームの位置を更新
        self.previous_position = current_pos.copy()
    
    def _apply_movement_pattern(self, all_icons):
        """サービスタイプ固有の動きパターンを適用"""
        if self.service_type == "API Gateway":
            # API Gatewayの振る舞いを管理
            self._api_gateway_behavior(all_icons)
            return
            
        if self.service_type == "Lambda":
            # Lambdaの振る舞いを管理
            self._lambda_behavior(all_icons)
            return
            
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
            
            # VPCの数が5個以下の場合、体力を回復する
            if all_icons:
                vpc_count = sum(1 for icon in all_icons if icon.service_type == "VPC")
                if vpc_count <= 5:
                    # VPCが少ない場合は回復速度を上げる（希少性による重要性の増加）
                    recovery_rate = 0.2  # 通常の回復速度より高い
                    self.health = min(self.max_health, self.health + recovery_rate)
            
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
    def _lambda_behavior(self, all_icons):
        """Lambdaの振る舞いを管理する"""
        # Lambdaの場合のみ実行
        if self.service_type != "Lambda":
            return
            
        # Lambdaの状態管理（初期化）
        if not hasattr(self, 'lambda_state'):
            self.lambda_state = 'normal'  # 'normal', 'active', 'burst'
            self.state_timer = 0
            self.burst_duration = 0
            self.target_position = None
            self.burst_cooldown = 0
            self.max_burst_cooldown = random.randint(180, 360)  # 3〜6秒のクールダウン
            
        # 基本速度を設定
        base_speed = 1.5  # 通常状態の基本速度
        
        # 状態に応じた動作
        if self.lambda_state == 'normal':
            # 通常状態: 比較的ランダムな動き
            
            # 方向転換の確率を高く設定（ランダムな動きを表現）
            if random.random() < 0.05:  # 5%の確率で方向転換（EC2の2.5倍）
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(1.0, 2.0)  # 速度もランダムに変化
                self.velocity = [
                    math.cos(angle) * speed,
                    math.sin(angle) * speed
                ]
            
            # 時々急加速する（バースト状態に移行）
            if random.random() < 0.01 and self.burst_cooldown <= 0:  # 1%の確率でバースト
                self.lambda_state = 'burst'
                self.state_timer = 0
                self.burst_duration = random.randint(60, 120)  # 1〜2秒のバースト
                
                # ランダムな目標位置を設定（画面内）
                target_x = random.randint(50, GAME_AREA_WIDTH - 50)
                target_y = random.randint(50, SCREEN_HEIGHT - 50)
                self.target_position = [target_x, target_y]
                
                # IAMアイコンが近くにある場合は、そちらに向かう確率を高める
                if all_icons:
                    iam_icons = [icon for icon in all_icons if icon.service_type == "IAM"]
                    if iam_icons and random.random() < 0.4:  # 40%の確率でIAMに向かう
                        iam_icon = random.choice(iam_icons)
                        self.target_position = [iam_icon.rect.centerx, iam_icon.rect.centery]
            
            # API Gatewayが近くにある場合、アクティブ状態に移行
            if all_icons:
                api_gateways = [icon for icon in all_icons if icon.service_type == "API Gateway"]
                for api in api_gateways:
                    if self._is_near(api, 100):  # 100px以内にAPI Gatewayがある
                        self.lambda_state = 'active'
                        self.state_timer = 0
                        break
            
            # クールダウンの更新
            if self.burst_cooldown > 0:
                self.burst_cooldown -= 1
                
        elif self.lambda_state == 'active':
            # アクティブ状態: API Gatewayとの相互作用中
            
            # 速度を上げる（処理中の高負荷を表現）
            current_speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
            target_speed = 2.0  # アクティブ状態の目標速度
            
            if current_speed > 0:
                # 現在の速度を目標速度に調整
                ratio = target_speed / current_speed
                self.velocity = [v * ratio for v in self.velocity]
            
            # 方向をより頻繁に変える（忙しい動きを表現）
            if random.random() < 0.1:  # 10%の確率で方向転換
                angle_change = random.uniform(-math.pi/2, math.pi/2)  # ±90度
                speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
                if speed > 0:
                    current_angle = math.atan2(self.velocity[1], self.velocity[0])
                    new_angle = current_angle + angle_change
                    self.velocity = [
                        math.cos(new_angle) * speed,
                        math.sin(new_angle) * speed
                    ]
            
            # 状態タイマーの更新
            self.state_timer += 1
            
            # 一定時間経過後、通常状態に戻る
            if self.state_timer > 120:  # 2秒後
                self.lambda_state = 'normal'
                self.state_timer = 0
                
        elif self.lambda_state == 'burst':
            # バースト状態: 高速で目標位置に向かう
            
            if self.target_position:
                # 目標位置への方向ベクトルを計算
                dx = self.target_position[0] - self.rect.centerx
                dy = self.target_position[1] - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:  # 0除算を防ぐ
                    # 高速で移動（バーストの高速性を表現）
                    speed = 5.0
                    direction_x = dx / distance
                    direction_y = dy / distance
                    self.velocity = [direction_x * speed, direction_y * speed]
            
            # バースト時間の更新
            self.state_timer += 1
            
            # バースト終了判定
            if self.state_timer >= self.burst_duration:
                self.lambda_state = 'normal'
                self.state_timer = 0
                self.burst_cooldown = self.max_burst_cooldown  # クールダウン開始
                
        # IAMアイコンとの関係（依存関係）
        if all_icons:
            iam_icons = [icon for icon in all_icons if icon.service_type == "IAM"]
            if iam_icons:
                # 最も近いIAMを探す
                closest_iam = None
                min_distance = float('inf')
                
                for icon in iam_icons:
                    dx = icon.rect.centerx - self.rect.centerx
                    dy = icon.rect.centery - self.rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_iam = icon
                
                # 最も近いIAMが見つかった場合、その方向に弱い引力
                if closest_iam:
                    dx = closest_iam.rect.centerx - self.rect.centerx
                    dy = closest_iam.rect.centery - self.rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance > 200:  # 200px以上離れている場合
                        # 引力の強さ（距離に反比例）
                        attraction = 0.05
                        direction_x = dx / distance
                        direction_y = dy / distance
                        self.velocity[0] += direction_x * attraction
                        self.velocity[1] += direction_y * attraction
                        
            # DynamoDBとの関係（DynamoDBがLambdaに依存する関係を表現）
            dynamodb_icons = [icon for icon in all_icons if icon.service_type == "DynamoDB"]
            for dynamodb in dynamodb_icons:
                # DynamoDBとの距離を計算
                dx = self.rect.centerx - dynamodb.rect.centerx
                dy = self.rect.centery - dynamodb.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                # 近くにいる場合は相互作用を記録
                if distance < 100:
                    self.last_interaction = dynamodb
                    self.interaction_timer = 30
                    dynamodb.last_interaction = self
                    dynamodb.interaction_timer = 30

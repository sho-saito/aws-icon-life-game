#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AutoScalingアイコンの実装

このファイルには、AutoScalingアイコンの動作パターンを実装するコードが含まれています。
aws_icon.pyファイルに追加する必要があります。
"""

# 1. _apply_movement_pattern メソッドに追加するコード
"""
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
            
        if self.service_type == "AutoScaling":
            # AutoScalingの振る舞いを管理
            self._autoscaling_behavior(all_icons)
            return
"""

# 2. AutoScalingの振る舞いを管理するメソッド
"""
    def _autoscaling_behavior(self, all_icons):
        """AutoScalingの振る舞いを管理する"""
        # AutoScalingの場合のみ実行
        if self.service_type != "AutoScaling":
            return
            
        # AutoScalingの状態管理（初期化）
        if not hasattr(self, 'autoscaling_state'):
            self.autoscaling_state = 'monitoring'  # 'monitoring', 'scaling_up', 'scaling_down'
            self.state_timer = 0
            self.scale_duration = 0
            self.scale_cooldown = 0
            self.max_scale_cooldown = random.randint(180, 300)  # 3〜5秒のクールダウン
            self.target_ec2s = []
            self.monitoring_radius = 150  # モニタリング範囲の半径
            self.scale_factor = 1.0  # スケーリング係数（1.0が通常サイズ）
            self.original_image = self.image.copy()  # 元の画像を保存
            
        # 基本速度を設定
        base_speed = 1.8  # 通常状態の基本速度
        
        # 状態に応じた動作
        if self.autoscaling_state == 'monitoring':
            # モニタリング状態: EC2の周りを監視するような動き
            
            # 方向転換の確率を中程度に設定（監視パターンを表現）
            if random.random() < 0.03:  # 3%の確率で方向転換
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(1.5, 2.2)  # 速度もランダムに変化
                self.velocity = [
                    math.cos(angle) * speed,
                    math.sin(angle) * speed
                ]
            
            # EC2の集団を探す
            if all_icons:
                ec2_icons = [icon for icon in all_icons if icon.service_type == "EC2"]
                
                # EC2が一定数以上ある場合、スケーリング判断を行う
                if len(ec2_icons) >= 3:
                    # EC2の集中している場所を見つける（中心点を計算）
                    center_x = sum(icon.rect.centerx for icon in ec2_icons) / len(ec2_icons)
                    center_y = sum(icon.rect.centery for icon in ec2_icons) / len(ec2_icons)
                    
                    # 中心点からの距離を計算
                    dx = center_x - self.rect.centerx
                    dy = center_y - self.rect.centery
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    # EC2の集団に向かう
                    if distance > 0:  # 0除算を防ぐ
                        # 引力の強さ（距離に反比例）
                        attraction = min(0.1, 30 / distance)
                        direction_x = dx / distance
                        direction_y = dy / distance
                        self.velocity[0] += direction_x * attraction
                        self.velocity[1] += direction_y * attraction
                    
                    # EC2の集団の近くにいる場合、スケーリング判断
                    if distance < self.monitoring_radius:
                        # EC2の数に応じてスケーリング状態を決定
                        if len(ec2_icons) > 5 and random.random() < 0.02 and self.scale_cooldown <= 0:
                            # EC2が多すぎる場合、スケールアップ（サイズ拡大）
                            self.autoscaling_state = 'scaling_up'
                            self.state_timer = 0
                            self.scale_duration = random.randint(90, 150)  # 1.5〜2.5秒のスケーリング
                            self.target_ec2s = random.sample(ec2_icons, min(3, len(ec2_icons)))
                        elif len(ec2_icons) < 3 and random.random() < 0.02 and self.scale_cooldown <= 0:
                            # EC2が少なすぎる場合、スケールダウン（サイズ縮小）
                            self.autoscaling_state = 'scaling_down'
                            self.state_timer = 0
                            self.scale_duration = random.randint(90, 150)  # 1.5〜2.5秒のスケーリング
                            self.target_ec2s = random.sample(ec2_icons, min(2, len(ec2_icons)))
                
                # EC2がない場合、ランダムに動き回る
                elif len(ec2_icons) == 0:
                    if random.random() < 0.05:  # 5%の確率で方向転換
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(1.0, 2.0)
                        self.velocity = [
                            math.cos(angle) * speed,
                            math.sin(angle) * speed
                        ]
            
            # クールダウンの更新
            if self.scale_cooldown > 0:
                self.scale_cooldown -= 1
                
        elif self.autoscaling_state == 'scaling_up':
            # スケールアップ状態: サイズを大きくし、EC2に接近
            
            # サイズを徐々に大きくする
            target_scale = 1.5  # 最大50%大きく
            self.scale_factor = min(self.scale_factor + 0.01, target_scale)
            
            # 画像のサイズを変更
            scaled_size = (int(50 * self.scale_factor), int(50 * self.scale_factor))
            self.image = pygame.transform.scale(self.original_image, scaled_size)
            
            # 矩形の中心位置を保持したままサイズを更新
            center = self.rect.center
            self.rect = self.image.get_rect()
            self.rect.center = center
            
            # ターゲットのEC2に接近
            if self.target_ec2s:
                # ランダムに選んだEC2に向かう
                target = random.choice(self.target_ec2s)
                dx = target.rect.centerx - self.rect.centerx
                dy = target.rect.centery - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:  # 0除算を防ぐ
                    # 高速で移動（スケーリングの即応性を表現）
                    speed = 3.0
                    direction_x = dx / distance
                    direction_y = dy / distance
                    self.velocity = [direction_x * speed, direction_y * speed]
            
            # 状態タイマーの更新
            self.state_timer += 1
            
            # スケーリング終了判定
            if self.state_timer >= self.scale_duration:
                self.autoscaling_state = 'monitoring'
                self.state_timer = 0
                self.scale_cooldown = self.max_scale_cooldown  # クールダウン開始
                
        elif self.autoscaling_state == 'scaling_down':
            # スケールダウン状態: サイズを小さくし、EC2から離れる
            
            # サイズを徐々に小さくする
            target_scale = 0.7  # 最小30%小さく
            self.scale_factor = max(self.scale_factor - 0.01, target_scale)
            
            # 画像のサイズを変更
            scaled_size = (int(50 * self.scale_factor), int(50 * self.scale_factor))
            self.image = pygame.transform.scale(self.original_image, scaled_size)
            
            # 矩形の中心位置を保持したままサイズを更新
            center = self.rect.center
            self.rect = self.image.get_rect()
            self.rect.center = center
            
            # EC2から離れる
            if self.target_ec2s and all_icons:
                # EC2の中心点を計算
                center_x = sum(icon.rect.centerx for icon in self.target_ec2s) / len(self.target_ec2s)
                center_y = sum(icon.rect.centery for icon in self.target_ec2s) / len(self.target_ec2s)
                
                # 中心点からの逆方向に移動
                dx = self.rect.centerx - center_x
                dy = self.rect.centery - center_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:  # 0除算を防ぐ
                    # 中速で移動（スケールダウンの慎重さを表現）
                    speed = 2.0
                    direction_x = dx / distance
                    direction_y = dy / distance
                    self.velocity = [direction_x * speed, direction_y * speed]
            
            # 状態タイマーの更新
            self.state_timer += 1
            
            # スケーリング終了判定
            if self.state_timer >= self.scale_duration:
                self.autoscaling_state = 'monitoring'
                self.state_timer = 0
                self.scale_cooldown = self.max_scale_cooldown  # クールダウン開始
                
        # モニタリング範囲の可視化（デバッグ用、必要に応じてコメントアウト）
        # if self.autoscaling_state == 'monitoring':
        #     pygame.draw.circle(pygame.display.get_surface(), (0, 255, 0), self.rect.center, self.monitoring_radius, 1)
        
        # スケーリング状態が終了したら、徐々に通常サイズに戻す
        if self.autoscaling_state == 'monitoring' and self.scale_factor != 1.0:
            if self.scale_factor > 1.0:
                self.scale_factor = max(1.0, self.scale_factor - 0.005)
            else:
                self.scale_factor = min(1.0, self.scale_factor + 0.005)
            
            # 画像のサイズを更新
            scaled_size = (int(50 * self.scale_factor), int(50 * self.scale_factor))
            self.image = pygame.transform.scale(self.original_image, scaled_size)
            
            # 矩形の中心位置を保持したままサイズを更新
            center = self.rect.center
            self.rect = self.image.get_rect()
            self.rect.center = center
"""

# 3. _set_dependencies メソッドに追加するコード
"""
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
"""
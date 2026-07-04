#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame

from evolution_system import EvolutionSystem

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

        # 進化の達成状況（同種アイコンの合体による進化発動）
        # EvolutionSystemの進化ルールから自動生成するため、
        # 進化パターンを追加すれば自動的に実績表示の対象になる
        group_size = EvolutionSystem.GROUP_SIZE
        self.evolution_achievements = {
            f"{source}-{target}": {
                "achieved": False,
                "description": f"{source} x{group_size} evolved into {target}",
            }
            for source, target in EvolutionSystem.EVOLUTION_RULES.items()
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
                            self.add_notification(f"Complementary Relation: {description}")
                        return
    
    def record_evolution(self, source_type, target_type):
        """進化の発動を実績として記録し、未達成なら通知する"""
        key = f"{source_type}-{target_type}"
        achievement = self.evolution_achievements.get(key)
        if achievement is None:
            # 未定義の進化ルールにも対応できるよう動的に登録する
            achievement = {
                "achieved": False,
                "description": f"{source_type} evolved into {target_type}"
            }
            self.evolution_achievements[key] = achievement
        if not achievement["achieved"]:
            achievement["achieved"] = True
            self.add_notification(f"Evolution Achieved: {achievement['description']}")

    def add_notification(self, message):
        """通知メッセージを追加"""
        # 絵文字を使わないようにする
        if message not in self.notifications:
            self.notifications.append(message)
            self.notification_timers[message] = 0
    
    def update_notifications(self):
        """通知の表示時間を更新"""
        # 表示時間を超えた通知を削除
        messages_to_remove = []
        for message, timer in self.notification_timers.items():
            self.notification_timers[message] += 1
            if timer >= self.notification_duration:
                messages_to_remove.append(message)
        
        # 削除対象の通知を削除
        for message in messages_to_remove:
            if message in self.notifications:
                self.notifications.remove(message)
            if message in self.notification_timers:
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
    
    def get_evolution_achievement_rate(self):
        """進化の達成率を計算"""
        achieved = sum(1 for item in self.evolution_achievements.values() if item["achieved"])
        total = len(self.evolution_achievements)
        return achieved, total

    def get_total_achievement_rate(self):
        """全体の達成率を計算"""
        dep_achieved, dep_total = self.get_dependency_achievement_rate()
        comp_achieved, comp_total = self.get_complementary_achievement_rate()
        evo_achieved, evo_total = self.get_evolution_achievement_rate()
        return (dep_achieved + comp_achieved + evo_achieved,
                dep_total + comp_total + evo_total)
    
    def draw(self, surface, font):
        """進行状況と通知を描画"""
        # 達成率の件数表示は画面左上には出さず、実績オーバーレイ（Shift+A）で確認する
        # 通知の表示
        self._draw_notifications(surface, font)
    
    def draw_overlay(self, surface):
        """全実績の達成状況を最前面の半透明オーバーレイとして表示する（Shift+A押下中）

        下でアイコンたちが活動している様子が透けて見えるように、
        半透明の暗幕の上に各実績の達成/未達成を一覧表示する。
        """
        from constants import SCREEN_WIDTH, SCREEN_HEIGHT

        # 半透明の暗幕（アルファ付きSurfaceで下のアイコンを透過させる）
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))

        title_font = pygame.font.SysFont(None, 48)
        heading_font = pygame.font.SysFont(None, 32)
        item_font = pygame.font.SysFont(None, 28)

        achieved_color = (80, 220, 120)   # 達成: 緑
        pending_color = (160, 160, 160)   # 未達成: グレー
        white = (240, 240, 240)

        margin_x = 60
        y = 40

        # タイトル（全体の達成率）
        total_achieved, total_total = self.get_total_achievement_rate()
        title_surface = title_font.render(
            f"Achievements  {total_achieved} / {total_total}", True, white)
        overlay.blit(title_surface, (margin_x, y))
        y += 70

        # 依存関係・補完関係の各セクションを一覧表示
        sections = [
            ("Dependencies", self.dependency_achievements,
             self.get_dependency_achievement_rate()),
            ("Complementary Relations", self.complementary_achievements,
             self.get_complementary_achievement_rate()),
            ("Evolutions", self.evolution_achievements,
             self.get_evolution_achievement_rate()),
        ]
        for heading, achievements, (sec_achieved, sec_total) in sections:
            heading_surface = heading_font.render(
                f"{heading}  {sec_achieved} / {sec_total}", True, white)
            overlay.blit(heading_surface, (margin_x, y))
            y += 42

            for item in achievements.values():
                achieved = item["achieved"]
                marker = "[x]" if achieved else "[ ]"
                color = achieved_color if achieved else pending_color
                line_surface = item_font.render(
                    f"{marker}  {item['description']}", True, color)
                overlay.blit(line_surface, (margin_x + 24, y))
                y += 32
            y += 24

        surface.blit(overlay, (0, 0))

    def _draw_notifications(self, surface, font):
        """通知メッセージを描画"""
        if not self.notifications:
            return
        
        # 定数をインポート
        from constants import GAME_AREA_WIDTH
        
        # 通知の高さと間隔を大きくする
        notification_height = 40
        total_height = len(self.notifications) * notification_height
        
        # 通知の位置（ゲームエリア下部）
        start_y = surface.get_height() - total_height - 20
        
        for i, message in enumerate(self.notifications):
            # 通知の透明度（表示時間に応じて変化）
            alpha = 255
            if message in self.notification_timers:
                timer = self.notification_timers[message]
                if timer < 30:  # フェードイン
                    alpha = int(255 * timer / 30)
                elif timer > self.notification_duration - 30:  # フェードアウト
                    alpha = int(255 * (self.notification_duration - timer) / 30)
            
            # 通知テキスト（フォントサイズを適切に調整）
            notification_font = pygame.font.SysFont(None, 26)  # フォントサイズを小さく調整
            text_surface = notification_font.render(message, True, (255, 255, 255))
            text_surface.set_alpha(alpha)
            
            # 通知背景（ゲームエリア幅いっぱいに）
            bg_rect = pygame.Rect(
                0,  # 左端から
                start_y + i * notification_height,
                GAME_AREA_WIDTH,  # ゲームエリア幅いっぱい
                notification_height
            )
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.fill((0, 0, 100))  # 濃い青色に変更
            bg_surface.set_alpha(int(alpha * 0.8))  # 透明度を少し下げる
            
            # 描画
            surface.blit(bg_surface, bg_rect)
            
            # テキストがゲームエリア幅を超える場合は調整
            if text_surface.get_width() > GAME_AREA_WIDTH - 40:  # 左右に20pxずつ余白
                # テキストを縮小
                scale_factor = (GAME_AREA_WIDTH - 40) / text_surface.get_width()
                new_width = int(text_surface.get_width() * scale_factor)
                new_height = int(text_surface.get_height() * scale_factor)
                text_surface = pygame.transform.scale(text_surface, (new_width, new_height))
            
            # テキストはゲームエリア内で中央揃え
            text_x = (GAME_AREA_WIDTH - text_surface.get_width()) / 2
            text_y = start_y + i * notification_height + (notification_height - text_surface.get_height()) / 2
            surface.blit(text_surface, (text_x, text_y))

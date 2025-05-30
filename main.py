#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
import sys
import os
import random
from pygame.locals import *

# 定数
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
BACKGROUND_COLOR = (240, 240, 240)
TITLE = "AWS Icon Life"

# AWSアイコンの種類
AWS_ICONS = ["EC2", "S3", "VPC", "Lambda"]

class AWSIcon(pygame.sprite.Sprite):
    """AWSサービスアイコンを表すクラス"""
    
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
                "EC2": (255, 153, 0),    # オレンジ
                "S3": (227, 86, 0),      # 赤っぽいオレンジ
                "VPC": (138, 180, 248),  # 水色
                "Lambda": (250, 146, 3)  # 濃いオレンジ
            }
            self.image.fill(color_map.get(service_type, (200, 200, 200)))
            font = pygame.font.SysFont(None, 20)
            text = font.render(service_type, True, (0, 0, 0))
            text_rect = text.get_rect(center=(25, 25))
            self.image.blit(text, text_rect)
        
        self.rect = self.image.get_rect()
        self.rect.center = position
        
        # 速度がない場合はランダムな速度を設定
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
        
        # 依存関係の設定
        self.dependencies = self._set_dependencies()
    
    def _set_dependencies(self):
        """サービスの依存関係を設定"""
        if self.service_type == "EC2":
            return ["VPC"]
        elif self.service_type == "Lambda":
            return ["IAM"]  # 実際にはIAMアイコンはまだ実装していない
        return []
    
    def update(self):
        """アイコンの状態を更新"""
        # 移動
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        
        # 画面端での反射
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
            self.velocity[0] *= -1
        if self.rect.top < 0 or self.rect.bottom > SCREEN_HEIGHT:
            self.velocity[1] *= -1
        
        # 画面内に収める
        self.rect.left = max(0, min(self.rect.left, SCREEN_WIDTH - self.rect.width))
        self.rect.top = max(0, min(self.rect.top, SCREEN_HEIGHT - self.rect.height))

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
        
        # 初期アイコンの生成
        self._create_initial_icons()
    
    def _create_initial_icons(self):
        """初期アイコンを生成"""
        for service in AWS_ICONS:
            position = (random.randint(50, SCREEN_WIDTH - 50), 
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
                    position = (random.randint(50, SCREEN_WIDTH - 50), 
                                random.randint(50, SCREEN_HEIGHT - 50))
                    icon = AWSIcon(service, position)
                    self.all_icons.add(icon)
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # 左クリック
                    # クリック位置に新しいアイコンを追加
                    service = random.choice(AWS_ICONS)
                    icon = AWSIcon(service, event.pos)
                    self.all_icons.add(icon)
    
    def update(self):
        """ゲーム状態の更新"""
        self.all_icons.update()
        
        # 衝突検出と相互作用
        self._handle_collisions()
    
    def _handle_collisions(self):
        """アイコン同士の衝突と相互作用を処理"""
        # すべてのアイコンペアをチェック
        icons = list(self.all_icons)
        for i, icon1 in enumerate(icons):
            for icon2 in icons[i+1:]:
                if pygame.sprite.collide_rect(icon1, icon2):
                    # 衝突時の反応（単純な反射）
                    icon1.velocity[0], icon2.velocity[0] = icon2.velocity[0], icon1.velocity[0]
                    icon1.velocity[1], icon2.velocity[1] = icon2.velocity[1], icon1.velocity[1]
                    
                    # 依存関係の処理
                    if icon2.service_type in icon1.dependencies:
                        # 依存関係が満たされた場合、何か特別な効果を与える
                        pass
    
    def render(self):
        """描画処理"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # アイコンの描画
        self.all_icons.draw(self.screen)
        
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

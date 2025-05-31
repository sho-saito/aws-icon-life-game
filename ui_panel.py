#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
from constants import UI_BACKGROUND_COLOR, UI_TEXT_COLOR, UI_BORDER_COLOR

class UIPanel:
    """ゲームのUIパネルを管理するクラス"""
    
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = pygame.font.SysFont(None, 24)
        self.small_font = pygame.font.SysFont(None, 18)
        
        # 選択中のアイコン
        self.selected_icon = None
        
        # アイコン数のカウント
        self.icon_counts = {}
    
    def update(self, all_icons, selected_icon):
        """UIパネルの状態を更新"""
        self.selected_icon = selected_icon
        
        # アイコン数のカウントを更新
        self.icon_counts = {}
        for icon in all_icons:
            if icon.service_type in self.icon_counts:
                self.icon_counts[icon.service_type] += 1
            else:
                self.icon_counts[icon.service_type] = 1
    
    def draw(self, surface):
        """UIパネルを描画"""
        # 背景
        pygame.draw.rect(surface, UI_BACKGROUND_COLOR, self.rect)
        
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
            "Space: Place random icon",
            "ESC: Exit"
        ]
        
        for control in controls:
            control_text = self.small_font.render(control, True, UI_TEXT_COLOR)
            surface.blit(control_text, (self.rect.x + 20, self.rect.y + y_offset))
            y_offset += 20

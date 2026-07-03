#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 画面サイズと表示関連の定数
SCREEN_WIDTH = 850
SCREEN_HEIGHT = 650
FPS = 60
BACKGROUND_COLOR = (240, 240, 240)
TITLE = "AWS Icon Life"
UI_PANEL_WIDTH = 250
GAME_AREA_WIDTH = SCREEN_WIDTH - UI_PANEL_WIDTH
UI_BACKGROUND_COLOR = (230, 230, 230)
UI_TEXT_COLOR = (50, 50, 50)
UI_BORDER_COLOR = (200, 200, 200)

# AWSアイコンの種類
AWS_ICONS = ["EC2", "S3", "VPC", "Lambda", "EBS", "RDS", "IAM", "DynamoDB", "API Gateway", "CloudFront", "AutoScaling"]

# アイコンの色マッピング
ICON_COLORS = {
    "EC2": (255, 153, 0),      # オレンジ
    "S3": (227, 86, 0),        # 赤っぽいオレンジ
    "VPC": (138, 180, 248),    # 水色
    "Lambda": (250, 146, 3),   # 濃いオレンジ
    "EBS": (255, 153, 153),    # ピンク
    "RDS": (0, 128, 128),      # ティール
    "IAM": (255, 215, 0),      # 金色
    "DynamoDB": (54, 150, 215),# 青
    "API Gateway": (150, 0, 150), # 紫
    "CloudFront": (255, 99, 71),  # トマト色
    "AutoScaling": (76, 175, 80)  # 緑（成長・スケーリングを表現）
}

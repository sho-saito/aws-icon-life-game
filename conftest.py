#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# pygameをヘッドレス（ディスプレイなし）で動かすため、
# pygameのimport前にダミードライバを設定する
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def pygame_session():
    """テストセッション全体でpygameを初期化する"""
    pygame.init()
    yield
    pygame.quit()

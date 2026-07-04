#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from main import Game


@pytest.fixture
def game():
    return Game()


class TestVpcQuota:
    def test_up_to_quota_vpcs_survive(self, game):
        """デフォルトクォータ（5個）までのVPCは即死しない"""
        icons = [game._spawn_icon("VPC", (100, 100))
                 for _ in range(game.VPC_DEFAULT_QUOTA)]

        assert all(icon.health > 0 for icon in icons)

    def test_sixth_vpc_dies_instantly(self, game):
        """クォータ超過の6個目のVPCは生成された瞬間に即死する"""
        for _ in range(game.VPC_DEFAULT_QUOTA):
            game._spawn_icon("VPC", (100, 100))

        sixth = game._spawn_icon("VPC", (100, 100))

        assert sixth.health == 0

    def test_sixth_vpc_triggers_aws_error_notification(self, game):
        """6個目生成時にAWSのVpcLimitExceededエラーメッセージが通知される"""
        for _ in range(game.VPC_DEFAULT_QUOTA):
            game._spawn_icon("VPC", (100, 100))
        game._spawn_icon("VPC", (100, 100))

        assert game.VPC_QUOTA_ERROR_MESSAGE in game.progress_system.notifications
        assert "VpcLimitExceeded" in game.VPC_QUOTA_ERROR_MESSAGE
        assert ("The maximum number of VPCs has been reached."
                in game.VPC_QUOTA_ERROR_MESSAGE)

    def test_dead_sixth_vpc_is_removed_on_update(self, game):
        """即死した6個目は更新で除去され、生存VPCはクォータ数に戻る"""
        for _ in range(game.VPC_DEFAULT_QUOTA + 1):
            game._spawn_icon("VPC", (100, 100))

        game.update()

        alive_vpcs = [i for i in game.all_icons if i.service_type == "VPC"]
        assert len(alive_vpcs) == game.VPC_DEFAULT_QUOTA

    def test_quota_counts_only_living_vpcs(self, game):
        """死亡したVPCはクォータにカウントされない（枠が空けば再び作れる）"""
        for _ in range(game.VPC_DEFAULT_QUOTA):
            game._spawn_icon("VPC", (100, 100))
        # 生存VPCを1つ減らす
        living = [i for i in game.all_icons
                  if i.service_type == "VPC" and i.health > 0]
        living[0].health = 0

        replacement = game._spawn_icon("VPC", (100, 100))

        assert replacement.health > 0

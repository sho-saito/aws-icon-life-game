#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

import aws_icon
from aws_icon import AWSIcon
from main import Game


def make_icon(service_type, position):
    return AWSIcon(service_type, position, velocity=[0, 0])


@pytest.fixture
def game():
    return Game()


class TestEC2Retirement:
    def test_new_ec2_is_not_retiring(self):
        ec2 = make_icon("EC2", (100, 100))
        assert ec2.retiring is False
        assert ec2.age_frames == 0
        assert ec2.instance_id.startswith("i-")

    def test_young_ec2_does_not_retire_even_if_probability_hits(self, monkeypatch):
        """経過時間が短いEC2は、確率を引いてもリタイアしない"""
        ec2 = make_icon("EC2", (100, 100))
        monkeypatch.setattr(aws_icon.random, "random", lambda: 0.0)

        ec2._update_retirement()

        assert ec2.retiring is False

    def test_old_ec2_retires_when_probability_hits(self, monkeypatch):
        """十分に経過したEC2は、確率を引くとリタイアする"""
        ec2 = make_icon("EC2", (100, 100))
        ec2.age_frames = ec2.EC2_RETIREMENT_MIN_AGE_FRAMES
        monkeypatch.setattr(aws_icon.random, "random", lambda: 0.0)

        ec2._update_retirement()

        assert ec2.retiring is True

    def test_old_ec2_does_not_retire_when_probability_misses(self, monkeypatch):
        ec2 = make_icon("EC2", (100, 100))
        ec2.age_frames = ec2.EC2_RETIREMENT_MIN_AGE_FRAMES
        monkeypatch.setattr(aws_icon.random, "random", lambda: 1.0)

        ec2._update_retirement()

        assert ec2.retiring is False

    def test_retiring_ec2_health_decreases_faster(self):
        """リタイア中は体力減少が加速する"""
        ec2 = make_icon("EC2", (100, 100))
        ec2.retiring = True
        before = ec2.health

        ec2._update_retirement()

        assert ec2.health == before - ec2.EC2_RETIREMENT_HEALTH_DECREASE

    def test_retirement_triggers_notification_once(self, game):
        """リタイア発動時にAWS公式のリタイア通知が1度だけ出る"""
        ec2 = game._spawn_icon("EC2", (100, 100))
        ec2.retiring = True

        game.update()
        after_first = list(game.progress_system.notifications)

        assert ec2.retirement_announced is True
        # AWS公式メッセージの文面・インスタンスID・リージョンが含まれる
        assert any(
            msg.startswith(
                "EC2 has detected degradation of the underlying hardware "
                "hosting your Amazon EC2 instance")
            and ec2.instance_id in msg
            and game.EC2_RETIREMENT_REGION in msg
            and "We will stop your instance after" in msg
            for msg in after_first
        )

        # 2回目のupdateでは通知が増えない
        game.update()
        assert game.progress_system.notifications == after_first

    def test_retirement_message_matches_official_wording(self, game):
        """公式メッセージの文面が完全一致で再現されている"""
        ec2 = game._spawn_icon("EC2", (100, 100))

        message = game._ec2_retirement_message(ec2)

        expected_prefix = (
            f"EC2 has detected degradation of the underlying hardware hosting "
            f"your Amazon EC2 instance (instance-ID: {ec2.instance_id}) "
            f"associated with your AWS account (AWS Account ID: "
            f"{game.aws_account_id}) in the {game.EC2_RETIREMENT_REGION} region. "
            f"Due to this degradation your instance could already be "
            f"unreachable. We will stop your instance after "
        )
        assert message.startswith(expected_prefix)
        assert message.endswith(" UTC.")

    def test_non_ec2_icons_never_retire(self):
        vpc = make_icon("VPC", (100, 100))
        vpc.age_frames = 100000

        vpc.update([vpc])

        assert vpc.retiring is False

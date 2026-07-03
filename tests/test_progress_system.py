#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from aws_icon import AWSIcon
from progress_system import ProgressSystem


@pytest.fixture
def progress():
    return ProgressSystem()


def make_icon(service_type, position):
    return AWSIcon(service_type, position, velocity=[0, 0])


class TestDependencyAchievements:
    def test_near_icons_achieve_dependency(self, progress):
        ec2 = make_icon("EC2", (100, 100))
        vpc = make_icon("VPC", (150, 100))  # 50px離れ（150px以内）

        progress.check_achievements([ec2, vpc])

        assert progress.dependency_achievements["EC2-VPC"]["achieved"] is True

    def test_far_icons_do_not_achieve_dependency(self, progress):
        ec2 = make_icon("EC2", (100, 100))
        vpc = make_icon("VPC", (500, 500))  # 150pxより遠い

        progress.check_achievements([ec2, vpc])

        assert progress.dependency_achievements["EC2-VPC"]["achieved"] is False

    def test_missing_partner_does_not_achieve(self, progress):
        ec2 = make_icon("EC2", (100, 100))

        progress.check_achievements([ec2])

        assert progress.dependency_achievements["EC2-VPC"]["achieved"] is False

    def test_achievement_persists_after_icons_separate(self, progress):
        ec2 = make_icon("EC2", (100, 100))
        vpc = make_icon("VPC", (150, 100))
        progress.check_achievements([ec2, vpc])

        vpc.rect.center = (700, 500)  # 離す
        progress.check_achievements([ec2, vpc])

        assert progress.dependency_achievements["EC2-VPC"]["achieved"] is True


class TestComplementaryAchievements:
    def test_interaction_achieves_complementary_relation(self, progress):
        lam = make_icon("Lambda", (100, 100))
        dynamo = make_icon("DynamoDB", (150, 100))
        lam.last_interaction = dynamo

        progress.check_achievements([lam, dynamo])

        assert progress.complementary_achievements["Lambda-DynamoDB"]["achieved"] is True

    def test_no_interaction_no_achievement(self, progress):
        lam = make_icon("Lambda", (100, 100))
        dynamo = make_icon("DynamoDB", (150, 100))

        progress.check_achievements([lam, dynamo])

        assert progress.complementary_achievements["Lambda-DynamoDB"]["achieved"] is False


class TestNotifications:
    def test_achievement_adds_notification(self, progress):
        ec2 = make_icon("EC2", (100, 100))
        vpc = make_icon("VPC", (150, 100))

        progress.check_achievements([ec2, vpc])

        assert progress.notifications == ["Dependency Achieved: EC2 exists in VPC"]

    def test_duplicate_notification_is_ignored(self, progress):
        progress.add_notification("same message")
        progress.add_notification("same message")

        assert progress.notifications == ["same message"]

    def test_notification_expires_after_duration(self, progress):
        progress.add_notification("temporary")

        for _ in range(progress.notification_duration + 1):
            progress.update_notifications()

        assert progress.notifications == []
        assert "temporary" not in progress.notification_timers


class TestAchievementRates:
    def test_initial_rates_are_zero(self, progress):
        assert progress.get_dependency_achievement_rate() == (0, 6)
        assert progress.get_complementary_achievement_rate() == (0, 3)
        assert progress.get_total_achievement_rate() == (0, 9)

    def test_rates_count_achieved_items(self, progress):
        progress.dependency_achievements["EC2-VPC"]["achieved"] = True
        progress.complementary_achievements["EC2-EBS"]["achieved"] = True

        assert progress.get_dependency_achievement_rate() == (1, 6)
        assert progress.get_complementary_achievement_rate() == (1, 3)
        assert progress.get_total_achievement_rate() == (2, 9)

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
        assert progress.get_evolution_achievement_rate() == (0, 1)
        assert progress.get_total_achievement_rate() == (0, 10)

    def test_rates_count_achieved_items(self, progress):
        progress.dependency_achievements["EC2-VPC"]["achieved"] = True
        progress.complementary_achievements["EC2-EBS"]["achieved"] = True

        assert progress.get_dependency_achievement_rate() == (1, 6)
        assert progress.get_complementary_achievement_rate() == (1, 3)
        assert progress.get_total_achievement_rate() == (2, 10)


class TestEvolutionAchievements:
    def test_record_evolution_marks_achieved_and_notifies(self, progress):
        progress.record_evolution("EC2", "AutoScaling")

        assert progress.evolution_achievements["EC2-AutoScaling"]["achieved"] is True
        assert progress.get_evolution_achievement_rate() == (1, 1)
        assert any("Evolution Achieved" in msg for msg in progress.notifications)

    def test_record_evolution_notifies_only_once(self, progress):
        progress.record_evolution("EC2", "AutoScaling")
        first_count = len(progress.notifications)
        progress.record_evolution("EC2", "AutoScaling")

        assert len(progress.notifications) == first_count

    def test_unknown_evolution_rule_is_registered_dynamically(self, progress):
        progress.record_evolution("Lambda", "StepFunctions")

        assert progress.evolution_achievements["Lambda-StepFunctions"]["achieved"] is True

    def test_evolution_achievements_derived_from_rules(self, progress):
        """進化ルールを追加すれば自動的に実績表示の対象になる"""
        from evolution_system import EvolutionSystem

        expected_keys = {
            f"{source}-{target}"
            for source, target in EvolutionSystem.EVOLUTION_RULES.items()
        }
        assert expected_keys <= set(progress.evolution_achievements)
        # 初期状態ではすべて未達成として一覧に載る
        for key in expected_keys:
            assert progress.evolution_achievements[key]["achieved"] is False


class TestNotificationWrapping:
    def test_long_message_wraps_into_multiple_lines(self, progress):
        import pygame
        font = pygame.font.SysFont(None, 26)
        long_message = (
            "EC2 has detected degradation of the underlying hardware hosting "
            "your Amazon EC2 instance (instance-ID: i-0123456789abcdef0) "
            "associated with your AWS account (AWS Account ID: 123456789012) "
            "in the us-east-1 region."
        )
        max_width = 300

        lines = progress._wrap_text(long_message, font, max_width)

        assert len(lines) > 1
        for line in lines:
            assert font.size(line)[0] <= max_width

    def test_short_message_is_single_line(self, progress):
        import pygame
        font = pygame.font.SysFont(None, 26)

        lines = progress._wrap_text("Short one", font, 400)

        assert lines == ["Short one"]

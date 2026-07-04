#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from aws_icon import AWSIcon
from evolution_system import EvolutionSystem


@pytest.fixture
def system():
    return EvolutionSystem()


def make_icon(service_type, position):
    return AWSIcon(service_type, position, velocity=[0, 0])


def make_adjacent_ec2s(count=3):
    """互いに隣接距離内（80px未満）に並んだEC2アイコンを生成する"""
    positions = [(100, 100), (150, 100), (125, 140), (175, 140)]
    return [make_icon("EC2", pos) for pos in positions[:count]]


def run_frames(system, icons, frames):
    """指定フレーム数だけ進化判定を実行し、発生した進化を集める"""
    evolutions = []
    for _ in range(frames):
        evolutions.extend(system.update(icons))
    return evolutions


class TestEvolutionTrigger:
    def test_three_adjacent_ec2_evolve_after_required_frames(self, system):
        icons = make_adjacent_ec2s(3)

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES)

        assert len(evolutions) == 1
        evolution = evolutions[0]
        assert evolution.source_type == "EC2"
        assert evolution.target_type == "AutoScaling"
        assert sorted(id(i) for i in evolution.icons) == sorted(id(i) for i in icons)

    def test_no_evolution_before_required_frames(self, system):
        icons = make_adjacent_ec2s(3)

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES - 1)

        assert evolutions == []

    def test_two_adjacent_ec2_do_not_evolve(self, system):
        icons = make_adjacent_ec2s(2)

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES * 2)

        assert evolutions == []
        assert all(icon.evolution_timer == 0 for icon in icons)

    def test_far_ec2_do_not_evolve(self, system):
        icons = [
            make_icon("EC2", (100, 100)),
            make_icon("EC2", (300, 100)),
            make_icon("EC2", (500, 100)),
        ]

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES * 2)

        assert evolutions == []

    def test_non_ec2_icons_do_not_evolve(self, system):
        icons = [
            make_icon("Lambda", (100, 100)),
            make_icon("Lambda", (150, 100)),
            make_icon("Lambda", (125, 140)),
        ]

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES * 2)

        assert evolutions == []


class TestEvolutionTimer:
    def test_timer_counts_up_in_qualifying_cluster(self, system):
        icons = make_adjacent_ec2s(3)

        run_frames(system, icons, 10)

        assert all(icon.evolution_timer == 10 for icon in icons)
        assert all(icon.evolution_progress == pytest.approx(10 / system.REQUIRED_FRAMES)
                   for icon in icons)

    def test_timer_resets_when_cluster_breaks(self, system):
        icons = make_adjacent_ec2s(3)
        run_frames(system, icons, 100)

        # 1つを遠くに移動させるとクラスタが2個になり条件を満たさなくなる
        icons[2].rect.center = (500, 500)
        run_frames(system, icons, 1)

        assert all(icon.evolution_timer == 0 for icon in icons)
        assert all(icon.evolution_progress == 0.0 for icon in icons)

    def test_evolution_requires_full_duration_after_reset(self, system):
        icons = make_adjacent_ec2s(3)
        run_frames(system, icons, 100)

        # 一度クラスタを崩してから元に戻す
        icons[2].rect.center = (500, 500)
        run_frames(system, icons, 1)
        icons[2].rect.center = (125, 140)

        assert run_frames(system, icons, system.REQUIRED_FRAMES - 1) == []
        assert len(run_frames(system, icons, 1)) == 1


class TestEvolutionResult:
    def test_new_icon_spawns_at_centroid_with_average_velocity(self, system):
        icons = [
            AWSIcon("EC2", (100, 100), velocity=[3, 0]),
            AWSIcon("EC2", (150, 100), velocity=[0, 3]),
            AWSIcon("EC2", (125, 140), velocity=[0, 0]),
        ]

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES)

        assert len(evolutions) == 1
        evolution = evolutions[0]
        assert evolution.position == (125, (100 + 100 + 140) / 3)
        assert evolution.velocity == [1, 1]

    def test_four_adjacent_ec2_consume_only_three(self, system):
        icons = make_adjacent_ec2s(4)

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES)

        assert len(evolutions) == 1
        assert len(evolutions[0].icons) == 3

    def test_chain_of_six_ec2_produces_two_evolutions(self, system):
        # 60px間隔のチェーン状クラスタ（全体が1つの連結クラスタになる）
        icons = [make_icon("EC2", (100 + i * 60, 100)) for i in range(6)]

        evolutions = run_frames(system, icons, system.REQUIRED_FRAMES)

        assert len(evolutions) == 2
        evolved_ids = [id(icon) for e in evolutions for icon in e.icons]
        assert len(set(evolved_ids)) == 6


class TestAutoScalingSpawnCost:
    def test_spawning_ec2_consumes_ratio_of_current_health(self):
        """EC2をスポーンするとその時点の残存体力の10%が消費される"""
        autoscaling = make_icon("AutoScaling", (400, 300))
        autoscaling.autoscaling_state = 'scaling_out'
        autoscaling.health = 80
        expected = 80 * (1 - autoscaling.AUTOSCALING_SPAWN_HEALTH_COST_RATIO)

        autoscaling._complete_scaling()

        assert autoscaling.spawn_requests[0][0] == "EC2"
        assert autoscaling.health == pytest.approx(expected)

    def test_spawn_cost_scales_with_remaining_health(self):
        """残存体力が少ないほど消費量（絶対値）も小さくなる"""
        low = make_icon("AutoScaling", (400, 300))
        low.autoscaling_state = 'scaling_out'
        low.health = 10

        low._complete_scaling()

        assert low.health == pytest.approx(9)
        assert low.health >= 0

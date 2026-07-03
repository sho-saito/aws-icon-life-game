#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from collections import namedtuple

# 進化の結果を表すデータ
# icons: 進化して消えるアイコンのリスト
# source_type / target_type: 進化前 / 進化後のサービスタイプ
# position: 進化後アイコンの生成位置（進化するアイコンの重心）
# velocity: 進化後アイコンの初速（進化するアイコンの平均速度）
Evolution = namedtuple(
    "Evolution", ["icons", "source_type", "target_type", "position", "velocity"]
)


class EvolutionSystem:
    """アイコンの「進化」を管理するクラス

    同種のアイコンが3つ以上隣接した状態が一定フレーム数続くと、
    それらが合体して1つの別のアイコンに進化する。
    """

    # 隣接と判定するアイコン中心間の距離（ピクセル）
    ADJACENCY_DISTANCE = 80
    # 進化に必要な隣接継続フレーム数（60FPSで約3秒）
    REQUIRED_FRAMES = 180
    # 進化で消費されるアイコン数
    GROUP_SIZE = 3
    # 進化ルール: {進化前のサービスタイプ: 進化後のサービスタイプ}
    EVOLUTION_RULES = {
        "EC2": "AutoScaling",
    }

    def update(self, all_icons):
        """進化条件を判定し、発生した進化（Evolution）のリストを返す

        各アイコンの evolution_timer / evolution_progress を更新する。
        進化で消えるアイコンの削除と進化後アイコンの生成は呼び出し側が行う。
        """
        icons = list(all_icons)
        evolutions = []
        for source_type, target_type in self.EVOLUTION_RULES.items():
            evolutions.extend(self._process_rule(icons, source_type, target_type))
        return evolutions

    def _process_rule(self, icons, source_type, target_type):
        """1つの進化ルールについて、タイマーの更新と進化の判定を行う"""
        source_icons = [icon for icon in icons if icon.service_type == source_type]
        evolutions = []
        qualified_ids = set()

        for cluster in self._find_clusters(source_icons):
            # GROUP_SIZE以上のアイコンが隣接しているクラスタのみ進化条件を満たす
            if len(cluster) < self.GROUP_SIZE:
                continue

            for icon in cluster:
                qualified_ids.add(id(icon))
                icon.evolution_timer += 1
                icon.evolution_progress = min(
                    1.0, icon.evolution_timer / self.REQUIRED_FRAMES
                )

            # タイマーが満了したアイコンがGROUP_SIZE個揃うごとに進化が発生
            ready = [
                icon for icon in cluster
                if icon.evolution_timer >= self.REQUIRED_FRAMES
            ]
            ready.sort(key=lambda icon: icon.evolution_timer, reverse=True)
            while len(ready) >= self.GROUP_SIZE:
                group = ready[:self.GROUP_SIZE]
                ready = ready[self.GROUP_SIZE:]
                evolutions.append(
                    self._create_evolution(group, source_type, target_type)
                )

        # 進化条件を満たすクラスタから外れたアイコンはタイマーをリセット
        for icon in source_icons:
            if id(icon) not in qualified_ids:
                icon.evolution_timer = 0
                icon.evolution_progress = 0.0

        return evolutions

    def _find_clusters(self, icons):
        """隣接（ADJACENCY_DISTANCE以内）で連結しているアイコンのクラスタを列挙する"""
        clusters = []
        visited = set()
        for start in icons:
            if id(start) in visited:
                continue
            cluster = []
            stack = [start]
            visited.add(id(start))
            while stack:
                icon = stack.pop()
                cluster.append(icon)
                for other in icons:
                    if id(other) not in visited and self._is_adjacent(icon, other):
                        visited.add(id(other))
                        stack.append(other)
            clusters.append(cluster)
        return clusters

    def _is_adjacent(self, icon1, icon2):
        """2つのアイコンが隣接しているかを判定"""
        dx = icon1.rect.centerx - icon2.rect.centerx
        dy = icon1.rect.centery - icon2.rect.centery
        return math.hypot(dx, dy) < self.ADJACENCY_DISTANCE

    def _create_evolution(self, group, source_type, target_type):
        """進化後アイコンの生成位置（重心）と初速（平均速度）を計算する"""
        count = len(group)
        position = (
            sum(icon.rect.centerx for icon in group) / count,
            sum(icon.rect.centery for icon in group) / count,
        )
        velocity = [
            sum(icon.velocity[0] for icon in group) / count,
            sum(icon.velocity[1] for icon in group) / count,
        ]
        return Evolution(group, source_type, target_type, position, velocity)

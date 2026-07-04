#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aws_icon import AWSIcon


def make_icon(service_type):
    return AWSIcon(service_type, (10, 10), velocity=[0, 0])


class TestStateIndicator:
    def test_base_states_have_no_border(self):
        """基本/待機状態は枠色・ラベルなし"""
        lam = make_icon("Lambda")
        lam.lambda_state = "normal"
        assert lam.state_border_color() is None
        assert lam.state_label() is None

    def test_lambda_burst_has_orange_border_and_label(self):
        lam = make_icon("Lambda")
        lam.lambda_state = "burst"
        assert lam.state_border_color() == (255, 140, 0)
        assert lam.state_label() == "Burst"

    def test_lambda_active_has_border(self):
        lam = make_icon("Lambda")
        lam.lambda_state = "active"
        assert lam.state_border_color() == (0, 200, 255)
        assert lam.state_label() == "Active"

    def test_api_gateway_states(self):
        api = make_icon("API Gateway")
        api.api_state = "connect"
        assert api.state_label() == "Connecting"
        assert api.state_border_color() == (255, 140, 0)  # オレンジ
        api.api_state = "return"
        assert api.state_label() == "Returning"
        assert api.state_border_color() == (0, 220, 120)  # 緑
        api.api_state = "patrol"
        assert api.state_label() is None
        assert api.state_border_color() is None  # 基本状態は枠なし

    def test_autoscaling_scaling_out(self):
        asg = make_icon("AutoScaling")
        asg.autoscaling_state = "scaling_out"
        assert asg.state_label() == "Scaling out"
        assert asg.state_border_color() == (255, 140, 0)  # オレンジ
        asg.autoscaling_state = "monitoring"
        assert asg.state_label() is None
        assert asg.state_border_color() is None  # 基本状態は枠なし

    def test_autoscaling_scaling_in(self):
        asg = make_icon("AutoScaling")
        asg.autoscaling_state = "monitoring"
        asg.scaling_in = True
        assert asg.state_label() == "Scaling in"
        assert asg.state_border_color() == (160, 90, 220)  # 紫

    def test_autoscaling_scaling_out_takes_priority_over_scaling_in(self):
        asg = make_icon("AutoScaling")
        asg.autoscaling_state = "scaling_out"
        asg.scaling_in = True
        assert asg.state_label() == "Scaling out"

    def test_scaling_in_flag_set_when_excess_ec2_nearby(self):
        """監視範囲内の生存EC2がDesiredCountを超えるとスケールインになる"""
        asg = make_icon("AutoScaling")
        asg.desired_count = 1
        asg.autoscaling_state = "monitoring"
        ec2s = [make_icon("EC2") for _ in range(3)]
        for e in ec2s:
            e.rect.center = asg.rect.center  # 監視範囲内に配置
        asg._autoscaling_behavior([asg] + ec2s)
        assert asg.scaling_in is True
        assert asg.state_label() == "Scaling in"

    def test_scaling_in_flag_cleared_when_no_excess(self):
        """超過が無い（EC2が居ない）フレームではスケールインフラグは下がる"""
        asg = make_icon("AutoScaling")
        asg.desired_count = 3
        asg.autoscaling_state = "monitoring"
        asg.scaling_in = True  # 前フレームの残り
        asg._autoscaling_behavior([asg])
        assert asg.scaling_in is False

    def test_retiring_takes_priority_with_red_border(self):
        ec2 = make_icon("EC2")
        ec2.retiring = True
        assert ec2.state_border_color() == (255, 0, 0)
        assert ec2.state_label() == "Retiring"

    def test_service_without_state_machine_has_no_indicator(self):
        s3 = make_icon("S3")
        assert s3.state_border_color() is None
        assert s3.state_label() is None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import pytest

from aws_icon import AWSIcon
from constants import AWS_REGION, AWS_ACCOUNT_ID


def make_icon(service_type):
    return AWSIcon(service_type, (10, 10), velocity=[0, 0])


class TestArnGeneration:
    def test_every_icon_gets_an_arn_on_creation(self):
        for st in ["EC2", "S3", "VPC", "Lambda", "EBS", "RDS", "IAM",
                   "DynamoDB", "API Gateway", "CloudFront", "AutoScaling"]:
            icon = make_icon(st)
            assert icon.arn.startswith("arn:aws:")

    def test_arns_are_unique_per_icon(self):
        arns = {make_icon("EC2").arn for _ in range(20)}
        assert len(arns) == 20

    def test_ec2_arn_format_and_instance_id_embedded(self):
        ec2 = make_icon("EC2")
        assert re.fullmatch(
            rf"arn:aws:ec2:{AWS_REGION}:{AWS_ACCOUNT_ID}:instance/i-[0-9a-f]{{17}}",
            ec2.arn,
        )
        # インスタンスIDがARNに埋め込まれている（リタイア通知と一貫）
        assert ec2.instance_id is not None
        assert ec2.instance_id in ec2.arn

    def test_vpc_and_ebs_use_ec2_namespace_with_correct_prefixes(self):
        assert re.fullmatch(
            rf"arn:aws:ec2:{AWS_REGION}:{AWS_ACCOUNT_ID}:vpc/vpc-[0-9a-f]{{17}}",
            make_icon("VPC").arn,
        )
        assert re.fullmatch(
            rf"arn:aws:ec2:{AWS_REGION}:{AWS_ACCOUNT_ID}:volume/vol-[0-9a-f]{{17}}",
            make_icon("EBS").arn,
        )

    def test_s3_arn_has_no_region_or_account(self):
        assert make_icon("S3").arn.startswith("arn:aws:s3:::")

    def test_global_services_omit_region(self):
        # IAM/CloudFrontはグローバルサービスのためregionが空
        assert make_icon("IAM").arn.startswith(f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/")
        assert make_icon("CloudFront").arn.startswith(
            f"arn:aws:cloudfront::{AWS_ACCOUNT_ID}:distribution/")

    def test_non_ec2_icons_have_no_instance_id(self):
        assert make_icon("S3").instance_id is None

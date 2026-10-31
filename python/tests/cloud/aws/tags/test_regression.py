"""Regression test: every server has the required tags."""
import pytest

from checks.cloud.aws.tags import ec2_missing_tags

pytestmark = pytest.mark.regression


def test_tc03_ec2_has_required_tags(aws, config):
    """TC-03: Every EC2 instance has the required FinOps tags."""
    problems = ec2_missing_tags(aws, config["required_tags"])
    assert not problems, "\n".join(problems)

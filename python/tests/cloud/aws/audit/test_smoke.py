"""Smoke test: the account is keeping an audit log."""
import pytest

from checks.cloud.aws.audit import cloudtrail_problems

pytestmark = pytest.mark.smoke


def test_tc02_cloudtrail_is_logging(aws):
    """TC-02: At least one CloudTrail trail exists and is logging."""
    problems = cloudtrail_problems(aws)
    assert not problems, "\n".join(problems)

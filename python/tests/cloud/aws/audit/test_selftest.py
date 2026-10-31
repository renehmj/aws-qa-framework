"""Self-tests: a bad audit setting must be reported."""
import pytest

from checks.cloud.aws.audit import cloudtrail_problems

pytestmark = pytest.mark.selftest


def test_missing_cloudtrail_is_caught(empty_mock_account):
    assert cloudtrail_problems(empty_mock_account) == ["no CloudTrail trail found"]


def test_stopped_cloudtrail_is_caught(empty_mock_account):
    """Edge case: a trail that exists but is not logging is still a problem."""
    empty_mock_account.client("s3").create_bucket(Bucket="trail-logs-bucket")
    trail = empty_mock_account.client("cloudtrail")
    trail.create_trail(Name="stopped-trail", S3BucketName="trail-logs-bucket")
    assert cloudtrail_problems(empty_mock_account) == ["trail stopped-trail is not logging"]

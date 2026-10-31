"""Self-tests: a bad storage setting must be reported."""
import pytest

from checks.cloud.aws.storage import (
    buckets_without_encryption,
    buckets_without_public_block,
)

pytestmark = pytest.mark.selftest


def test_public_bucket_is_caught(empty_mock_account):
    empty_mock_account.client("s3").create_bucket(Bucket="no-block-bucket")
    problems = buckets_without_public_block(empty_mock_account)
    assert problems == ["no-block-bucket: no public access block"]


def test_partly_public_bucket_is_caught(empty_mock_account):
    """Edge case: three of the four settings on is still a problem."""
    s3 = empty_mock_account.client("s3")
    s3.create_bucket(Bucket="partly-open-bucket")
    s3.put_public_access_block(Bucket="partly-open-bucket", PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": False})
    problems = buckets_without_public_block(empty_mock_account)
    assert problems == ["partly-open-bucket: public access block is only partly on"]


def test_unencrypted_bucket_is_caught(empty_mock_account):
    empty_mock_account.client("s3").create_bucket(Bucket="plain-bucket")
    problems = buckets_without_encryption(empty_mock_account)
    assert problems == ["plain-bucket: no default encryption"]

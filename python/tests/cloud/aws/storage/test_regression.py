"""Regression tests: S3 buckets are private and encrypted."""
import pytest

from checks.cloud.aws.storage import (
    buckets_without_encryption,
    buckets_without_public_block,
)

pytestmark = pytest.mark.regression


def test_tc05_s3_blocks_public_access(aws):
    """TC-05: Every S3 bucket fully blocks public access."""
    problems = buckets_without_public_block(aws)
    assert not problems, "\n".join(problems)


def test_tc06_s3_encrypted_by_default(aws):
    """TC-06: Every S3 bucket has default encryption."""
    problems = buckets_without_encryption(aws)
    assert not problems, "\n".join(problems)

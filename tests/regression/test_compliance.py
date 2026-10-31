"""Regression tests: did any change break our AWS standards?"""
import pytest

from checks.iam import users_without_mfa
from checks.network import ports_open_to_world
from checks.storage import buckets_without_encryption, buckets_without_public_block
from checks.tags import ec2_missing_tags

pytestmark = [pytest.mark.regression, pytest.mark.aws]


def test_tc03_ec2_has_required_tags(aws, config):
    """TC-03: Every EC2 instance has the required FinOps tags."""
    problems = ec2_missing_tags(aws, config["required_tags"])
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("port", [22, 3389], ids=["ssh", "rdp"])
def test_tc04_admin_ports_not_open_to_world(aws, port):
    """TC-04: No security group opens SSH or RDP to the internet."""
    problems = ports_open_to_world(aws, ports=(port,))
    assert not problems, "\n".join(problems)


def test_tc05_s3_blocks_public_access(aws):
    """TC-05: Every S3 bucket fully blocks public access."""
    problems = buckets_without_public_block(aws)
    assert not problems, "\n".join(problems)


def test_tc06_s3_encrypted_by_default(aws):
    """TC-06: Every S3 bucket has default encryption."""
    problems = buckets_without_encryption(aws)
    assert not problems, "\n".join(problems)


def test_tc07_console_users_have_mfa(aws):
    """TC-07: Every IAM user with a console password has MFA."""
    problems = users_without_mfa(aws)
    assert not problems, "\n".join(problems)

"""Smoke tests: we can log in, and the login is safe."""
import pytest

from checks.cloud.aws.iam import credential_problems

pytestmark = pytest.mark.smoke


def test_tc01_credentials_work(aws):
    """TC-01: We can call AWS with the test role."""
    identity = aws.client("sts").get_caller_identity()
    assert identity["Account"], "could not read the account ID"


def test_tc11_credentials_are_short_lived(aws):
    """TC-11: We use temporary credentials, and never the root user."""
    problems = credential_problems(aws)
    assert not problems, "\n".join(problems)

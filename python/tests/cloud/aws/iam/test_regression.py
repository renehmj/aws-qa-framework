"""Regression test: people who log in to the console use MFA."""
import pytest

from checks.cloud.aws.iam import users_without_mfa

pytestmark = pytest.mark.regression


def test_tc07_console_users_have_mfa(aws):
    """TC-07: Every IAM user with a console password has MFA."""
    problems = users_without_mfa(aws)
    assert not problems, "\n".join(problems)

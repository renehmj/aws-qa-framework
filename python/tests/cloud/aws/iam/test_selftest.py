"""Self-tests: a bad iam setting must be reported."""
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from checks.cloud.aws.iam import credential_problems, role_can_write, users_without_mfa

pytestmark = pytest.mark.selftest


def _denied(code):
    return ClientError({"Error": {"Code": code, "Message": "denied"}}, "AnyCall")


def test_console_user_without_mfa_is_caught(empty_mock_account):
    iam = empty_mock_account.client("iam")
    iam.create_user(UserName="alice")
    iam.create_login_profile(UserName="alice", Password="Temp-Passw0rd!")
    iam.create_user(UserName="ci-bot")  # no console login, so it is ignored
    assert users_without_mfa(empty_mock_account) == ["alice: console user without MFA"]


def test_console_user_with_mfa_is_not_flagged(empty_mock_account):
    """No false alarm: a user who did the right thing must pass."""
    iam = empty_mock_account.client("iam")
    iam.create_user(UserName="bob")
    iam.create_login_profile(UserName="bob", Password="Temp-Passw0rd!")
    device = iam.create_virtual_mfa_device(VirtualMFADeviceName="bob-mfa")["VirtualMFADevice"]
    iam.enable_mfa_device(UserName="bob", SerialNumber=device["SerialNumber"],
                          AuthenticationCode1="123456", AuthenticationCode2="654321")
    assert users_without_mfa(empty_mock_account) == []


def test_write_access_is_caught(empty_mock_account):
    """Fake AWS allows everything, so the DryRun call reports write access."""
    assert role_can_write(empty_mock_account) is True


def test_read_only_role_passes():
    session = MagicMock()
    session.client.return_value.create_security_group.side_effect = _denied("UnauthorizedOperation")
    assert role_can_write(session) is False


def test_long_lived_key_is_caught():
    session = MagicMock()
    session.get_credentials.return_value.get_frozen_credentials.return_value.token = None
    session.client.return_value.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:user/me"}
    assert credential_problems(session) == ["long-lived access key in use, expected OIDC or assume role"]


def test_root_user_is_caught():
    session = MagicMock()
    session.client.return_value.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789012:root"}
    assert credential_problems(session) == ["running as the root user"]

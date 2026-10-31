"""Self-tests: a bad scp setting must be reported."""
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from checks.cloud.aws.scp import region_is_blocked, scp_problems

pytestmark = pytest.mark.selftest


def _denied(code):
    return ClientError({"Error": {"Code": code, "Message": "denied"}}, "AnyCall")


def _session_with_scp_answer(allowed):
    session = MagicMock()
    session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [{"OrganizationsDecisionDetail": {"AllowedByOrganizations": allowed}}]
    }
    return session


@pytest.mark.parametrize("code", ["AccessDenied", "AccessDeniedException", "UnauthorizedOperation"])
def test_denied_region_is_detected(code):
    session = MagicMock()
    session.client.return_value.describe_instances.side_effect = _denied(code)
    assert region_is_blocked(session, "us-west-2") is True


def test_working_region_is_not_blocked():
    assert region_is_blocked(MagicMock(), "us-east-1") is False


def test_other_errors_are_not_called_blocked():
    """Edge case: AWS being busy must not look like an SCP block."""
    session = MagicMock()
    session.client.return_value.describe_instances.side_effect = _denied("RequestLimitExceeded")
    with pytest.raises(ClientError):
        region_is_blocked(session, "us-west-2")


@pytest.mark.parametrize("expect, allowed, problem_count", [
    ("deny", False, 0),
    ("allow", True, 0),
    ("deny", True, 1),    # the SCP should block this but does not
    ("allow", False, 1),  # the SCP blocks normal work
], ids=["deny-ok", "allow-ok", "scp-too-open", "scp-too-strict"])
def test_scp_answer_is_compared_with_the_rule(expect, allowed, problem_count):
    rules = [{"action": "ec2:RunInstances", "expect": expect}]
    problems = scp_problems(_session_with_scp_answer(allowed), "arn:role", rules, "us-east-1")
    assert len(problems) == problem_count


def test_account_outside_an_organization_is_reported():
    """Edge case: with no organization there is no SCP result. That is not a pass."""
    session = MagicMock()
    session.client.return_value.simulate_principal_policy.return_value = {"EvaluationResults": [{}]}
    rules = [{"action": "ec2:RunInstances", "expect": "deny"}]
    assert "no SCP result" in scp_problems(session, "arn:role", rules, "us-east-1")[0]

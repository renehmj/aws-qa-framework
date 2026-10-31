"""Guardrail tests: prove permissions work, on both sides.

These need a real account in an OU with the SCPs attached,
so they are skipped in mock mode.
"""
import os

import pytest

from checks.auth import role_can_write
from checks.guardrails import region_is_blocked, scp_problems

pytestmark = [pytest.mark.guardrail, pytest.mark.aws]


@pytest.fixture(autouse=True)
def _live_only(live):
    if not live:
        pytest.skip("SCPs only exist in real AWS. Run with --live.")


def test_tc08_allowed_region_works(aws, config):
    """TC-08 (positive): Normal work in the allowed region is NOT blocked."""
    assert not region_is_blocked(aws, config["region"])


def test_tc09_blocked_region_is_denied(aws, config):
    """TC-09 (negative): The same call in the blocked region gets AccessDenied."""
    assert region_is_blocked(aws, config["blocked_region"])


def test_tc10_global_service_still_works(aws):
    """TC-10 (edge): Global services like IAM are not broken by the region SCP."""
    aws.client("iam").get_account_summary()


def test_tc28_test_role_can_not_write(aws):
    """TC-28 (negative): The role these tests run with is really read-only."""
    assert not role_can_write(aws)


def test_tc29_scp_permission_table(aws, config):
    """TC-29: Every SCP rule in the config allows or denies as expected."""
    principal = os.environ.get("QA_SCP_PRINCIPAL_ARN")
    if not principal:
        pytest.skip("set QA_SCP_PRINCIPAL_ARN to the role to simulate")
    problems = scp_problems(aws, principal, config["scp_rules"], config["region"])
    assert not problems, "\n".join(problems)

"""Guardrail test: the role these tests use can not change anything."""
import pytest

from checks.cloud.aws.iam import role_can_write

pytestmark = pytest.mark.guardrail


def test_tc28_test_role_can_not_write(aws):
    """TC-28 (negative): The role these tests run with is really read-only."""
    assert not role_can_write(aws)

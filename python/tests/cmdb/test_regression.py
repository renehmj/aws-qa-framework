"""Regression tests for asset data: the CMDB must match reality."""
import pytest

from checks.cmdb import cmdb_problems, running_instance_ids

pytestmark = pytest.mark.regression


def test_tc34_cmdb_matches_aws(aws, cmdb_servers, request):
    """TC-34: Every running server is in the CMDB, and every active record still exists."""
    environment = request.config.getoption("--env")
    problems = cmdb_problems(cmdb_servers, environment, running_instance_ids(aws))
    assert not problems, "\n".join(problems)

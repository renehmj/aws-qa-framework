"""Self-tests for the GitHub Environment variables."""
import re

import pytest

from framework.config import REPO_ROOT, load_config
from framework.variables import (
    EVERY_ACCOUNT,
    TEST_SERVER_ACCOUNTS,
    apply_variables,
    missing_variables,
)

pytestmark = pytest.mark.selftest

LIVE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "live.yml"
ALL_SET = {name: "value" for name in EVERY_ACCOUNT + TEST_SERVER_ACCOUNTS}
NOT_REQUIRED = {"LIVE_ENABLED", "QA_DATABASES", "QA_REQUIRED_CONNECTIONS", "QA_CMDB_URL"}


def test_missing_variable_is_caught():
    available = {name: value for name, value in ALL_SET.items() if name != "AWS_ACCOUNT_ID"}
    assert missing_variables("qa", available) == ["AWS_ACCOUNT_ID"]


def test_empty_variable_is_caught():
    """Edge case: GitHub gives a variable that was never added as an empty value."""
    assert missing_variables("qa", {**ALL_SET, "AWS_REGION": ""}) == ["AWS_REGION"]


def test_all_variables_set_is_not_flagged():
    assert missing_variables("qa", ALL_SET) == []


def test_test_server_variables_are_needed_outside_prod():
    available = {name: "value" for name in EVERY_ACCOUNT}
    assert missing_variables("stage", available) == TEST_SERVER_ACCOUNTS


def test_prod_does_not_need_test_server_variables():
    """No false alarm: production has no test server."""
    available = {name: "value" for name in EVERY_ACCOUNT}
    assert missing_variables("prod", available) == []


def test_pipeline_uses_only_variables_listed_here():
    """A new variable in the pipeline must be added to a list, so it can not be forgotten."""
    used = set(re.findall(r"vars\.(\w+)", LIVE_WORKFLOW.read_text()))
    assert used == set(ALL_SET) | NOT_REQUIRED


def test_variables_replace_config_settings():
    settings = {"region": "us-east-1", "blocked_region": "us-west-2", "required_tags": ["Owner"]}
    available = {
        "AWS_REGION": "eu-west-1",
        "QA_BLOCKED_REGION": "ap-south-1",
        "QA_DATABASES": "- name: primary\n  port: 5432",
        "QA_REQUIRED_CONNECTIONS": "- name: on-prem\n  port: 443",
    }
    assert apply_variables(settings, "qa", available) == {
        "region": "eu-west-1",
        "blocked_region": "ap-south-1",
        "required_tags": ["Owner"],
        "databases": [{"name": "primary", "port": 5432}],
        "required_connections": [{"name": "on-prem", "port": 443}],
    }


def test_empty_variable_keeps_config_setting():
    """Edge case: a variable that was never added does not wipe out the setting."""
    assert apply_variables({"region": "us-east-1"}, "qa", {"AWS_REGION": ""}) == {"region": "us-east-1"}


def test_mock_ignores_variables():
    """Edge case: AWS_REGION on a laptop must not change a fake run."""
    assert apply_variables({"region": "us-east-1"}, "mock", {"AWS_REGION": "eu-west-1"}) == {"region": "us-east-1"}


def test_badly_pasted_value_names_the_variable():
    with pytest.raises(ValueError, match="QA_DATABASES"):
        apply_variables({}, "qa", {"QA_DATABASES": "[{name: primary"})


def test_real_settings_use_the_variables(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    assert load_config("qa")["region"] == "eu-west-1"
    assert load_config("mock")["region"] != "eu-west-1"

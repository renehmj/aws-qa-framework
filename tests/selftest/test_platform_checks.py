"""Self-tests for Lambda, CMDB, connectivity, and server checks."""
import socket
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from checks.cmdb import build_inventory, cmdb_problems
from checks.connectivity import port_is_open
from checks.hosts import os_problems, scan_problems, vulnerability_problems
from checks.serverless import invoke_problems, runtime_problems

pytestmark = pytest.mark.selftest

BAD_SERVER = Path(__file__).parents[1] / "fixtures" / "hosts" / "bad" / "demo-server"
CLEAN_SERVER = Path(__file__).parents[1] / "fixtures" / "hosts" / "clean" / "demo-server"

CLOUD = {"name": "app-1", "instance_id": "i-111", "location": "cloud", "environment": "qa",
         "status": "active", "ip_address": ""}
ONPREM = {"name": "plant-gw-1", "instance_id": "", "location": "onprem", "environment": "qa",
          "status": "active", "ip_address": "10.20.0.15"}


# ---------- Lambda ----------

def test_old_lambda_runtime_is_caught(empty_mock_account, lambda_zip):
    role = empty_mock_account.client("iam").create_role(
        RoleName="old-role", AssumeRolePolicyDocument="{}"
    )["Role"]["Arn"]
    empty_mock_account.client("lambda").create_function(
        FunctionName="old-function", Runtime="python3.8", Role=role,
        Handler="handler.run", Code={"ZipFile": lambda_zip},
    )
    assert runtime_problems(empty_mock_account, ["python3.8"]) == ["old-function: uses python3.8"]


def test_crashed_lambda_is_caught():
    """Edge case: Lambda returns 200 even when the function crashes."""
    session = MagicMock()
    payload = MagicMock()
    payload.read.return_value = b"KeyError: state_of_charge"
    session.client.return_value.invoke.return_value = {
        "StatusCode": 200, "FunctionError": "Unhandled", "Payload": payload,
    }
    assert "crashed" in invoke_problems(session, "telemetry", {})[0]


# ---------- CMDB ----------

def test_server_missing_from_cmdb_is_caught():
    assert cmdb_problems([], "qa", {"i-999"}) == ["i-999: running in AWS but missing from the CMDB"]


def test_stale_cmdb_record_is_caught():
    assert cmdb_problems([CLOUD], "qa", set()) == ["i-111: active in the CMDB but not running in AWS"]


def test_matching_cmdb_is_not_flagged():
    """No false alarm: on-prem and other environments do not count against AWS."""
    other_env = {**CLOUD, "instance_id": "i-222", "environment": "prod"}
    assert cmdb_problems([CLOUD, ONPREM, other_env], "qa", {"i-111"}) == []


def test_inventory_handles_cloud_and_on_prem():
    retired = {**CLOUD, "instance_id": "i-333", "status": "retired"}
    inventory = build_inventory([CLOUD, ONPREM, retired], "qa")
    assert inventory["cloud"]["hosts"] == ["i-111"]
    assert inventory["onprem"]["hosts"] == ["plant-gw-1"]
    assert inventory["_meta"]["hostvars"]["plant-gw-1"] == {"ansible_host": "10.20.0.15", "ansible_connection": "ssh"}


# ---------- Connectivity ----------

def test_open_and_closed_ports_are_told_apart():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert port_is_open("127.0.0.1", port) is True
    assert port_is_open("127.0.0.1", port) is False


# ---------- Servers ----------

def test_wrong_server_settings_are_caught():
    expected = {"selinux": "enforcing", "ssh_root_login": "no"}
    problems = os_problems(BAD_SERVER, expected)
    assert problems == [
        "demo-server: selinux is permissive, expected enforcing",
        "demo-server: ssh_root_login is yes, expected no",
    ]


def test_failed_scan_rule_is_caught():
    problems = scan_problems(BAD_SERVER, ["high"], {})
    assert any("sshd_disable_root_login is fail" in p for p in problems)


def test_low_severity_failure_does_not_block():
    """No false alarm: a low severity failure is reported in the file, but does not fail."""
    problems = scan_problems(BAD_SERVER, ["high"], {})
    assert not any("banner_etc_issue" in p for p in problems)


def test_rule_that_errored_is_caught():
    """Edge case: a rule that could not run was not checked, so it is not a pass."""
    problems = scan_problems(BAD_SERVER, ["high"], {})
    assert any("audit_rules_time is error" in p for p in problems)


def test_waived_rule_is_not_flagged():
    problems = scan_problems(BAD_SERVER, ["high"], {"sshd_disable_root_login": "accepted risk"})
    assert not any("sshd_disable_root_login" in p for p in problems)


def test_serious_vulnerability_is_caught():
    problems = vulnerability_problems(BAD_SERVER, ["Critical", "Important"])
    assert len(problems) == 1
    assert "RHSA-2026:0001" in problems[0]


def test_clean_server_has_no_problems():
    """No false alarm: a clean server passes every check."""
    assert os_problems(CLEAN_SERVER, {"selinux": "enforcing"}) == []
    assert scan_problems(CLEAN_SERVER, ["high", "medium", "low"], {}) == []
    assert vulnerability_problems(CLEAN_SERVER, ["Critical", "Important", "Moderate", "Low"]) == []

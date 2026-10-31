"""Self-tests for the server checks. Sample scan results stand in for a real server."""
from pathlib import Path

import pytest

from checks.os.linux import os_problems, scan_problems, vulnerability_problems

pytestmark = pytest.mark.selftest

BAD_SERVER = Path(__file__).parent / "rhel" / "sample_results" / "bad" / "demo-server"
CLEAN_SERVER = Path(__file__).parent / "rhel" / "sample_results" / "clean" / "demo-server"


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

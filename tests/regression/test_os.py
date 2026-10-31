"""Regression tests for servers and RHEL images.

Ansible collects the evidence. These tests decide pass or fail.
"""
import pytest

from checks.hosts import os_problems, scan_problems, vulnerability_problems

pytestmark = [pytest.mark.regression, pytest.mark.os]


def test_tc36_server_settings_are_correct(server_results, config):
    """TC-36: OS version, SELinux, SSH rules, service, and packages are as expected."""
    problems = [p for server in server_results for p in os_problems(server, config["os_expected"])]
    assert not problems, "\n".join(problems)


def test_tc37_compliance_scan_passes(server_results, config):
    """TC-37: OpenSCAP finds no failed rule at a blocking severity."""
    scan = config["scan"]
    problems = [
        p for server in server_results
        for p in scan_problems(server, scan["fail_on_severity"], scan["waived_rules"])
    ]
    assert not problems, "\n".join(problems)


def test_tc38_no_serious_vulnerabilities(server_results, config):
    """TC-38: OpenSCAP finds no known vulnerability at a blocking severity."""
    problems = [
        p for server in server_results
        for p in vulnerability_problems(server, config["scan"]["fail_on_vulnerability"])
    ]
    assert not problems, "\n".join(problems)

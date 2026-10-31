"""Self-tests for the CMDB checks."""
import pytest

from checks.cmdb import build_inventory, cmdb_problems

pytestmark = pytest.mark.selftest

CLOUD = {"name": "app-1", "instance_id": "i-111", "location": "cloud", "environment": "qa",
         "status": "active", "ip_address": ""}
ONPREM = {"name": "plant-gw-1", "instance_id": "", "location": "onprem", "environment": "qa",
          "status": "active", "ip_address": "10.20.0.15"}


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

"""Connector to the CMDB, the company's list of servers.

It reads the ServiceNow Table API format: {"result": [ {record}, ... ]}.
Another CMDB only needs a different load_servers().
"""
import json
from pathlib import Path

import requests


def load_servers(source, token=None):
    """Read server records from a CMDB URL, or from a file for demos."""
    if source.startswith("http"):
        response = requests.get(source, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        response.raise_for_status()
        return response.json()["result"]
    return json.loads(Path(source).read_text())["result"]


def build_inventory(servers, environment):
    """Turn CMDB records into an Ansible inventory, for cloud and on-prem servers."""
    inventory = {"_meta": {"hostvars": {}}, "cloud": {"hosts": []}, "onprem": {"hosts": []}}
    for server in servers:
        if server["status"] != "active" or server["environment"] != environment:
            continue
        if server["location"] == "cloud":
            inventory["cloud"]["hosts"].append(server["instance_id"])
        else:
            inventory["onprem"]["hosts"].append(server["name"])
            inventory["_meta"]["hostvars"][server["name"]] = {
                "ansible_host": server["ip_address"],
                "ansible_connection": "ssh",
            }
    return inventory


def running_instance_ids(session):
    """Return the IDs of every EC2 instance that is not terminated."""
    ec2 = session.client("ec2")
    return {
        instance["InstanceId"]
        for page in ec2.get_paginator("describe_instances").paginate()
        for reservation in page["Reservations"]
        for instance in reservation["Instances"]
        if instance["State"]["Name"] != "terminated"
    }


def cmdb_problems(servers, environment, running_ids):
    """The CMDB and AWS must agree on which cloud servers exist."""
    recorded = {
        server["instance_id"]
        for server in servers
        if server["location"] == "cloud" and server["status"] == "active" and server["environment"] == environment
    }
    return (
        [f"{i}: running in AWS but missing from the CMDB" for i in sorted(running_ids - recorded)]
        + [f"{i}: active in the CMDB but not running in AWS" for i in sorted(recorded - running_ids)]
    )

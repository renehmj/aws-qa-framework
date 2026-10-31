"""Setup for this project: where the server records come from."""
import os

import pytest

from checks.cmdb import load_servers, running_instance_ids


@pytest.fixture(scope="session")
def cmdb_servers(aws, live):
    """Server records from the CMDB. Mock: built to match the fake account."""
    if live:
        return load_servers(os.environ["QA_CMDB_URL"], os.environ["QA_CMDB_TOKEN"])
    return [
        {"name": instance_id, "instance_id": instance_id, "location": "cloud",
         "environment": "mock", "status": "active", "ip_address": ""}
        for instance_id in running_instance_ids(aws)
    ]

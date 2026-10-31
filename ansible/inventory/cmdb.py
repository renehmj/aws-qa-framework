#!/usr/bin/env python3
"""Ansible inventory from the CMDB, for cloud and on-prem servers.

Try it:
  QA_ENV=qa QA_CMDB_URL=../python/tests/cmdb/sample_cmdb.json ansible-inventory -i inventory/cmdb.py --list
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "python"))

from checks.cmdb import build_inventory, load_servers  # noqa: E402

if __name__ == "__main__":
    servers = load_servers(os.environ["QA_CMDB_URL"], os.environ.get("QA_CMDB_TOKEN"))
    print(json.dumps(build_inventory(servers, os.environ["QA_ENV"])))

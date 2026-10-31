"""Setup for Linux servers: where the scan results are. Used by every Linux family."""
import pytest

from framework.config import PYTHON_ROOT
from framework.missing import missing


@pytest.fixture
def server_results(request, live):
    """Scan results, one folder per server. Ansible collects them in live mode."""
    folder = PYTHON_ROOT / "reports" / "hosts" if live else request.path.parent / "sample_results" / "clean"
    servers = sorted(path for path in folder.glob("*") if path.is_dir())
    if not servers:
        missing(f"no scan results in {folder}, run ansible/playbooks/scan.yml first")
    return servers

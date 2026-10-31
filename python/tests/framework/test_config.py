"""Self-tests for turning test folders on and off."""
import subprocess
import sys

import pytest

from framework.config import PYTHON_ROOT, is_turned_on, load_config

pytestmark = pytest.mark.selftest


def test_everything_is_on_by_default():
    """A new folder runs with no list to update."""
    assert is_turned_on("cloud/azure/iam/test_smoke.py", {})


def test_folder_can_be_turned_off():
    settings = {"tests_off": ["cmdb"]}
    assert not is_turned_on("cmdb/test_regression.py", settings)
    assert is_turned_on("network/test_regression.py", settings)


def test_only_listed_folders_run_when_there_is_an_on_list():
    settings = {"tests_on": ["cloud/aws"]}
    assert is_turned_on("cloud/aws/iam/test_smoke.py", settings)
    assert not is_turned_on("os/linux/rhel/test_regression.py", settings)


def test_production_only_runs_the_account_checks():
    """Safety: a new folder must not run in production until someone adds it."""
    settings = load_config("prod")
    assert is_turned_on("cloud/aws/iam/test_regression.py", settings)
    assert not is_turned_on("apps/sample_app/load/test_load.py", settings)
    assert not is_turned_on("apps/new_app/test_smoke.py", settings)


def test_mock_runs_every_folder():
    assert is_turned_on("os/linux/deb/test_regression.py", load_config("mock"))


def _pytest_on_production(folder):
    """Run pytest the way the pipeline does."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", "--live", "--env", "prod", folder,
         "-q", "-rs", "-p", "no:cacheprovider", "-o", "addopts=--import-mode=importlib"],
        cwd=PYTHON_ROOT, capture_output=True, text=True,
    ).stdout


def test_production_really_skips_a_folder_that_is_off():
    """Safety: the load test must skip, before any AWS call."""
    output = _pytest_on_production("tests/apps/sample_app/load")
    assert "1 skipped" in output, output
    assert "is turned off in this account" in output, output


def test_framework_tests_can_not_be_turned_off():
    """Safety: if the switch breaks and turns everything off, these tests must still run and fail."""
    output = _pytest_on_production("tests/framework/test_config.py")
    assert "is turned off in this account" not in output, output

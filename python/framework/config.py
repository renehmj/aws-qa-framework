"""Load the settings of an account, and decide which tests it runs."""
import os
from pathlib import Path

import yaml

from framework.variables import apply_variables

PYTHON_ROOT = Path(__file__).parents[1]
REPO_ROOT = PYTHON_ROOT.parent
CONFIG = PYTHON_ROOT / "config"
TESTS = PYTHON_ROOT / "tests"


def load_config(env):
    common = yaml.safe_load((CONFIG / "common.yaml").read_text())
    settings = {**common, **yaml.safe_load((CONFIG / f"{env}.yaml").read_text())}
    return apply_variables(settings, env, os.environ)


def is_turned_on(test_path, settings):
    """A test runs if its path starts with tests_on (default: every path), and not with tests_off."""
    turned_on = tuple(settings.get("tests_on", [""]))
    turned_off = tuple(settings.get("tests_off", []))
    return test_path.startswith(turned_on) and not test_path.startswith(turned_off)

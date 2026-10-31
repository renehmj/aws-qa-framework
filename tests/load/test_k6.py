"""Load test: can the API keep up, and stay correct, under traffic?"""
from pathlib import Path

import pytest

from checks.load import k6_problems

pytestmark = pytest.mark.load

SCRIPT = Path(__file__).parent / "api_load.js"


def test_tc30_api_meets_load_targets(k6, api, config, tmp_path):
    """TC-30: Errors, speed, and correct answers stay within the targets."""
    settings = config["load"]
    problems = k6_problems(
        SCRIPT, api["url"], api["token"], settings["vus"], settings["duration"], tmp_path / "summary.json"
    )
    assert not problems, "\n".join(problems)

"""Load test: can the API keep up, and stay correct, under traffic?"""
import pytest

from checks.shared.load import k6_problems
from framework.config import REPO_ROOT

pytestmark = pytest.mark.load

SCRIPT = REPO_ROOT / "k6" / "sample_app_load.js"


def test_tc30_api_meets_load_targets(k6, api, config, tmp_path):
    """TC-30: Errors, speed, and correct answers stay within the targets."""
    settings = config["load"]
    problems = k6_problems(
        SCRIPT, api["url"], api["token"], settings["vus"], settings["duration"], tmp_path / "summary.json"
    )
    assert not problems, "\n".join(problems)

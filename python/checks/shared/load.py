import json
import os
import subprocess

THRESHOLD_FAILED = 99  # the k6 exit code when a threshold is missed


def k6_problems(script, url, token, vus, duration, summary_file):
    """Run a k6 script. Return the thresholds it missed."""
    env = {**os.environ, "TARGET_URL": url, "API_TOKEN": token, "VUS": str(vus), "DURATION": duration}
    result = subprocess.run(
        ["k6", "run", "--quiet", f"--summary-export={summary_file}", str(script)],
        env=env, capture_output=True, text=True,
    )
    if result.returncode not in (0, THRESHOLD_FAILED):
        raise RuntimeError(f"k6 could not run: {result.stderr}")

    with open(summary_file) as f:
        metrics = json.load(f)["metrics"]
    return [
        f"{metric}: missed threshold {threshold}"
        for metric, data in metrics.items()
        for threshold, failed in data.get("thresholds", {}).items()
        if failed
    ]

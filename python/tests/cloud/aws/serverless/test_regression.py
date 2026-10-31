"""Regression test: no Lambda function uses an old runtime."""
import pytest

from checks.cloud.aws.serverless import runtime_problems

pytestmark = pytest.mark.regression


def test_tc31_lambda_runtimes_are_supported(aws, settings):
    """TC-31: No Lambda function uses an out-of-support runtime."""
    problems = runtime_problems(aws, settings["blocked_lambda_runtimes"])
    assert not problems, "\n".join(problems)

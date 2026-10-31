"""Regression tests for Lambda: supported runtime, and the function works."""
import json
import os

import pytest

from checks.serverless import invoke_problems, runtime_problems
from sample_app.lambda_handler import handler

pytestmark = [pytest.mark.regression, pytest.mark.serverless]

GOOD_READING = {"unit_id": "UPS-001", "state_of_charge": 15, "voltage_v": 480, "current_a": 100}


def test_tc31_lambda_runtimes_are_supported(aws, config):
    """TC-31: No Lambda function uses an out-of-support runtime."""
    problems = runtime_problems(aws, config["blocked_lambda_runtimes"])
    assert not problems, "\n".join(problems)


def test_tc32_lambda_answers(aws, config):
    """TC-32: The deployed function can be called and does not crash."""
    name = os.environ.get("QA_LAMBDA_NAME") or config["lambda_function"]
    problems = invoke_problems(aws, name, {"body": json.dumps(GOOD_READING)})
    assert not problems, "\n".join(problems)


def test_tc33_lambda_code_accepts_good_reading():
    """TC-33 (positive): The handler saves a good reading."""
    response = handler({"body": json.dumps(GOOD_READING)}, None)
    assert response["statusCode"] == 201
    assert json.loads(response["body"])["status"] == "low"


def test_tc33_lambda_code_refuses_bad_reading():
    """TC-33 (negative): The handler refuses a bad reading."""
    response = handler({"body": json.dumps({**GOOD_READING, "state_of_charge": 101})}, None)
    assert response["statusCode"] == 400

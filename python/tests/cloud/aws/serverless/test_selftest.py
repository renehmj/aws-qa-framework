"""Self-tests: a bad serverless setting must be reported."""
from unittest.mock import MagicMock

import pytest

from checks.cloud.aws.serverless import invoke_problems, runtime_problems

pytestmark = pytest.mark.selftest


def test_old_lambda_runtime_is_caught(empty_mock_account, lambda_zip):
    role = empty_mock_account.client("iam").create_role(
        RoleName="old-role", AssumeRolePolicyDocument="{}"
    )["Role"]["Arn"]
    empty_mock_account.client("lambda").create_function(
        FunctionName="old-function", Runtime="python3.8", Role=role,
        Handler="handler.run", Code={"ZipFile": lambda_zip},
    )
    assert runtime_problems(empty_mock_account, ["python3.8"]) == ["old-function: uses python3.8"]


def test_crashed_lambda_is_caught():
    """Edge case: Lambda returns 200 even when the function crashes."""
    session = MagicMock()
    payload = MagicMock()
    payload.read.return_value = b"KeyError: state_of_charge"
    session.client.return_value.invoke.return_value = {
        "StatusCode": 200, "FunctionError": "Unhandled", "Payload": payload,
    }
    assert "crashed" in invoke_problems(session, "telemetry", {})[0]

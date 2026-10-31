import json


def runtime_problems(session, blocked_runtimes):
    """Return Lambda functions on a runtime we no longer allow."""
    client = session.client("lambda")
    problems = []
    for page in client.get_paginator("list_functions").paginate():
        for function in page["Functions"]:
            if function.get("Runtime") in blocked_runtimes:
                problems.append(f"{function['FunctionName']}: uses {function['Runtime']}")
    return problems


def invoke_problems(session, function_name, payload):
    """Call a function. A crash still returns 200, so FunctionError is the real signal."""
    response = session.client("lambda").invoke(FunctionName=function_name, Payload=json.dumps(payload))
    if response.get("FunctionError"):
        return [f"{function_name}: crashed: {response['Payload'].read().decode()[:200]}"]
    if response["StatusCode"] != 200:
        return [f"{function_name}: returned {response['StatusCode']}"]
    return []

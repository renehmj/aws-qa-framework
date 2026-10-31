"""GitHub Environment variables: which ones an account needs, and what they replace."""
import json
import os
import sys

import yaml

EVERY_ACCOUNT = ["AWS_ACCOUNT_ID", "AWS_REGION", "QA_READONLY_ROLE_ARN", "QA_BLOCKED_REGION", "QA_SCP_PRINCIPAL_ARN"]
TEST_SERVER_ACCOUNTS = ["QA_TEST_ENV_ROLE_ARN", "QA_LAMBDA_ROLE_ARN", "QA_SSM_BUCKET"]

# Config setting: the variable that replaces it.
REPLACES = {
    "region": "AWS_REGION",
    "blocked_region": "QA_BLOCKED_REGION",
    "databases": "QA_DATABASES",
    "required_connections": "QA_REQUIRED_CONNECTIONS",
}


def missing_variables(environment, available):
    """Return the variables this account still needs. An empty value counts as missing."""
    required = EVERY_ACCOUNT if environment == "prod" else EVERY_ACCOUNT + TEST_SERVER_ACCOUNTS
    return [name for name in required if not available.get(name)]


def _parse(name, value):
    try:
        return yaml.safe_load(value)
    except yaml.YAMLError as error:
        raise ValueError(f"The variable {name} is not valid YAML: {error}") from error


def apply_variables(settings, environment, available):
    """Return the settings with variables applied. Mock ignores them, so it runs the same everywhere."""
    if environment == "mock":
        return settings
    replaced = {key: _parse(name, available[name]) for key, name in REPLACES.items() if available.get(name)}
    return {**settings, **replaced}


if __name__ == "__main__":
    environment, variables = sys.argv[1], json.loads(os.environ["GITHUB_VARS"])
    missing = missing_variables(environment, variables)
    for name in missing:
        print(f"::error::Add the variable {name} to the GitHub Environment {environment}. See docs/OIDC_SETUP.md.")
    apply_variables({}, environment, variables)   # a badly pasted value stops the run here too
    sys.exit(1 if missing else 0)

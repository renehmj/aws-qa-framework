"""Shared setup for every test (pytest fixtures).

Two modes:
  mock (default)  - fake AWS, the sample API on this machine. No account needed.
  live (--live)   - a real AWS account. Credentials come from OIDC or SSO.
                    Nothing is ever stored in code.

A fixture that only one folder needs is in that folder's own conftest.py.
"""
import io
import os
import shutil
import zipfile

import boto3
import psycopg
import pytest
import yaml

from checks.shared.database import connect, databases_for, password_for
from framework.config import CONFIG, TESTS, is_turned_on, load_config
from framework.missing import missing


def pytest_addoption(parser):
    parser.addoption("--env", default="mock", help="config file to use: qa, dev, stage, prod")
    parser.addoption("--live", action="store_true", help="run against real AWS")


def pytest_configure(config):
    env = config.getoption("--env")
    if config.getoption("--live") == (env == "mock"):
        raise pytest.UsageError("Use 'pytest' for mock, or 'pytest --live --env qa' for a real account.")
    if not (CONFIG / f"{env}.yaml").exists():
        raise pytest.UsageError(f"There is no config/{env}.yaml file.")


def pytest_collection_modifyitems(config, items):
    """Skip tests in any folder this account has turned off.

    The framework's own tests always run, so a broken switch can not hide itself.
    """
    settings = load_config(config.getoption("--env"))
    for item in items:
        path = item.path.relative_to(TESTS).as_posix()
        if not path.startswith("framework/") and not is_turned_on(path, settings):
            item.add_marker(pytest.mark.skip(reason=f"{path} is turned off in this account"))


@pytest.fixture(autouse=True)
def _each_level_runs_in_its_mode(request, live):
    if live and request.node.get_closest_marker("selftest"):
        pytest.skip("self-tests build bad things, so they only run in mock mode")
    if not live and request.node.get_closest_marker("guardrail"):
        pytest.skip("SCPs only exist in real AWS. Run with --live.")


@pytest.fixture(scope="session")
def config(request):
    """The settings of this account."""
    return load_config(request.config.getoption("--env"))


@pytest.fixture
def settings(request, config):
    """The settings.yaml next to this test, plus this account's settings. The account wins."""
    path = request.path.parent / "settings.yaml"
    return {**yaml.safe_load(path.read_text()), **config}


@pytest.fixture(scope="session")
def live(request):
    return request.config.getoption("--live")


# ---------- AWS ----------

def _fake_credentials():
    for key, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
    }.items():
        os.environ[key] = value


def seed_compliant_env(session, config):
    """Build a small fake account that follows every rule."""
    ec2 = session.client("ec2")
    tags = [{"Key": k, "Value": "demo"} for k in config["required_tags"]]
    ec2.run_instances(
        ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro",
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}],
    )

    s3 = session.client("s3")
    s3.create_bucket(Bucket="demo-logs-bucket")
    s3.put_public_access_block(
        Bucket="demo-logs-bucket",
        PublicAccessBlockConfiguration={k: True for k in (
            "BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")},
    )
    s3.put_bucket_encryption(
        Bucket="demo-logs-bucket",
        ServerSideEncryptionConfiguration={"Rules": [
            {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]},
    )

    ct = session.client("cloudtrail")
    ct.create_trail(Name="org-trail", S3BucketName="demo-logs-bucket")
    ct.start_logging(Name="org-trail")

    role = session.client("iam").create_role(
        RoleName="demo-lambda-role", AssumeRolePolicyDocument="{}"
    )["Role"]["Arn"]
    session.client("lambda").create_function(
        FunctionName="demo-telemetry", Runtime="python3.12", Role=role,
        Handler="sample_app.lambda_handler.handler", Code={"ZipFile": fake_zip()},
    )


def fake_zip():
    """Fake AWS needs a zip file for a Lambda function, but does not run it."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("handler.py", "")
    return buffer.getvalue()


@pytest.fixture(scope="session")
def aws(config, live):
    """A boto3 session for the target environment."""
    if live:
        yield boto3.Session(region_name=config["region"])
        return

    from moto import mock_aws

    _fake_credentials()
    with mock_aws(config={"lambda": {"use_docker": False}}):
        session = boto3.Session(region_name=config["region"])
        seed_compliant_env(session, config)
        yield session


@pytest.fixture
def lambda_zip():
    return fake_zip()


_account_counter = iter(range(100000000000, 999999999999))


@pytest.fixture
def empty_mock_account(aws, config):
    """A brand-new, empty fake account for each self-test (mock only).

    We assume a role into a new account ID, just like live mode assumes
    a read-only role into each real account. Nothing leaks between tests.
    """
    account_id = str(next(_account_counter))
    creds = aws.client("sts").assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/qa-selftest",
        RoleSessionName="selftest",
    )["Credentials"]
    yield boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=config["region"],
    )


# ---------- Databases ----------

@pytest.fixture(scope="module")
def database_settings(request, config):
    """The databases for this test."""
    found = databases_for(config.get("databases", []), request.path)
    if not found:
        missing("this test needs a database, but none are set, add the QA_DATABASES variable")
    return found


@pytest.fixture(scope="module")
def databases(database_settings, aws):
    """One read-only connection per database, as {name: connection}."""
    try:
        conns = {db["name"]: connect(db, password_for(db, aws)) for db in database_settings}
    except psycopg.OperationalError as error:
        missing(f"cannot reach the databases, try 'docker compose up -d': {error}")
    yield conns
    for conn in conns.values():
        conn.close()


# ---------- Load ----------

@pytest.fixture
def k6():
    if not shutil.which("k6"):
        missing("k6 is not installed")

"""Shared setup for every test (pytest fixtures).

Two modes:
  mock (default)  - fake AWS, the sample API on this machine. No account needed.
  live (--live)   - a real AWS account. Credentials come from OIDC or SSO.
                    Nothing is ever stored in code.
"""
import io
import os
import shutil
import zipfile
from pathlib import Path
from threading import Thread

import boto3
import psycopg
import pytest
import yaml

from checks.cmdb import load_servers, running_instance_ids
from checks.database import connect, password_for
from checks.variables import apply_variables
from sample_app.server import make_server

ROOT = Path(__file__).parent
MODULES = {"aws", "code", "api", "connectivity", "database", "os", "serverless", "cmdb", "load"}


def pytest_addoption(parser):
    parser.addoption("--env", default="mock", help="config file to use: qa, dev, stage, prod")
    parser.addoption("--live", action="store_true", help="run against real AWS")


def pytest_configure(config):
    env = config.getoption("--env")
    if config.getoption("--live") == (env == "mock"):
        raise pytest.UsageError("Use 'pytest' for mock, or 'pytest --live --env qa' for a real account.")
    if not (ROOT / "config" / f"{env}.yaml").exists():
        raise pytest.UsageError(f"There is no config/{env}.yaml file.")


def pytest_collection_modifyitems(config, items):
    """Skip tests for any module this environment has turned off."""
    settings = load_config(config.getoption("--env"))
    for item in items:
        for marker in item.iter_markers():
            if marker.name in MODULES and marker.name not in settings["modules"]:
                item.add_marker(pytest.mark.skip(reason=f"{marker.name} module is off in this environment"))


def load_config(env):
    common = yaml.safe_load((ROOT / "config" / "common.yaml").read_text())
    settings = {**common, **yaml.safe_load((ROOT / "config" / f"{env}.yaml").read_text())}
    return apply_variables(settings, env, os.environ)


def missing(reason):
    """A missing tool is a skip on a laptop, but a failure in the pipeline."""
    if os.environ.get("CI"):
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def config(request):
    return load_config(request.config.getoption("--env"))


@pytest.fixture(scope="session")
def live(request):
    return request.config.getoption("--live")


@pytest.fixture
def settings_for():
    """Load the settings of any environment, for the self-tests."""
    return load_config


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


# ---------- API ----------

@pytest.fixture(scope="session")
def api(live):
    """Where the API is. Live: the test server. Mock: the same code, on this machine."""
    if live:
        yield {"url": os.environ["QA_API_URL"], "token": os.environ["QA_API_TOKEN"]}
        return

    server = make_server(port=0, token="local-test-token")
    Thread(target=server.serve_forever, daemon=True).start()
    yield {"url": f"http://127.0.0.1:{server.server_port}", "token": "local-test-token"}
    server.shutdown()


# ---------- Databases ----------

@pytest.fixture(scope="session")
def databases(config, aws):
    """One read-only connection per database, as {name: connection}."""
    if not config.get("databases"):
        missing("the database module is on, but no databases are set, add the QA_DATABASES variable")
    try:
        conns = {db["name"]: connect(db, password_for(db, aws)) for db in config["databases"]}
    except psycopg.OperationalError as error:
        missing(f"cannot reach the databases, try 'docker compose up -d': {error}")
    yield conns
    for conn in conns.values():
        conn.close()


# ---------- Servers ----------

@pytest.fixture(scope="session")
def server_results(live):
    """Scan results, one folder per server. Ansible collects them in live mode."""
    folder = ROOT / "reports" / "hosts" if live else ROOT / "tests" / "fixtures" / "hosts" / "clean"
    servers = sorted(path for path in folder.glob("*") if path.is_dir())
    if not servers:
        missing(f"no scan results in {folder}, run ansible/playbooks/scan.yml first")
    return servers


# ---------- CMDB ----------

@pytest.fixture(scope="session")
def cmdb_servers(aws, live):
    """Server records from the CMDB. Mock: built to match the fake account."""
    if live:
        return load_servers(os.environ["QA_CMDB_URL"], os.environ["QA_CMDB_TOKEN"])
    return [
        {"name": instance_id, "instance_id": instance_id, "location": "cloud",
         "environment": "mock", "status": "active", "ip_address": ""}
        for instance_id in running_instance_ids(aws)
    ]


# ---------- Load ----------

@pytest.fixture
def k6():
    if not shutil.which("k6"):
        missing("k6 is not installed")

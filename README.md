# AWS QA Framework

A modular Python test framework for cloud infrastructure, servers, APIs, databases,
and permissions. Built with **pytest** and **boto3**. It is built to run from **GitHub Actions**
across QA, DEV, STAGE, and PROD accounts, with no stored credentials.

```
GitHub Actions  ──OIDC, short-lived credentials──▶  AWS account
      │
      ├─ Terraform   creates a RHEL server and a Lambda function
      ├─ Ansible     configures the server and scans it with OpenSCAP
      ├─ pytest      smoke  ▶  regression  ▶  load (k6)
      └─ Terraform   destroys everything, even if tests fail
```

**Each tool does one job.** Python decides pass or fail for everything. Terraform builds.
Ansible reaches servers and collects evidence. k6 creates traffic.

## Status

This is a personal project, to show how I approach testing a cloud platform.
It is not connected to any company's systems.

**Tested:** the full suite with fake AWS, real PostgreSQL, and real k6, on macOS and Linux.
Ansible and OpenSCAP on a real Rocky Linux 9 server.

**Not run yet:** real AWS accounts (Terraform, OIDC, Systems Manager, SCPs, and RDS login),
a real RHEL image, and a live CMDB. The first real run may need small fixes.

## How I approached it

One question drives the design: after a change, what could be broken, and how would we know?

- **Start from the risks.** The [test plan](docs/TEST_PLAN.md) lists what could go wrong and which test covers it.
- **Use one pattern.** A check returns a list of problems. Empty means pass. AWS, database, and server tests all read the same way.
- **Test the tests.** A test that can not fail proves nothing. Self-tests create bad data on purpose and confirm the check reports it.
- **A skip is not a pass.** In the pipeline, a missing tool or database fails the run.
- **Same tests in every account.** Only the config and the GitHub variables change. Production stays read-only.

## Where to start reading

Follow one check from start to end. The tag check is the smallest.

| Step | File | What to look for |
|---|---|---|
| 1 | [checks/tags.py](checks/tags.py) | The check. It returns a list of problems. |
| 2 | [tests/regression/test_compliance.py](tests/regression/test_compliance.py) | The test. It calls the check and fails if the list is not empty. |
| 3 | [tests/selftest/test_checks_catch_problems.py](tests/selftest/test_checks_catch_problems.py) | The proof. An untagged server must be reported. |
| 4 | [conftest.py](conftest.py) | The switch between fake AWS and a real account. |
| 5 | [config/](config/) | What to test in each account. |
| 6 | [.github/workflows/live.yml](.github/workflows/live.yml) | The full flow: build, configure, test, destroy. |

Most other modules follow the same pattern.

## Try it

No AWS account needed. You need Python 3.12 and Docker.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d    # two sample PostgreSQL databases
brew install k6         # for the load test

pytest                  # everything, with fake AWS
pytest -m smoke         # one level
pytest -m database      # one module
```

Without Docker or k6 those tests skip on a laptop. In the pipeline they fail,
so a missing tool can never look like a pass.

## Test levels

| Level | Question it answers | Runs |
|---|---|---|
| **Smoke** | Is everything alive? | First. If it fails, stop. |
| **Regression** | Did a change break anything? | After smoke passes |
| **Guardrail** | Do SCPs and permissions hold, on both sides? | Real account only |
| **Load** | Does it stay fast and correct under traffic? | Last |
| **Self-test** | Do the checks really catch problems? | Fake AWS only |

## Modules

Each module is one area to test. An environment turns modules on or off in its config file.

| Module | What it tests | Tools |
|---|---|---|
| `aws` | Credentials, CloudTrail, tags, security groups, S3, MFA, SCPs | boto3 |
| `code` | Application rules: boundaries and bad input | pytest |
| `api` | Right answers, right refusals, login required | requests |
| `connectivity` | Hybrid paths work, admin ports stay closed | socket |
| `database` | Logins, read-only access, data quality, same data on every database | psycopg, SQL |
| `os` | Server and RHEL image settings, compliance, vulnerabilities | Ansible, OpenSCAP |
| `serverless` | Lambda runtimes, and the function really works | boto3 |
| `cmdb` | The CMDB and AWS agree on which servers exist | requests, boto3 |
| `load` | Errors, speed, and correct answers under traffic | k6 |

**To add a module:** add one file in `checks/`, one test file with its marker,
and add its name to the environments that need it. Nothing else changes.

## Accounts

The tests are the same everywhere. Two things change for each account:

- **What to test** is a file in `config/`, so a change gets reviewed.
- **Where to test** is a set of GitHub Environment variables: the account, roles, region, and hosts.
  No account details are stored in this repo. The [setup guide](docs/OIDC_SETUP.md#step-3-add-the-variables-to-the-github-environment) lists them.

| Environment | Modules | Test server | Load |
|---|---|---|---|
| `qa` | All, once real databases and a CMDB are connected | Yes | 20 users, 1 minute |
| `dev` | Same as `qa` | Yes | 5 users, 30 seconds |
| `stage` | Same as `qa` | Yes | 50 users, 5 minutes |
| `prod` | `aws` only, read-only | No, on purpose | No, on purpose |

```bash
pytest --live --env qa -m "smoke and aws"
```

## Folder layout

```
checks/        reusable checks. Most return a list of problems. Empty = pass.
tests/         one folder per test level
sample_app/    a small battery telemetry API and Lambda, the code under test
config/        one file per environment, plus common.yaml
ansible/       server configuration, OpenSCAP scan, CMDB inventory
terraform/     oidc = one-time account setup. test_env = short-lived test server.
docs/          test plan, test cases, security, OIDC setup guide
.github/       ci.yml on every change. live.yml for real accounts.
```

## Documents

- [Test plan](docs/TEST_PLAN.md): scope, risks, entry and exit rules, coverage
- [Test cases](docs/TEST_CASES.md): every case with steps and expected results
- [Security](docs/SECURITY.md): how credentials and access are handled
- [OIDC setup guide](docs/OIDC_SETUP.md): connect GitHub Actions to AWS, step by step

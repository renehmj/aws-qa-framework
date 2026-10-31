# AWS QA Framework

A modular Python test framework for cloud platforms, servers, applications, and databases.
It is built to run from **GitHub Actions** across QA, DEV, STAGE, and PROD accounts, with no stored credentials.

## The big picture

```mermaid
flowchart TB
    vars["<b>GitHub Environment variables</b><br/>One set for each account"] --> actions["<b>GitHub Actions</b><br/>Python, Terraform, Ansible, k6"]

    actions -- "OIDC login,<br/>no stored keys" --> controls
    actions -- "Build, scan,<br/>and test" --> temp
    actions -. "Compare<br/>data" .-> db
    actions -. "Compare<br/>servers" .-> cmdb
    actions -. "Check<br/>the path" .-> onprem

    subgraph cloud["Cloud account: QA, DEV, STAGE, or PROD"]
        controls["<b>Cloud controls</b><br/>IAM, SCPs, network,<br/>storage, tags"]
        subgraph temp["Built and destroyed in each run"]
            server["<b>Linux server</b><br/>OS settings,<br/>OpenSCAP"]
            app["<b>Application</b><br/>API and Lambda"]
        end
        db[("<b>Databases</b><br/>Same data on each")]
    end

    cmdb["<b>CMDB</b><br/>Server inventory"]
    onprem["<b>On-prem</b><br/>Hybrid paths"]

    classDef tool fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef target fill:#f3f4f6,stroke:#6b7280,color:#111827
    classDef short fill:#fef3c7,stroke:#d97706,color:#111827
    class vars,actions tool
    class controls,db,cmdb,onprem target
    class server,app short
    style cloud fill:transparent,stroke:#6b7280
    style temp fill:transparent,stroke:#d97706,stroke-dasharray:5 5
```

Dashed lines are optional. Each one turns on when that system is connected.

**Each tool does one job.** Python decides pass or fail for everything. Terraform builds.
Ansible reaches servers and collects evidence. k6 creates traffic.

## What a run does

```mermaid
flowchart TB
    subgraph job1["Job 1: test the account, read-only"]
        direction LR
        a1["<b>1. Check</b><br/>GitHub variables"] --> a2["<b>2. Log in</b><br/>OIDC, read-only role"] --> a3["<b>3. Test</b><br/>Smoke, regression,<br/>SCP guardrails"]
    end

    subgraph job2["Job 2: test a short-lived server"]
        direction LR
        b1["<b>4. Build</b><br/>OIDC test role,<br/>Terraform"] --> b2["<b>5. Scan</b><br/>Ansible, OpenSCAP"] --> b3["<b>6. Test</b><br/>Smoke, regression,<br/>load with k6"] --> b4["<b>7. Destroy</b><br/>Terraform, runs<br/>even if a test fails"]
    end

    job1 -- "Passed, and not production" --> job2

    classDef step fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef last fill:#fef3c7,stroke:#d97706,color:#111827
    class a1,a2,a3,b1,b2,b3 step
    class b4 last
    style job1 fill:transparent,stroke:#2563eb
    style job2 fill:transparent,stroke:#2563eb
```

This is [live.yml](.github/workflows/live.yml), for real accounts. It stays off until you turn it on.
[ci.yml](.github/workflows/ci.yml) runs on every change, with fake AWS and sample databases.

## Status

This is a personal project, to show how I approach testing a cloud platform.
It is not connected to any company's systems.

**Tested:** the full suite with fake AWS, real PostgreSQL, and real k6, on macOS and Linux.
Ansible and OpenSCAP on a real Rocky Linux 9 server.

**Not run yet:** real AWS accounts (Terraform, OIDC, Systems Manager, SCPs, and RDS login),
a real RHEL image, a real Debian server, and a live CMDB. The first real run may need small fixes.

## Where everything is

There is one folder for each tool. In Python, `checks/` and `tests/` use the same folder names.

```
ansible/                 Servers: inventory and playbooks
docs/                    Test plan, test cases, security, setup guide
k6/                      Load test scripts
sample_app/              A small sample app, so the tests have something to test
terraform/
└── aws/                 One folder for each cloud
    ├── oidc/            One-time account setup
    └── test_env/        The short-lived test server
python/
├── config/              One file for each account
├── framework/           The main framework: settings, variables, on and off switches
├── checks/              HOW to check
│   ├── cloud/aws/       audit, iam, network, scp, serverless, storage, tags
│   ├── os/              linux
│   ├── shared/          database, load, ports
│   └── cmdb.py
└── tests/               WHAT to check. All tests are here.
    ├── apps/
    │   └── sample_app/  api, code, database, load, serverless
    ├── cloud/
    │   └── aws/         audit, iam, network, scp, serverless, storage, tags
    ├── cmdb/
    ├── framework/       Tests for the framework itself
    ├── onprem/
    │   └── network/
    ├── os/
    │   └── linux/       rhel, deb, ports
    └── shared/          Tests for the shared checks
```

## How one check works

```mermaid
flowchart TB
    subgraph test["The test: tests/cloud/aws/tags/test_regression.py"]
        direction LR
        t1["<b>AWS account</b>"] --> t2["<b>Check</b><br/>checks/cloud/aws/tags.py"] --> t3["<b>List of problems</b><br/>Empty means pass"]
    end

    subgraph proof["The proof: tests/cloud/aws/tags/test_selftest.py"]
        direction LR
        p1["<b>Fake account</b><br/>A bad server on purpose"] --> p2["<b>Same check</b><br/>checks/cloud/aws/tags.py"] --> p3["<b>List of problems</b><br/>Must name the bad server"]
    end

    test ~~~ proof

    classDef step fill:#dbeafe,stroke:#2563eb,color:#111827
    classDef bad fill:#fef3c7,stroke:#d97706,color:#111827
    class t1,t2,t3,p2,p3 step
    class p1 bad
    style test fill:transparent,stroke:#2563eb
    style proof fill:transparent,stroke:#d97706
```

**To follow the code,** open these in order:

1. [checks/cloud/aws/tags.py](python/checks/cloud/aws/tags.py): the check
2. [tests/cloud/aws/tags/test_regression.py](python/tests/cloud/aws/tags/test_regression.py): the test
3. [tests/cloud/aws/tags/test_selftest.py](python/tests/cloud/aws/tags/test_selftest.py): the proof
4. [conftest.py](python/conftest.py): the switch between fake AWS and a real account
5. [config/](python/config/): what each account runs

## Add something new

Add a folder. pytest finds it, and there is no list to update.

| You want to add | Tests go in `python/tests/` | Checks go in `python/checks/` |
|---|---|---|
| A test for AWS IAM | `cloud/aws/iam/` | `cloud/aws/iam.py` |
| A new AWS topic | `cloud/aws/<topic>/` | `cloud/aws/<topic>.py` |
| Another cloud, such as Azure or OCI | `cloud/azure/iam/` | `cloud/azure/iam.py` |
| An app, such as web or mobile | `apps/web/` | `shared/`, or a new file |
| A Linux family, or Windows | `os/linux/<family>/`, `os/windows/` | `os/windows.py` |
| An on-prem system | `onprem/<topic>/` | `onprem/<topic>.py` |

A folder can have its own `settings.yaml` for its rules, and its own `conftest.py` for its setup.

A new folder runs everywhere except production. To run it in production, add it to `tests_on` in
[prod.yaml](python/config/prod.yaml). Another cloud also needs its own login in `live.yml`, and its
own folder in `terraform/`.

## How I approached it

One question drives the design: after a change, what could be broken, and how would we know?

- **Start from the risks.** The [test plan](docs/TEST_PLAN.md) lists what could go wrong and which test covers it.
- **Use one pattern.** A check returns a list of problems. Empty means pass. Most tests read the same way.
- **Test the tests.** A test that can not fail proves nothing. Self-tests create bad data on purpose and confirm the check reports it.
- **A skip is not a pass.** In the pipeline, a missing tool, database, or variable fails the run.
- **Same tests in every account.** Only the config and the GitHub variables change. Production stays read-only.

## Try it

No AWS account needed. You need Python 3.12 and Docker.

```bash
docker compose up -d         # two sample PostgreSQL databases
brew install k6              # for the load test

cd python
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest                       # everything, with fake AWS
pytest -m smoke              # one level
pytest tests/cloud/aws/iam   # one folder
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

## Accounts

The tests are the same everywhere. Two things change for each account:

- **What to test** is a file in [python/config/](python/config/), so a change gets reviewed.
- **Where to test** is a set of GitHub Environment variables: the account, roles, region, and hosts.
  No account details are stored in this repo. The [setup guide](docs/OIDC_SETUP.md#step-3-add-the-variables-to-the-github-environment) lists them.

| Account | What runs | Load test |
|---|---|---|
| `qa` | Every folder, except those in `tests_off` | 20 users, 1 minute |
| `dev` | Same as `qa` | 5 users, 30 seconds |
| `stage` | Same as `qa` | 50 users, 5 minutes |
| `prod` | Only `cloud/aws`, read-only. No test server, on purpose. | No, on purpose |

## Documents

- [Test plan](docs/TEST_PLAN.md): scope, risks, entry and exit rules, coverage
- [Test cases](docs/TEST_CASES.md): every case with steps and expected results
- [Security](docs/SECURITY.md): how credentials and access are handled
- [OIDC setup guide](docs/OIDC_SETUP.md): connect GitHub Actions to AWS, step by step

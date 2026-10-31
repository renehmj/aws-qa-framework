# Test Plan

## Goal

Find problems before a change reaches production, and prove that the controls
we rely on still work: access, network, data, and servers.

## How the tests are designed

Every important area is tested from more than one side.

| Technique | Question | Example |
|---|---|---|
| **Positive** | Does the right thing work? | TC-08: the allowed region works |
| **Negative** | Is the wrong thing refused? | TC-09: the blocked region is denied |
| **Boundary** | Is the limit exactly right? | TC-14: 10% is low, 9.9% is critical |
| **Edge** | Does an unusual case behave? | TC-10: global services still work under a region SCP |
| **No false alarm** | Do we stay quiet when all is well? | SSH from a private range is not flagged |

A test that can not fail proves nothing. So the **self-tests** build bad resources
and bad data on purpose, and confirm each check reports them.

## Risks, and what covers them

| Risk | Impact | Covered by |
|---|---|---|
| An SCP is changed and stops blocking | Security control is lost, and nobody notices | TC-09, TC-29 |
| An SCP is too strict | Normal work stops | TC-08, TC-10, TC-29 |
| Untagged resources | Costs can not be assigned | TC-03, TC-29 |
| Admin port open to the internet | Direct attack path | TC-04, TC-21 |
| A deployment reaches one database but not the other | Users get different answers | TC-27 |
| A new server image breaks a standard | Every server built from it inherits the problem | TC-36, TC-37, TC-38 |
| The CMDB is out of date | Decisions are made on wrong data | TC-34 |
| The tests themselves have too much access | The tests become a risk | TC-11, TC-23, TC-28 |
| A check silently stops working | False confidence | Self-tests |

## Entry and exit rules

| Level | Starts when | Passes when |
|---|---|---|
| Smoke | The environment is deployed | All pass. Otherwise stop here. |
| Regression | Smoke passes | All pass, or the failure has a written waiver |
| Guardrail | Account is a member of the organization | All pass |
| Load | Regression passes | Under 1% errors, 95% of requests under 500 ms, over 99% correct answers |

**A skip is not a pass.** In the pipeline, a missing tool, database, or GitHub variable
fails the run. The only allowed skips are folders an account has turned off on purpose,
and TC-35 when an environment has no hybrid paths.

**Waivers need a reason.** An accepted OpenSCAP rule is listed in `settings.yaml` for that Linux family,
with its reason, so a reviewer can challenge it.

## When a test fails

1. Read the message. Each check names the resource and the problem.
2. Open a bug with the test case ID and the report from the pipeline.
3. The owner fixes it. For a server, the scan also produces a fix playbook for the owner.
4. Run the same test again. The bug closes only when it passes.

QA does not apply fixes. Keeping that separate means a test result can be trusted.

## After a deployment

Another pipeline can call `live.yml` with the environment name. It runs the same levels.

## Migration from legacy to cloud

TC-27 compares any list of databases. To check a migration, list the old database
and the new one in the config. TC-34 finds servers that exist in only one place.

## Coverage

| Area | Status | Test cases |
|---|---|---|
| IAM, SCP guardrails, tag enforcement | Built | TC-01, TC-07 to TC-11, TC-28, TC-29 |
| Multi-account | Built | One config and one GitHub Environment per account |
| Deployments and configuration | Built | TC-12, TC-36 |
| Network | Partly built | TC-04, TC-21, TC-35 |
| Security findings and retest | Partly built | TC-37, TC-38. Rerun confirms closure. |
| CI/CD quality gates | Built | Smoke, regression, and load stop the pipeline in order |
| Database checks | Built | TC-13, TC-22 to TC-27 |
| Performance | Built | TC-30 |
| Lambda | Built | TC-31 to TC-33 |
| Asset data (CMDB) | Built | TC-34 |
| Linux servers and images | Built for RHEL | TC-36 to TC-38, with any image ID. Debian runs TC-36 and TC-37 on sample results only. |

### Not built yet

These follow the same pattern: one check, one test, one self-test.

| Area | How it would be tested |
|---|---|
| Security Hub, GuardDuty, Inspector | No open Critical or High findings. A fixed finding stays closed on retest. |
| CloudWatch alarms and routing | Required alarms exist, and each one notifies someone. Trigger one and confirm it arrives. |
| Grafana dashboards | Query the API. Compare a panel's number with the source data. |
| Transit Gateway, VPN, Route 53, WAF | Tunnels are up, routes exist, names resolve, WAF blocks a test request. |
| ECS on EC2 and Fargate | Services at desired count, health checks pass, a rollback returns the old version. |
| Data lake and ETL | Source and target row counts match, the Data Catalog schema is correct. |
| RDS and Aurora settings | Encrypted, not public, backups on, IAM login on. |
| Debian and Ubuntu in the pipeline | Ansible with `apt` and Debian scan content, and Terraform with a Debian image. Debian's vulnerability feed is different, so TC-38 needs its own check. |
| Other clouds, such as Azure and OCI | One folder per topic in `tests/cloud/azure/`, with checks in `checks/cloud/azure/`, its own login in the pipeline, and its own `terraform/azure/`. |

## What this framework does not prove

- A fake AWS account shows that the code works, not that a real account is correct.
  Only `--live` runs prove that.
- The SCP simulator can differ from real AWS in some advanced cases, such as role
  chaining. TC-08 and TC-09 make real calls for that reason.
- The Debian tests only read sample results. They do not prove a real Debian server was scanned correctly.
- The RHEL vulnerability feed is only valid on real RHEL. On a rebuild such as Rocky
  it reports every definition as found, even for packages that are not installed.

# Test Cases

Each test in the code has the same ID. For example, `test_tc03_...` is TC-03.

## Smoke: is everything alive?

| ID | Title | Area | Precondition | Steps | Expected result |
|---|---|---|---|---|---|
| TC-01 | Credentials work | aws | Test role is set up | Call `sts get-caller-identity` | Account ID is returned |
| TC-02 | CloudTrail is logging | aws | Account has a trail | List trails, read each status | At least one trail, and every trail is logging |
| TC-11 | Credentials are short-lived | aws | Test role is set up | Read the current credentials and identity | Temporary credentials, not the root user |
| TC-12 | API is healthy | api | API is deployed | Open the port, call `/health` | Port is open, status is ok |
| TC-13 | Database login works | database | Databases are running | Log in to each database | Login works as the QA user |

## Regression: AWS standards

| ID | Title | Precondition | Steps | Expected result |
|---|---|---|---|---|
| TC-03 | EC2 has required tags | `required_tags` in config | List instances except terminated, compare tags | None is missing a required tag |
| TC-04 | SSH and RDP not open to the world | None | Check security group rules for 22 and 3389 | No rule allows `0.0.0.0/0` or `::/0` |
| TC-05 | S3 blocks public access | None | Read the public access block of each bucket | All 4 settings are on |
| TC-06 | S3 encrypted by default | None | Read default encryption of each bucket | Every bucket has it |
| TC-07 | Console users have MFA | None | List users with a console password, list their MFA | Every console user has MFA |

## Regression: application code

| ID | Title | Type | Input | Expected result |
|---|---|---|---|---|
| TC-14 | Status limits | Boundary | Charge 0, 9.9, 10, 19.9, 20, 100 | critical, critical, low, low, ok, ok |
| TC-15 | Power calculation | Positive | Discharging, charging, idle | 48 kW, -48 kW, 0 kW |
| TC-16 | Reading validation | Positive, negative | Good reading, then each field bad | Good is accepted, each bad one is reported |

## Regression: API

| ID | Title | Type | Steps | Expected result |
|---|---|---|---|---|
| TC-17 | Valid reading is saved | Positive | POST a good reading, then read it back | 201, and the same data returns |
| TC-18 | Bad reading is refused | Negative | POST a charge of 101 | 400 with a clear reason |
| TC-19 | Login is required | Negative | POST with no token, then a wrong token | 401 both times |
| TC-20 | Unknown unit | Edge | GET a unit that does not exist | 404, not a crash |

## Regression: connectivity

| ID | Title | Type | Steps | Expected result |
|---|---|---|---|---|
| TC-21 | Admin ports are closed | Negative | Try ports 22, 3389, 5432 from outside | None can be reached |
| TC-35 | Required connections work | Positive | Try each path in `required_connections` | All can be reached |

## Regression: databases

Every test runs on every database in the config.

| ID | Title | Type | Steps | Expected result |
|---|---|---|---|---|
| TC-22 | Wrong password is refused | Negative | Log in with a wrong password | Authentication fails. A network error fails the test. |
| TC-23 | QA login is read-only | Negative | Read role and table privileges | Not a superuser, no insert, update, or delete |
| TC-24 | Tables have rows | Positive | Count rows | At least `min_rows` |
| TC-25 | No empty required values | Negative | Count NULLs in required columns | Zero |
| TC-26 | No duplicate keys | Negative | Group by key, find counts above 1 | None |
| TC-27 | All databases match | Positive | Compare all rows with the first database | Same rows, in any order |

## Regression: Linux servers and images

Ansible collects the evidence. pytest decides.

| ID | Title | Steps | Expected result |
|---|---|---|---|
| TC-36 | Server settings are correct | Compare collected settings with `os_expected` | RHEL 9, SELinux enforcing, SSH rules set, service running, no missing packages. Debian has its own rules in its folder. |
| TC-37 | Compliance scan passes | Read OpenSCAP CIS Level 1 results | No high severity failure, no rule that errored, except written waivers |
| TC-38 | No serious vulnerabilities | Read OpenSCAP OVAL results | No Critical or Important advisory applies |

## Regression: serverless and asset data

| ID | Title | Type | Steps | Expected result |
|---|---|---|---|---|
| TC-31 | Lambda runtimes are supported | Negative | List functions, compare runtimes | None uses a blocked runtime |
| TC-32 | Lambda answers | Positive | Invoke the function | No `FunctionError`. Lambda returns 200 even after a crash. |
| TC-33 | Lambda code | Positive, negative | Call the handler with good and bad input | 201 and 400 |
| TC-34 | CMDB matches AWS | Negative | Compare CMDB records with running instances | No server missing from the CMDB, no stale record |

## Guardrails: permissions, on both sides

Precondition: a **member** account in an OU with the SCPs attached.
SCPs do not apply to the organization's management account, so these tests mean nothing there.

| ID | Title | Type | Steps | Expected result |
|---|---|---|---|---|
| TC-08 | Allowed region works | Positive | Call EC2 in the allowed region | Call succeeds |
| TC-09 | Blocked region is denied | Negative | Call EC2 in the blocked region | AccessDenied or UnauthorizedOperation |
| TC-10 | Global services still work | Edge | Call IAM | Call succeeds |
| TC-28 | Test role can not write | Negative | Create a security group with `DryRun` | Denied. Nothing is created. |
| TC-29 | SCP permission table | Positive, negative | Simulate each rule in `scp_rules` | Each is allowed or denied as listed, including tag enforcement |

## Load

| ID | Title | Steps | Expected result |
|---|---|---|---|
| TC-30 | API meets load targets | Run k6 with the users and time in the config | Under 1% errors, 95% under 500 ms, over 99% correct answers |

## Self-tests: testing the tests

These build bad things on purpose in a fake account or a temporary table.

| Check | Bad thing created | Must report |
|---|---|---|
| Tags | Instance with only an Owner tag | Missing CostCenter |
| Tags (edge) | Terminated instance with no tags | Nothing |
| Network | SSH open, IPv6 open, a port range, all traffic | That group, all 4 ways |
| Network (edge) | SSH from `10.0.0.0/8` only | Nothing |
| S3 | No public block, one setting off, no encryption | That bucket |
| CloudTrail | No trail, or a trail that is not logging | The problem |
| IAM | Console user without MFA, and a bot with no console | Only the console user |
| IAM (edge) | Console user with MFA | Nothing |
| Credentials | Long-lived key, root user | The problem |
| SCP | Rule too open, rule too strict, no organization | The problem |
| Database | Empty table, NULL, duplicate key | The problem |
| Database compare | Missing row, changed row | The difference |
| Database compare (edge) | Same rows in a different order | Nothing |
| Database login (edge) | Dead server | An error, not a pass |
| Load | API that returns errors, API that is too slow | The missed threshold |
| Lambda | Old runtime, crashed function | The problem |
| CMDB | Server not recorded, stale record | The difference |
| Server | Wrong settings, failed rule, errored rule, serious CVE | The problem |
| Server (edge) | Low severity failure, waived rule | Nothing |
| GitHub variables | Missing variable, empty variable, badly pasted value | That variable |
| GitHub variables (edge) | `prod` with no test server variables | Nothing |
| Folder switches | A folder that an account has turned off | It is skipped |
| Folder switches (edge) | A new folder, and a run on `prod` | Runs everywhere except `prod` |

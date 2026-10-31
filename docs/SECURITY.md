# Security

## The main rule

**No long-lived secrets are stored anywhere.** Not in code, not in GitHub, not on a server.

| Connection | How it logs in | Lasts |
|---|---|---|
| GitHub Actions to AWS | OIDC, then a role | 30 to 60 minutes |
| Ansible to a cloud server | AWS Systems Manager. No SSH keys, port 22 closed. | One session |
| Ansible to an on-prem server | SSH, with the key held by the runner | One session |
| Tests to RDS | IAM token over verified TLS | 15 minutes |
| Tests to the API | A token made new for each run | One run |
| Tests to the CMDB | A token from a GitHub Environment secret | Until rotated |

## How GitHub Actions gets into AWS

```
GitHub job      "I am repo X, environment qa."  (signed OIDC token)
    │
    ▼
AWS STS         Checks the signature, the audience, and the exact repo and environment
    │
    ▼
Role            Gives temporary credentials. They expire on their own.
```

Setup steps are in the [OIDC setup guide](OIDC_SETUP.md).

## What is in place

**Identity**

- Each account trusts one repo and one GitHub Environment. Not a branch, and not a wildcard.
- `allowed-account-ids` stops the job if the credentials reach the wrong account.
- TC-11 fails if the tests ever run with a long-lived key, or as root.
- The role session name holds the run ID, so CloudTrail shows which run did what.

**Least privilege**

- Two roles with two jobs: `qa-readonly` for account checks, `qa-test-env` for the test server.
- `qa-readonly` lists exact actions. It does not use a broad managed policy.
- TC-28 proves the role can not write. TC-23 proves the database login can not write.
- `qa-test-env` can only destroy, and open sessions on, servers tagged by this project.

**Pipeline**

- Default permission is `contents: read`. Only jobs that need it get `id-token: write`.
- Every action is pinned to a full commit hash, so a moved tag can not change what runs.
- Pull requests never touch AWS. They use a fake account.
- The Terraform provider versions are locked by hash.

**Test server**

- Reaches only the API port, and only from the runner running the test.
- IMDSv2 required, disk encrypted, SELinux enforcing.
- Destroyed after every run. If that fails, it shuts itself down and terminates.

**Production**

- Read-only checks only. No test server and no load test.
- Add required reviewers to the `prod` GitHub Environment, so a person approves each run.

## Keep live results private

A live failure message names real resources: security groups, buckets, users with no MFA.
Anyone can read the logs and reports of a public repo.

- **Use a private repo for real accounts.** This public copy stays off, because
  `LIVE_ENABLED` is not set.
- GitHub prints variables in the logs, so role ARNs and hosts are visible there too.
  Passwords and tokens go in Environment secrets, never in variables.
- Reports are kept for 7 days.

## Private networks

GitHub's hosted runners are on the public internet, so they can not reach a private database.
For that, use a runner inside the VPC, such as AWS CodeBuild-hosted runners.
Never attach a self-hosted runner to a public repo, because a stranger's pull request
could run code on it.

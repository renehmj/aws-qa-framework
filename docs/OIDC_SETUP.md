# OIDC Setup Guide

Connect GitHub Actions to AWS with no stored keys. Do steps 1 to 3 once for each account.

You need: an admin login to the AWS account, admin on the GitHub repo, and Terraform.

## Step 1: Create the GitHub Environment

In the repo, go to **Settings ▸ Environments ▸ New environment**. Use the name `qa`.

Under **Deployment branches and tags**, choose **Selected branches** and add `main`.
For `prod`, also turn on **Required reviewers**.

Environments are free on a public repo. On a private repo they need GitHub Pro or Team,
and required reviewers need GitHub Enterprise.

## Step 2: Create the trust and the roles in AWS

This creates the OIDC provider, the two roles, and the file transfer bucket.

```bash
aws sso login                      # or any admin login for this account
cd terraform/aws/oidc
terraform init
terraform apply \
  -var 'github_repo=YOUR-USER/aws-qa-framework' \
  -var 'environment=qa'
```

**Check the trust before you continue.** This is the most important setting.
Open the `qa-readonly` role in the AWS console, then **Trust relationships**. You must see:

```json
"StringEquals": {
  "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
  "token.actions.githubusercontent.com:sub": "repo:YOUR-USER/aws-qa-framework:environment:qa"
}
```

If `sub` is missing or has a `*`, other repos may be able to use your role.

## Step 3: Add the variables to the GitHub Environment

Each GitHub Environment has its own copy of these variables, with the values for its account.
No account details are stored in this repo.

Open **Settings ▸ Environments ▸ qa ▸ Environment variables ▸ Add variable**.

| Variable | Needed in | Value |
|---|---|---|
| `AWS_ACCOUNT_ID` | All | Terraform output |
| `QA_READONLY_ROLE_ARN` | All | Terraform output |
| `QA_TEST_ENV_ROLE_ARN` | `qa`, `dev`, `stage` | Terraform output |
| `QA_LAMBDA_ROLE_ARN` | `qa`, `dev`, `stage` | Terraform output |
| `QA_SSM_BUCKET` | `qa`, `dev`, `stage` | Terraform output |
| `AWS_REGION` | All | The region to test, such as `us-east-1` |
| `QA_BLOCKED_REGION` | All | A region your SCP denies, such as `us-west-2` |
| `QA_SCP_PRINCIPAL_ARN` | All | A normal role in this account, to simulate for TC-29 |

If one is missing, the run stops before it logs in to AWS, and names the variable.

These are optional. Add them only when the account has that system.

| Variable | What it does | How to set it |
|---|---|---|
| `QA_DATABASES` | The databases to test and compare | [Connect the databases](#connect-the-databases) |
| `QA_REQUIRED_CONNECTIONS` | Hybrid paths for TC-35 | [Connect hybrid paths](#connect-hybrid-paths) |
| `QA_CMDB_URL` | The CMDB to compare with AWS | [Connect the CMDB](#connect-the-cmdb) |

**GitHub prints variables in the logs.** Never put a password or token in a variable.
Use an Environment secret instead.

**What goes where:**

- **Where to test** is a GitHub variable: the account, roles, region, and hosts.
- **What to test** is a file in `python/config/`: the test folders and the load size. A change there gets reviewed.

## Step 4: Turn on live runs

Open **Settings ▸ Secrets and variables ▸ Actions ▸ Variables ▸ New repository variable**.
This setting is for the whole repo, and you set it once.

| Variable | Value |
|---|---|
| `LIVE_ENABLED` | `true` |

## Step 5: Run it

Open **Actions ▸ live ▸ Run workflow**, choose `qa`, and start it.

TC-01 and TC-11 prove the login worked, and that the credentials are short-lived.

To test a specific image, put its ID in the `ami_id` box. Empty means the latest RHEL 9.

## Step 6: Add the other accounts

Log in to each account and repeat steps 1 to 3, with `dev`, `stage`, and `prod`.
Use the same variable names, with the values for that account.
Each account trusts only its own environment, so a `dev` job can not reach `prod`.

## Run it after a deployment

Add this to a deployment workflow in the same repo:

```yaml
jobs:
  test-after-deploy:
    needs: deploy
    uses: ./.github/workflows/live.yml
    with:
      environment: qa
    permissions:
      contents: read
      id-token: write
```

## Connect the databases

Real databases are off by default. To turn them on for an environment:

1. In `python/config/qa.yaml`, remove `apps/sample_app/database` from `tests_off`.
2. In the GitHub Environment, add the variable `QA_DATABASES`. List every database to compare:

   ```yaml
   - name: primary
     host: qa-db-a.example.internal
     port: 5432
     dbname: energy
     user: qa_reader
     auth: iam                    # short-lived token, no stored password
     sslmode: verify-full
     sslrootcert: global-bundle.pem
   - name: redundant
     host: qa-db-b.example.internal
     port: 5432
     dbname: energy
     user: qa_reader
     auth: iam
     sslmode: verify-full
     sslrootcert: global-bundle.pem
   ```

3. Allow the `qa-test-env` role to log in, by adding `rds-db:connect` for the `qa_reader` user.
   This is not in Terraform, because each account has different database IDs.

If an account has several apps with different databases, add `project: <app folder>` to each entry.

The pipeline downloads `global-bundle.pem` from AWS when this variable is set.
The runner must be able to reach the database. See [Private networks](SECURITY.md#private-networks).

## Connect hybrid paths

To test a path such as cloud to on-prem, add the variable `QA_REQUIRED_CONNECTIONS`:

```yaml
- name: on-prem gateway
  host: 10.20.0.15
  port: 443
```

## Connect the CMDB

The CMDB is off by default. To turn it on for an environment:

1. In `python/config/qa.yaml`, remove `cmdb` from `tests_off`.
2. In the GitHub Environment, add the variable `QA_CMDB_URL`. For ServiceNow:
   `https://YOUR-COMPANY.service-now.com/api/now/table/cmdb_ci_server`
3. Add the secret `QA_CMDB_TOKEN`, from a read-only CMDB user.

The connector expects these fields on each record: `name`, `instance_id`, `location`,
`environment`, `status`, `ip_address`. Map them in `python/checks/cmdb.py` if yours differ.

To use the CMDB as the Ansible inventory, for cloud and on-prem servers together:

```bash
cd ansible
QA_ENV=qa QA_CMDB_URL=../python/tests/cmdb/sample_cmdb.json ansible-inventory -i inventory/cmdb.py --graph
ansible-playbook -i inventory/cmdb.py playbooks/scan.yml
```

Cloud servers connect through Systems Manager. On-prem servers connect through SSH.

## When something goes wrong

| Error | Likely cause | Fix |
|---|---|---|
| `Add the variable ... to the GitHub Environment` | The variable is missing or empty | Add it, see step 3 |
| `this test needs a database, but none are set` | `apps/sample_app/database` is on, but `QA_DATABASES` is not set | Add the variable, or add the folder to `tests_off` |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | `sub` in the trust does not match | Check the repo name and environment name, exactly |
| `Credentials could not be loaded` | Job has no `id-token: write`, or the variable is empty | Check `permissions:` and the Environment variables |
| `No OpenIDConnect provider found` | Step 2 was not run in this account | Run step 2 |
| `Provider with url ... already exists` | The account already has the GitHub provider | `terraform import aws_iam_openid_connect_provider.github <its ARN>` |
| `The account is not allowed` | Credentials reached the wrong account | Check `AWS_ACCOUNT_ID` |
| Live job is skipped | `LIVE_ENABLED` is not `true` | Do step 4 |
| TC-29 says `no SCP result` | Account is not in an organization | Use a member account |
| TC-09 fails, not blocked | This is the management account, or no SCP is attached | Use a member account in the OU with the SCP |
| Ansible hangs on connect | Instance can not reach Systems Manager | Check the instance role and outbound 443 |

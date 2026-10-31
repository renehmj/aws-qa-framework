from botocore.exceptions import ClientError

from checks.cloud.aws.scp import DENIED_CODES


def users_without_mfa(session):
    """Return IAM users that can log in to the console but have no MFA."""
    iam = session.client("iam")
    problems = []
    for page in iam.get_paginator("list_users").paginate():
        for user in page["Users"]:
            name = user["UserName"]
            try:
                iam.get_login_profile(UserName=name)
            except iam.exceptions.NoSuchEntityException:
                continue  # no console password, so MFA rule does not apply
            if not iam.list_mfa_devices(UserName=name)["MFADevices"]:
                problems.append(f"{name}: console user without MFA")
    return problems


def credential_problems(session):
    """Credentials must be short-lived and must not be the root user."""
    problems = []
    if not session.get_credentials().get_frozen_credentials().token:
        problems.append("long-lived access key in use, expected OIDC or assume role")
    if session.client("sts").get_caller_identity()["Arn"].endswith(":root"):
        problems.append("running as the root user")
    return problems


def role_can_write(session):
    """True if the role could make changes. DryRun means nothing is created."""
    ec2 = session.client("ec2")
    try:
        ec2.create_security_group(GroupName="qa-dry-run", Description="qa dry run", DryRun=True)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "DryRunOperation":
            return True
        if code in DENIED_CODES:
            return False
        raise
    return True

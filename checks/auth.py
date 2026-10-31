from botocore.exceptions import ClientError

from checks.guardrails import DENIED_CODES


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

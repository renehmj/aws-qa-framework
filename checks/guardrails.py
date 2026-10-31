from botocore.exceptions import ClientError

DENIED_CODES = {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}


def region_is_blocked(session, region):
    """True if a read call in `region` is denied (for example by an SCP)."""
    ec2 = session.client("ec2", region_name=region)
    try:
        ec2.describe_instances(MaxResults=5)
        return False
    except ClientError as e:
        if e.response["Error"]["Code"] in DENIED_CODES:
            return True
        raise


def scp_problems(session, principal_arn, rules, region):
    """Ask AWS what SCPs would do for each rule. Nothing is really run."""
    iam = session.client("iam")
    problems = []
    for rule in rules:
        context = {"aws:RequestedRegion": region, **rule.get("context", {})}
        result = iam.simulate_principal_policy(
            PolicySourceArn=principal_arn,
            ActionNames=[rule["action"]],
            ContextEntries=[
                {"ContextKeyName": key, "ContextKeyValues": [value], "ContextKeyType": "string"}
                for key, value in context.items()
            ],
        )["EvaluationResults"][0]

        detail = result.get("OrganizationsDecisionDetail")
        if detail is None:
            problems.append(f"{rule['action']}: no SCP result, is this account in an organization?")
        elif detail["AllowedByOrganizations"] != (rule["expect"] == "allow"):
            problems.append(f"{rule['action']}: expected {rule['expect']}, context {rule.get('context', {})}")
    return problems

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

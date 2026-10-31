def ec2_missing_tags(session, required_tags):
    """Return EC2 instances that are missing any required tag."""
    ec2 = session.client("ec2")
    problems = []
    for page in ec2.get_paginator("describe_instances").paginate():
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                if inst["State"]["Name"] == "terminated":
                    continue
                tags = {t["Key"] for t in inst.get("Tags", [])}
                missing = [t for t in required_tags if t not in tags]
                if missing:
                    problems.append(f"{inst['InstanceId']} missing {missing}")
    return problems

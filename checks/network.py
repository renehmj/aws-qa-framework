OPEN_TO_WORLD = {"0.0.0.0/0", "::/0"}


def _rule_covers_port(rule, port):
    # IpProtocol "-1" means all traffic, all ports.
    if rule.get("IpProtocol") == "-1":
        return True
    low, high = rule.get("FromPort"), rule.get("ToPort")
    return low is not None and high is not None and low <= port <= high


def ports_open_to_world(session, ports=(22, 3389)):
    """Return security groups that allow SSH/RDP from anywhere."""
    ec2 = session.client("ec2")
    problems = []
    for page in ec2.get_paginator("describe_security_groups").paginate():
        for sg in page["SecurityGroups"]:
            for rule in sg["IpPermissions"]:
                cidrs = {r["CidrIp"] for r in rule.get("IpRanges", [])}
                cidrs |= {r["CidrIpv6"] for r in rule.get("Ipv6Ranges", [])}
                if not cidrs & OPEN_TO_WORLD:
                    continue
                for port in ports:
                    if _rule_covers_port(rule, port):
                        problems.append(f"{sg['GroupId']} ({sg['GroupName']}) port {port} open to world")
    return problems

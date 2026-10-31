def cloudtrail_problems(session):
    """Return problems if there is no trail, or a trail is not logging."""
    ct = session.client("cloudtrail")
    trails = ct.describe_trails()["trailList"]
    if not trails:
        return ["no CloudTrail trail found"]
    problems = []
    for trail in trails:
        status = ct.get_trail_status(Name=trail["TrailARN"])
        if not status.get("IsLogging"):
            problems.append(f"trail {trail['Name']} is not logging")
    return problems

from botocore.exceptions import ClientError

ALL_BLOCKS = (
    "BlockPublicAcls",
    "IgnorePublicAcls",
    "BlockPublicPolicy",
    "RestrictPublicBuckets",
)


def buckets_without_public_block(session):
    """Return S3 buckets that do not fully block public access."""
    s3 = session.client("s3")
    problems = []
    for bucket in s3.list_buckets()["Buckets"]:
        name = bucket["Name"]
        try:
            cfg = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
            if not all(cfg.get(k) for k in ALL_BLOCKS):
                problems.append(f"{name}: public access block is only partly on")
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration":
                problems.append(f"{name}: no public access block")
            else:
                raise
    return problems


def buckets_without_encryption(session):
    """Return S3 buckets with no default encryption setting."""
    s3 = session.client("s3")
    problems = []
    for bucket in s3.list_buckets()["Buckets"]:
        name = bucket["Name"]
        try:
            s3.get_bucket_encryption(Bucket=name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ServerSideEncryptionConfigurationNotFoundError":
                problems.append(f"{name}: no default encryption")
            else:
                raise
    return problems

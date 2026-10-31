"""Self-tests: test the tests.

A check that always says PASS is useless. Here we build BAD resources
on purpose in a fake account and prove each check reports them.
"""
import pytest

from checks.audit import cloudtrail_problems
from checks.iam import users_without_mfa
from checks.network import ports_open_to_world
from checks.storage import buckets_without_encryption, buckets_without_public_block
from checks.tags import ec2_missing_tags

pytestmark = pytest.mark.selftest


def test_untagged_instance_is_caught(empty_mock_account, config):
    ec2 = empty_mock_account.client("ec2")
    ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1,
                      TagSpecifications=[{"ResourceType": "instance",
                                          "Tags": [{"Key": "Owner", "Value": "x"}]}])
    problems = ec2_missing_tags(empty_mock_account, config["required_tags"])
    assert len(problems) == 1
    assert "CostCenter" in problems[0]


def test_terminated_instance_is_ignored(empty_mock_account):
    """Edge case: a terminated instance can not be fixed, so it is not a problem."""
    ec2 = empty_mock_account.client("ec2")
    instance = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1)["Instances"][0]
    ec2.terminate_instances(InstanceIds=[instance["InstanceId"]])
    assert ec2_missing_tags(empty_mock_account, ["Owner"]) == []


@pytest.mark.parametrize("rule", [
    {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
    {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "Ipv6Ranges": [{"CidrIpv6": "::/0"}]},
    {"IpProtocol": "tcp", "FromPort": 20, "ToPort": 30, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
    {"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
], ids=["ssh-open", "ipv6-open", "port-range-open", "all-traffic-open"])
def test_open_ssh_is_caught(empty_mock_account, rule):
    ec2 = empty_mock_account.client("ec2")
    sg = ec2.create_security_group(GroupName="bad-sg", Description="ssh open")
    ec2.authorize_security_group_ingress(GroupId=sg["GroupId"], IpPermissions=[rule])
    problems = ports_open_to_world(empty_mock_account, ports=(22,))
    assert any(sg["GroupId"] in p for p in problems)


def test_ssh_from_office_only_is_not_flagged(empty_mock_account):
    """Edge case: SSH from a private range is fine, no false alarm."""
    ec2 = empty_mock_account.client("ec2")
    sg = ec2.create_security_group(GroupName="ok-sg", Description="office ssh")
    ec2.authorize_security_group_ingress(
        GroupId=sg["GroupId"],
        IpPermissions=[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                        "IpRanges": [{"CidrIp": "10.0.0.0/8"}]}])
    assert ports_open_to_world(empty_mock_account, ports=(22,)) == []


def test_public_bucket_is_caught(empty_mock_account):
    empty_mock_account.client("s3").create_bucket(Bucket="no-block-bucket")
    problems = buckets_without_public_block(empty_mock_account)
    assert problems == ["no-block-bucket: no public access block"]


def test_partly_public_bucket_is_caught(empty_mock_account):
    """Edge case: three of the four settings on is still a problem."""
    s3 = empty_mock_account.client("s3")
    s3.create_bucket(Bucket="partly-open-bucket")
    s3.put_public_access_block(Bucket="partly-open-bucket", PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": False})
    problems = buckets_without_public_block(empty_mock_account)
    assert problems == ["partly-open-bucket: public access block is only partly on"]


def test_unencrypted_bucket_is_caught(empty_mock_account):
    empty_mock_account.client("s3").create_bucket(Bucket="plain-bucket")
    problems = buckets_without_encryption(empty_mock_account)
    assert problems == ["plain-bucket: no default encryption"]


def test_missing_cloudtrail_is_caught(empty_mock_account):
    assert cloudtrail_problems(empty_mock_account) == ["no CloudTrail trail found"]


def test_stopped_cloudtrail_is_caught(empty_mock_account):
    """Edge case: a trail that exists but is not logging is still a problem."""
    empty_mock_account.client("s3").create_bucket(Bucket="trail-logs-bucket")
    trail = empty_mock_account.client("cloudtrail")
    trail.create_trail(Name="stopped-trail", S3BucketName="trail-logs-bucket")
    assert cloudtrail_problems(empty_mock_account) == ["trail stopped-trail is not logging"]


def test_console_user_without_mfa_is_caught(empty_mock_account):
    iam = empty_mock_account.client("iam")
    iam.create_user(UserName="alice")
    iam.create_login_profile(UserName="alice", Password="Temp-Passw0rd!")
    iam.create_user(UserName="ci-bot")  # no console login, so it is ignored
    assert users_without_mfa(empty_mock_account) == ["alice: console user without MFA"]


def test_console_user_with_mfa_is_not_flagged(empty_mock_account):
    """No false alarm: a user who did the right thing must pass."""
    iam = empty_mock_account.client("iam")
    iam.create_user(UserName="bob")
    iam.create_login_profile(UserName="bob", Password="Temp-Passw0rd!")
    device = iam.create_virtual_mfa_device(VirtualMFADeviceName="bob-mfa")["VirtualMFADevice"]
    iam.enable_mfa_device(UserName="bob", SerialNumber=device["SerialNumber"],
                          AuthenticationCode1="123456", AuthenticationCode2="654321")
    assert users_without_mfa(empty_mock_account) == []

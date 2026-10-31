"""Self-tests: a bad tags setting must be reported."""
import pytest

from checks.cloud.aws.tags import ec2_missing_tags

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

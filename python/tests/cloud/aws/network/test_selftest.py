"""Self-tests: a bad network setting must be reported."""
import pytest

from checks.cloud.aws.network import ports_open_to_world

pytestmark = pytest.mark.selftest


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

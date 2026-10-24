import json
import re
import subprocess
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
class CfnLoader(yaml.SafeLoader):
    pass
def intrinsic(loader, tag, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    return {"Fn::" + tag: value}
CfnLoader.add_multi_constructor("!", intrinsic)

class TestTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = yaml.load((ROOT / "template.yaml").read_text(), Loader=CfnLoader)
        cls.r = cls.template["Resources"]
        cls.policy = json.loads((ROOT / "iam/least-privilege-policy.json").read_text())
    def test_resource_counts(self):
        for kind in ("VPC", "Subnet", "InternetGateway", "Instance"):
            self.assertEqual(sum(x["Type"] == "AWS::EC2::" + kind for x in self.r.values()), 1)
    def test_route(self):
        self.assertEqual(self.r["PublicRoute"]["Properties"]["DestinationCidrBlock"], "0.0.0.0/0")
        self.assertEqual(self.r["PublicRouteAssociation"]["Properties"]["SubnetId"], {"Fn::Ref":"PublicSubnet"})
    def test_ingress(self):
        rules = self.r["WebSecurityGroup"]["Properties"]["SecurityGroupIngress"]
        self.assertEqual({x["FromPort"] for x in rules}, {22,80})
        self.assertEqual(next(x["CidrIp"] for x in rules if x["FromPort"] == 80), "0.0.0.0/0")
        self.assertEqual(next(x["CidrIp"] for x in rules if x["FromPort"] == 22), {"Fn::Ref":"SshCidr"})
    def test_ssh_cidr(self):
        pattern = self.template["Parameters"]["SshCidr"]["AllowedPattern"]
        self.assertTrue(re.fullmatch(pattern,"203.0.113.5/32"))
        self.assertFalse(re.fullmatch(pattern,"0.0.0.0/0"))
    def test_ec2(self):
        x = self.r["WebInstance"]["Properties"]
        self.assertEqual(x["InstanceType"],"t3.micro")
        self.assertEqual(x["MetadataOptions"]["HttpTokens"],"required")
        self.assertTrue(x["NetworkInterfaces"][0]["AssociatePublicIpAddress"])
        self.assertTrue(x["BlockDeviceMappings"][0]["Ebs"]["DeleteOnTermination"])
    def test_userdata(self):
        bash = self.r["WebInstance"]["Properties"]["UserData"]["Fn::Base64"]
        self.assertEqual(subprocess.run(["bash","-n"],input=bash,text=True).returncode,0)
        self.assertIn("systemctl enable --now nginx",bash)
    def test_iam(self):
        actions = [a for s in self.policy["Statement"] if s["Effect"]=="Allow" for a in (s["Action"] if isinstance(s["Action"],list) else [s["Action"]])]
        self.assertNotIn("*",actions)
        self.assertTrue(all(not a.startswith(("iam:","s3:","rds:")) for a in actions))
if __name__=="__main__":
    unittest.main()

"""Read what Ansible collected from each server. Python decides pass or fail."""
import json
import xml.etree.ElementTree as ET

RULE_PREFIX = "xccdf_org.ssgproject.content_rule_"


def os_problems(server, expected):
    """Compare the server's real settings with what we expect."""
    facts = json.loads((server / "facts.json").read_text())
    return [
        f"{server.name}: {key} is {facts.get(key)}, expected {wanted}"
        for key, wanted in expected.items()
        if facts.get(key) != wanted
    ]


def scan_problems(server, fail_on, waived):
    """Return OpenSCAP rules that failed. A rule that errored was not checked, so it counts."""
    problems = []
    for rule in ET.parse(server / "xccdf.xml").getroot().findall(".//{*}rule-result"):
        name = rule.get("idref").removeprefix(RULE_PREFIX)
        result = rule.find("{*}result").text
        if name in waived:
            continue
        if result == "error" or (result == "fail" and rule.get("severity") in fail_on):
            problems.append(f"{server.name}: {name} is {result} (severity {rule.get('severity')})")
    return problems


def vulnerability_problems(server, fail_on):
    """Return known vulnerabilities found on the server, from the OVAL scan."""
    root = ET.parse(server / "oval.xml").getroot()
    found = {
        result.get("definition_id")
        for result in root.findall(".//{*}results//{*}definition")
        if result.get("result") == "true"
    }
    problems = []
    for definition in root.findall(".//{*}oval_definitions/{*}definitions/{*}definition"):
        if definition.get("id") not in found:
            continue
        severity = definition.findtext(".//{*}advisory/{*}severity")
        if severity in fail_on:
            problems.append(f"{server.name}: {definition.findtext('.//{*}title')}")
    return problems

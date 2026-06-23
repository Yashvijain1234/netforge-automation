"""Configuration compliance auditing.

A rule is a small declarative check against a command's output (default: the
running-config). Each rule asserts that a regex either must or must not appear.
Rules can be loaded from YAML; a set of sensible Cisco hardening defaults is
built in so the auditor is useful out of the box.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml

from .connector import make_connector
from .inventory import Device

DEFAULT_RULES = [
    {
        "id": "ssh-v2",
        "description": "SSH version 2 must be enabled",
        "severity": "high",
        "must_contain": r"ip ssh version 2",
    },
    {
        "id": "no-telnet",
        "description": "Telnet must not be allowed on VTY lines",
        "severity": "high",
        "must_not_contain": r"transport input.*telnet",
    },
    {
        "id": "password-encryption",
        "description": "service password-encryption must be configured",
        "severity": "medium",
        "must_contain": r"service password-encryption",
    },
    {
        "id": "no-http-server",
        "description": "Insecure HTTP management server must be disabled",
        "severity": "medium",
        "must_not_contain": r"^ip http server",
    },
    {
        "id": "enable-secret",
        "description": "An enable secret must be set",
        "severity": "high",
        "must_contain": r"enable secret",
    },
    {
        "id": "syslog-host",
        "description": "A central syslog host should be configured",
        "severity": "low",
        "must_contain": r"logging host",
    },
]


@dataclass
class Rule:
    id: str
    description: str
    severity: str
    must_contain: Optional[str] = None
    must_not_contain: Optional[str] = None
    command: str = "show running-config"

    def evaluate(self, output: str) -> bool:
        """Return True if the device PASSES the rule."""
        if self.must_contain is not None:
            if re.search(self.must_contain, output, re.MULTILINE) is None:
                return False
        if self.must_not_contain is not None:
            if re.search(self.must_not_contain, output, re.MULTILINE) is not None:
                return False
        return True


@dataclass
class Finding:
    device: str
    rule_id: str
    description: str
    severity: str
    passed: bool


def load_rules(path: Optional[str]) -> List[Rule]:
    raw = DEFAULT_RULES
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        raw = data.get("rules", DEFAULT_RULES)
    return [Rule(**r) for r in raw]


def audit_device(device: Device, rules: List[Rule], simulate: bool) -> List[Finding]:
    # Fetch each distinct command once, then evaluate all rules against it.
    needed = {rule.command for rule in rules}
    outputs: Dict[str, str] = {}
    connector = make_connector(device, simulate)
    with connector.connect() as conn:
        for cmd in needed:
            outputs[cmd] = conn.send_command(cmd)

    findings = []
    for rule in rules:
        passed = rule.evaluate(outputs.get(rule.command, ""))
        findings.append(Finding(
            device=device.name, rule_id=rule.id, description=rule.description,
            severity=rule.severity, passed=passed,
        ))
    return findings


def audit_all(devices: List[Device], rules: List[Rule], simulate: bool) -> List[Finding]:
    findings: List[Finding] = []
    for device in devices:
        try:
            findings.extend(audit_device(device, rules, simulate))
        except Exception as exc:  # pragma: no cover
            findings.append(Finding(device.name, "connection", str(exc), "high", False))
    return findings

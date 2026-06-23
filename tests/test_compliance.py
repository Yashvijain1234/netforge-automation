"""Tests for the compliance rule engine."""

from netforge.compliance import Rule, audit_device, load_rules
from netforge.inventory import Device


class TestRuleEvaluate:
    def test_must_contain_pass(self):
        rule = Rule("r", "desc", "high", must_contain=r"ip ssh version 2")
        assert rule.evaluate("...\nip ssh version 2\n...") is True

    def test_must_contain_fail(self):
        rule = Rule("r", "desc", "high", must_contain=r"ip ssh version 2")
        assert rule.evaluate("no ssh configured") is False

    def test_must_not_contain_pass(self):
        rule = Rule("r", "desc", "high", must_not_contain=r"transport input.*telnet")
        assert rule.evaluate("transport input ssh") is True

    def test_must_not_contain_fail(self):
        rule = Rule("r", "desc", "high", must_not_contain=r"transport input.*telnet")
        assert rule.evaluate("transport input telnet ssh") is False

    def test_anchored_regex_matches_line_start(self):
        """^ip http server should not match 'no ip http server'."""
        rule = Rule("r", "desc", "medium", must_not_contain=r"^ip http server")
        assert rule.evaluate("no ip http server") is True
        assert rule.evaluate("ip http server") is False


class TestDefaultRules:
    def test_defaults_load(self):
        rules = load_rules(None)
        ids = {r.id for r in rules}
        assert {"ssh-v2", "no-telnet", "password-encryption"} <= ids


class TestAuditSimulated:
    def test_hardened_device_passes_all(self):
        findings = audit_device(
            Device(name="core-sw1", host="10.0.1.1"), load_rules(None), simulate=True
        )
        assert all(f.passed for f in findings)

    def test_weak_device_has_failures(self):
        findings = audit_device(
            Device(name="access-sw1", host="10.0.2.10"), load_rules(None), simulate=True
        )
        failed_ids = {f.rule_id for f in findings if not f.passed}
        assert "no-telnet" in failed_ids
        assert "ssh-v2" in failed_ids

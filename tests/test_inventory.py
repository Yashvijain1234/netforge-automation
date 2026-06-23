"""Tests for inventory loading, defaults merging, and secret resolution."""

import pytest

from netforge.inventory import load_inventory


INVENTORY_YAML = """
defaults:
  platform: cisco_ios
  username: admin
  password: env:TEST_NETFORGE_PW

devices:
  - name: core-sw1
    host: 10.0.1.1
    role: core
  - name: edge-rtr1
    host: 10.0.0.254
    role: edge
    platform: cisco_xe
    password: inline-secret
"""


def _write(tmp_path, text):
    path = tmp_path / "inv.yaml"
    path.write_text(text)
    return str(path)


def test_loads_all_devices(tmp_path):
    devices = load_inventory(_write(tmp_path, INVENTORY_YAML))
    assert len(devices) == 2
    assert {d.name for d in devices} == {"core-sw1", "edge-rtr1"}


def test_defaults_are_applied(tmp_path):
    devices = load_inventory(_write(tmp_path, INVENTORY_YAML))
    core = next(d for d in devices if d.name == "core-sw1")
    assert core.platform == "cisco_ios"
    assert core.username == "admin"


def test_per_device_override_wins(tmp_path):
    devices = load_inventory(_write(tmp_path, INVENTORY_YAML))
    edge = next(d for d in devices if d.name == "edge-rtr1")
    assert edge.platform == "cisco_xe"


def test_env_secret_is_resolved(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_NETFORGE_PW", "super-secret")
    devices = load_inventory(_write(tmp_path, INVENTORY_YAML))
    core = next(d for d in devices if d.name == "core-sw1")
    assert core.password == "super-secret"


def test_inline_secret_is_kept(tmp_path):
    devices = load_inventory(_write(tmp_path, INVENTORY_YAML))
    edge = next(d for d in devices if d.name == "edge-rtr1")
    assert edge.password == "inline-secret"


def test_missing_env_secret_resolves_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_NETFORGE_PW", raising=False)
    devices = load_inventory(_write(tmp_path, INVENTORY_YAML))
    core = next(d for d in devices if d.name == "core-sw1")
    assert core.password == ""


def test_empty_inventory_raises(tmp_path):
    with pytest.raises(ValueError):
        load_inventory(_write(tmp_path, "devices: []\n"))

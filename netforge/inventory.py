"""Device inventory loading.

The inventory is a YAML file describing the devices NetForge manages. Global
defaults (credentials, platform) can be set once and overridden per device.
Passwords may be inlined for a lab, or pulled from environment variables using
the ``env:VAR_NAME`` syntax so secrets stay out of source control.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

import yaml


@dataclass
class Device:
    name: str
    host: str
    platform: str = "cisco_ios"
    username: str = "admin"
    password: str = ""
    role: str = "unknown"
    port: int = 22

    @property
    def label(self) -> str:
        return f"{self.name} ({self.host})"


def _resolve_secret(value: Optional[str]) -> str:
    """Resolve ``env:VAR`` references against the environment."""
    if not value:
        return ""
    if value.startswith("env:"):
        return os.environ.get(value[4:], "")
    return value


def load_inventory(path: str) -> List[Device]:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    defaults = data.get("defaults", {}) or {}
    devices: List[Device] = []

    for entry in data.get("devices", []) or []:
        merged = {**defaults, **entry}
        devices.append(Device(
            name=merged["name"],
            host=merged["host"],
            platform=merged.get("platform", "cisco_ios"),
            username=merged.get("username", "admin"),
            password=_resolve_secret(merged.get("password", "")),
            role=merged.get("role", "unknown"),
            port=int(merged.get("port", 22)),
        ))

    if not devices:
        raise ValueError(f"No devices found in inventory '{path}'.")
    return devices

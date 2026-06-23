"""Configuration backup with change detection.

For each device NetForge pulls the running-config, writes a timestamped file
under ``backups/<device>/``, and diffs it against the most recent previous
backup so config drift is surfaced immediately.
"""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .connector import make_connector
from .inventory import Device

_CONFIG_CMD = "show running-config"


@dataclass
class BackupResult:
    device: str
    path: str
    changed: bool
    diff: str
    error: Optional[str] = None


def _latest_existing(device_dir: str) -> Optional[str]:
    if not os.path.isdir(device_dir):
        return None
    files = sorted(f for f in os.listdir(device_dir) if f.endswith(".cfg"))
    return os.path.join(device_dir, files[-1]) if files else None


def backup_device(device: Device, backup_root: str, simulate: bool) -> BackupResult:
    device_dir = os.path.join(backup_root, device.name)
    os.makedirs(device_dir, exist_ok=True)

    try:
        connector = make_connector(device, simulate)
        with connector.connect() as conn:
            config = conn.send_command(_CONFIG_CMD)
    except Exception as exc:  # network/auth errors shouldn't abort the batch
        return BackupResult(device.name, "", False, "", error=str(exc))

    previous_path = _latest_existing(device_dir)
    previous = ""
    if previous_path:
        with open(previous_path, "r", encoding="utf-8") as fh:
            previous = fh.read()

    diff_text = ""
    changed = True
    if previous:
        diff_lines = list(difflib.unified_diff(
            previous.splitlines(), config.splitlines(),
            fromfile="previous", tofile="current", lineterm="",
        ))
        diff_text = "\n".join(diff_lines)
        changed = bool(diff_lines)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(device_dir, f"{stamp}.cfg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(config)

    return BackupResult(device.name, path, changed, diff_text)


def backup_all(devices: List[Device], backup_root: str, simulate: bool) -> List[BackupResult]:
    return [backup_device(d, backup_root, simulate) for d in devices]

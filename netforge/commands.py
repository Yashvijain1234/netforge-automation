"""Concurrent bulk command execution across the inventory.

Runs one or more show/exec commands against every device in parallel using a
thread pool (network I/O is the bottleneck, so threads scale well). Failures on
one device never abort the batch.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .connector import make_connector
from .inventory import Device


@dataclass
class CommandResult:
    device: str
    outputs: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


def _run_one(device: Device, commands: List[str], simulate: bool) -> CommandResult:
    result = CommandResult(device=device.name)
    try:
        connector = make_connector(device, simulate)
        with connector.connect() as conn:
            for cmd in commands:
                result.outputs[cmd] = conn.send_command(cmd)
    except Exception as exc:
        result.error = str(exc)
    return result


def run_commands(
    devices: List[Device],
    commands: List[str],
    simulate: bool,
    max_workers: int = 10,
) -> List[CommandResult]:
    results: List[CommandResult] = []
    workers = min(max_workers, len(devices)) or 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_run_one, dev, commands, simulate): dev for dev in devices
        }
        for future in as_completed(futures):
            results.append(future.result())
    # Preserve inventory order for stable, readable output.
    order = {d.name: i for i, d in enumerate(devices)}
    results.sort(key=lambda r: order.get(r.device, 0))
    return results

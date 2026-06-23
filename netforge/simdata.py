"""Synthetic device data for simulation mode.

Defines a small but realistic five-device lab (core / distribution / access /
edge) and renders believable Cisco IOS CLI output for the handful of commands
NetForge issues. The CDP adjacency below is intentionally consistent so the
topology builder produces a real graph, and the running-configs intentionally
vary so the compliance auditor finds a mix of passes and failures.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .inventory import Device

# name -> list of (neighbor_name, local_intf, remote_intf, neighbor_ip, platform)
NEIGHBORS: Dict[str, List[Tuple[str, str, str, str, str]]] = {
    "core-sw1": [
        ("dist-sw1", "GigabitEthernet1/0/1", "GigabitEthernet0/1", "10.0.1.2", "cisco WS-C3850"),
        ("dist-sw2", "GigabitEthernet1/0/2", "GigabitEthernet0/1", "10.0.1.3", "cisco WS-C3850"),
        ("edge-rtr1", "GigabitEthernet1/0/24", "GigabitEthernet0/0", "10.0.0.254", "cisco ISR4331"),
    ],
    "dist-sw1": [
        ("core-sw1", "GigabitEthernet0/1", "GigabitEthernet1/0/1", "10.0.1.1", "cisco C9500"),
        ("access-sw1", "GigabitEthernet0/2", "GigabitEthernet0/1", "10.0.2.10", "cisco WS-C2960"),
    ],
    "dist-sw2": [
        ("core-sw1", "GigabitEthernet0/1", "GigabitEthernet1/0/2", "10.0.1.1", "cisco C9500"),
        ("access-sw1", "GigabitEthernet0/2", "GigabitEthernet0/2", "10.0.2.10", "cisco WS-C2960"),
    ],
    "access-sw1": [
        ("dist-sw1", "GigabitEthernet0/1", "GigabitEthernet0/2", "10.0.1.2", "cisco WS-C3850"),
        ("dist-sw2", "GigabitEthernet0/2", "GigabitEthernet0/2", "10.0.1.3", "cisco WS-C3850"),
    ],
    "edge-rtr1": [
        ("core-sw1", "GigabitEthernet0/0", "GigabitEthernet1/0/24", "10.0.1.1", "cisco C9500"),
    ],
}

# Devices flagged here intentionally OMIT certain hardening lines so the
# compliance auditor has something to report.
_WEAK_DEVICES = {"access-sw1", "dist-sw2"}


def _running_config(device: Device) -> str:
    name = device.name
    lines = [
        "Building configuration...",
        "",
        "Current configuration : 4231 bytes",
        "!",
        "version 15.2",
        "service timestamps debug datetime msec",
        "service timestamps log datetime msec",
    ]
    # Hardening lines present only on properly-configured devices.
    if name not in _WEAK_DEVICES:
        lines.append("service password-encryption")
    lines += [
        "!",
        f"hostname {name}",
        "!",
        "enable secret 5 $1$mERr$examplehashvalue123",
        "!",
        "no ip domain-lookup",
        "ip domain-name lab.cisco.local",
    ]
    if name not in _WEAK_DEVICES:
        lines += [
            "!",
            "no ip http server",
            "no ip http secure-server",
            "!",
            "logging host 10.0.0.50",
        ]
    else:
        lines += [
            "!",
            "ip http server",   # insecure: management over HTTP enabled
        ]
    lines += [
        "!",
        "interface GigabitEthernet0/0",
        f" description uplink",
        f" ip address {device.host} 255.255.255.0",
        " no shutdown",
        "!",
        "line vty 0 4",
    ]
    if name not in _WEAK_DEVICES:
        lines += [
            " transport input ssh",
            " login local",
            "!",
            "ip ssh version 2",
        ]
    else:
        lines += [
            " transport input telnet ssh",  # insecure: telnet allowed
            " login local",
        ]
    lines += ["!", "end", ""]
    return "\n".join(lines)


def _show_version(device: Device) -> str:
    return (
        "Cisco IOS Software, IOS-XE Software\n"
        f"{device.name} uptime is 42 weeks, 3 days, 5 hours\n"
        "System returned to ROM by power-on\n"
        "Processor board ID FOC2145X0AB\n"
        "Configuration register is 0x2102\n"
    )


def _show_cdp_neighbors_detail(device: Device) -> str:
    blocks = []
    for nbr, local_if, remote_if, nbr_ip, platform in NEIGHBORS.get(device.name, []):
        blocks.append(
            "-------------------------\n"
            f"Device ID: {nbr}.lab.cisco.local\n"
            "Entry address(es):\n"
            f"  IP address: {nbr_ip}\n"
            f"Platform: {platform},  Capabilities: Router Switch\n"
            f"Interface: {local_if},  Port ID (outgoing port): {remote_if}\n"
            "Holdtime : 142 sec\n"
        )
    if not blocks:
        return "Total cdp entries displayed : 0\n"
    return "\n".join(blocks) + f"\nTotal cdp entries displayed : {len(blocks)}\n"


def render_command(device: Device, command: str) -> str:
    cmd = command.lower().strip()
    if "running-config" in cmd or cmd == "show run":
        return _running_config(device)
    if cmd.startswith("show version") or cmd == "show ver":
        return _show_version(device)
    if "cdp neighbors detail" in cmd or "cdp neighbor detail" in cmd:
        return _show_cdp_neighbors_detail(device)
    return f"% Simulated device '{device.name}' has no canned output for: {command}\n"

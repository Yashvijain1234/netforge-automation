"""Network topology discovery from CDP/LLDP.

NetForge collects ``show cdp neighbors detail`` from every device, parses the
output, and assembles a deduplicated link graph. The graph can be exported as
JSON or as Graphviz DOT for rendering (``dot -Tpng topology.dot -o topo.png``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from .connector import make_connector
from .inventory import Device

_CDP_CMD = "show cdp neighbors detail"

_DEVICE_ID_RE = re.compile(r"Device ID:\s*(\S+)")
_LOCAL_IF_RE = re.compile(r"Interface:\s*([^,]+),")
_REMOTE_IF_RE = re.compile(r"Port ID \(outgoing port\):\s*(\S+)")


@dataclass
class Link:
    a_device: str
    a_interface: str
    b_device: str
    b_interface: str

    def normalized(self) -> Tuple[str, str, str, str]:
        """Order endpoints so A<->B and B<->A collapse to one link."""
        if self.a_device <= self.b_device:
            return (self.a_device, self.a_interface, self.b_device, self.b_interface)
        return (self.b_device, self.b_interface, self.a_device, self.a_interface)


@dataclass
class Topology:
    nodes: Set[str] = field(default_factory=set)
    links: List[Link] = field(default_factory=list)
    _seen: Set[Tuple[str, str, str, str]] = field(default_factory=set)

    def add_link(self, link: Link) -> None:
        self.nodes.add(link.a_device)
        self.nodes.add(link.b_device)
        key = link.normalized()
        if key not in self._seen:
            self._seen.add(key)
            self.links.append(link)

    def to_dict(self) -> dict:
        return {
            "nodes": sorted(self.nodes),
            "links": [
                {
                    "source": l.a_device, "source_interface": l.a_interface,
                    "target": l.b_device, "target_interface": l.b_interface,
                }
                for l in self.links
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_dot(self) -> str:
        lines = ["graph network {", '  node [shape=box, style=rounded];']
        for node in sorted(self.nodes):
            lines.append(f'  "{node}";')
        for l in self.links:
            lines.append(
                f'  "{l.a_device}" -- "{l.b_device}" '
                f'[label="{l.a_interface} <-> {l.b_interface}"];'
            )
        lines.append("}")
        return "\n".join(lines)


def _short_name(device_id: str) -> str:
    """'core-sw1.lab.cisco.local' -> 'core-sw1'."""
    return device_id.split(".")[0]


def parse_cdp_detail(local_device: str, output: str) -> List[Link]:
    """Parse one device's CDP detail output into links."""
    links: List[Link] = []
    # Each neighbor block is separated by a dashed line.
    for block in output.split("-------------------------"):
        dev_match = _DEVICE_ID_RE.search(block)
        local_if = _LOCAL_IF_RE.search(block)
        remote_if = _REMOTE_IF_RE.search(block)
        if dev_match and local_if and remote_if:
            links.append(Link(
                a_device=local_device,
                a_interface=local_if.group(1).strip(),
                b_device=_short_name(dev_match.group(1)),
                b_interface=remote_if.group(1).strip(),
            ))
    return links


def discover(devices: List[Device], simulate: bool) -> Topology:
    topo = Topology()
    for device in devices:
        topo.nodes.add(device.name)
        try:
            connector = make_connector(device, simulate)
            with connector.connect() as conn:
                output = conn.send_command(_CDP_CMD)
        except Exception:
            continue
        for link in parse_cdp_detail(device.name, output):
            topo.add_link(link)
    return topo

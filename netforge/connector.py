"""Connection backends.

``SSHConnector`` wraps Netmiko for real Cisco/Arista/Juniper gear.
``SimulatedConnector`` returns realistic canned CLI output for the lab topology
defined in :mod:`netforge.simdata`, so every NetForge feature is demoable with
no hardware, no credentials, and no network access.

Both expose the same tiny interface::

    with connector.connect() as conn:
        output = conn.send_command("show running-config")
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from .inventory import Device
from . import simdata


class SimulatedSession:
    def __init__(self, device: Device):
        self.device = device

    def send_command(self, command: str) -> str:
        return simdata.render_command(self.device, command)

    def disconnect(self) -> None:  # parity with Netmiko's API
        pass


class SimulatedConnector:
    def __init__(self, device: Device):
        self.device = device

    @contextmanager
    def connect(self) -> Iterator[SimulatedSession]:
        yield SimulatedSession(self.device)


class SSHConnector:
    """Real SSH connection via Netmiko (lazy-imported)."""

    def __init__(self, device: Device):
        self.device = device

    @contextmanager
    def connect(self):
        from netmiko import ConnectHandler

        conn = ConnectHandler(
            device_type=self.device.platform,
            host=self.device.host,
            username=self.device.username,
            password=self.device.password,
            port=self.device.port,
        )
        try:
            yield conn
        finally:
            conn.disconnect()


def make_connector(device: Device, simulate: bool):
    return SimulatedConnector(device) if simulate else SSHConnector(device)

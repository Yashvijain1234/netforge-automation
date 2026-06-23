# NetForge — Multi-Device Network Automation Toolkit

A Python CLI that automates day-to-day network operations across a fleet of
Cisco-style devices: **configuration backup with drift detection**, **parallel
bulk command execution**, **security compliance auditing**, and **Layer-2
topology discovery via CDP/LLDP**.

Every feature runs against either **real devices over SSH** (Netmiko) or a
**built-in virtual lab** (`--simulate`), so the whole toolkit is demoable with
no hardware, credentials, or network access.

## Why this project

Network engineering at scale is automation: you don't SSH into 500 switches by
hand. NetForge demonstrates the core building blocks of an automation platform —
a declarative inventory, a pluggable connection layer, concurrent execution, a
config-as-data compliance engine, and neighbor-discovery-based topology mapping —
all directly relevant to Cisco's networking and DevNet ecosystems.

## Features

- **YAML inventory** with global defaults, per-device overrides, and
  `env:VAR_NAME` secret resolution (no plaintext passwords in source control).
- **Config backup + diff** — timestamped per-device backups with `unified_diff`
  drift detection against the previous snapshot.
- **Concurrent command runner** — execute commands across the fleet in parallel
  with a thread pool; one device failing never aborts the batch.
- **Compliance auditing** — declarative regex rules (must-contain /
  must-not-contain) with a built-in Cisco hardening baseline (SSHv2, no telnet,
  password encryption, no HTTP server, enable secret, syslog host).
- **Topology discovery** — parses `show cdp neighbors detail`, builds a
  deduplicated link graph, and exports **JSON** or **Graphviz DOT**.
- **Pluggable connectors** — identical interface for simulated and real
  (Netmiko/SSH) backends.

## Quick start

```bash
pip install -r requirements.txt   # PyYAML; uncomment netmiko for real devices

# Discover the virtual lab topology and export a Graphviz diagram
python -m netforge.cli -i inventory.example.yaml --simulate topology --dot topo.dot

# Audit every device against the security baseline
python -m netforge.cli -i inventory.example.yaml --simulate audit

# Back up all running-configs (re-run to see drift detection)
python -m netforge.cli -i inventory.example.yaml --simulate backup

# Run a command across the whole fleet
python -m netforge.cli -i inventory.example.yaml --simulate run "show version"
```

Sample topology output:

```
Discovered 5 nodes and 5 links:
  core-sw1 [GigabitEthernet1/0/1] <-> [GigabitEthernet0/1] dist-sw1
  core-sw1 [GigabitEthernet1/0/2] <-> [GigabitEthernet0/1] dist-sw2
  core-sw1 [GigabitEthernet1/0/24] <-> [GigabitEthernet0/0] edge-rtr1
  dist-sw1 [GigabitEthernet0/2] <-> [GigabitEthernet0/1] access-sw1
  dist-sw2 [GigabitEthernet0/2] <-> [GigabitEthernet0/2] access-sw1
```

Render the diagram (requires Graphviz): `dot -Tpng topo.dot -o topo.png`

## Running against real devices

Drop `--simulate` and point the inventory at real gear:

```bash
pip install netmiko
export NETFORGE_PASSWORD='your-password'
python -m netforge.cli -i inventory.example.yaml audit
```

The `SimulatedConnector` and `SSHConnector` expose the same
`connect()` / `send_command()` interface, so no other code changes.

## Tests

A `pytest` suite covers the CDP parser (multi-neighbor parsing, domain
stripping, malformed-block handling), topology assembly (reciprocal-link
deduplication, JSON/DOT export), the compliance rule engine (must/must-not
regex, anchored matches), and inventory loading (defaults merging, `env:`
secret resolution):

```bash
pip install -r requirements-dev.txt
pytest            # 25 tests
```

## Inventory format

```yaml
defaults:
  platform: cisco_ios
  username: admin
  password: env:NETFORGE_PASSWORD   # resolved from $NETFORGE_PASSWORD

devices:
  - name: core-sw1
    host: 10.0.1.1
    role: core
  - name: edge-rtr1
    host: 10.0.0.254
    role: edge
    platform: cisco_xe
```

## Project layout

```
netforge/
  inventory.py    # YAML inventory + env-var secret resolution
  connector.py    # Simulated and Netmiko/SSH connection backends
  simdata.py      # Virtual lab: configs + CDP adjacency for --simulate
  backup.py       # Config backup with unified-diff drift detection
  commands.py     # Concurrent bulk command execution (thread pool)
  compliance.py   # Declarative regex rule engine + hardening defaults
  topology.py     # CDP parsing -> link graph -> JSON / Graphviz DOT
  cli.py          # argparse subcommands: backup / run / audit / topology
inventory.example.yaml
```

## Resume bullet points

> - Built **NetForge**, a Python network-automation CLI that performs
>   configuration backup with diff-based drift detection, parallel bulk command
>   execution, security compliance auditing, and CDP-based Layer-2 topology
>   discovery across a multi-device inventory.
> - Designed a pluggable connection layer with a common interface over both
>   **Netmiko SSH** (real devices) and a built-in **virtual lab**, plus a
>   declarative YAML inventory with environment-variable secret resolution.
> - Implemented a config-as-data **compliance engine** enforcing a Cisco
>   hardening baseline (SSHv2, no telnet, password encryption, no HTTP server)
>   and exported discovered topology to **Graphviz DOT** for visualization;
>   backed the toolkit with a 25-case **pytest** suite for the CDP parser,
>   compliance engine, and inventory loader.

## Tech stack

Python 3 · Netmiko · PyYAML · concurrent.futures · regex · Graphviz · argparse

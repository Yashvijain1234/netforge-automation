"""NetForge command-line interface.

Subcommands
-----------
    backup    Pull running-configs and diff against the last backup.
    run       Execute one or more commands across the whole inventory.
    audit     Check every device against compliance rules.
    topology  Discover the L2 topology via CDP and export JSON/DOT.

Add ``--simulate`` to any command to use the built-in virtual lab (no hardware,
credentials, or network required).

Examples
--------
    python -m netforge.cli --inventory inventory.example.yaml --simulate topology --dot topo.dot
    python -m netforge.cli -i inventory.example.yaml --simulate audit
    python -m netforge.cli -i inventory.example.yaml --simulate run "show version"
"""

from __future__ import annotations

import argparse
import sys

from .backup import backup_all
from .commands import run_commands
from .compliance import audit_all, load_rules
from .inventory import load_inventory
from .topology import discover


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netforge",
        description="Multi-device network automation toolkit.",
    )
    parser.add_argument("-i", "--inventory", required=True,
                        help="Path to the YAML inventory file.")
    parser.add_argument("--simulate", action="store_true",
                        help="Use the built-in virtual lab instead of real SSH.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_backup = sub.add_parser("backup", help="Back up running-configs with diffing.")
    p_backup.add_argument("--dir", default="backups", help="Backup output directory.")

    p_run = sub.add_parser("run", help="Run command(s) on every device.")
    p_run.add_argument("commands", nargs="+", help="One or more CLI commands.")

    p_audit = sub.add_parser("audit", help="Run compliance checks.")
    p_audit.add_argument("--rules", help="Optional YAML rules file (uses defaults otherwise).")

    p_topo = sub.add_parser("topology", help="Discover topology via CDP.")
    p_topo.add_argument("--json", dest="json_path", help="Write topology JSON to FILE.")
    p_topo.add_argument("--dot", dest="dot_path", help="Write Graphviz DOT to FILE.")

    return parser


def _cmd_backup(devices, args) -> int:
    results = backup_all(devices, args.dir, args.simulate)
    for r in results:
        if r.error:
            print(f"[FAIL] {r.device}: {r.error}")
        elif r.diff:
            print(f"[CHANGED] {r.device}: saved {r.path}")
            print(r.diff)
        elif r.changed:
            print(f"[NEW] {r.device}: first backup saved to {r.path}")
        else:
            print(f"[OK] {r.device}: no change ({r.path})")
    return 0


def _cmd_run(devices, args) -> int:
    results = run_commands(devices, args.commands, args.simulate)
    for r in results:
        print(f"\n===== {r.device} =====")
        if not r.ok:
            print(f"  ERROR: {r.error}")
            continue
        for cmd, out in r.outputs.items():
            print(f"--- {cmd} ---")
            print(out.rstrip())
    return 0


def _cmd_audit(devices, args) -> int:
    rules = load_rules(args.rules)
    findings = audit_all(devices, rules, args.simulate)

    by_device = {}
    for f in findings:
        by_device.setdefault(f.device, []).append(f)

    total_fail = 0
    for device, items in by_device.items():
        fails = [f for f in items if not f.passed]
        total_fail += len(fails)
        status = "PASS" if not fails else f"{len(fails)} FAILED"
        print(f"\n===== {device}: {status} =====")
        for f in items:
            mark = "PASS" if f.passed else "FAIL"
            print(f"  [{mark}] ({f.severity}) {f.rule_id}: {f.description}")

    print(f"\nAudited {len(by_device)} device(s); {total_fail} failed check(s).")
    return 1 if total_fail else 0


def _cmd_topology(devices, args) -> int:
    topo = discover(devices, args.simulate)
    print(f"Discovered {len(topo.nodes)} nodes and {len(topo.links)} links:")
    for l in topo.links:
        print(f"  {l.a_device} [{l.a_interface}] <-> [{l.b_interface}] {l.b_device}")

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as fh:
            fh.write(topo.to_json())
        print(f"\nTopology JSON written to {args.json_path}")
    if args.dot_path:
        with open(args.dot_path, "w", encoding="utf-8") as fh:
            fh.write(topo.to_dot())
        print(f"Graphviz DOT written to {args.dot_path} "
              f"(render with: dot -Tpng {args.dot_path} -o topo.png)")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        devices = load_inventory(args.inventory)
    except Exception as exc:
        print(f"error loading inventory: {exc}", file=sys.stderr)
        return 2

    dispatch = {
        "backup": _cmd_backup,
        "run": _cmd_run,
        "audit": _cmd_audit,
        "topology": _cmd_topology,
    }
    return dispatch[args.command](devices, args)


if __name__ == "__main__":
    raise SystemExit(main())

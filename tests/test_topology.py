"""Tests for CDP parsing and topology graph assembly."""

from netforge.topology import parse_cdp_detail, Topology, Link, discover
from netforge.inventory import Device

SAMPLE_CDP = """-------------------------
Device ID: dist-sw1.lab.cisco.local
Entry address(es):
  IP address: 10.0.1.2
Platform: cisco WS-C3850,  Capabilities: Router Switch
Interface: GigabitEthernet1/0/1,  Port ID (outgoing port): GigabitEthernet0/1
Holdtime : 142 sec

-------------------------
Device ID: edge-rtr1.lab.cisco.local
Entry address(es):
  IP address: 10.0.0.254
Platform: cisco ISR4331,  Capabilities: Router
Interface: GigabitEthernet1/0/24,  Port ID (outgoing port): GigabitEthernet0/0
Holdtime : 130 sec

Total cdp entries displayed : 2
"""


class TestParseCdpDetail:
    def test_parses_all_neighbors(self):
        links = parse_cdp_detail("core-sw1", SAMPLE_CDP)
        assert len(links) == 2

    def test_strips_domain_from_neighbor_name(self):
        links = parse_cdp_detail("core-sw1", SAMPLE_CDP)
        names = {l.b_device for l in links}
        assert names == {"dist-sw1", "edge-rtr1"}

    def test_captures_local_and_remote_interfaces(self):
        links = parse_cdp_detail("core-sw1", SAMPLE_CDP)
        link = next(l for l in links if l.b_device == "dist-sw1")
        assert link.a_device == "core-sw1"
        assert link.a_interface == "GigabitEthernet1/0/1"
        assert link.b_interface == "GigabitEthernet0/1"

    def test_empty_output_yields_no_links(self):
        assert parse_cdp_detail("core-sw1", "Total cdp entries displayed : 0\n") == []

    def test_malformed_block_is_skipped(self):
        partial = (
            "-------------------------\n"
            "Device ID: foo.lab\n"
            "Holdtime : 10 sec\n"   # no Interface / Port ID lines
        )
        assert parse_cdp_detail("core-sw1", partial) == []


class TestTopology:
    def test_deduplicates_reciprocal_links(self):
        """A->B reported by A and B->A reported by B collapse to one link."""
        topo = Topology()
        topo.add_link(Link("core-sw1", "Gi1/0/1", "dist-sw1", "Gi0/1"))
        topo.add_link(Link("dist-sw1", "Gi0/1", "core-sw1", "Gi1/0/1"))
        assert len(topo.links) == 1
        assert topo.nodes == {"core-sw1", "dist-sw1"}

    def test_distinct_links_are_kept(self):
        topo = Topology()
        topo.add_link(Link("core-sw1", "Gi1/0/1", "dist-sw1", "Gi0/1"))
        topo.add_link(Link("core-sw1", "Gi1/0/2", "dist-sw2", "Gi0/1"))
        assert len(topo.links) == 2

    def test_to_dict_structure(self):
        topo = Topology()
        topo.add_link(Link("a", "i1", "b", "i2"))
        d = topo.to_dict()
        assert d["nodes"] == ["a", "b"]
        assert d["links"][0]["source"] == "a"
        assert d["links"][0]["target"] == "b"

    def test_dot_export_is_valid_graph(self):
        topo = Topology()
        topo.add_link(Link("a", "i1", "b", "i2"))
        dot = topo.to_dot()
        assert dot.startswith("graph network {")
        assert '"a" -- "b"' in dot
        assert dot.rstrip().endswith("}")


class TestDiscoverSimulated:
    def test_discovers_full_lab_topology(self):
        devices = [
            Device(name="core-sw1", host="10.0.1.1"),
            Device(name="dist-sw1", host="10.0.1.2"),
            Device(name="dist-sw2", host="10.0.1.3"),
            Device(name="access-sw1", host="10.0.2.10"),
            Device(name="edge-rtr1", host="10.0.0.254"),
        ]
        topo = discover(devices, simulate=True)
        assert len(topo.nodes) == 5
        # The simulated lab has 5 unique physical links.
        assert len(topo.links) == 5

import json

import pytest

from network_assessment.ingestion import normalize, parse_document, parse_json

from ..conftest import SAMPLE_JSON, SUB_HUB, SUB_SPOKE


def _rows(*rows):
    return parse_document(list(rows))


@pytest.fixture(scope="module")
def sample():
    return normalize(parse_json(SAMPLE_JSON.read_text(encoding="utf-8")))


def test_sample_maps_every_type(sample):
    topo = sample.topology
    assert [s.subscription_id for s in topo.subscriptions] == [SUB_HUB, SUB_SPOKE]
    hub, spoke = topo.subscriptions
    assert len(hub.vnets) == 1 and len(spoke.vnets) == 3 and len(hub.nsgs) == 1 and len(hub.route_tables) == 2
    assert [fw.effective_threat_intel_mode for fw in hub.firewalls] == ["Alert"] and hub.firewalls[
        0
    ].firewall_policy.name == "hcw-sample-fwpolicy"
    assert {gw.gateway_type: len(gw.connections) for gw in hub.virtual_network_gateways} == {
        "Vpn": 1,
        "ExpressRoute": 1,
    }
    assert hub.virtual_network_gateways[0].connections[0].shared_key_set is True
    assert {p.name: p.associated_resource_type for p in hub.public_ips}["hcw-sample-pip-orphan"] is None
    assert {p.name: p.associated_resource_type for p in hub.public_ips}["hcw-sample-pip-nat"] == "NAT"
    assert hub.load_balancers[0].lb_type == "Internal" and spoke.load_balancers[0].lb_type == "Public"
    assert hub.private_endpoints[0].dns_zone_group_names == ["privatelink-blob-core-windows-net"]
    assert hub.private_dns_zones[0].linked_vnet_names == ["hcw-sample-vnet-hub"]
    assert (
        hub.application_gateways[0].waf_policy.mode == "Detection" and hub.application_gateways[1].waf_enabled is False
    )
    assert (
        hub.flow_logs[0].target_resource_id == hub.nsgs[0].id
        and hub.nsgs[0].flow_logs_enabled
        and hub.vnets[0].flow_logs_enabled
    )
    assert not spoke.vnets[0].flow_logs_enabled
    assert hub.front_door_waf_policies[0].custom_rules_count == 1 and hub.nat_gateways[0].associated_subnet_ids == []
    assert hub.bastion_hosts[0].tunneling_enabled and hub.express_route_circuits[0].bandwidth_mbps == 200
    assert topo.resource_counts["microsoft.network/networkinterfaces"] == 5
    assert topo.unmapped_types == ["microsoft.network/localnetworkgateways", "microsoft.network/networkwatchers"]
    assert topo.has_properties and len(topo.warnings) == 2


def test_subnet_references_resolve_within_the_export(sample):
    hub = sample.topology.subscriptions[0]
    shared = next(s for s in hub.vnets[0].subnets if s.name == "snet-shared")
    assert (
        shared.nsg_name == "hcw-sample-nsg-hub"
        and shared.route_table_name == "hcw-sample-rt-hub"
        and shared.ip_configuration_count == 6
    )
    assert shared.private_endpoint_network_policies == "Disabled"
    peer = hub.vnets[0].peerings[0]
    assert peer.remote_vnet_name == "hcw-sample-vnet-spoke1" and peer.remote_subscription_id == SUB_SPOKE


def test_facts_and_rows_are_kept(sample):
    hub_vnet = sample.topology.subscriptions[0].vnets[0]
    assert (
        sample.facts[hub_vnet.id]["dnsServers"] == ["10.0.4.4", "10.0.4.5"]
        and sample.facts[hub_vnet.id]["subnets"] == 6
    )
    assert len(sample.rows) == 48


def test_unresolved_references_become_warnings():
    vnet = {
        "type": "microsoft.network/virtualnetworks",
        "id": f"/subscriptions/{SUB_HUB}/resourceGroups/rg/providers/microsoft.network/virtualnetworks/v",
        "properties": {
            "subnets": [
                {
                    "name": "s",
                    "properties": {
                        "addressPrefix": "10.0.0.0/24",
                        "networkSecurityGroup": {"id": "/x/nsg-missing"},
                        "routeTable": {"id": "/x/rt-missing"},
                    },
                }
            ],
            "virtualNetworkPeerings": [
                {"name": "p", "properties": {"remoteVirtualNetwork": {"id": "/subscriptions/other/x/remote"}}}
            ],
        },
    }
    fw = {
        "type": "microsoft.network/azurefirewalls",
        "id": f"/subscriptions/{SUB_HUB}/resourceGroups/rg/providers/microsoft.network/azurefirewalls/fw",
        "properties": {"firewallPolicy": {"id": "/x/policy-missing"}, "sku": {"tier": "Premium"}},
    }
    conn = {
        "type": "microsoft.network/connections",
        "id": f"/subscriptions/{SUB_HUB}/resourceGroups/rg/providers/microsoft.network/connections/c",
        "properties": {"virtualNetworkGateway1": {"id": "/x/gw-missing"}, "connectionStatus": "Connected"},
    }
    hub = {
        "type": "microsoft.network/virtualhubs",
        "id": f"/subscriptions/{SUB_HUB}/resourceGroups/rg/providers/microsoft.network/virtualhubs/h",
        "properties": {
            "virtualWan": {"id": "/x/wan-missing"},
            "addressPrefix": "10.9.0.0/23",
            "azureFirewall": {"id": "/x/fw"},
        },
    }
    rs = {
        "type": "microsoft.network/virtualhubs",
        "kind": "RouteServer",
        "id": f"/subscriptions/{SUB_HUB}/resourceGroups/rg/providers/microsoft.network/virtualhubs/rs",
        "properties": {"virtualRouterAsn": 65515, "allowBranchToBranchTraffic": True},
    }
    other = {
        "type": "microsoft.compute/virtualmachines",
        "id": "/subscriptions/x/resourceGroups/rg/providers/microsoft.compute/virtualmachines/vm",
        "properties": {"a": 1},
    }
    unmapped = {
        "type": "microsoft.network/ddosprotectionplans",
        "id": "/subscriptions/x/resourceGroups/rg/providers/microsoft.network/ddosprotectionplans/d",
        "properties": {},
    }
    n = normalize(_rows(vnet, fw, conn, hub, rs, other, unmapped))
    topo = n.topology
    sub = topo.subscriptions[0]
    assert sub.vnets[0].subnets[0].nsg_name is None and sub.vnets[0].subnets[0].nsg_id == "/x/nsg-missing"
    assert sub.vnets[0].peerings[0].remote_subscription_id == "other"
    assert sub.firewalls[0].firewall_policy is None and sub.firewalls[0].policy_id == "/x/policy-missing"
    assert sub.virtual_network_gateways == [] and sub.virtual_wans[0].hubs[0].azure_firewall_id == "/x/fw"
    assert sub.route_servers[0].virtual_router_asn == 65515
    joined = "\n".join(topo.warnings)
    for what in (
        "network security group nsg-missing",
        "route table rt-missing",
        "firewall policy policy-missing",
        "virtual network gateway gw-missing",
        "virtual WAN wan-missing",
    ):
        assert what in joined, what
    assert "1 row(s) outside microsoft.network/ were ignored" in topo.warnings
    assert topo.unmapped_types == ["microsoft.network/ddosprotectionplans"]
    assert "rt-missing" in joined and joined.count("rt-missing") == 1


def test_no_network_rows_is_an_error():
    with pytest.raises(ValueError, match="no microsoft.network"):
        normalize(_rows({"type": "microsoft.compute/virtualmachines", "name": "vm"}))


def test_portal_rows_normalise_without_properties():
    parsed = parse_document(
        [{"type": "microsoft.network/virtualnetworks", "name": "v", "subscriptionId": SUB_HUB, "resourceGroup": "rg"}]
    )
    topo = normalize(parsed).topology
    assert not topo.has_properties and topo.subscriptions[0].vnets[0].subnets == []


def test_flow_log_targets_vnet_and_subnet():
    vid = f"/subscriptions/{SUB_HUB}/resourceGroups/rg/providers/microsoft.network/virtualnetworks/v"
    vnet = {
        "type": "microsoft.network/virtualnetworks",
        "id": vid,
        "properties": {
            "subnets": [{"name": "s", "id": f"{vid}/subnets/s", "properties": {"addressPrefix": "10.0.0.0/24"}}]
        },
    }
    fl = {
        "type": "microsoft.network/networkwatchers/flowlogs",
        "id": f"/subscriptions/{SUB_HUB}/resourceGroups/rg/providers/microsoft.network/networkwatchers/nw/flowlogs/f",
        "properties": {"targetResourceId": f"{vid}/subnets/s", "enabled": True},
    }
    assert normalize(_rows(vnet, fl)).topology.subscriptions[0].vnets[0].flow_logs_enabled
    fl["properties"]["targetResourceId"] = vid
    assert normalize(_rows(vnet, fl)).topology.subscriptions[0].vnets[0].flow_logs_enabled
    fl["properties"]["enabled"] = False
    assert not normalize(_rows(vnet, fl)).topology.subscriptions[0].vnets[0].flow_logs_enabled


def test_topology_document_round_trips():
    n = normalize(parse_json(SAMPLE_JSON.read_text(encoding="utf-8")))
    doc = n.topology.model_dump(mode="json")
    assert doc["model_version"] == "lab-1.0.0" and json.dumps(doc)

# Ported from saulpatinojr/Work-Cloud_Network_Core tests/unit/test_topology_classifier.py at 5d3b914; changes: lab model
# builders, no discovery_blocked case (an export has no blocked subscriptions).
from network_assessment.classify import classify_topology
from network_assessment.model.topology import AzureVHub, AzureVWan

from .model_fixtures import firewall, peering, subnet, subscription, topology, vnet


def test_isolated_when_no_peerings():
    result = classify_topology(topology(subscription(vnets=[vnet("vnet-a"), vnet("vnet-b")])))
    assert result.pattern == "isolated" and result.hub_vnet_ids == []


def test_hub_spoke_from_gateway_transit():
    hub = vnet("hub")
    spoke = vnet("spoke", peerings=[peering("spoke-to-hub", hub.id, use_remote_gateways=True)])
    hub.peerings = [peering("hub-to-spoke", spoke.id, allow_gateway_transit=True)]
    result = classify_topology(topology(subscription(vnets=[hub, spoke])))
    assert result.pattern == "hub_spoke"
    assert hub.id in result.hub_vnet_ids and spoke.id in result.spoke_vnet_ids
    assert result.model_dump(by_alias=True)["hubVnetIds"] == [hub.id]


def test_hub_identified_by_firewall_subnet():
    fw_subnet = subnet("hub", "AzureFirewallSubnet", "10.0.1.0/26")
    hub = vnet("hub", subnets=[fw_subnet])
    spoke = vnet("spoke", peerings=[peering("spoke-to-hub", hub.id)])
    sub = subscription(vnets=[hub, spoke], firewalls=[firewall("fw-1", subnet_id=fw_subnet.id)])
    result = classify_topology(topology(sub))
    assert result.pattern == "hub_spoke" and result.hub_vnet_ids == [hub.id]


def test_mesh_when_peered_without_hub():
    a, b = vnet("vnet-a"), vnet("vnet-b")
    a.peerings = [peering("a-to-b", b.id)]
    b.peerings = [peering("b-to-a", a.id)]
    assert classify_topology(topology(subscription(vnets=[a, b]))).pattern == "mesh"


def test_vwan_takes_precedence():
    vhub = AzureVHub(
        id="vhub-1", name="vhub-1", location="eastus2", resource_group="rg", address_prefix="10.100.0.0/23"
    )
    sub = subscription(
        vnets=[vnet("vnet-a")],
        virtual_wans=[AzureVWan(id="vwan-1", name="vwan-1", resource_group="rg", sku="Standard", hubs=[vhub])],
    )
    result = classify_topology(topology(sub))
    assert result.pattern == "vwan" and result.hub_vnet_ids == ["vhub-1"]


def test_gateway_placement_marks_hub_across_subscriptions():
    from .model_fixtures import gateway

    hub = vnet("hub")
    spoke = vnet("spoke", peerings=[peering("spoke-to-hub", hub.id)])
    gw = gateway("gw", subnet_id=f"{hub.id}/subnets/GatewaySubnet")
    result = classify_topology(topology(subscription(vnets=[hub, spoke], virtual_network_gateways=[gw])))
    assert result.pattern == "hub_spoke" and result.hub_vnet_ids == [hub.id]

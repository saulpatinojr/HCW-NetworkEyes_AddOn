# Ported from saulpatinojr/HCW-NetworkEyes_App tests/unit/test_analysis_engine.py (TestAzureNetFindingRules,
# TestAzurePeeringGatewayTransit) at 5d3b914; changes: lab model builders and the registry's evaluate() replace the
# AnalysisEngine/EngagementStore fixtures; cases for the reimplemented AZ-NET-011, the extended 003/006/007/012/014 and
# the Engine B rules AZ-NET-020..033 added.
from network_assessment.model.topology import (
    AppGatewayWafPolicy,
    AzureBastionHost,
    AzureFirewallPolicy,
    AzureGatewayConnection,
    AzureLoadBalancer,
    AzureNSG,
    AzurePrivateEndpoint,
    AzurePrivateEndpointConnection,
    AzurePublicIP,
    AzureRouteEntry,
    AzureRouteTable,
    AzureTopology,
    AzureVHub,
    AzureVWan,
    FlowLog,
    FrontDoorWAFPolicy,
    NSGSecurityRule,
)
from network_assessment.rules import evaluate

from ..model_fixtures import (
    SUB,
    app_gateway,
    circuit,
    firewall,
    gateway,
    peering,
    subnet,
    subscription,
    topology,
    vnet,
)


def _net(topo: AzureTopology, rule_id: str):
    return [f for f in evaluate(topo).findings if f.rule_id == rule_id]


def _unknown(topo: AzureTopology, rule_id: str) -> str | None:
    return next((u.reason for u in evaluate(topo).unknowns if u.rule_id == rule_id), None)


# ── Engine A, ported ───────────────────────────────────────────────────────


def test_vnet_no_ddos_produces_finding():
    assert len(_net(topology(subscription(vnets=[vnet("vnet-prod", ddos=False)])), "AZ-NET-001")) == 1
    assert _net(topology(subscription(vnets=[vnet("vnet-prod", ddos=True)])), "AZ-NET-001") == []


def test_subnet_no_nsg_produces_high_finding():
    v = vnet("vnet-prod", ddos=True, subnets=[subnet("vnet-prod", "snet-app", nsg_id=None)])
    findings = _net(topology(subscription(vnets=[v])), "AZ-NET-002")
    assert len(findings) == 1 and findings[0].severity == "high" and findings[0].rule_version == 2
    assert findings[0].traffic_direction == "east_west"


def test_platform_subnets_without_nsg_are_not_flagged():
    names = ["GatewaySubnet", "AzureFirewallSubnet", "AzureFirewallManagementSubnet", "RouteServerSubnet"]
    v = vnet("vnet-hub", subnets=[subnet("vnet-hub", n, "10.1.255.0/27") for n in names])
    assert _net(topology(subscription(vnets=[v])), "AZ-NET-002") == []
    bastion = vnet("b", subnets=[subnet("b", "AzureBastionSubnet", "10.1.254.0/26")])
    assert len(_net(topology(subscription(vnets=[bastion])), "AZ-NET-002")) == 1, "Bastion subnets take an NSG"


def test_firewall_threat_intel_alert_is_critical_and_policy_resolves():
    findings = _net(
        topology(subscription(firewalls=[firewall("fw-hub", threat_intel_mode="Alert", sku_tier="Premium")])),
        "AZ-NET-003",
    )
    assert (
        len(findings) == 1
        and findings[0].severity == "critical"
        and "(from the firewall)" in findings[0].observed_state.fact
    )
    policy = AzureFirewallPolicy(id="p", name="p", resource_group="rg", threat_intel_mode="Deny")
    fw = firewall("fw-pol", threat_intel_mode="Alert", firewall_policy=policy)
    assert _net(topology(subscription(firewalls=[fw])), "AZ-NET-003") == []
    off = AzureFirewallPolicy(id="p2", name="p2", resource_group="rg", threat_intel_mode="Off")
    f = _net(
        topology(subscription(firewalls=[firewall("fw-off", threat_intel_mode="Deny", firewall_policy=off)])),
        "AZ-NET-003",
    )
    assert len(f) == 1 and "firewall policy" in f[0].observed_state.fact


def test_single_er_circuit_emits_004_and_two_do_not():
    assert len(_net(topology(subscription(express_route_circuits=[circuit()])), "AZ-NET-004")) == 1
    assert _net(topology(subscription(express_route_circuits=[circuit("a"), circuit("b")])), "AZ-NET-004") == []


class TestPeeringGatewayTransit:
    """A gateway lives in a GatewaySubnet whose ARM id nests under its VNet id (T-410 regression in the Core)."""

    def _vnet(self, name="vnet-prod", allow_gateway_transit=True):
        return vnet(name, peerings=[peering("to-hub", "/x/vnet-hub", allow_gateway_transit=allow_gateway_transit)])

    def test_a_gateway_in_this_vnet_suppresses_the_finding(self):
        v = self._vnet()
        sub = subscription(
            vnets=[v], virtual_network_gateways=[gateway("gw1", subnet_id=f"{v.id}/subnets/GatewaySubnet")]
        )
        assert _net(topology(sub), "AZ-NET-005") == []

    def test_a_gateway_in_a_different_vnet_does_not_count(self):
        v = self._vnet()
        other = f"{v.id}-other/subnets/GatewaySubnet"
        sub = subscription(vnets=[v], virtual_network_gateways=[gateway("gw1", subnet_id=other)])
        findings = _net(topology(sub), "AZ-NET-005")
        assert len(findings) == 1 and findings[0].resource_type.endswith("virtualNetworkPeerings")

    def test_no_transit_flag_no_finding(self):
        assert _net(topology(subscription(vnets=[self._vnet(allow_gateway_transit=False)])), "AZ-NET-005") == []


def test_flow_logs_unknown_without_rows_and_observed_with_them():
    v = vnet("v", flow_logs_enabled=False)
    assert "flowlogs rows" in _unknown(topology(subscription(vnets=[v])), "AZ-NET-006")
    assert "flowlogs rows" in _unknown(topology(subscription(vnets=[v])), "AZ-NET-014")
    fl = FlowLog(id="fl", name="fl", target_resource_id="/nsg", enabled=True, traffic_analytics_enabled=False)
    topo = topology(subscription(vnets=[v, vnet("covered", flow_logs_enabled=True)], flow_logs=[fl]))
    assert [f.resource_id for f in _net(topo, "AZ-NET-006")] == [v.id]
    assert len(_net(topo, "AZ-NET-014")) == 1 and _unknown(topo, "AZ-NET-014") is None
    ta = FlowLog(id="fl2", name="fl2", target_resource_id="/nsg", enabled=True, traffic_analytics_enabled=True)
    assert _net(topology(subscription(flow_logs=[ta])), "AZ-NET-014") == []


def test_app_gateway_waf_rules_007_and_025():
    plain = app_gateway("plain", "Standard_v2", waf_enabled=False)
    f = _net(topology(subscription(application_gateways=[plain])), "AZ-NET-007")
    assert len(f) == 1 and any(m.pillar == "Applications and Workloads" for m in f[0].framework_mappings)
    detection = app_gateway("det", "WAF_v2", waf_enabled=True, waf_mode="Detection")
    topo = topology(subscription(application_gateways=[detection]))
    assert _net(topo, "AZ-NET-007") == [] and len(_net(topo, "AZ-NET-025")) == 1
    policy = AppGatewayWafPolicy(id="wp", name="wp", resource_group="rg", state="Enabled", mode="Prevention")
    via_policy = app_gateway("pol", "WAF_v2", waf_policy=policy)
    topo = topology(subscription(application_gateways=[via_policy]))
    assert _net(topo, "AZ-NET-007") == [] and _net(topo, "AZ-NET-025") == []
    disabled = AppGatewayWafPolicy(id="wp2", name="wp2", resource_group="rg", state="Disabled", mode="Prevention")
    assert (
        len(
            _net(
                topology(subscription(application_gateways=[app_gateway("d", "WAF_v2", waf_policy=disabled)])),
                "AZ-NET-007",
            )
        )
        == 1
    )


def test_subnet_ip_exhaustion_011_is_derived_from_ip_configurations():
    full = subnet("v", "dense", "10.0.0.0/27", ip_configuration_count=22)  # 27 usable, 22 used = 81 percent
    sparse = subnet("v", "sparse", "10.0.1.0/24", ip_configuration_count=10)
    tiny = subnet("v", "tiny", "10.0.2.0/30", ip_configuration_count=0)  # fewer than 5 usable: skipped
    bad = subnet("v", "bad", "not-a-prefix", ip_configuration_count=99)
    dual = subnet("v", "dual", "", address_prefixes=["10.0.3.0/28", "fd00::/64"], ip_configuration_count=9)
    v = vnet("v", subnets=[full, sparse, tiny, bad, dual])
    findings = _net(topology(subscription(vnets=[v])), "AZ-NET-011")
    assert sorted(f.resource_id for f in findings) == sorted([full.id, dual.id])
    assert (
        "22 ipConfigurations against 27 usable"
        in next(f for f in findings if f.resource_id == full.id).observed_state.fact
    )
    assert findings[0].rule_version == 2


def _rt(name: str, routes: list[tuple[str, str]], **extra) -> AzureRouteTable:
    return AzureRouteTable(
        id=f"/rt/{name}",
        name=name,
        location="eastus2",
        resource_group="rg",
        routes=[AzureRouteEntry(name=f"r{i}", address_prefix=p, next_hop_type=h) for i, (p, h) in enumerate(routes)],
        **extra,
    )


def test_spoke_fw_bypass_012_resolves_route_tables_by_id():
    nva = _rt("to-nva", [("0.0.0.0/0", "VirtualAppliance")])
    internet = _rt("to-internet", [("0.0.0.0/0", "Internet")])
    spoke = vnet(
        "spoke",
        peerings=[peering("to-hub", "/x/hub", use_remote_gateways=True)],
        subnets=[
            subnet("spoke", "no-rt"),
            subnet("spoke", "nva", route_table_id=nva.id),
            subnet("spoke", "internet", route_table_id=internet.id),
            subnet("spoke", "missing", route_table_id="/rt/not-in-export"),
            subnet("spoke", "AzureBastionSubnet"),
        ],
    )
    findings = _net(topology(subscription(vnets=[spoke], route_tables=[nva, internet])), "AZ-NET-012")
    assert sorted(f.resource_id.rsplit("/", 1)[-1] for f in findings) == ["internet", "no-rt"]
    not_spoke = vnet("alone", subnets=[subnet("alone", "s")])
    assert _net(topology(subscription(vnets=[not_spoke])), "AZ-NET-012") == []


def test_front_door_waf_detection_018():
    policy = FrontDoorWAFPolicy(id="fd", name="fd-waf", resource_group="rg", location="global", policy_mode="Detection")
    f = _net(topology(subscription(front_door_waf_policies=[policy])), "AZ-NET-018")
    assert len(f) == 1 and any(m.pillar == "Applications and Workloads" for m in f[0].framework_mappings)
    prevention = FrontDoorWAFPolicy(
        id="fd2", name="fd2", resource_group="rg", location="global", policy_mode="Prevention"
    )
    assert _net(topology(subscription(front_door_waf_policies=[prevention])), "AZ-NET-018") == []


# ── Engine B, ported as typed rules ────────────────────────────────────────


def _nsg(*rules: NSGSecurityRule) -> AzureNSG:
    return AzureNSG(id="/nsg/n", name="n", location="eastus2", resource_group="rg", security_rules=list(rules))


def _rule(name, *, access="Allow", direction="Inbound", protocol="Tcp", src="*", ports=None, port=None, prefixes=None):
    return NSGSecurityRule(
        name=name,
        priority=100,
        direction=direction,
        access=access,
        protocol=protocol,
        source_address_prefix=src,
        source_address_prefixes=prefixes or [],
        destination_port_range=port,
        destination_port_ranges=ports or [],
        destination_address_prefix="*",
    )


def test_nsg_rdp_ssh_from_internet_020_expands_ranges_and_wildcards():
    nsg = _nsg(
        _rule("rdp", src="Internet", port="3389"),
        _rule("ssh-range", src="0.0.0.0/0", ports=["20-25"]),
        _rule("any-port", src="*", port="*"),
        _rule("deny", access="Deny", src="Internet", port="22"),
        _rule("outbound", direction="Outbound", src="Internet", port="22"),
        _rule("vnet", src="VirtualNetwork", port="22"),
        _rule("prefixes", src=None, prefixes=["10.0.0.0/8", "Internet"], port="22"),
    )
    findings = _net(topology(subscription(nsgs=[nsg])), "AZ-NET-020")
    names = sorted(f.resource_id.rsplit("/", 1)[-1] for f in findings)
    assert names == ["any-port", "prefixes", "rdp", "ssh-range"]
    assert findings[0].severity == "critical" and findings[0].affected_resources == ["/nsg/n"]
    assert "22, 3389" in next(f for f in findings if f.resource_id.endswith("any-port")).observed_state.fact


def test_nsg_wildcard_allow_all_021():
    nsg = _nsg(
        _rule("open", src="*", port="*", protocol="*"),
        _rule("open-out", direction="Outbound", src="Any", port="*", protocol="*"),
        _rule("tcp-only", src="*", port="*", protocol="Tcp"),
        _rule("one-port", src="*", port="443", protocol="*"),
    )
    findings = _net(topology(subscription(nsgs=[nsg])), "AZ-NET-021")
    assert sorted(f.resource_id.rsplit("/", 1)[-1] for f in findings) == ["open", "open-out"]


def test_route_table_rules_022_and_023():
    internet = _rt("internet", [("0.0.0.0/0", "Internet"), ("10.0.0.0/8", "VnetLocal")])
    nobgp = _rt("nobgp", [], disable_bgp_route_propagation=True)
    topo = topology(subscription(route_tables=[internet, nobgp]))
    assert [f.resource_id for f in _net(topo, "AZ-NET-022")] == [internet.id]
    f023 = _net(topo, "AZ-NET-023")
    assert [f.resource_id for f in f023] == [nobgp.id] and f023[0].severity == "informational"


def test_vnet_custom_dns_024():
    assert _net(topology(subscription(vnets=[vnet("azure", dns_servers=["168.63.129.16"])])), "AZ-NET-024") == []
    f = _net(topology(subscription(vnets=[vnet("custom", dns_servers=["10.0.4.4", "168.63.129.16"])])), "AZ-NET-024")
    assert (
        len(f) == 1
        and "10.0.4.4" in f[0].observed_state.fact
        and "168.63" not in f[0].observed_state.fact.split(":")[-1]
    )


def _lb(name: str, sku: str) -> AzureLoadBalancer:
    return AzureLoadBalancer(id=f"/lb/{name}", name=name, location="eastus2", resource_group="rg", sku_name=sku)


def test_basic_sku_rules_026_027_028():
    topo = topology(
        subscription(
            load_balancers=[_lb("basic", "Basic"), _lb("std", "Standard")],
            public_ips=[
                AzurePublicIP(id="/pip/b", name="b", location="eastus2", resource_group="rg", sku_name="Basic"),
                AzurePublicIP(
                    id="/pip/b2",
                    name="b2",
                    location="eastus2",
                    resource_group="rg",
                    sku_name="Basic",
                    associated_resource_type="NIC",
                ),
                AzurePublicIP(id="/pip/s", name="s", location="eastus2", resource_group="rg", sku_name="Standard"),
            ],
            virtual_network_gateways=[
                gateway("basic", sku_name="Basic"),
                gateway("er-basic", "ExpressRoute", sku_name="Basic"),
            ],
        )
    )
    assert [f.resource_id for f in _net(topo, "AZ-NET-026")] == ["/lb/basic"]
    assert sorted(f.resource_id for f in _net(topo, "AZ-NET-027")) == ["/pip/b", "/pip/b2"], "one finding per IP"
    assert [f.resource_id for f in _net(topo, "AZ-NET-028")] == ["gw-basic"]


def test_vpn_generation_029():
    topo = topology(
        subscription(
            virtual_network_gateways=[gateway("g1", generation="Generation1"), gateway("g2", generation="Generation2")]
        )
    )
    assert [f.resource_id for f in _net(topo, "AZ-NET-029")] == ["gw-g1"]


def _conn(name: str, status: str) -> AzureGatewayConnection:
    return AzureGatewayConnection(id=f"/conn/{name}", name=name, connection_type="IPsec", connection_status=status)


def test_gateway_connection_status_030_and_unknown_without_connection_rows():
    gw = gateway("gw", connections=[_conn("down", "NotConnected"), _conn("up", "Connected"), _conn("u", "Unknown")])
    counted = topology(
        subscription(virtual_network_gateways=[gw]), resource_counts={"microsoft.network/connections": 3}
    )
    findings = _net(counted, "AZ-NET-030")
    assert [f.resource_id for f in findings] == ["/conn/down"] and findings[0].affected_resources == ["gw-gw"]
    no_rows = topology(subscription(virtual_network_gateways=[gateway("gw2")]))
    assert "no connections rows" in _unknown(no_rows, "AZ-NET-030")
    assert _unknown(topology(subscription()), "AZ-NET-030") is None, "no gateways: nothing to say"


def test_private_endpoint_pending_031():
    def pe(name, status):
        return AzurePrivateEndpoint(
            id=f"/pe/{name}",
            name=name,
            location="eastus2",
            resource_group="rg",
            service_connections=[
                AzurePrivateEndpointConnection(
                    connection_name="c", private_link_service_id="/x/storage", connection_state=status
                )
            ],
        )

    topo = topology(subscription(private_endpoints=[pe("pending", "Pending"), pe("ok", "Approved")]))
    f = _net(topo, "AZ-NET-031")
    assert [x.resource_id for x in f] == ["/pe/pending"] and "storage" in f[0].observed_state.fact


def test_no_firewall_032_with_suppressions():
    assert len(_net(topology(subscription(vnets=[vnet("a")])), "AZ-NET-032")) == 1
    assert _net(topology(subscription()), "AZ-NET-032") == []
    assert _net(topology(subscription(vnets=[vnet("a")], firewalls=[firewall("fw")])), "AZ-NET-032") == []
    nva = _rt("nva", [("0.0.0.0/0", "VirtualAppliance")])
    assert _net(topology(subscription(vnets=[vnet("a")], route_tables=[nva])), "AZ-NET-032") == []
    hub = AzureVHub(
        id="vh",
        name="vh",
        location="eastus2",
        resource_group="rg",
        address_prefix="10.9.0.0/23",
        azure_firewall_id="/fw",
    )
    secured = subscription(
        sub="00000000-0000-0000-0000-000000000002",
        virtual_wans=[AzureVWan(id="w", name="w", resource_group="rg", sku="Standard", hubs=[hub])],
    )
    assert _net(topology(subscription(vnets=[vnet("a")]), secured), "AZ-NET-032") == []
    f = _net(topology(subscription(vnets=[vnet("a")])), "AZ-NET-032")
    assert f[0].severity == "medium" and f[0].resource_id == f"/subscriptions/{SUB}" and f[0].affected_resources


def test_no_bastion_033_is_low():
    f = _net(topology(subscription(vnets=[vnet("a")])), "AZ-NET-033")
    assert len(f) == 1 and f[0].severity == "low" and f[0].traffic_direction == "management"
    bastion = AzureBastionHost(id="b", name="b", location="eastus2", resource_group="rg")
    assert _net(topology(subscription(vnets=[vnet("a")], bastion_hosts=[bastion])), "AZ-NET-033") == []

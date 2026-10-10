# Ported from saulpatinojr/Work-Cloud_Network_Core tests/unit/test_bcdr_signals.py at 5d3b914; changes: lab model
# builders and the registry's evaluate() replace generate_bcdr_findings; the discovery_blocked case is gone; cases for
# the new AZ-BCDR-006/007 added.
from network_assessment.model.topology import AzureLBFrontendIP, AzureLoadBalancer
from network_assessment.rules import evaluate

from ..model_fixtures import SUB, app_gateway, circuit, firewall, gateway, rule_ids, subscription, topology, vnet


def _bcdr(*subs):
    return [f for f in evaluate(topology(*subs)).findings if f.rule_id.startswith("AZ-BCDR-")]


def test_single_zone_firewall_emits_bcdr_001():
    assert "AZ-BCDR-001" in rule_ids(_bcdr(subscription(firewalls=[firewall("fw", zones=["1"])])))


def test_zone_redundant_firewall_passes_bcdr_001():
    assert "AZ-BCDR-001" not in rule_ids(_bcdr(subscription(firewalls=[firewall("fw", zones=["1", "2", "3"])])))


def test_active_passive_vpn_gateway_emits_bcdr_002():
    gw = gateway("vpn-gw", active_active=False, zones=["1", "2", "3"])
    findings = _bcdr(subscription(virtual_network_gateways=[gw]))
    assert "AZ-BCDR-002" in rule_ids(findings) and "AZ-BCDR-005" not in rule_ids(findings)
    f = next(f for f in findings if f.rule_id == "AZ-BCDR-002")
    assert f.traffic_direction == "north_south" and f.framework_mappings and f.category == "BC/DR"


def test_single_er_gateway_with_circuit_emits_bcdr_003():
    er_gw = gateway("er-gw", "ExpressRoute", sku_name="Standard", zones=["1", "2", "3"])
    findings = _bcdr(subscription(virtual_network_gateways=[er_gw], express_route_circuits=[circuit()]))
    f = next(f for f in findings if f.rule_id == "AZ-BCDR-003")
    assert f.severity == "high" and "circuit-1" in f.observed_state.fact


def test_single_firewall_spof_emits_bcdr_004_once_across_subscriptions():
    hub = subscription(vnets=[vnet("hub"), vnet("spoke-1")], firewalls=[firewall("fw", zones=["1", "2", "3"])])
    other = subscription(
        sub="00000000-0000-0000-0000-000000000002", vnets=[vnet("spoke-2", sub="00000000-0000-0000-0000-000000000002")]
    )
    findings = [f for f in _bcdr(hub, other) if f.rule_id == "AZ-BCDR-004"]
    assert len(findings) == 1 and findings[0].account_id == SUB and "3 VNets" in findings[0].observed_state.fact


def test_two_firewalls_or_one_vnet_do_not_emit_bcdr_004():
    assert "AZ-BCDR-004" not in rule_ids(_bcdr(subscription(vnets=[vnet("only")], firewalls=[firewall("fw")])))
    assert "AZ-BCDR-004" not in rule_ids(
        _bcdr(subscription(vnets=[vnet("a"), vnet("b")], firewalls=[firewall("fw1"), firewall("fw2")]))
    )


def test_non_zone_redundant_gateway_emits_bcdr_005_but_basic_is_skipped():
    gw = gateway("vpn-gw", sku_name="VpnGw2", active_active=True, zones=[])
    assert "AZ-BCDR-005" in rule_ids(_bcdr(subscription(virtual_network_gateways=[gw])))
    basic = gateway("basic", sku_name="Basic", active_active=True, zones=[])
    assert "AZ-BCDR-005" not in rule_ids(_bcdr(subscription(virtual_network_gateways=[basic])))


def test_app_gateway_zone_redundancy_bcdr_006():
    assert "AZ-BCDR-006" in rule_ids(
        _bcdr(subscription(application_gateways=[app_gateway("agw", "WAF_v2", zones=["1"])]))
    )
    assert "AZ-BCDR-006" not in rule_ids(
        _bcdr(subscription(application_gateways=[app_gateway("agw", "WAF_v2", zones=["1", "2"])]))
    )
    assert "AZ-BCDR-006" not in rule_ids(
        _bcdr(subscription(application_gateways=[app_gateway("v1", "Standard_Medium", zones=[])]))
    )


def _lb(sku: str, zones: list[str]) -> AzureLoadBalancer:
    return AzureLoadBalancer(
        id="lb-1",
        name="lb-1",
        location="eastus2",
        resource_group="rg",
        sku_name=sku,
        frontend_ip_configs=[AzureLBFrontendIP(name="fe", zones=zones)],
    )


def test_standard_lb_frontend_zones_bcdr_007():
    assert "AZ-BCDR-007" in rule_ids(_bcdr(subscription(load_balancers=[_lb("Standard", [])])))
    assert "AZ-BCDR-007" not in rule_ids(_bcdr(subscription(load_balancers=[_lb("Standard", ["1", "2", "3"])])))
    assert "AZ-BCDR-007" not in rule_ids(_bcdr(subscription(load_balancers=[_lb("Basic", [])])))

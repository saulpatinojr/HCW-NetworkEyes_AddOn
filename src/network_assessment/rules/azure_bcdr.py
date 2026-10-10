# Ported from saulpatinojr/Work-Cloud_Network_Core cna/modules/network/analysis/bcdr_signals.py at 5d3b914; changes:
# (source also covers AZ-BCDR-001..005; AZ-BCDR-006/007 come from apps/cna-api/main.py `_check_app_gateways` /
# `_check_load_balancers` zone checks at the same commit) the
# `_finding` builder and `_FindingParams` are replaced by the registry's `Emit`; the `discovery_blocked` skip is gone;
# framework mappings moved to rules/frameworks.py; evidence refs read `export:`; hedge language removed from the texts.
"""AZ-BCDR-* resilience rules over the lab topology model."""

from __future__ import annotations

from collections.abc import Iterator

from network_assessment.model.findings import FindingSeverity as S
from network_assessment.model.topology import AzureSubscriptionTopology, AzureTopology
from network_assessment.rules.frameworks import FRAMEWORKS as F
from network_assessment.rules.registry import Emit, NotEvaluable, rule

_MIN_REDUNDANCY_ZONES = 2
_SINGLE_GATEWAY = 1
T_FW = "Microsoft.Network/azureFirewalls"
T_VNG = "Microsoft.Network/virtualNetworkGateways"
T_AGW = "Microsoft.Network/applicationGateways"
T_LB = "Microsoft.Network/loadBalancers"

Rows = Iterator[Emit | NotEvaluable]


def _ref(sub: AzureSubscriptionTopology, path: str) -> str:
    return f"export:{sub.subscription_id}.{path}"


@rule(
    id="AZ-BCDR-001",
    title="Azure Firewall is not zone-redundant",
    severity=S.MEDIUM,
    category="BC/DR",
    version=1,
    learn_url="https://learn.microsoft.com/azure/firewall/deploy-availability-zone-powershell",
    frameworks=F["AZ-BCDR-001"],
    evidence="azurefirewalls zones count below 2",
    remediation="Redeploy the firewall with zones [1, 2, 3] and zone-redundant public IPs.",
    description=(
        "A single-zone firewall has no protection against a zonal failure; every flow routed through it stops during "
        "a zone outage."
    ),
)
def fw_not_zone_redundant(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for fw in sub.firewalls:
        if len(fw.zones) >= _MIN_REDUNDANCY_ZONES:
            continue
        yield Emit(
            resource_id=fw.id,
            resource_type=T_FW,
            region=fw.location,
            fact=(
                f"Azure Firewall {fw.name} ({fw.sku_tier} tier) in {fw.location} is deployed in {len(fw.zones)} "
                f"availability zone(s)."
            ),
            evidence_ref=_ref(sub, f"firewalls[id={fw.id}].zones"),
        )


@rule(
    id="AZ-BCDR-002",
    title="VPN gateway runs in active-passive mode",
    severity=S.MEDIUM,
    category="BC/DR",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/vpn-gateway-highlyavailable",
    frameworks=F["AZ-BCDR-002"],
    evidence="virtualnetworkgateways gatewayType Vpn with activeActive false",
    remediation=(
        "Enable active-active mode (a second public IP and a VpnGw2 or higher SKU) and BGP for automatic failover."
    ),
    description="Active-passive gateways interrupt tunnels during failover and planned maintenance.",
)
def vpn_active_passive(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for gw in sub.virtual_network_gateways:
        if gw.gateway_type == "Vpn" and not gw.active_active:
            yield Emit(
                resource_id=gw.id,
                resource_type=T_VNG,
                region=gw.location,
                fact=f"VPN gateway {gw.name} (SKU: {gw.sku_name}) has activeActive=false.",
                evidence_ref=_ref(sub, f"virtual_network_gateways[id={gw.id}].active_active"),
            )


@rule(
    id="AZ-BCDR-003",
    title="Single ExpressRoute gateway terminates all circuit connectivity",
    severity=S.HIGH,
    category="BC/DR",
    version=1,
    learn_url=(
        "https://learn.microsoft.com/azure/expressroute/designing-for-disaster-recovery-with-expressroute-privatepeering"
    ),
    frameworks=F["AZ-BCDR-003"],
    evidence="expressroutecircuits present and exactly one virtualnetworkgateways row with gatewayType ExpressRoute",
    remediation=(
        "Deploy a second ExpressRoute gateway in another region, or a zone-redundant SKU plus a VPN failover path."
    ),
    description="All ExpressRoute private connectivity depends on one gateway.",
)
def single_er_gateway(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    er_gateways = [gw for gw in sub.virtual_network_gateways if gw.gateway_type == "ExpressRoute"]
    if sub.express_route_circuits and len(er_gateways) == _SINGLE_GATEWAY:
        gw = er_gateways[0]
        circuit_names = ", ".join(c.name for c in sub.express_route_circuits[:5])
        yield Emit(
            resource_id=gw.id,
            resource_type=T_VNG,
            region=gw.location,
            fact=(
                f"Subscription {sub.subscription_id} has {len(sub.express_route_circuits)} ExpressRoute circuit(s) "
                f"({circuit_names}) but only one ExpressRoute gateway ({gw.name}, SKU: {gw.sku_name})."
            ),
            evidence_ref=_ref(sub, "virtual_network_gateways[gateway_type=ExpressRoute]"),
        )


@rule(
    id="AZ-BCDR-004",
    title="One Azure Firewall is a single point of failure for the whole footprint",
    severity=S.HIGH,
    category="BC/DR",
    version=1,
    learn_url="https://learn.microsoft.com/azure/architecture/networking/architecture/hub-spoke",
    frameworks=F["AZ-BCDR-004"],
    evidence="exactly one azurefirewalls row across the export and more than one VNet",
    remediation=(
        "Deploy the firewall zone-redundant with a recorded bypass runbook; for multi-region footprints, one secured "
        "hub per region."
    ),
    description=(
        "When spoke traffic is force-tunnelled through one firewall, a firewall outage halts east-west and "
        "internet-bound traffic for every VNet."
    ),
)
def single_firewall_spof(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    all_firewalls = [(s.subscription_id, fw) for s in topo.subscriptions for fw in s.firewalls]
    vnet_count = sum(len(s.vnets) for s in topo.subscriptions)
    if len(all_firewalls) != 1 or vnet_count <= 1:
        return
    owner, fw = all_firewalls[0]
    if owner != sub.subscription_id:
        return
    yield Emit(
        resource_id=fw.id,
        resource_type=T_FW,
        region=fw.location,
        fact=(
            f"One Azure Firewall ({fw.name}, {fw.sku_tier} tier, {len(fw.zones)} zone(s)) is in the export while "
            f"{vnet_count} VNets are."
        ),
        evidence_ref=_ref(sub, f"firewalls[id={fw.id}]"),
    )


@rule(
    id="AZ-BCDR-005",
    title="Virtual network gateway is not zone-redundant",
    severity=S.MEDIUM,
    category="BC/DR",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/about-zone-redundant-vnet-gateways",
    frameworks=F["AZ-BCDR-005"],
    evidence="virtualnetworkgateways (non-Basic SKU) zones count below 2",
    remediation=(
        "Migrate to an AZ SKU (VpnGw2AZ, ErGw2AZ or higher) deployed with zones [1, 2, 3] and zone-redundant public "
        "IPs."
    ),
    description="A zonal failure takes down every tunnel or circuit terminating on this gateway.",
)
def gw_not_zone_redundant(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for gw in sub.virtual_network_gateways:
        if gw.sku_name.lower() != "basic" and len(gw.zones) < _MIN_REDUNDANCY_ZONES:
            yield Emit(
                resource_id=gw.id,
                resource_type=T_VNG,
                region=gw.location,
                fact=(
                    f"{gw.gateway_type} gateway {gw.name} (SKU: {gw.sku_name}) is deployed in {len(gw.zones)} "
                    f"availability zone(s)."
                ),
                evidence_ref=_ref(sub, f"virtual_network_gateways[id={gw.id}].zones"),
            )


@rule(
    id="AZ-BCDR-006",
    title="Application Gateway v2 is not zone-redundant",
    severity=S.MEDIUM,
    category="BC/DR",
    version=1,
    learn_url="https://learn.microsoft.com/azure/application-gateway/application-gateway-autoscaling-zone-redundant",
    frameworks=F["AZ-BCDR-006"],
    evidence="applicationgateways v2 SKU with zones count below 2",
    remediation="Redeploy the gateway with zones [1, 2, 3] and a zone-redundant Standard public IP.",
    description="A gateway in fewer than two zones is a single point of failure for the ingress it fronts.",
)
def agw_not_zone_redundant(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for agw in sub.application_gateways:
        if not agw.sku_name.lower().endswith("_v2") or len(agw.zones) >= _MIN_REDUNDANCY_ZONES:
            continue
        yield Emit(
            resource_id=agw.id,
            resource_type=T_AGW,
            region=agw.location,
            fact=(
                f"Application Gateway {agw.name} ({agw.sku_name}) is deployed in {len(agw.zones)} availability zone(s)."
            ),
            evidence_ref=_ref(sub, f"application_gateways[id={agw.id}].zones"),
        )


@rule(
    id="AZ-BCDR-007",
    title="Standard load balancer frontend is not zone-redundant",
    severity=S.LOW,
    category="BC/DR",
    version=1,
    learn_url="https://learn.microsoft.com/azure/reliability/reliability-load-balancer",
    frameworks=F["AZ-BCDR-007"],
    evidence="loadbalancers Standard SKU whose frontendIPConfigurations carry fewer than 2 zones",
    remediation="Configure the frontend IP as zone-redundant (zones [1, 2, 3]) and spread the backend across zones.",
    description="A zonal frontend stops serving when its zone fails.",
)
def lb_not_zone_redundant(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for lb in sub.load_balancers:
        if lb.sku_name.lower() != "standard":
            continue
        if len(lb.zones) >= _MIN_REDUNDANCY_ZONES or any(
            len(f.zones) >= _MIN_REDUNDANCY_ZONES for f in lb.frontend_ip_configs
        ):
            continue
        zones = max((len(f.zones) for f in lb.frontend_ip_configs), default=0)
        yield Emit(
            resource_id=lb.id,
            resource_type=T_LB,
            region=lb.location,
            fact=(
                f"Load balancer {lb.name} ({lb.lb_type}) has {len(lb.frontend_ip_configs)} frontend IP "
                f"configuration(s) with at most {zones} zone(s) each."
            ),
            evidence_ref=_ref(sub, f"load_balancers[id={lb.id}].frontend_ip_configs[].zones"),
        )

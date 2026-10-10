# Ported from saulpatinojr/HCW-NetworkEyes_App cna/ai_engine/analysis_engine.py (Engine A, `_check_azure_*`,
# lines 639-1660) and apps/cna-api/main.py (Engine B, `_check_*`, lines 195-1127) at 5d3b914; changes: the
# AnalysisEngine
# class, EngagementStore, escalation and AWS methods are gone; each check is a typed `@rule` evaluator yielding `Emit`
# over the lab model; framework mappings moved to rules/frameworks.py; evidence refs read `export:` instead of
# `discovery:`; AZ-NET-002 merges Engine B's platform-subnet skip list (version 2); AZ-NET-003 resolves the linked
# firewall policy; AZ-NET-006/014 read flowlogs rows and answer unknown when the export has none; AZ-NET-011 is
# re-derived from ipConfigurations per subnet (version 2); AZ-NET-012 resolves route tables by id; Engine B's untyped
# dict checks become AZ-NET-020..033 with the severities in design B.4 (032 MEDIUM with NVA/vWAN suppression, 033 LOW,
# 027 one finding per IP); hedge language removed from every title, fact and remediation (the enforcer gates them);
# AZ-NET-008/009/010/013/015/016/017/019 (metrics and diagnostic settings) are registered live-only.
"""AZ-NET-* rules over the lab topology model."""

from __future__ import annotations

import ipaddress
from collections.abc import Iterator

from network_assessment.model.findings import FindingSeverity as S
from network_assessment.model.topology import (
    AzureSubscriptionTopology,
    AzureTopology,
    NSGSecurityRule,
    VNet,
)
from network_assessment.rules.frameworks import FRAMEWORKS as F
from network_assessment.rules.registry import Emit, NotEvaluable, live_only, rule

T_VNET = "Microsoft.Network/virtualNetworks"
T_SUBNET = "Microsoft.Network/virtualNetworks/subnets"
T_PEERING = "Microsoft.Network/virtualNetworks/virtualNetworkPeerings"
T_NSG = "Microsoft.Network/networkSecurityGroups"
T_RT = "Microsoft.Network/routeTables"
T_FW = "Microsoft.Network/azureFirewalls"
T_ER = "Microsoft.Network/expressRouteCircuits"
T_AGW = "Microsoft.Network/applicationGateways"
T_LB = "Microsoft.Network/loadBalancers"
T_PIP = "Microsoft.Network/publicIPAddresses"
T_VNG = "Microsoft.Network/virtualNetworkGateways"
T_CONN = "Microsoft.Network/connections"
T_PE = "Microsoft.Network/privateEndpoints"
T_FLOWLOG = "Microsoft.Network/networkWatchers/flowLogs"
T_FDWAF = "Microsoft.Network/frontDoorWebApplicationFirewallPolicies"
T_BASTION = "Microsoft.Network/bastionHosts"

# Engine A skipped GatewaySubnet only; Engine B skipped its _PLATFORM_SUBNETS. The lab skips the union.
PLATFORM_SUBNETS = frozenset(
    {"gatewaysubnet", "azurefirewallsubnet", "azurefirewallmanagementsubnet", "routeserversubnet"}
)
# Engine A's _INFRA_SUBNETS (fw bypass rule): same set plus AzureBastionSubnet.
INFRA_SUBNETS = PLATFORM_SUBNETS | {"azurebastionsubnet"}
INTERNET_SOURCES = frozenset({"*", "internet", "0.0.0.0/0", "any", "::/0"})
AZURE_DNS = "168.63.129.16"
RESERVED_ADDRESSES_PER_SUBNET = 5
IP_EXHAUSTION_PCT = 80.0
MIN_ZONES = 2
PORT_SSH = 22
PORT_RDP = 3389

Rows = Iterator[Emit | NotEvaluable]


def _ref(sub: AzureSubscriptionTopology, path: str) -> str:
    return f"export:{sub.subscription_id}.{path}"


# ── Engine A, ported ───────────────────────────────────────────────────────


@rule(
    id="AZ-NET-001",
    title="VNet does not have DDoS Protection enabled",
    severity=S.LOW,
    category="Network Protection",
    version=1,
    learn_url="https://learn.microsoft.com/azure/ddos-protection/ddos-protection-overview",
    frameworks=F["AZ-NET-001"],
    evidence="virtualnetworks properties.enableDdosProtection",
    remediation=(
        "Attach a DDoS Network Protection plan to VNets that host public-facing workloads, in particular those with "
        "application gateways or public IPs."
    ),
    description=(
        "The VNet is not protected by a DDoS Network Protection plan; it relies on the platform's infrastructure "
        "protection only."
    ),
)
def vnet_no_ddos(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for vnet in sub.vnets:
        if not vnet.ddos_protection_enabled:
            yield Emit(
                resource_id=vnet.id,
                resource_type=T_VNET,
                region=vnet.location,
                fact=f"VNet {vnet.name} ({vnet.id}) in {vnet.location} has enableDdosProtection=false.",
                evidence_ref=_ref(sub, f"vnets[id={vnet.id}].ddos_protection_enabled"),
            )


@rule(
    id="AZ-NET-002",
    title="Subnet has no Network Security Group",
    severity=S.HIGH,
    category="Network Segmentation",
    version=2,
    learn_url="https://learn.microsoft.com/azure/virtual-network/network-security-groups-overview",
    frameworks=F["AZ-NET-002"],
    evidence="virtualnetworks properties.subnets[].properties.networkSecurityGroup (platform subnets skipped)",
    remediation=(
        "Attach an NSG with least-privilege inbound rules: deny by default, permit only the required ports from "
        "approved sources."
    ),
    description=(
        "Every workload subnet carries an NSG; GatewaySubnet, AzureFirewallSubnet, AzureFirewallManagementSubnet and "
        "RouteServerSubnet are platform subnets and are skipped."
    ),
)
def subnet_no_nsg(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for vnet in sub.vnets:
        for subnet in vnet.subnets:
            if subnet.nsg_id or subnet.name.lower() in PLATFORM_SUBNETS:
                continue
            yield Emit(
                resource_id=subnet.id,
                resource_type=T_SUBNET,
                region=vnet.location,
                fact=f"Subnet {subnet.name} ({subnet.id}) in VNet {vnet.name} has no NSG attached.",
                evidence_ref=_ref(sub, f"vnets[id={vnet.id}].subnets[id={subnet.id}].nsg_id"),
            )


@rule(
    id="AZ-NET-003",
    title="Azure Firewall Threat Intelligence mode is not set to Deny",
    severity=S.CRITICAL,
    category="Network Security",
    version=2,
    learn_url="https://learn.microsoft.com/azure/firewall/threat-intel",
    frameworks=F["AZ-NET-003"],
    evidence="azurefirewalls properties.threatIntelMode, else the linked firewallpolicies properties.threatIntelMode",
    remediation=(
        "Set Threat Intelligence to Deny in the firewall policy after reviewing the alert logs for legitimate traffic."
    ),
    description="Known malicious IPs and domains are alerted on but not blocked.",
)
def fw_threat_intel(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for fw in sub.firewalls:
        mode = fw.effective_threat_intel_mode
        if mode.lower() == "deny":
            continue
        source = "firewall policy" if fw.firewall_policy and fw.firewall_policy.threat_intel_mode else "firewall"
        yield Emit(
            resource_id=fw.id,
            resource_type=T_FW,
            region=fw.location,
            fact=(
                f"Azure Firewall {fw.name} has threatIntelMode='{mode}' (from the {source}). Known malicious IPs and "
                f"domains are not blocked."
            ),
            evidence_ref=_ref(sub, f"firewalls[id={fw.id}].threat_intel_mode"),
        )


@rule(
    id="AZ-NET-004",
    title="Single ExpressRoute circuit — no redundancy",
    severity=S.LOW,
    category="Connectivity",
    version=1,
    learn_url="https://learn.microsoft.com/azure/expressroute/designing-for-high-availability-with-expressroute",
    frameworks=F["AZ-NET-004"],
    evidence="count of expressroutecircuits rows in the subscription",
    remediation="Add a second circuit in another peering location, or a VPN connection as a failover path.",
    description="One circuit terminates all private connectivity in this subscription.",
    needs_properties=False,
)
def er_redundancy(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    if len(sub.express_route_circuits) == 1:
        er = sub.express_route_circuits[0]
        bandwidth = f"{er.bandwidth_mbps}Mbps" if er.bandwidth_mbps else "unknown bandwidth"
        yield Emit(
            resource_id=er.id,
            resource_type=T_ER,
            region=er.location,
            fact=(
                f"Only one ExpressRoute circuit ({er.name}, {bandwidth} via "
                f"{er.service_provider or 'unknown provider'}) is in subscription {sub.subscription_id}."
            ),
            evidence_ref=_ref(sub, "express_route_circuits"),
        )


@rule(
    id="AZ-NET-005",
    title="VNet peering allows gateway transit but VNet has no gateway",
    severity=S.LOW,
    category="Routing & Transit",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/vpn-gateway-peering-gateway-transit",
    frameworks=F["AZ-NET-005"],
    evidence=(
        "virtualnetworkpeerings allowGatewayTransit and virtualnetworkgateways ipConfigurations subnet under the VNet"
    ),
    remediation="Disable allowGatewayTransit on the peering, or deploy the gateway the peering advertises.",
    description="Spoke VNets that use this transit path have no effective route.",
)
def peering_gateway_transit(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for vnet in sub.vnets:
        # A gateway lives in a GatewaySubnet; an ARM subnet id nests under its VNet id as "<vnet_id>/subnets/<name>".
        has_local_gw = any(
            gw.subnet_id and gw.subnet_id.lower().startswith(f"{vnet.id.lower()}/")
            for s in topo.subscriptions
            for gw in s.virtual_network_gateways
        )
        for peering in vnet.peerings:
            if peering.allow_gateway_transit and not has_local_gw:
                yield Emit(
                    resource_id=vnet.id,
                    resource_type=T_PEERING,
                    region=vnet.location,
                    fact=(
                        f"Peering {peering.name} on VNet {vnet.name} has allowGatewayTransit=true but no virtual "
                        f"network gateway is in this VNet."
                    ),
                    evidence_ref=_ref(sub, f"vnets[id={vnet.id}].peerings[name={peering.name}].allow_gateway_transit"),
                )


def _any_flow_logs(topo: AzureTopology) -> bool:
    return any(s.flow_logs for s in topo.subscriptions)


@rule(
    id="AZ-NET-006",
    title="VNet has no flow logs enabled",
    severity=S.HIGH,
    category="Observability",
    version=2,
    learn_url="https://learn.microsoft.com/azure/network-watcher/vnet-flow-logs-overview",
    frameworks=F["AZ-NET-006"],
    evidence=(
        "networkwatchers/flowlogs rows targeting the VNet, its subnets or its subnets' NSGs; unknown when the export "
        "has none"
    ),
    remediation=(
        "Enable virtual network flow logs (or NSG flow logs on every NSG) through Network Watcher with a Log "
        "Analytics destination."
    ),
    description="Traffic to and from this VNet produces no flow telemetry for investigation.",
)
def vnet_flow_logs(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    if not _any_flow_logs(topo):
        yield NotEvaluable("the export has no networkwatchers/flowlogs rows; flow-log state is unknown for every VNet")
        return
    for vnet in sub.vnets:
        if not vnet.flow_logs_enabled:
            yield Emit(
                resource_id=vnet.id,
                resource_type=T_VNET,
                region=vnet.location,
                fact=(
                    f"VNet {vnet.name} ({vnet.id}) in {vnet.location} has no enabled flow log targeting it, its "
                    f"subnets or its subnets' NSGs."
                ),
                evidence_ref=_ref(sub, f"vnets[id={vnet.id}].flow_logs_enabled"),
            )


def _agw_waf_enabled(agw) -> bool:
    if agw.waf_enabled:
        return True
    return bool(agw.waf_policy and (agw.waf_policy.state or "").lower() == "enabled")


def _agw_waf_mode(agw) -> str | None:
    if agw.waf_policy and agw.waf_policy.mode:
        return agw.waf_policy.mode
    return agw.waf_mode


@rule(
    id="AZ-NET-007",
    title="Application Gateway WAF is disabled",
    severity=S.HIGH,
    category="Application Security",
    version=2,
    learn_url="https://learn.microsoft.com/azure/web-application-firewall/ag/ag-overview",
    frameworks=F["AZ-NET-007"],
    evidence=(
        "applicationgateways sku.tier, webApplicationFirewallConfiguration.enabled or the linked WAF policy "
        "policySettings.state"
    ),
    remediation=(
        "Move the gateway to the WAF_v2 SKU with a WAF policy, run Detection first to tune false positives, then "
        "switch to Prevention."
    ),
    description=(
        "HTTP-layer attacks (injection, cross-site scripting, request smuggling) reach the backends uninspected."
    ),
)
def agw_waf_disabled(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for agw in sub.application_gateways:
        if _agw_waf_enabled(agw):
            continue
        yield Emit(
            resource_id=agw.id,
            resource_type=T_AGW,
            region=agw.location,
            fact=(
                f"Application Gateway {agw.name} ({agw.sku_name}) has no enabled Web Application Firewall "
                f"configuration or policy."
            ),
            evidence_ref=_ref(sub, f"application_gateways[id={agw.id}].waf_enabled"),
        )


@rule(
    id="AZ-NET-011",
    title="Subnet address space is close to exhaustion",
    severity=S.HIGH,
    category="Network Segmentation",
    version=2,
    learn_url="https://learn.microsoft.com/azure/virtual-network/virtual-networks-faq",
    frameworks=F["AZ-NET-011"],
    evidence=(
        "virtualnetworks subnets[].properties.ipConfigurations count against the prefix size minus the 5 reserved "
        "addresses (80 percent)"
    ),
    remediation=(
        "Add an address prefix to the subnet or the VNet, or move workloads to a larger subnet before allocations fail."
    ),
    description=(
        "Counted from the ipConfigurations the export lists on the subnet; delegated and private-endpoint subnets "
        "report their allocations the same way."
    ),
)
def subnet_ip_exhaustion(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for vnet in sub.vnets:
        for subnet in vnet.subnets:
            prefixes = subnet.address_prefixes or ([subnet.address_prefix] if subnet.address_prefix else [])
            total = 0
            for prefix in prefixes:
                try:
                    network = ipaddress.ip_network(prefix, strict=False)
                except ValueError:
                    continue
                if network.version == 4:
                    total += network.num_addresses
            usable = total - RESERVED_ADDRESSES_PER_SUBNET
            if usable <= 0:
                continue
            pct = subnet.ip_configuration_count / usable * 100
            if pct >= IP_EXHAUSTION_PCT:
                yield Emit(
                    resource_id=subnet.id,
                    resource_type=T_SUBNET,
                    region=vnet.location,
                    fact=(
                        f"Subnet {subnet.name} ({', '.join(prefixes)}) in VNet {vnet.name} lists "
                        f"{subnet.ip_configuration_count} ipConfigurations against {usable} usable addresses "
                        f"({pct:.0f} percent)."
                    ),
                    evidence_ref=_ref(sub, f"vnets[id={vnet.id}].subnets[id={subnet.id}].ip_configuration_count"),
                )


def _is_spoke(vnet: VNet) -> bool:
    return any(p.allow_forwarded_traffic or p.use_remote_gateways for p in vnet.peerings)


@rule(
    id="AZ-NET-012",
    title="Spoke subnet routes internet-bound traffic past the hub firewall",
    severity=S.MEDIUM,
    category="Network Segmentation",
    version=2,
    learn_url="https://learn.microsoft.com/azure/architecture/networking/architecture/hub-spoke",
    frameworks=F["AZ-NET-012"],
    evidence="spoke VNet subnets' routeTable (resolved by id) and its routes: 0.0.0.0/0 -> VirtualAppliance",
    remediation=(
        "Associate a route table whose 0.0.0.0/0 route points at the hub firewall or NVA with every spoke workload "
        "subnet."
    ),
    description=(
        "A spoke (a VNet whose peering uses remote gateways or allows forwarded traffic) sends internet-bound "
        "traffic through the hub only when a default route to a virtual appliance exists."
    ),
)
def fw_bypass(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    tables = {rt.id.lower(): rt for s in topo.subscriptions for rt in s.route_tables}
    for vnet in sub.vnets:
        if not _is_spoke(vnet):
            continue
        for subnet in vnet.subnets:
            if subnet.name.lower() in INFRA_SUBNETS:
                continue
            rt = tables.get((subnet.route_table_id or "").lower())
            if subnet.route_table_id and rt is None:
                continue  # referenced table is outside the export: recorded as an ingestion warning, not a finding
            if rt is None:
                yield Emit(
                    resource_id=subnet.id,
                    resource_type=T_SUBNET,
                    region=vnet.location,
                    fact=(
                        f"Subnet {subnet.name} in spoke VNet {vnet.name} has no route table; internet-bound traffic "
                        f"leaves through the system default route."
                    ),
                    evidence_ref=_ref(sub, f"vnets[id={vnet.id}].subnets[id={subnet.id}].route_table_id"),
                )
                continue
            forced = any(r.address_prefix == "0.0.0.0/0" and r.next_hop_type == "VirtualAppliance" for r in rt.routes)
            if not forced:
                yield Emit(
                    resource_id=subnet.id,
                    resource_type=T_SUBNET,
                    region=vnet.location,
                    fact=(
                        f"Subnet {subnet.name} in spoke VNet {vnet.name} has route table {rt.name} with no 0.0.0.0/0 "
                        f"route to a VirtualAppliance."
                    ),
                    evidence_ref=_ref(sub, f"route_tables[id={rt.id}].routes"),
                )


@rule(
    id="AZ-NET-014",
    title="Flow log is enabled but Traffic Analytics is disabled",
    severity=S.MEDIUM,
    category="Observability",
    version=2,
    learn_url="https://learn.microsoft.com/azure/network-watcher/traffic-analytics",
    frameworks=F["AZ-NET-014"],
    evidence=(
        "networkwatchers/flowlogs "
        "properties.flowAnalyticsConfiguration.networkWatcherFlowAnalyticsConfiguration.enabled; unknown when the "
        "export has no flowlogs rows"
    ),
    remediation="Enable Traffic Analytics on the flow log with a Log Analytics workspace destination.",
    description="Flow records are collected but not aggregated into traffic insights.",
)
def traffic_analytics(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    if not _any_flow_logs(topo):
        yield NotEvaluable("the export has no networkwatchers/flowlogs rows; Traffic Analytics state is unknown")
        return
    for fl in sub.flow_logs:
        if fl.enabled and not fl.traffic_analytics_enabled:
            yield Emit(
                resource_id=fl.id,
                resource_type=T_FLOWLOG,
                fact=(
                    f"Flow log {fl.name} targeting {fl.target_resource_id} is enabled with Traffic Analytics disabled."
                ),
                evidence_ref=_ref(sub, f"flow_logs[id={fl.id}].traffic_analytics_enabled"),
            )


@rule(
    id="AZ-NET-018",
    title="Front Door WAF policy is in Detection mode, not Prevention",
    severity=S.MEDIUM,
    category="Application Security",
    version=1,
    learn_url="https://learn.microsoft.com/azure/web-application-firewall/afds/waf-front-door-policy-settings",
    frameworks=F["AZ-NET-018"],
    evidence="frontdoorwebapplicationfirewallpolicies properties.policySettings.mode",
    remediation="Switch the policy to Prevention after reviewing the Detection logs for false positives.",
    description="Malicious requests are logged but not blocked.",
)
def front_door_waf(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for policy in sub.front_door_waf_policies:
        if str(policy.policy_mode).lower() == "detection":
            yield Emit(
                resource_id=policy.id,
                resource_type=T_FDWAF,
                region=policy.location,
                fact=(
                    f"Front Door WAF policy {policy.name} is in Detection mode. Custom rules: "
                    f"{policy.custom_rules_count}, managed rule sets: {policy.managed_rules_count}."
                ),
                evidence_ref=_ref(sub, f"front_door_waf_policies[id={policy.id}].policy_mode"),
            )


# ── Engine B, ported as typed rules ────────────────────────────────────────


def _sources(r: NSGSecurityRule) -> set[str]:
    values = set(r.source_address_prefixes)
    if r.source_address_prefix:
        values.add(r.source_address_prefix)
    return {v.lower() for v in values}


def _ports(r: NSGSecurityRule) -> set[int] | None:
    """Destination ports of the rule; None means every port."""
    ranges = list(r.destination_port_ranges)
    if r.destination_port_range:
        ranges.append(r.destination_port_range)
    ports: set[int] = set()
    for value in ranges:
        value = value.strip()
        if value in ("*", "Any", "any"):
            return None
        if "-" in value:
            lo, _, hi = value.partition("-")
            if lo.isdigit() and hi.isdigit():
                ports.update(range(int(lo), min(int(hi), 65535) + 1))
        elif value.isdigit():
            ports.add(int(value))
    return ports


@rule(
    id="AZ-NET-020",
    title="NSG allows RDP or SSH inbound from the Internet",
    severity=S.CRITICAL,
    category="Remote Access",
    version=1,
    learn_url="https://learn.microsoft.com/azure/bastion/bastion-overview",
    frameworks=F["AZ-NET-020"],
    evidence=(
        "networksecuritygroups securityRules: Allow, Inbound, source in {*, Internet, 0.0.0.0/0, Any}, destination "
        "ports including 22 or 3389"
    ),
    remediation=(
        "Remove the Internet source from the rule; reach the hosts through Azure Bastion or from named corporate "
        "ranges, with just-in-time access."
    ),
    description="Management ports open to the Internet are the first target of brute-force campaigns.",
)
def nsg_rdp_ssh(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for nsg in sub.nsgs:
        for r in nsg.security_rules:
            if r.access.lower() != "allow" or r.direction.lower() != "inbound":
                continue
            if not (_sources(r) & INTERNET_SOURCES):
                continue
            ports = _ports(r)
            exposed = sorted({PORT_SSH, PORT_RDP} if ports is None else ports & {PORT_SSH, PORT_RDP})
            if not exposed:
                continue
            yield Emit(
                resource_id=f"{nsg.id}/securityRules/{r.name}",
                resource_type=T_NSG,
                region=nsg.location,
                fact=(
                    f"NSG {nsg.name} rule {r.name} (priority {r.priority}) allows inbound traffic on port(s) "
                    f"{', '.join(map(str, exposed))} from the Internet."
                ),
                evidence_ref=_ref(sub, f"nsgs[id={nsg.id}].security_rules[name={r.name}]"),
                affected_resources=(nsg.id,),
            )


@rule(
    id="AZ-NET-021",
    title="NSG has a wildcard allow-all rule",
    severity=S.HIGH,
    category="Network Segmentation",
    version=1,
    learn_url="https://learn.microsoft.com/azure/virtual-network/network-security-group-how-it-works",
    frameworks=F["AZ-NET-021"],
    evidence="networksecuritygroups securityRules: Allow, source in {*, Internet, Any}, destination port *, protocol *",
    remediation=(
        "Replace the wildcard rule with rules that name the required source ranges, ports and protocols; deny by "
        "default."
    ),
    description=(
        "A rule that allows every source, port and protocol disables network-layer access control for the direction "
        "it covers."
    ),
)
def nsg_wildcard(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for nsg in sub.nsgs:
        for r in nsg.security_rules:
            if r.access.lower() != "allow":
                continue
            if not (_sources(r) & {"*", "internet", "any"}):
                continue
            if _ports(r) is not None or r.protocol not in ("*", "Any"):
                continue
            dst = r.destination_address_prefix or ", ".join(r.destination_address_prefixes) or "*"
            yield Emit(
                resource_id=f"{nsg.id}/securityRules/{r.name}",
                resource_type=T_NSG,
                region=nsg.location,
                fact=(
                    f"NSG {nsg.name} rule {r.name} (priority {r.priority}) allows all {r.direction} traffic from "
                    f"'{r.source_address_prefix or '*'}' to '{dst}' on all ports and protocols."
                ),
                evidence_ref=_ref(sub, f"nsgs[id={nsg.id}].security_rules[name={r.name}]"),
                affected_resources=(nsg.id,),
            )


@rule(
    id="AZ-NET-022",
    title="Route table sends default traffic directly to the Internet",
    severity=S.MEDIUM,
    category="Routing & Transit",
    version=1,
    learn_url="https://learn.microsoft.com/azure/virtual-network/virtual-networks-udr-overview",
    frameworks=F["AZ-NET-022"],
    evidence="routetables routes: addressPrefix 0.0.0.0/0 with nextHopType Internet",
    remediation=(
        "Point the default route at the firewall or NVA private IP for centralised egress inspection; keep a direct "
        "Internet next hop only on dedicated egress subnets with a recorded reason."
    ),
    description=(
        "Subnets associated with this table send outbound traffic straight to the Internet, outside any central "
        "inspection."
    ),
)
def rt_default_internet(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for rt in sub.route_tables:
        for route in rt.routes:
            if route.address_prefix == "0.0.0.0/0" and route.next_hop_type == "Internet":
                yield Emit(
                    resource_id=rt.id,
                    resource_type=T_RT,
                    region=rt.location,
                    fact=(
                        f"Route table {rt.name} route {route.name} has addressPrefix 0.0.0.0/0 with nextHopType "
                        f"Internet; it is associated with {len(rt.associated_subnet_ids)} subnet(s)."
                    ),
                    evidence_ref=_ref(sub, f"route_tables[id={rt.id}].routes[name={route.name}]"),
                )


@rule(
    id="AZ-NET-023",
    title="Route table has BGP route propagation disabled",
    severity=S.INFORMATIONAL,
    category="Routing & Transit",
    version=1,
    learn_url="https://learn.microsoft.com/azure/virtual-network/virtual-networks-udr-overview",
    frameworks=F["AZ-NET-023"],
    evidence="routetables properties.disableBgpRoutePropagation",
    remediation=(
        "Confirm the setting is intended; subnets that need on-premises reachability either enable propagation or "
        "carry explicit static routes for the on-premises prefixes."
    ),
    description="Routes learned over VPN or ExpressRoute are not added to the subnets associated with this table.",
)
def rt_bgp_propagation(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for rt in sub.route_tables:
        if rt.disable_bgp_route_propagation:
            yield Emit(
                resource_id=rt.id,
                resource_type=T_RT,
                region=rt.location,
                fact=f"Route table {rt.name} has disableBgpRoutePropagation=true.",
                evidence_ref=_ref(sub, f"route_tables[id={rt.id}].disable_bgp_route_propagation"),
            )


@rule(
    id="AZ-NET-024",
    title="VNet uses custom DNS servers",
    severity=S.INFORMATIONAL,
    category="DNS & Name Resolution",
    version=1,
    learn_url=(
        "https://learn.microsoft.com/azure/virtual-network/virtual-networks-name-resolution-for-vms-and-role-instances"
    ),
    frameworks=F["AZ-NET-024"],
    evidence="virtualnetworks properties.dhcpOptions.dnsServers other than 168.63.129.16",
    remediation=(
        "Confirm the custom servers forward Azure Private DNS zones to 168.63.129.16 and are deployed redundantly; "
        "Azure DNS Private Resolver is the managed alternative."
    ),
    description=(
        "Name resolution for every workload in the VNet depends on the listed servers, including private endpoint "
        "resolution."
    ),
)
def vnet_custom_dns(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for vnet in sub.vnets:
        custom = [d for d in vnet.dns_servers if d != AZURE_DNS]
        if custom:
            yield Emit(
                resource_id=vnet.id,
                resource_type=T_VNET,
                region=vnet.location,
                fact=f"VNet {vnet.name} ({vnet.location}) lists custom DNS servers: {', '.join(custom)}.",
                evidence_ref=_ref(sub, f"vnets[id={vnet.id}].dns_servers"),
            )


@rule(
    id="AZ-NET-025",
    title="Application Gateway WAF is in Detection mode, not Prevention",
    severity=S.MEDIUM,
    category="Application Security",
    version=1,
    learn_url="https://learn.microsoft.com/azure/web-application-firewall/ag/ag-overview",
    frameworks=F["AZ-NET-025"],
    evidence=(
        "applicationgateways webApplicationFirewallConfiguration.firewallMode or the linked WAF policy "
        "policySettings.mode"
    ),
    remediation="Switch the WAF to Prevention after tuning the Detection logs; apply the current OWASP core rule set.",
    description="Attacks are logged but not blocked.",
)
def agw_waf_detection(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for agw in sub.application_gateways:
        if not _agw_waf_enabled(agw):
            continue
        mode = _agw_waf_mode(agw)
        if mode and mode.lower() != "prevention":
            yield Emit(
                resource_id=agw.id,
                resource_type=T_AGW,
                region=agw.location,
                fact=f"Application Gateway {agw.name} has WAF enabled in {mode} mode.",
                evidence_ref=_ref(sub, f"application_gateways[id={agw.id}].waf_mode"),
            )


@rule(
    id="AZ-NET-026",
    title="Load balancer uses the Basic SKU",
    severity=S.MEDIUM,
    category="Resilience",
    version=1,
    learn_url="https://learn.microsoft.com/azure/load-balancer/load-balancer-basic-upgrade-guidance",
    frameworks=F["AZ-NET-026"],
    evidence="loadbalancers sku.name == Basic",
    remediation=(
        "Upgrade to the Standard SKU: zone redundancy, an SLA, secure-by-default inbound and HA ports. Basic load "
        "balancers were retired on 2025-09-30 [VERIFY]."
    ),
    description="The Basic SKU has no SLA and no zone redundancy.",
)
def lb_basic(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for lb in sub.load_balancers:
        if lb.sku_name.lower() == "basic":
            yield Emit(
                resource_id=lb.id,
                resource_type=T_LB,
                region=lb.location,
                fact=f"Load balancer {lb.name} ({lb.lb_type}) has sku.name=Basic.",
                evidence_ref=_ref(sub, f"load_balancers[id={lb.id}].sku_name"),
            )


@rule(
    id="AZ-NET-027",
    title="Public IP uses the Basic SKU",
    severity=S.MEDIUM,
    category="Resilience",
    version=1,
    learn_url="https://learn.microsoft.com/azure/virtual-network/ip-services/public-ip-basic-upgrade-guidance",
    frameworks=F["AZ-NET-027"],
    evidence="publicipaddresses sku.name == Basic (one finding per IP)",
    remediation=(
        "Upgrade the address to the Standard SKU; Standard IPs are closed by default and zone-redundant. Basic "
        "public IPs were retired on 2025-09-30 [VERIFY]."
    ),
    description="Basic public IPs are open by default and not zone-redundant.",
)
def pip_basic(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for pip in sub.public_ips:
        if pip.sku_name.lower() == "basic":
            attached = pip.associated_resource_type or "nothing"
            yield Emit(
                resource_id=pip.id,
                resource_type=T_PIP,
                region=pip.location,
                fact=f"Public IP {pip.name} has sku.name=Basic and is attached to {attached}.",
                evidence_ref=_ref(sub, f"public_ips[id={pip.id}].sku_name"),
            )


@rule(
    id="AZ-NET-028",
    title="VPN gateway uses the Basic SKU",
    severity=S.HIGH,
    category="Gateway",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/about-gateway-skus",
    frameworks=F["AZ-NET-028"],
    evidence="virtualnetworkgateways gatewayType Vpn with sku.name Basic",
    remediation="Resize to VpnGw2 or higher (an AZ SKU for zone redundancy) and enable BGP with active-active mode.",
    description=(
        "The Basic SKU caps throughput at 100 Mbps, has no BGP, no active-active mode, no zone redundancy and no SLA."
    ),
)
def vpngw_basic(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for gw in sub.virtual_network_gateways:
        if gw.gateway_type == "Vpn" and (gw.sku_name or gw.sku_tier).lower() == "basic":
            yield Emit(
                resource_id=gw.id,
                resource_type=T_VNG,
                region=gw.location,
                fact=f"VPN gateway {gw.name} has sku.name=Basic.",
                evidence_ref=_ref(sub, f"virtual_network_gateways[id={gw.id}].sku_name"),
            )


@rule(
    id="AZ-NET-029",
    title="VPN gateway is Generation 1",
    severity=S.LOW,
    category="Gateway",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/about-gateway-skus",
    frameworks=F["AZ-NET-029"],
    evidence="virtualnetworkgateways properties.vpnGatewayGeneration == Generation1",
    remediation="Resize to a Generation 2 SKU (VpnGw2 to VpnGw5, or their AZ variants).",
    description="Generation 1 gateways top out at 1.25 Gbps aggregate throughput.",
)
def vpngw_gen1(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for gw in sub.virtual_network_gateways:
        if gw.gateway_type == "Vpn" and gw.generation and "generation1" in gw.generation.lower():
            yield Emit(
                resource_id=gw.id,
                resource_type=T_VNG,
                region=gw.location,
                fact=f"VPN gateway {gw.name} (SKU {gw.sku_name}) has vpnGatewayGeneration={gw.generation}.",
                evidence_ref=_ref(sub, f"virtual_network_gateways[id={gw.id}].generation"),
            )


@rule(
    id="AZ-NET-030",
    title="Gateway connection is not connected",
    severity=S.HIGH,
    category="Connectivity",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/vpn-gateway-troubleshoot-site-to-site-cannot-connect",
    frameworks=F["AZ-NET-030"],
    evidence=(
        "connections properties.connectionStatus not in {Connected, Unknown}; unknown when the export has no "
        "connections rows"
    ),
    remediation=(
        "Check the on-premises device logs, the pre-shared key and the IKE parameters, and that UDP 500/4500 is "
        "allowed."
    ),
    description="A tunnel that is not connected breaks hybrid connectivity for the routes it carries.",
)
def gateway_connections(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    gateways = [gw for gw in sub.virtual_network_gateways if gw.gateway_type in ("Vpn", "ExpressRoute")]
    if not gateways:
        return
    if topo.resource_counts.get("microsoft.network/connections", 0) == 0:
        yield NotEvaluable("the export has no connections rows; tunnel status is unknown for every gateway")
        return
    for gw in gateways:
        for conn in gw.connections:
            if conn.connection_status in ("Connected", "Unknown"):
                continue
            yield Emit(
                resource_id=conn.id,
                resource_type=T_CONN,
                region=gw.location,
                fact=(
                    f"Connection {conn.name} ({conn.connection_type}) on gateway {gw.name} has connectionStatus "
                    f"'{conn.connection_status}'."
                ),
                evidence_ref=_ref(
                    sub, f"virtual_network_gateways[id={gw.id}].connections[id={conn.id}].connection_status"
                ),
                affected_resources=(gw.id,),
            )


@rule(
    id="AZ-NET-031",
    title="Private endpoint connection is pending approval",
    severity=S.MEDIUM,
    category="Connectivity",
    version=1,
    learn_url="https://learn.microsoft.com/azure/private-link/manage-private-endpoint",
    frameworks=F["AZ-NET-031"],
    evidence=(
        "privateendpoints privateLinkServiceConnections[].properties.privateLinkServiceConnectionState.status == "
        "Pending"
    ),
    remediation=(
        "Approve the connection on the target resource's private endpoint connections blade after confirming the "
        "requesting subscription."
    ),
    description="Traffic to the private service does not flow until the connection is approved.",
)
def pe_pending(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for pe in sub.private_endpoints:
        for sc in pe.service_connections:
            if sc.connection_state.lower() != "pending":
                continue
            target = sc.private_link_service_id.rsplit("/", 1)[-1]
            yield Emit(
                resource_id=pe.id,
                resource_type=T_PE,
                region=pe.location,
                fact=f"Private endpoint {pe.name} connection {sc.connection_name} to {target} has status Pending.",
                evidence_ref=_ref(
                    sub,
                    f"private_endpoints[id={pe.id}].service_connections[name={sc.connection_name}].connection_state",
                ),
            )


def _nva_default_route(sub: AzureSubscriptionTopology) -> bool:
    return any(
        r.address_prefix == "0.0.0.0/0" and r.next_hop_type == "VirtualAppliance"
        for rt in sub.route_tables
        for r in rt.routes
    )


def _secured_vhub(topo: AzureTopology) -> bool:
    return any(hub.azure_firewall_id for s in topo.subscriptions for w in s.virtual_wans for hub in w.hubs)


@rule(
    id="AZ-NET-032",
    title="No Azure Firewall in a subscription with VNets",
    severity=S.MEDIUM,
    category="Network Security",
    version=1,
    learn_url="https://learn.microsoft.com/azure/firewall/overview",
    frameworks=F["AZ-NET-032"],
    evidence=(
        "zero azurefirewalls rows and at least one VNet in the subscription; suppressed by a vWAN secured hub or a "
        "0.0.0.0/0 -> VirtualAppliance route"
    ),
    remediation="Deploy Azure Firewall (or a partner NVA) in the hub and route spoke subnets through it.",
    description=(
        "Neither a firewall nor an appliance-shaped default route is in this subscription; traffic leaves without "
        "central inspection."
    ),
)
def no_firewall(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    if not sub.vnets or sub.firewalls or _nva_default_route(sub) or _secured_vhub(topo):
        return
    yield Emit(
        resource_id=f"/subscriptions/{sub.subscription_id}",
        resource_type="Microsoft.Resources/subscriptions",
        fact=(
            f"Subscription {sub.subscription_id} has {len(sub.vnets)} VNet(s), no Azure Firewall, no secured virtual "
            f"hub and no 0.0.0.0/0 route to a VirtualAppliance."
        ),
        evidence_ref=_ref(sub, "firewalls"),
        affected_resources=tuple(v.id for v in sub.vnets),
    )


@rule(
    id="AZ-NET-033",
    title="No Azure Bastion in a subscription with VNets",
    severity=S.LOW,
    category="Remote Access",
    version=1,
    learn_url="https://learn.microsoft.com/azure/bastion/bastion-overview",
    frameworks=F["AZ-NET-033"],
    evidence="zero bastionhosts rows and at least one VNet in the subscription",
    remediation=(
        "Deploy Azure Bastion (Standard SKU) for browser-based RDP and SSH without public IPs on the hosts, or "
        "record the alternative access path."
    ),
    description=(
        "The subscription has no Bastion host; RDP and SSH access to its VMs goes through another path (public IPs, "
        "VPN or a jump host)."
    ),
    needs_properties=False,
)
def no_bastion(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    if not sub.vnets or sub.bastion_hosts:
        return
    yield Emit(
        resource_id=f"/subscriptions/{sub.subscription_id}",
        resource_type="Microsoft.Resources/subscriptions",
        fact=f"Subscription {sub.subscription_id} has {len(sub.vnets)} VNet(s) and no Azure Bastion host.",
        evidence_ref=_ref(sub, "bastion_hosts"),
        affected_resources=tuple(v.id for v in sub.vnets),
    )


# ── Engine A rules that need live reads: registered, surfaced as unknowns ──

live_only(
    id="AZ-NET-008",
    title="Gateway bandwidth utilisation is above 80 percent",
    severity=S.HIGH,
    category="Performance",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/monitor-vpn-gateway",
    frameworks=F["AZ-NET-008"],
    evidence="Azure Monitor AverageBandwidth metric over 24 hours against the SKU ceiling",
    remediation="Resize to a higher-throughput SKU or enable ExpressRoute FastPath.",
    description="A gateway running near its provisioned bandwidth drops packets under peak load.",
)
live_only(
    id="AZ-NET-009",
    title="Azure Firewall recorded zero rule hits in 24 hours",
    severity=S.HIGH,
    category="Network Security",
    version=1,
    learn_url="https://learn.microsoft.com/azure/firewall/metrics",
    frameworks=F["AZ-NET-009"],
    evidence="Azure Monitor NetworkRuleHit, ApplicationRuleHit and NATRuleHit metrics",
    remediation="Confirm routing sends traffic through the firewall; decommission it if it is unused.",
    description="A firewall that sees no traffic is either bypassed or unneeded.",
)
live_only(
    id="AZ-NET-010",
    title="Load balancer SNAT port utilisation is above 80 percent",
    severity=S.HIGH,
    category="Performance",
    version=1,
    learn_url="https://learn.microsoft.com/azure/load-balancer/load-balancer-outbound-connections",
    frameworks=F["AZ-NET-010"],
    evidence="Azure Monitor UsedSnatPorts against AllocatedSnatPorts",
    remediation="Add outbound IPs or a NAT gateway for outbound connectivity.",
    description="SNAT exhaustion fails new outbound connections.",
)
live_only(
    id="AZ-NET-013",
    title="Azure Firewall has no Log Analytics diagnostic setting",
    severity=S.MEDIUM,
    category="Observability",
    version=1,
    learn_url="https://learn.microsoft.com/azure/firewall/firewall-diagnostics",
    frameworks=F["AZ-NET-013"],
    evidence="Microsoft.Insights/diagnosticSettings on each firewall",
    remediation="Send the firewall rule and threat intelligence logs to a Log Analytics workspace.",
    description="Without a diagnostic sink the firewall's rule and threat logs are lost.",
)
live_only(
    id="AZ-NET-015",
    title="Azure Bastion has no session audit logging",
    severity=S.MEDIUM,
    category="Observability",
    version=1,
    learn_url="https://learn.microsoft.com/azure/bastion/diagnostic-logs",
    frameworks=F["AZ-NET-015"],
    evidence="Microsoft.Insights/diagnosticSettings on each Bastion host",
    remediation="Send BastionAuditLogs to a Log Analytics workspace.",
    description="Without a diagnostic sink the RDP and SSH session audit trail is unavailable.",
)
live_only(
    id="AZ-NET-016",
    title="ExpressRoute circuit utilisation is above 80 percent",
    severity=S.HIGH,
    category="Performance",
    version=1,
    learn_url="https://learn.microsoft.com/azure/expressroute/monitor-expressroute",
    frameworks=F["AZ-NET-016"],
    evidence="Azure Monitor BitsInPerSecond and BitsOutPerSecond against the circuit bandwidth",
    remediation="Upgrade the circuit bandwidth or add a second circuit.",
    description="A saturated circuit drops hybrid traffic under peak load.",
)
live_only(
    id="AZ-NET-017",
    title="DDoS attack detected on a public IP",
    severity=S.CRITICAL,
    category="Network Protection",
    version=1,
    learn_url="https://learn.microsoft.com/azure/ddos-protection/telemetry",
    frameworks=F["AZ-NET-017"],
    evidence="Azure Monitor IfUnderDDoSAttack metric over 24 hours",
    remediation="Engage the DDoS rapid response process and review the mitigation reports.",
    description="An attack in progress against a public IP in the subscription.",
)
live_only(
    id="AZ-NET-019",
    title="Application Gateway backend latency or failure rate is high",
    severity=S.HIGH,
    category="Performance",
    version=1,
    learn_url="https://learn.microsoft.com/azure/application-gateway/application-gateway-metrics",
    frameworks=F["AZ-NET-019"],
    evidence="Azure Monitor BackendLastByteResponseTime and FailedRequests over 24 hours",
    remediation="Investigate backend health probes, capacity units and the application's own latency.",
    description="Slow or failing backends behind the gateway.",
)

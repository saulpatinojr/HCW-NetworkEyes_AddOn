# Ported from saulpatinojr/Work-Cloud_Network_Core cna/modules/network/analysis/finops_signals.py at 5d3b914; changes:
# (source functions: AZ-COST-001 `_check_orphaned_pips` and AZ-COST-004 `_check_idle_nat_gateways`) the price table
# (azure_network_prices.py)
# and `est_monthly_cost_usd` are gone (the lab makes no price claims); the `_finding` builder is replaced by the
# registry's `Emit`; AZ-COST-002/003/005 (24-hour metrics) are registered live-only; hedge language removed.
"""AZ-COST-* FinOps rules over the lab topology model."""

from __future__ import annotations

from collections.abc import Iterator

from network_assessment.model.findings import FindingSeverity as S
from network_assessment.model.topology import AzureSubscriptionTopology, AzureTopology
from network_assessment.rules.frameworks import FRAMEWORKS as F
from network_assessment.rules.registry import Emit, NotEvaluable, live_only, rule

T_PIP = "Microsoft.Network/publicIPAddresses"
T_NAT = "Microsoft.Network/natGateways"
Rows = Iterator[Emit | NotEvaluable]


def _ref(sub: AzureSubscriptionTopology, path: str) -> str:
    return f"export:{sub.subscription_id}.{path}"


@rule(
    id="AZ-COST-001",
    title="Orphaned public IP incurs charges with no workload",
    severity=S.LOW,
    category="FinOps",
    version=1,
    learn_url="https://learn.microsoft.com/azure/virtual-network/ip-services/public-ip-addresses",
    frameworks=F["AZ-COST-001"],
    evidence="publicipaddresses with no properties.ipConfiguration",
    remediation=(
        "Delete the unassociated public IP if it is no longer needed, or record the reservation intent in a tag; an "
        "Azure Policy alert catches new orphans."
    ),
    description="A public IP is billed while unattached.",
)
def orphaned_pips(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for pip in sub.public_ips:
        if pip.associated_resource_id:
            continue
        yield Emit(
            resource_id=pip.id,
            resource_type=T_PIP,
            region=pip.location,
            fact=(
                f"Public IP {pip.name} ({pip.sku_name} SKU) in {pip.location} has no ipConfiguration; it is not "
                f"attached to any resource."
            ),
            evidence_ref=_ref(sub, f"public_ips[id={pip.id}].associated_resource_id"),
        )


@rule(
    id="AZ-COST-004",
    title="NAT gateway has no associated subnets",
    severity=S.LOW,
    category="FinOps",
    version=1,
    learn_url="https://learn.microsoft.com/azure/nat-gateway/nat-overview",
    frameworks=F["AZ-COST-004"],
    evidence="natgateways with an empty properties.subnets list",
    remediation=(
        "Associate the NAT gateway with the subnets that need predictable outbound SNAT, or delete it and its public "
        "IPs."
    ),
    description="An unattached NAT gateway is billed hourly while providing no egress path.",
)
def idle_nat_gateways(sub: AzureSubscriptionTopology, topo: AzureTopology) -> Rows:
    for nat in sub.nat_gateways:
        if nat.associated_subnet_ids:
            continue
        yield Emit(
            resource_id=nat.id,
            resource_type=T_NAT,
            region=nat.location,
            fact=(
                f"NAT gateway {nat.name} in {nat.location} has an empty subnets list; no subnet routes outbound "
                f"traffic through it."
            ),
            evidence_ref=_ref(sub, f"nat_gateways[id={nat.id}].associated_subnet_ids"),
        )


live_only(
    id="AZ-COST-002",
    title="Gateway is billed but moved zero traffic in 24 hours",
    severity=S.MEDIUM,
    category="FinOps",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/monitor-vpn-gateway",
    frameworks=F["AZ-COST-002"],
    evidence="Azure Monitor TunnelIngressBytes and TunnelEgressBytes over 24 hours",
    remediation="Confirm the gateway is still required; decommission unused gateways and their public IPs.",
    description="An idle gateway accrues hourly charges.",
)
live_only(
    id="AZ-COST-003",
    title="VPN gateway SKU is oversized for the observed traffic",
    severity=S.LOW,
    category="FinOps",
    version=1,
    learn_url="https://learn.microsoft.com/azure/vpn-gateway/about-gateway-skus",
    frameworks=F["AZ-COST-003"],
    evidence="Azure Monitor AverageBandwidth over 24 hours against the SKU ceiling (below 10 percent)",
    remediation="Resize to the next smaller SKU after reviewing a 30-day window and planned growth.",
    description="A gateway peaking far below its ceiling is paid for capacity it does not use.",
)
live_only(
    id="AZ-COST-005",
    title="Azure Firewall is billed while processing zero traffic",
    severity=S.MEDIUM,
    category="FinOps",
    version=1,
    learn_url="https://learn.microsoft.com/azure/firewall/metrics",
    frameworks=F["AZ-COST-005"],
    evidence="Azure Monitor rule-hit metrics over 24 hours (cost angle of AZ-NET-009)",
    remediation=(
        "Confirm routing sends traffic through the firewall; decommission it if it is unused, or use Firewall Basic "
        "for intermittent workloads."
    ),
    description="A deployed firewall accrues hourly charges regardless of traffic.",
)

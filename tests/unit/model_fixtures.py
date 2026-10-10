"""Builders for the lab model, shared by the ported rule tests (the Core's fixtures built SDK-shaped models)."""

from __future__ import annotations

from network_assessment.model.topology import (
    ApplicationGateway,
    AzureFirewall,
    AzureSubnet,
    AzureSubscriptionTopology,
    AzureTopology,
    AzureVirtualNetworkGateway,
    ExpressRouteCircuit,
    VNet,
    VNetPeering,
)

SUB = "00000000-0000-0000-0000-000000000001"


def vnet_id(name: str, sub: str = SUB) -> str:
    return f"/subscriptions/{sub}/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/{name}"


def vnet(name: str, *, peerings=None, subnets=None, ddos=False, sub: str = SUB, **extra) -> VNet:
    return VNet(
        id=vnet_id(name, sub),
        name=name,
        location="eastus2",
        resource_group="rg",
        subscription_id=sub,
        address_space=["10.0.0.0/16"],
        peerings=peerings or [],
        subnets=subnets or [],
        ddos_protection_enabled=ddos,
        **extra,
    )


def subnet(vnet_name: str, name: str, prefix: str = "10.0.1.0/24", **extra) -> AzureSubnet:
    return AzureSubnet(id=f"{vnet_id(vnet_name)}/subnets/{name}", name=name, address_prefix=prefix, **extra)


def peering(name: str, remote_id: str, **flags) -> VNetPeering:
    return VNetPeering(
        id=f"peering-{name}",
        name=name,
        remote_vnet_id=remote_id,
        remote_subscription_id=SUB,
        peering_state="Connected",
        allow_forwarded_traffic=flags.get("allow_forwarded_traffic", False),
        allow_gateway_transit=flags.get("allow_gateway_transit", False),
        use_remote_gateways=flags.get("use_remote_gateways", False),
    )


def firewall(name: str, zones: list[str] | None = None, **extra) -> AzureFirewall:
    extra.setdefault("sku_tier", "Standard")
    return AzureFirewall(
        id=f"fw-{name}", name=name, location="eastus2", resource_group="rg", zones=zones or [], **extra
    )


def gateway(name: str, gateway_type: str = "Vpn", **extra) -> AzureVirtualNetworkGateway:
    return AzureVirtualNetworkGateway(
        id=f"gw-{name}", name=name, location="eastus2", resource_group="rg", gateway_type=gateway_type, **extra
    )


def circuit(name: str = "circuit-1") -> ExpressRouteCircuit:
    return ExpressRouteCircuit(id=f"er-{name}", name=name, location="eastus2", resource_group="rg")


def app_gateway(name: str, sku: str = "Standard_v2", **extra) -> ApplicationGateway:
    return ApplicationGateway(
        id=f"agw-{name}",
        name=name,
        location="eastus2",
        resource_group="rg",
        sku_name=sku,
        subnet_id=f"{vnet_id('hub')}/subnets/snet-agw",
        **extra,
    )


def subscription(sub: str = SUB, **collections) -> AzureSubscriptionTopology:
    return AzureSubscriptionTopology(subscription_id=sub, **collections)


def topology(*subs: AzureSubscriptionTopology, **extra) -> AzureTopology:
    return AzureTopology(subscriptions=list(subs), **extra)


def rule_ids(findings) -> set[str]:
    return {f.rule_id for f in findings}

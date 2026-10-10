# Ported from saulpatinojr/HCW-NetworkEyes_App cna/core/topology_schema.py at 5d3b914; changes: (source lines
# 315-1006, the Azure classes) AWS, metrics, observability, BGP, Defender, NVA, NIC, workload and management-group
# classes dropped;
# fields an export cannot populate removed (subnet_type, dns_resolves_to_private_ip, egress/ingress bytes, dpd timeout,
# idle timeouts, provisioning states, bgp connections, vpn client pools, soa records); `ip_configuration_count` added to
# AzureSubnet (AZ-NET-011); AzureFirewallPolicy, AppGatewayWafPolicy and FlowLog added; VNet.route_tables dropped (route
# tables live on the subscription and subnets reference them by id); AzureSubscriptionTopology lost tenant_id,
# discovery_blocked and the live-only collections and gained firewall_policies, waf_policies, flow_logs; AzureTopology
# carries TOPOLOGY_MODEL_VERSION = "lab-1.0.0" (declared equivalent to the Core's 1.3.0 Azure subset), resource counts,
# unmapped types and ingestion warnings instead of engagement and tenant ids.
"""Topology data contract of the lab edition: what a Resource Graph export of microsoft.network/* can populate."""

from __future__ import annotations

from pydantic import BaseModel, Field

TOPOLOGY_MODEL_VERSION = "lab-1.0.0"


# ── Azure primitives ───────────────────────────────────────────────────────


class AzureSubnet(BaseModel):
    id: str
    name: str
    address_prefix: str
    nsg_id: str | None = None
    nsg_name: str | None = None
    route_table_id: str | None = None
    route_table_name: str | None = None
    nat_gateway_id: str | None = None
    service_endpoints: list[str] = Field(default_factory=list)
    private_endpoint_network_policies: str = "Enabled"
    default_outbound_access: bool = True
    delegation: str | None = None
    address_prefixes: list[str] = Field(default_factory=list)  # dual-stack
    ip_configuration_count: int = 0  # len(properties.ipConfigurations) in the export


class AzureRouteEntry(BaseModel):
    name: str
    address_prefix: str
    next_hop_type: str  # VirtualNetworkGateway | VnetLocal | Internet | VirtualAppliance | None
    next_hop_ip: str | None = None
    has_bgp_override: bool = False


class AzureRouteTable(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    routes: list[AzureRouteEntry] = Field(default_factory=list)
    associated_subnet_ids: list[str] = Field(default_factory=list)
    disable_bgp_route_propagation: bool = False
    tags: dict = Field(default_factory=dict)


class VNetPeering(BaseModel):
    id: str
    name: str
    remote_vnet_id: str
    remote_vnet_name: str | None = None
    remote_subscription_id: str
    peering_state: str
    allow_forwarded_traffic: bool
    allow_gateway_transit: bool
    use_remote_gateways: bool
    do_not_verify_remote_gateways: bool = False
    peer_complete_vnets: bool = True


class AzureFirewallPolicy(BaseModel):
    """Lab addition: microsoft.network/firewallpolicies, resolved onto its firewall by id."""

    id: str
    name: str
    resource_group: str
    sku_tier: str | None = None
    threat_intel_mode: str | None = None
    dns_proxy_enabled: bool = False
    intrusion_detection_mode: str | None = None


class AzureFirewall(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    sku_tier: str  # "Basic" | "Standard" | "Premium"
    subnet_id: str | None = None  # AzureFirewallSubnet
    public_ip_ids: list[str] = Field(default_factory=list)
    policy_id: str | None = None
    firewall_policy: AzureFirewallPolicy | None = None
    threat_intel_mode: str = "Alert"
    zones: list[str] = Field(default_factory=list)
    tags: dict = Field(default_factory=dict)

    @property
    def effective_threat_intel_mode(self) -> str:
        """The firewall's own mode, or the linked policy's when the firewall row carries none."""
        if self.firewall_policy and self.firewall_policy.threat_intel_mode:
            return self.firewall_policy.threat_intel_mode
        return self.threat_intel_mode


class AppGatewayWafPolicy(BaseModel):
    """Lab addition: microsoft.network/applicationgatewaywebapplicationfirewallpolicies."""

    id: str
    name: str
    resource_group: str
    state: str | None = None  # "Enabled" | "Disabled"
    mode: str | None = None  # "Detection" | "Prevention"


class ApplicationGateway(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    sku_name: str  # "Standard_v2" | "WAF_v2"
    sku_tier: str | None = None
    sku_capacity: int | None = None
    subnet_id: str | None = None
    waf_enabled: bool = False
    waf_mode: str | None = None  # "Detection" | "Prevention"
    waf_rule_set_type: str | None = None
    waf_rule_set_version: str | None = None
    waf_policy_id: str | None = None
    waf_policy: AppGatewayWafPolicy | None = None
    ssl_policy_name: str | None = None
    autoscale_min: int | None = None
    autoscale_max: int | None = None
    zones: list[str] = Field(default_factory=list)
    tags: dict = Field(default_factory=dict)


class PrivateDnsZone(BaseModel):
    id: str
    name: str  # e.g. "privatelink.blob.core.windows.net"
    resource_group: str
    linked_vnet_ids: list[str] = Field(default_factory=list)
    linked_vnet_names: list[str] = Field(default_factory=list)
    auto_registration_enabled: bool = False
    record_count: int = 0


class ExpressRouteCircuit(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    service_provider: str | None = None
    peering_location: str | None = None
    bandwidth_mbps: int | None = None
    sku_tier: str = "Standard"  # "Standard" | "Premium"
    sku_family: str = "MeteredData"  # "MeteredData" | "UnlimitedData"
    circuit_provisioning_state: str = "Enabled"
    global_reach_enabled: bool = False
    peering_types: list[str] = Field(default_factory=list)  # AzurePrivatePeering, MicrosoftPeering
    tags: dict = Field(default_factory=dict)


# ── NSG ────────────────────────────────────────────────────────────────────


class NSGSecurityRule(BaseModel):
    name: str
    priority: int
    direction: str  # "Inbound" | "Outbound"
    access: str  # "Allow" | "Deny"
    protocol: str  # "Tcp" | "Udp" | "Icmp" | "*"
    source_port_range: str | None = None
    source_port_ranges: list[str] = Field(default_factory=list)
    destination_port_range: str | None = None
    destination_port_ranges: list[str] = Field(default_factory=list)
    source_address_prefix: str | None = None
    source_address_prefixes: list[str] = Field(default_factory=list)
    source_asgs: list[str] = Field(default_factory=list)  # ASG resource IDs
    destination_address_prefix: str | None = None
    destination_address_prefixes: list[str] = Field(default_factory=list)
    destination_asgs: list[str] = Field(default_factory=list)
    description: str | None = None
    is_default_rule: bool = False


class AzureNSG(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    security_rules: list[NSGSecurityRule] = Field(default_factory=list)
    default_security_rules: list[NSGSecurityRule] = Field(default_factory=list)
    associated_subnet_ids: list[str] = Field(default_factory=list)
    associated_nic_ids: list[str] = Field(default_factory=list)
    flow_logs_enabled: bool = False
    flow_log_ids: list[str] = Field(default_factory=list)
    tags: dict = Field(default_factory=dict)


# ── Public IP ──────────────────────────────────────────────────────────────


class AzurePublicIP(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    sku_name: str = "Standard"  # "Basic" | "Standard"
    allocation_method: str = "Static"  # "Static" | "Dynamic"
    ip_address: str | None = None
    ip_version: str = "IPv4"  # "IPv4" | "IPv6"
    dns_label: str | None = None
    fqdn: str | None = None
    zones: list[str] = Field(default_factory=list)
    # What it's attached to (the export carries the ipConfiguration id; its type is derived from the id)
    associated_resource_id: str | None = None
    associated_resource_type: str | None = None  # "NIC" | "LB" | "AppGW" | "Firewall" | "Bastion" | "Gateway" | "NAT"
    ddos_protection_mode: str = "VirtualNetworkInherited"
    tags: dict = Field(default_factory=dict)


# ── Load Balancer ──────────────────────────────────────────────────────────


class AzureLBFrontendIP(BaseModel):
    name: str
    public_ip_id: str | None = None
    private_ip_address: str | None = None
    private_ip_allocation_method: str | None = None
    subnet_id: str | None = None
    zones: list[str] = Field(default_factory=list)


class AzureLBRule(BaseModel):
    name: str
    protocol: str  # "Tcp" | "Udp" | "All"
    frontend_port: int
    backend_port: int
    enable_floating_ip: bool = False
    enable_tcp_reset: bool = False
    idle_timeout_minutes: int = 4
    load_distribution: str = "Default"
    disable_outbound_snat: bool = False


class AzureLBProbe(BaseModel):
    name: str
    protocol: str  # "Http" | "Https" | "Tcp"
    port: int
    interval_seconds: int = 15
    number_of_probes: int = 2
    request_path: str | None = None


class AzureLoadBalancer(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    sku_name: str = "Standard"  # "Basic" | "Standard" | "Gateway"
    lb_type: str = "Public"  # "Public" | "Internal"
    frontend_ip_configs: list[AzureLBFrontendIP] = Field(default_factory=list)
    lb_rules: list[AzureLBRule] = Field(default_factory=list)
    probes: list[AzureLBProbe] = Field(default_factory=list)
    backend_pool_ids: list[str] = Field(default_factory=list)
    inbound_nat_rule_count: int = 0
    zones: list[str] = Field(default_factory=list)
    tags: dict = Field(default_factory=dict)


# ── VPN / VNet Gateway ─────────────────────────────────────────────────────


class AzureGatewayConnection(BaseModel):
    id: str
    name: str
    connection_type: str  # "IPsec" | "ExpressRoute" | "Vnet2Vnet" | "VPNClient"
    connection_status: str
    remote_vnet_id: str | None = None
    local_network_gateway_id: str | None = None
    express_route_circuit_id: str | None = None
    routing_weight: int = 10
    enable_bgp: bool = False
    use_policy_based_traffic_selectors: bool = False
    shared_key_set: bool = False  # never store the actual key


class AzureVirtualNetworkGateway(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    gateway_type: str  # "Vpn" | "ExpressRoute" | "LocalGateway"
    vpn_type: str | None = None  # "RouteBased" | "PolicyBased"
    sku_name: str = "VpnGw1"
    sku_tier: str = "VpnGw1"
    active_active: bool = False
    enable_bgp: bool = False
    bgp_asn: int | None = None
    public_ip_ids: list[str] = Field(default_factory=list)
    subnet_id: str | None = None  # GatewaySubnet
    connections: list[AzureGatewayConnection] = Field(default_factory=list)
    generation: str | None = None  # "Generation1" | "Generation2"
    zones: list[str] = Field(default_factory=list)
    tags: dict = Field(default_factory=dict)


# ── Private Endpoint ───────────────────────────────────────────────────────


class AzurePrivateEndpointConnection(BaseModel):
    connection_name: str
    private_link_service_id: str
    group_ids: list[str] = Field(default_factory=list)  # e.g. ["blob", "file"]
    connection_state: str  # "Approved" | "Pending" | "Rejected"


class AzurePrivateEndpoint(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    subnet_id: str | None = None
    service_connections: list[AzurePrivateEndpointConnection] = Field(default_factory=list)
    dns_zone_group_names: list[str] = Field(default_factory=list)
    custom_dns_configs: list[str] = Field(default_factory=list)  # FQDNs with overrides
    tags: dict = Field(default_factory=dict)


# ── NAT Gateway ────────────────────────────────────────────────────────────


class AzureNatGateway(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    sku_name: str = "Standard"
    idle_timeout_minutes: int = 4
    public_ip_ids: list[str] = Field(default_factory=list)
    public_ip_prefix_ids: list[str] = Field(default_factory=list)
    associated_subnet_ids: list[str] = Field(default_factory=list)
    zones: list[str] = Field(default_factory=list)
    tags: dict = Field(default_factory=dict)


# ── Bastion Host ───────────────────────────────────────────────────────────


class AzureBastionHost(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    sku_name: str = "Standard"  # "Basic" | "Standard" | "Premium"
    subnet_id: str | None = None  # AzureBastionSubnet
    public_ip_id: str | None = None
    scale_units: int = 2
    tunneling_enabled: bool = False
    shareable_link_enabled: bool = False
    ip_connect_enabled: bool = False
    file_copy_enabled: bool = False
    kerberos_enabled: bool = False
    tags: dict = Field(default_factory=dict)


# ── Azure Route Server ─────────────────────────────────────────────────────


class AzureRouteServer(BaseModel):
    """Azure Route Server — a virtual hub with kind == 'RouteServer'."""

    id: str
    name: str
    location: str
    resource_group: str
    hosted_subnet_id: str | None = None
    vnet_id: str | None = None
    virtual_router_asn: int | None = None
    virtual_router_ips: list[str] = Field(default_factory=list)
    allow_branch_to_branch_traffic: bool = False
    hub_routing_preference: str | None = None  # "ExpressRoute" | "VpnGateway" | "ASPath"
    tags: dict = Field(default_factory=dict)


# ── Core VNet / vWAN models ────────────────────────────────────────────────


class VNet(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    subscription_id: str
    address_space: list[str] = Field(default_factory=list)
    dns_servers: list[str] = Field(default_factory=list)
    subnets: list[AzureSubnet] = Field(default_factory=list)
    peerings: list[VNetPeering] = Field(default_factory=list)
    ddos_protection_enabled: bool = False
    ddos_protection_plan_id: str | None = None
    flow_logs_enabled: bool = False
    encryption_enabled: bool = False
    tags: dict = Field(default_factory=dict)


class AzureVHub(BaseModel):
    id: str
    name: str
    location: str
    resource_group: str
    address_prefix: str
    sku: str = "Standard"
    connected_vnet_ids: list[str] = Field(default_factory=list)
    express_route_gateway_id: str | None = None
    azure_firewall_id: str | None = None
    routing_state: str = "Provisioned"
    virtual_router_asn: int | None = None
    virtual_router_ips: list[str] = Field(default_factory=list)


class AzureVWan(BaseModel):
    id: str
    name: str
    resource_group: str
    sku: str
    hubs: list[AzureVHub] = Field(default_factory=list)
    allow_vnet_to_vnet_traffic: bool = True
    allow_branch_to_branch_traffic: bool = True
    tags: dict = Field(default_factory=dict)


class FrontDoorWAFPolicy(BaseModel):
    """Azure Front Door Web Application Firewall policy."""

    id: str
    name: str
    resource_group: str
    location: str
    policy_mode: str = "Detection"  # "Detection" | "Prevention"
    policy_enabled_state: str = "Enabled"  # "Enabled" | "Disabled"
    custom_rules_count: int = 0
    managed_rules_count: int = 0
    tags: dict = Field(default_factory=dict)


class FlowLog(BaseModel):
    """Lab addition: microsoft.network/networkwatchers/flowlogs; projected onto VNet and NSG flow_logs_enabled."""

    id: str
    name: str
    target_resource_id: str
    enabled: bool = True
    traffic_analytics_enabled: bool = False
    retention_days: int | None = None


class AzureSubscriptionTopology(BaseModel):
    subscription_id: str
    subscription_name: str | None = None
    vnets: list[VNet] = Field(default_factory=list)
    nsgs: list[AzureNSG] = Field(default_factory=list)
    route_tables: list[AzureRouteTable] = Field(default_factory=list)
    virtual_network_gateways: list[AzureVirtualNetworkGateway] = Field(default_factory=list)
    load_balancers: list[AzureLoadBalancer] = Field(default_factory=list)
    public_ips: list[AzurePublicIP] = Field(default_factory=list)
    private_endpoints: list[AzurePrivateEndpoint] = Field(default_factory=list)
    nat_gateways: list[AzureNatGateway] = Field(default_factory=list)
    bastion_hosts: list[AzureBastionHost] = Field(default_factory=list)
    virtual_wans: list[AzureVWan] = Field(default_factory=list)
    route_servers: list[AzureRouteServer] = Field(default_factory=list)
    firewalls: list[AzureFirewall] = Field(default_factory=list)
    firewall_policies: list[AzureFirewallPolicy] = Field(default_factory=list)
    application_gateways: list[ApplicationGateway] = Field(default_factory=list)
    waf_policies: list[AppGatewayWafPolicy] = Field(default_factory=list)
    private_dns_zones: list[PrivateDnsZone] = Field(default_factory=list)
    express_route_circuits: list[ExpressRouteCircuit] = Field(default_factory=list)
    front_door_waf_policies: list[FrontDoorWAFPolicy] = Field(default_factory=list)
    flow_logs: list[FlowLog] = Field(default_factory=list)


class AzureTopology(BaseModel):
    model_version: str = TOPOLOGY_MODEL_VERSION
    subscriptions: list[AzureSubscriptionTopology] = Field(default_factory=list)
    resource_counts: dict[str, int] = Field(default_factory=dict)  # lower-cased ARG type -> rows
    unmapped_types: list[str] = Field(default_factory=list)
    has_properties: bool = True  # False for the portal "All resources" CSV: rules that read properties answer unknown
    warnings: list[str] = Field(default_factory=list)

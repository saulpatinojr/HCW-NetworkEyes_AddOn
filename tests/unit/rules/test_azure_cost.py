# Ported from saulpatinojr/Work-Cloud_Network_Core tests/unit/test_finops_signals.py at 5d3b914 (the AZ-COST-001/004
# cases); changes: lab model builders and evaluate(); the price assertions are gone (no price table in the lab) and the
# metric cases (002/003) become unknowns.
from network_assessment.model.topology import AzureNatGateway, AzurePublicIP
from network_assessment.rules import evaluate

from ..model_fixtures import rule_ids, subscription, topology


def _pip(name: str, owner: str | None) -> AzurePublicIP:
    return AzurePublicIP(
        id=f"pip-{name}", name=name, location="eastus2", resource_group="rg", associated_resource_id=owner
    )


def test_orphaned_public_ip_emits_cost_001():
    sub = subscription(public_ips=[_pip("orphan", None), _pip("used", "/x/azureFirewalls/fw/ipConfigurations/c")])
    findings = [f for f in evaluate(topology(sub)).findings if f.rule_id == "AZ-COST-001"]
    assert len(findings) == 1
    f = findings[0]
    assert f.resource_id == "pip-orphan" and f.traffic_direction == "north_south" and f.observed_state.fact
    assert "[VERIFY]" not in (f.description or ""), "the lab makes no price claims"


def test_nat_gateway_without_subnets_emits_cost_004():
    nat = AzureNatGateway(
        id="nat-1", name="nat-unused", location="eastus2", resource_group="rg", associated_subnet_ids=[]
    )
    assert "AZ-COST-004" in rule_ids(evaluate(topology(subscription(nat_gateways=[nat]))).findings)
    used = AzureNatGateway(
        id="nat-2", name="nat-used", location="eastus2", resource_group="rg", associated_subnet_ids=["s"]
    )
    assert "AZ-COST-004" not in rule_ids(evaluate(topology(subscription(nat_gateways=[used]))).findings)


def test_metric_cost_rules_are_unknown_not_findings():
    result = evaluate(topology(subscription()))
    assert {u.rule_id for u in result.unknowns} >= {"AZ-COST-002", "AZ-COST-003", "AZ-COST-005"}
    assert not any(f.rule_id in ("AZ-COST-002", "AZ-COST-003", "AZ-COST-005") for f in result.findings)

"""report.md and NOT-FOR-PRODUCTION.md. The report carries the visitor's own data back to the token holder."""

from __future__ import annotations

from network_assessment.engine import Finding
from network_assessment.report.summary import Assessment

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}

NOT_FOR_PRODUCTION = """# Not for production

This assessment was produced by the Hybrid Cloud Works Network Assessment lab edition from a Resource Graph export you
uploaded. It evaluates exported configuration only.

- It is not a compliance attestation, a penetration test, or a security assessment of record.
- It saw only the rows in the export: no metrics, no diagnostic settings, no BGP state, no effective routes or
  effective NSG rules, no private DNS resolution, no Defender assessments, no cost. Rules that need any of those are
  listed under "Rules this export cannot answer", in data (`unknowns`), not only in prose.
- Every finding states the fact the export carried and the field it came from; nothing is inferred.
- Compliance-framework references are carried over from the upstream engine and are marked for verification.
- The lab edition keeps nothing: the assessment expires after two hours or when you delete it.
"""

CANNOT_SHOW = (
    "Utilisation and saturation of gateways, firewalls, load balancers and circuits (Azure Monitor metrics)",
    "Diagnostic settings on firewalls and Bastion hosts",
    "Attacks in progress (DDoS telemetry)",
    "BGP peer state, learned and advertised routes",
    "Effective routes and effective NSG rules per network interface",
    "Private endpoint DNS resolution from inside the VNet",
    "Defender for Cloud assessments and cost",
    "Flow logs, when the export carries no networkwatchers/flowlogs rows",
    "Resources outside microsoft.network/ (VMs, NVAs by marketplace plan, DNS resolver rulesets)",
    "Resources the exporting identity could not read, and subscriptions not included in the export",
)


def _cell(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(a: Assessment) -> str:
    s = a.summary
    lines: list[str] = []
    lines.append("# Network assessment report (lab edition)")
    lines.append("")
    lines.append(
        f"Assessment `{a.id}` created {a.created_at.isoformat()} from a `{a.source_format}` export"
        + (f" (`{_cell(a.file_name)}`)" if a.file_name else "")
        + "."
    )
    lines.append(f"Rules {a.rules_version}, model {a.model_version}. Not for production; see NOT-FOR-PRODUCTION.md.")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- Rows in the export: {s.row_count}; network resources evaluated: {s.resource_count}")
    lines.append(f"- Subscriptions: {', '.join(s.subscriptions) or 'none'}")
    lines.append(f"- Rules evaluated: {s.rules_evaluated}; rules this export cannot answer: {s.unknown_rules}")
    if a.warnings:
        lines.append(f"- Ingestion warnings: {len(a.warnings)}")
        lines.extend(f"  - {_cell(w)}" for w in a.warnings)
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Severity | Findings |")
    lines.append("|---|---|")
    for sev, count in s.findings_by_severity.items():
        lines.append(f"| {sev} | {count} |")
    lines.append("")
    lines.append("| Resource type | Rows |")
    lines.append("|---|---|")
    for rtype, count in s.by_type.items():
        lines.append(f"| `{rtype}` | {count} |")
    lines.append("")
    lines.append("## Topology")
    lines.append("")
    t = s.topology
    lines.append(f"Pattern: **{t.pattern}**. {_cell(t.rationale)}")
    if t.hub_vnet_ids:
        lines.append("")
        lines.extend(f"- hub: `{h}`" for h in t.hub_vnet_ids)
    if t.spoke_vnet_ids:
        lines.extend(f"- spoke: `{v}`" for v in t.spoke_vnet_ids)
    lines.append("")
    lines.append("## Findings by severity")
    lines.append("")
    ordered = sorted(
        a.findings, key=lambda f: (SEVERITY_ORDER.get(f.severity.value, 9), f.rule_id or "", f.resource_id or "")
    )
    if not ordered:
        lines.append("No finding was observed.")
    for f in ordered:
        lines.extend(_finding_block(f))
    lines.append("## Rules this export cannot answer")
    lines.append("")
    if a.unknowns:
        lines.append("| Rule | Reason |")
        lines.append("|---|---|")
        lines.extend(f"| {u.rule_id} | {_cell(u.reason)} |" for u in a.unknowns)
    else:
        lines.append("Every registered rule was evaluated over this export.")
    lines.append("")
    lines.append("## What this export cannot show")
    lines.append("")
    lines.extend(f"- {item}" for item in CANNOT_SHOW)
    lines.append("")
    lines.append("## Notice")
    lines.append("")
    lines.append(
        "Not for production. Findings state observed configuration only; compliance references are marked for "
        "verification. Microsoft and Azure are trademarks of Microsoft Corporation; this project is not affiliated "
        "with or endorsed by Microsoft."
    )
    lines.append("")
    return "\n".join(lines)


def _finding_block(f: Finding) -> list[str]:
    frameworks = "; ".join(f"{m.framework} {m.control or m.control_id or ''}".strip() for m in f.framework_mappings[:3])
    return [
        f"### {f.severity.value.upper()} · {f.rule_id} · {_cell(f.title)}",
        "",
        f"- Resource: `{f.resource_id}` ({_cell(f.resource_type)}, {_cell(f.region)}, "
        f"subscription {_cell(f.account_id)})",
        f"- Fact: {_cell(f.observed_state.fact)}",
        f"- Evidence: `{_cell(f.observed_state.evidence_ref)}`",
        f"- Remediation: {_cell(f.remediation)}",
        f"- Learn: {f.learn_url} [VERIFY]",
        f"- Frameworks [VERIFY]: {_cell(frameworks)}",
        f"- Traffic plane: {f.traffic_direction or 'unclassified'}",
        "",
    ]

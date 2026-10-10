# Ported from saulpatinojr/Work-Cloud_Network_Core cna/ai_engine/analysis_engine.py (the FrameworkMapping literals of
# the Azure rules, lines 639-1660), cna/modules/network/analysis/bcdr_signals.py (_BCDR_FRAMEWORK) and
# finops_signals.py (_FINOPS_FRAMEWORK) at 5d3b914; changes: the literals are deduplicated into named constants and
# keyed by rule id as data; the Engine B rules (AZ-NET-020..033, AZ-BCDR-006/007), which carried no mappings, are
# mapped here by analogy to the nearest Engine A rule.
"""Compliance-framework mappings per rule, as data.

[VERIFY] Every control reference below is a compliance claim carried over from the Core. The owner's legal/compliance
review confirms each before public exposure (docs/rules/catalog.md marks the column [VERIFY]). [REVIEW REQUIRED]
"""

from __future__ import annotations

from network_assessment.model.findings import FrameworkMapping as FM

WAF_NS1 = FM(
    framework="Azure Well-Architected Framework",
    pillar="Security",
    control="NS-1 — Establish network segmentation boundaries",
)
WAF_NS2 = FM(framework="Azure Well-Architected Framework", pillar="Security", control="NS-2 — Monitor network security")
WAF_NS3 = FM(
    framework="Azure Well-Architected Framework",
    pillar="Security",
    control="NS-3 — Deploy firewall at the edge of enterprise network",
)
WAF_NS4 = FM(
    framework="Azure Well-Architected Framework",
    pillar="Security",
    control="NS-4 — Protect applications from external network attacks",
)
WAF_PA2 = FM(
    framework="Azure Well-Architected Framework",
    pillar="Security",
    control="PA-2 — Avoid standing access for user accounts and permissions",
)
WAF_RE3 = FM(
    framework="Azure Well-Architected Framework", pillar="Reliability", control="RE-3 — Use redundant connectivity"
)
WAF_RE5 = FM(framework="Azure Well-Architected Framework", pillar="Reliability", control="RE-5 — Design for redundancy")
WAF_CO7 = FM(
    framework="Azure Well-Architected Framework", pillar="Cost Optimization", control="CO-7 — Optimize component costs"
)
WAF_PE = FM(
    framework="Azure Well-Architected Framework", pillar="Performance Efficiency", control="PE-5 — Scale and partition"
)
ASB_NS4 = FM(framework="Azure Security Benchmark", pillar="Network Security", control="NS-4")
CIS_6_2 = FM(framework="CIS Microsoft Azure Foundations Benchmark", pillar="Networking", control="6.2")
CIS_6_1 = FM(
    framework="CIS Microsoft Azure Foundations Benchmark",
    pillar="Networking",
    control="6.1 — RDP access from the Internet is restricted",
)
CIS_6_2_SSH = FM(
    framework="CIS Microsoft Azure Foundations Benchmark",
    pillar="Networking",
    control="6.2 — SSH access from the Internet is restricted",
)
CIS_6_5 = FM(
    framework="CIS Microsoft Azure Foundations Benchmark",
    pillar="Networking",
    control="6.5 — Network Watcher is enabled",
)
NIST_PR_PT4 = FM(framework="NIST CSF", pillar="Protect", control="PR.PT-4")
NIST_PR_AC5 = FM(framework="NIST CSF", pillar="Protect", control="PR.AC-5 — Network integrity is protected")
NIST_DE_CM1 = FM(
    framework="NIST CSF",
    pillar="Detect",
    control="DE.CM-1 — The network is monitored to detect potential cybersecurity events",
)
NIST_DE_CM3 = FM(framework="NIST CSF", pillar="Detect", control="DE.CM-3 — Personnel activity is monitored")
PCI_1_2 = FM(
    framework="PCI-DSS 4.0",
    pillar="Network Security Controls",
    control="Req 1.2 — Network security controls configured and maintained",
)
PCI_1_3 = FM(
    framework="PCI-DSS 4.0",
    pillar="Network Security Controls",
    control="Req 1.3 — Restrict inbound and outbound traffic",
)
ISO_8_20 = FM(framework="ISO 27001:2022", pillar="Network Security", control="A.8.20 — Networks security")
ISO_8_21 = FM(framework="ISO 27001:2022", pillar="Network Security", control="A.8.21 — Security of network services")
ISO_8_22 = FM(framework="ISO 27001:2022", pillar="Network Security", control="A.8.22 — Segregation of networks")
ISO_8_23 = FM(framework="ISO 27001:2022", pillar="Network Security", control="A.8.23 — Web filtering")
HIPAA_A1 = FM(
    framework="HIPAA §164.312",
    pillar="Technical Safeguards",
    control="(a)(1) — Access control: unique user identification and network access controls for ePHI systems",
)
HIPAA_A2II = FM(
    framework="HIPAA §164.312",
    pillar="Technical Safeguards",
    control="(a)(2)(ii) — Automatic logoff / contingency operations; availability of ePHI systems",
)
HIPAA_B = FM(
    framework="HIPAA §164.312",
    pillar="Technical Safeguards",
    control="(b) — Audit controls: hardware/software activity records for ePHI systems",
)
HIPAA_E1 = FM(
    framework="HIPAA §164.312",
    pillar="Technical Safeguards",
    control="(e)(1) — Transmission security: guard against unauthorized access to ePHI in transit",
)
HIPAA_E2II = FM(
    framework="HIPAA §164.312",
    pillar="Technical Safeguards",
    control="(e)(2)(ii) — Encryption and decryption (addressable); integrity controls for ePHI in transit",
)
FEDRAMP_SC5 = FM(
    framework="FedRAMP Moderate",
    pillar="System and Communications Protection",
    control="SC-5 — Denial of Service Protection",
)
FEDRAMP_SC7 = FM(
    framework="FedRAMP Moderate", pillar="System and Communications Protection", control="SC-7 — Boundary Protection"
)
FEDRAMP_CP8 = FM(
    framework="FedRAMP Moderate",
    pillar="Contingency Planning",
    control="CP-8 — Telecommunications Services (redundancy)",
)
FEDRAMP_AU2 = FM(framework="FedRAMP Moderate", pillar="Audit and Accountability", control="AU-2 — Audit Events")
FEDRAMP_AC17 = FM(framework="FedRAMP Moderate", pillar="Access Control", control="AC-17 — Remote Access")
FINOPS_OPT = FM(
    framework="FinOps Framework", pillar="Optimize", control="Workload optimization — rightsizing and waste elimination"
)


def _ztmm(control_id: str, control_name: str, alignment: str, pillar: str = "Networks") -> FM:
    return FM(
        framework="CISA ZTMM v2",
        version="v2",
        pillar=pillar,
        control_id=control_id,
        control_name=control_name,
        alignment=alignment,
    )


ZTMM_SEGMENTATION = _ztmm("3.1", "Network Segmentation", "NSGs and routing enforce segmentation between subnets")
ZTMM_PEERING = _ztmm("3.1", "Network Segmentation", "Misconfigured peering can create unintended network paths")
ZTMM_BYPASS = _ztmm("3.1", "Network Segmentation", "Traffic bypassing the hub firewall violates segmentation policy")
ZTMM_TRAFFIC = _ztmm(
    "3.2", "Traffic Management", "Threat intel-based blocking controls traffic flows to known malicious destinations"
)
ZTMM_WAF = _ztmm("3.2", "Traffic Management", "WAF provides application-layer traffic filtering at the perimeter")
ZTMM_WAF_DETECTION = _ztmm("3.2", "Traffic Management", "WAF in Detection mode does not block malicious traffic")
ZTMM_FLOW = _ztmm(
    "3.2", "Traffic Management", "Flow logs enable traffic visibility required for zero trust enforcement"
)
ZTMM_TA = _ztmm(
    "3.2", "Traffic Management", "Traffic Analytics provides flow-level visibility for zero trust verification"
)
ZTMM_FW_LOGS = _ztmm(
    "3.2", "Traffic Management", "Firewall logs are required to audit and verify traffic management policies"
)
ZTMM_SESSION = _ztmm("3.2", "Traffic Management", "Session logging provides audit trail for privileged access paths")
ZTMM_RESILIENCE = _ztmm("3.4", "Network Resilience", "Redundant network components prevent single points of failure")
ZTMM_DDOS = _ztmm("3.4", "Network Resilience", "DDoS protection is a network resilience control")
ZTMM_APPS_WAF = _ztmm(
    "4.0",
    "Application and Workload Protection",
    "Disabled WAF leaves application workloads without HTTP-layer attack inspection",
    pillar="Applications and Workloads",
)
ZTMM_APPS_DETECTION = _ztmm(
    "4.0",
    "Application and Workload Protection",
    "Detection-only WAF does not enforce blocking for application-layer attacks",
    pillar="Applications and Workloads",
)
ZTMM_REMOTE = _ztmm(
    "3.2", "Traffic Management", "Management ports exposed to the Internet bypass identity-aware access paths"
)

_BCDR = (WAF_RE5, ZTMM_RESILIENCE)
_FINOPS = (FINOPS_OPT, WAF_CO7)

FRAMEWORKS: dict[str, tuple[FM, ...]] = {
    "AZ-NET-001": (WAF_NS1, ISO_8_20, HIPAA_E2II, FEDRAMP_SC5, ZTMM_DDOS),
    "AZ-NET-002": (WAF_NS1, CIS_6_2, PCI_1_2, ISO_8_22, HIPAA_A1, FEDRAMP_SC7, ZTMM_SEGMENTATION),
    "AZ-NET-003": (WAF_NS4, NIST_PR_PT4, PCI_1_3, ISO_8_20, HIPAA_E1, FEDRAMP_SC7, ZTMM_TRAFFIC),
    "AZ-NET-004": (WAF_RE3, ISO_8_21, HIPAA_A2II, FEDRAMP_CP8, ZTMM_RESILIENCE),
    "AZ-NET-005": (WAF_NS1, FEDRAMP_SC7, ZTMM_PEERING),
    "AZ-NET-006": (WAF_NS2, NIST_DE_CM1, HIPAA_B, FEDRAMP_AU2, ZTMM_FLOW),
    "AZ-NET-007": (WAF_NS4, PCI_1_3, ISO_8_23, HIPAA_E1, FEDRAMP_SC7, ZTMM_WAF, ZTMM_APPS_WAF),
    "AZ-NET-008": (WAF_PE, WAF_RE3),
    "AZ-NET-009": (WAF_NS3, WAF_CO7),
    "AZ-NET-010": (WAF_PE, WAF_RE5),
    "AZ-NET-011": (WAF_PE, WAF_NS1),
    "AZ-NET-012": (WAF_NS1, ASB_NS4, ZTMM_BYPASS),
    "AZ-NET-013": (WAF_NS3, NIST_DE_CM1, ZTMM_FW_LOGS),
    "AZ-NET-014": (WAF_NS2, ZTMM_TA),
    "AZ-NET-015": (WAF_PA2, NIST_DE_CM3, ZTMM_SESSION),
    "AZ-NET-016": (WAF_PE, WAF_RE3),
    "AZ-NET-017": (FEDRAMP_SC5, ZTMM_DDOS),
    "AZ-NET-018": (WAF_NS4, PCI_1_3, FEDRAMP_SC7, ZTMM_WAF_DETECTION, ZTMM_APPS_DETECTION),
    "AZ-NET-019": (WAF_PE,),
    "AZ-NET-020": (WAF_NS1, CIS_6_1, CIS_6_2_SSH, PCI_1_3, HIPAA_A1, FEDRAMP_AC17, ZTMM_REMOTE),
    "AZ-NET-021": (WAF_NS1, CIS_6_2, PCI_1_2, ISO_8_22, FEDRAMP_SC7, ZTMM_SEGMENTATION),
    "AZ-NET-022": (WAF_NS1, ASB_NS4, PCI_1_3, ZTMM_BYPASS),
    "AZ-NET-023": (WAF_RE3, NIST_PR_AC5),
    "AZ-NET-024": (WAF_RE5, ISO_8_21),
    "AZ-NET-025": (WAF_NS4, PCI_1_3, ISO_8_23, ZTMM_WAF_DETECTION, ZTMM_APPS_DETECTION),
    "AZ-NET-026": (WAF_RE5, ZTMM_RESILIENCE),
    "AZ-NET-027": (WAF_RE5, WAF_NS1, ZTMM_RESILIENCE),
    "AZ-NET-028": (WAF_RE3, WAF_RE5, ZTMM_RESILIENCE),
    "AZ-NET-029": (WAF_PE,),
    "AZ-NET-030": (WAF_RE3, ISO_8_21, ZTMM_RESILIENCE),
    "AZ-NET-031": (WAF_NS1, ISO_8_21),
    "AZ-NET-032": (WAF_NS3, PCI_1_3, FEDRAMP_SC7, ZTMM_TRAFFIC),
    "AZ-NET-033": (WAF_PA2, CIS_6_1, FEDRAMP_AC17, ZTMM_REMOTE),
    "AZ-BCDR-001": _BCDR,
    "AZ-BCDR-002": _BCDR,
    "AZ-BCDR-003": _BCDR,
    "AZ-BCDR-004": _BCDR,
    "AZ-BCDR-005": _BCDR,
    "AZ-BCDR-006": _BCDR,
    "AZ-BCDR-007": _BCDR,
    "AZ-COST-001": _FINOPS,
    "AZ-COST-002": _FINOPS,
    "AZ-COST-003": _FINOPS,
    "AZ-COST-004": _FINOPS,
    "AZ-COST-005": _FINOPS,
}

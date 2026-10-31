# Provenance of ported code

Owner decision 2026-10-09: the lab edition ports the Core's Azure network engine with provenance under MIT
(`[REVIEW REQUIRED]` relicensing, see `NOTICE`), as an **interim** measure (ADR-0001) until
`saulpatinojr/HCW-NetworkEyes_App` (the App; it was the Core until the owner's 2026-10-10 decision merged that lineage
back) publishes the `network-assessment-azure-engine` wheel (the first release, `engine-v0.1.0`, was published on 2026-10-12 under the package's earlier name, `cna-azure-network-engine`; **not adopted yet**: compared with this port on 2026-10-31 and found to need five fixes upstream, see `docs/whats-new-upstream.md`) (its `REFACTOR_APP.md` change sets A, B, C and E produce the same
symbols under `network_assessment_azure_engine`; change set J attaches the wheel to the GitHub Release of each `engine-v*` tag). Every ported file starts with
`# Ported from saulpatinojr/HCW-NetworkEyes_App <path> at 5d3b914; changes: …`, and
`tests/end_to_end/test_repository_manifest.py` asserts the header and this table agree. Source paths and line numbers
are those of commit `5d3b914` in `HCW-NetworkEyes_App` (the split point of 2026-09-18; the same commit in its history today).

**Ported code changes only through entries in this table** (CLAUDE.md invariant): a change to a ported file updates its
header line and the "what changed" column, with the reason.

| Ported file (lines) | Source at `5d3b914` (lines) | What changed | Why |
|---|---|---|---|
| `src/network_assessment/model/enforcer.py` (85) | `cna/ai_engine/observed_state_enforcer.py` (76, whole file) | Verbatim: class, 16 hedge patterns, `scan_text`, `validate`. Added `assert_text_is_hedge_free()` for the registry test. | The hedge-word gate the owner wants on every finding fact; the lab extends it to rule titles and remediation. |
| `src/network_assessment/model/findings.py` (91) | `cna/core/findings_schema.py` (104, whole file) | Dropped MCP and review fields (`FindingRecommendation`, `FindingStatus`, `recommendations`, `recommendation_source`, `recommendation`, `human_reviewed`, `human_notes`, `data_confidence`, `est_monthly_cost_usd`, `FindingsReport`); `ObservedState.state ∈ {observed, unknown, not-applicable}`; `Finding` gained `rule_version`, `remediation`, `learn_url`; `account_id` serialises as `subscriptionId`; camelCase aliases on output; `Unknown` model added; `FINDINGS_MODEL_VERSION = "lab-1.0.0"`. The string-coercion validator stays. | REFACTOR_APP.md section 9 (the Core's target contract); the lab has no MCP, review or price path. |
| `src/network_assessment/model/topology.py` (488) | `cna/core/topology_schema.py` lines 315–1006 (the Azure classes; file is 1,010 lines) | Kept the 26 Azure classes an export can populate; dropped AWS, metrics, observability, BGP, Defender, NVA, NIC, workload and management-group classes and fields an export cannot fill (`subnet_type`, `dns_resolves_to_private_ip`, byte counters, DPD/idle timeouts, provisioning states, VPN client pools, SOA records, `bgp_connections`); added `AzureSubnet.ip_configuration_count`, `AzureFirewallPolicy`, `AzureFirewall.firewall_policy` + `effective_threat_intel_mode`, `AppGatewayWafPolicy`, `ApplicationGateway.waf_policy`, `AzureNSG.flow_log_ids`, `FlowLog`; `AzureSubscriptionTopology` lost `tenant_id`, `discovery_blocked`, `block_reason` and the live collections, gained `firewall_policies`, `waf_policies`, `flow_logs`; `AzureTopology` carries `TOPOLOGY_MODEL_VERSION = "lab-1.0.0"` (declared equivalent to the Core's 1.3.0 Azure subset), `resource_counts`, `unmapped_types`, `has_properties`, `warnings`. | Design B.3: the model is what a Resource Graph export of `microsoft.network/*` carries; fields the export cannot fill are removed, not defaulted. |
| `src/network_assessment/classify/topology.py` (137) | `cna/modules/network/analysis/topology_classifier.py` (134, whole file) | Import path; the `discovery_blocked` skip removed; camelCase aliases on the result. Classification logic verbatim. | Pure function over the model; an export has no blocked subscriptions. |
| `src/network_assessment/rules/taxonomy.py` (218) | `cna/core/finding_taxonomy.py` (224, whole file) | AWS rule ids and resource hints removed; AZ-NET-020..033 and AZ-BCDR-006/007 added to the tables. Functions verbatim. | The typed Engine B rules need a traffic plane; the lab is Azure-only. |
| `src/network_assessment/rules/frameworks.py` (227) | `cna/ai_engine/analysis_engine.py` lines 639–1660 (`FrameworkMapping` literals), `bcdr_signals.py` (`_BCDR_FRAMEWORK`), `finops_signals.py` (`_FINOPS_FRAMEWORK`) | The literals are deduplicated into named constants and keyed by rule id as data; Engine B rules (no mappings in the Core) are mapped by analogy to the nearest Engine A rule. | Mappings are compliance claims: kept as reviewable data with `[VERIFY]` in the catalog. |
| `src/network_assessment/rules/azure_net.py` (921) | `cna/ai_engine/analysis_engine.py` lines 639–1660 (Engine A `_check_azure_*`, 1,022 lines incl. metric checks); `apps/cna-api/main.py` lines 195–1127 (Engine B `_check_*`, 933 lines incl. NVA/BGP/observability/metrics) | Each check is a `@rule` evaluator yielding `Emit` over the lab model; the `AnalysisEngine` class, `EngagementStore`, escalation, `_emit` dedup (moved to the registry) and AWS methods are gone; AZ-NET-002 merges Engine B's platform-subnet skip list (v2); AZ-NET-003 resolves the linked firewall policy (v2); AZ-NET-006/014 read flowlogs rows and answer unknown without them (v2); AZ-NET-007 reads the linked WAF policy (v2); AZ-NET-011 re-derived from `ipConfigurations` per subnet (v2, was a metric); AZ-NET-012 resolves route tables by id (v2); Engine B's untyped dict checks become AZ-NET-020..033 with design B.4 severities (032 MEDIUM with vWAN/NVA suppression, 033 LOW, 027 one finding per IP, 030 unknown without connections rows); AZ-NET-008/009/010/013/015/016/017/019 registered live-only; evidence refs read `export:` instead of `discovery:`; hedge language removed from every title, fact and remediation. | Design B.4; one typed registry replaces two engines (REFACTOR_APP.md change set B); the enforcer gates the texts. |
| `src/network_assessment/rules/azure_bcdr.py` (210) | `cna/modules/network/analysis/bcdr_signals.py` (294, whole file); `apps/cna-api/main.py` `_check_app_gateways` / `_check_load_balancers` zone checks (AZ-BCDR-006/007) | `_finding`/`_FindingParams` replaced by the registry's `Emit`; `discovery_blocked` skip gone; AZ-BCDR-004 emitted once from the subscription that owns the single firewall; framework mappings moved to `frameworks.py`; AZ-BCDR-006/007 added; hedge language removed. | Design B.4; zone-redundancy of application gateways and load balancers is a BC/DR signal (numbering flagged for the owner). |
| `src/network_assessment/rules/azure_cost.py` (110) | `cna/modules/network/analysis/finops_signals.py` lines 94–136 (`_check_orphaned_pips`) and 262–299 (`_check_idle_nat_gateways`) of 365 | The price table (`azure_network_prices.py`) and `est_monthly_cost_usd` are gone; `_finding` replaced by `Emit`; AZ-COST-002/003/005 (24-hour metrics) registered live-only; hedge language removed. | The lab makes no price claims; metrics are a live read. |
| `tests/unit/test_enforcer.py` (61) | `tests/unit/test_analysis_engine.py` `TestObservedStateEnforcer` (lines 396–468 of 574) | Re-expressed without the `AnalysisEngine` fixture. | Ported tests stay green on the lab model. |
| `tests/unit/test_classifier.py` (59) | `tests/unit/test_topology_classifier.py` (138, whole file) | Lab model builders; no `discovery_blocked` case; one gateway-placement case added. | Same. |
| `tests/unit/rules/test_azure_net.py` (385) | `tests/unit/test_analysis_engine.py` `TestAzureNetFindingRules`, `TestAzurePeeringGatewayTransit` (lines 226–383, 499–574) | Lab model builders and `evaluate()`; cases for the reimplemented and new rules added. | Same. |
| `tests/unit/rules/test_azure_bcdr.py` (86) | `tests/unit/test_bcdr_signals.py` (145, whole file) | Lab model builders and `evaluate()`; AZ-BCDR-006/007 cases added. | Same. |
| `tests/unit/rules/test_azure_cost.py` (39) | `tests/unit/test_finops_signals.py` (146; the 001/004 cases) | No price assertions; metric cases become unknowns. | Same. |

Not ported (and why): `azure_discovery.py` (live ARM discovery; its field-mapping knowledge informed
`ingestion/normalize.py`, which is new code and the reference for the Core's normalizer), the price table, the
escalation engine, `EngagementStore`, the report/diagram/AI/portal/review engines, `cna-web`, the `cna-api` shell, the
worker, everything AWS, the NVA/BGP/observability/metrics checks of both engines (live reads).

No file in the table changed on 2026-10-31. Lab code stopped importing these files directly: it goes through
`src/network_assessment/engine.py` (lab-edition code, not ported), which runs the released wheel when it is installed and
these files otherwise. The ported tests in the table keep testing these files; `tests/unit/test_engine.py` tests
whichever engine runs.

Deletion plan (REFACTOR_APP.md section 21, amended 2026-10-31; PyPI is not needed, the GitHub Release asset is pinned):

1. `core-update.yml` pins the wheel on the `ENGINE_REF` line of `pyproject.toml` (the marker is `# ENGINE_REF none`
   until then), re-locks and regenerates `docs/rules/catalog.md` in its bump pull request. That pull request changes no
   code: `engine.py` runs the wheel because it is installed, so the bump's checks test the lab against it.
2. The bump is merged only when its required checks pass on the bump pull request; auto-merge (when the repository
   variable `CORE_AUTOMERGE` is `true`) waits for them, and the `compatible` label is a hint, not the gate. A bump that
   really breaks the lab fails those checks, so it does not merge (a `needs-adaptation` label alone does not stop it:
   the label can also follow a one-off failure in the compatibility step); when the engine causes it, it is fixed
   upstream and arrives as the next release; it is not patched here.
3. After that merge, one pull request deletes `src/network_assessment/{model,rules,classify}`, the ported tests and the
   rows above, deletes `ingestion/normalize.py` (the wheel's normalizer replaced it; `tests/unit/test_engine.py` proves
   they agree), reduces `engine.py` to the wheel, and updates `CLAUDE.md`, `AGENTS.md`, `README.md`, ADR-0001 and
   `docs/whats-new-upstream.md`. `ingestion/arg_row.py` and `ingestion/parse.py`, `report/`, `store.py`, `routes/`,
   `security/` and `web/` stay.

# The output bundle

`GET /api/assessments/{id}/bundle.zip` (owner token required) is a STORE zip (no compression, fixed timestamps) with
exactly seven files, each also available at `…/files/{name}`:

| File | Content |
|---|---|
| `README.md` | This table |
| `report.md` | Scope (rows, resources, subscriptions, rules evaluated and unanswered, ingestion warnings), summary (findings by severity, rows by type), topology pattern with hub and spoke ids, every finding by severity with resource, fact, evidence reference, remediation, learn link and traffic plane, the rules this export cannot answer with reasons, "What this export cannot show", the notice |
| `findings.json` | `findings[]` (`id, ruleId, ruleVersion, severity, platform, region, category, title, description, resourceId, resourceType, subscriptionId, observedState{state, fact, evidenceRef}, affectedResources, frameworkMappings, remediation, learnUrl, trafficDirection, createdAt, version`) and `unknowns[]` (`ruleId, reason`) |
| `topology.json` | The normalised topology model the rules ran over (`model_version: lab-1.0.0`, subscriptions with every collection, `resource_counts`, `unmapped_types`, `warnings`) |
| `summary.json` | `resourceCount, rowCount, subscriptions, byType, topology{pattern, hubVnetIds, spokeVnetIds, rationale}, findingsCount, findingsBySeverity, unknownRules, rulesEvaluated, warnings, rulesVersion, modelVersion, generatedAt` |
| `rules.json` | `rulesVersion` and the registry at the time of the assessment (`id, title, severity, category, version, appliesTo, evidence, needsProperties, description, remediation, learnUrl, frameworks`) |
| `NOT-FOR-PRODUCTION.md` | What the assessment is and is not |

Versions let results be compared across releases: `modelVersion` moves only when the topology model changes;
`rulesVersion` when the rule set changes (a changed rule also bumps its own `ruleVersion`).

The bundle carries your own data (resource ids, subscription ids, address prefixes, rule names, tags) back to you. It is
returned only to the holder of the owner token and is never written to disk on the server.

# Architecture decision records

This edition's own decisions, numbered from 0001, and the shared skeleton decision copied from the sibling Python
AddOn. The canonical log for the pair is the Core's (`saulpatinojr/HCW-NetworkEyes_App`); copies here carry a
header saying where they came from.

| ADR | Title |
|---|---|
| [ADR-0001](ADR-0001-interim-ported-engine.md) | The lab edition ports the Core's engine with provenance, as an interim measure until the wheel exists |
| [ADR-0002 (copy)](ADR-0002-shared-addon-skeleton-no-kit-yet.md) | One shared AddOn skeleton convention across the Python AddOns; no `hcw-addon-kit` package yet |
| [ADR-0003](ADR-0003-lab-edition-on-the-lab-host-appliance-on-container-apps.md) | The lab edition runs on the lab host; the appliance on Azure Container Apps |
| [ADR-0004](ADR-0004-upstream-downstream-for-this-addon.md) | Upstream/downstream for this AddOn: the Core publishes, this edition consumes and never forks |
| [ADR-0005](ADR-0005-always-on-guided-workspace-handoff.md) | Always-on guided workspace handoff with one-time bundle tokens |

Next number: 0006.

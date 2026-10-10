# User guide

The Network Assessment pane reads one file: an export of your Azure network resources from Resource Graph. It never
asks for credentials and never connects to your cloud; the file is processed in memory, the results are returned only to
your browser session, and everything expires after two hours or when you delete it.

The export contains resource names, ids, address prefixes, rule names and tags. Review it before uploading; the pane
holds it in memory for at most two hours and deletes it at once on request.

## 1. Export your network resources

Permission needed: **Reader** on the subscriptions (Resource Graph returns only what the caller can read). The query
projects exactly the columns the normalizer reads; `--first 1000` is the CLI's maximum page. Both commands write
`network-resource-graph.json` in the current directory.

bash:

```bash
az extension add --name resource-graph --upgrade --only-show-errors
az graph query -q "Resources | where type startswith 'microsoft.network/' | project id, name, type, location, resourceGroup, subscriptionId, tags, zones, sku, kind, properties" --first 1000 --output json > network-resource-graph.json
```

PowerShell (same CLI; `Out-File` in Windows PowerShell 5.1 writes a BOM, which the pane strips):

```powershell
az extension add --name resource-graph --upgrade --only-show-errors
az graph query -q "Resources | where type startswith 'microsoft.network/' | project id, name, type, location, resourceGroup, subscriptionId, tags, zones, sku, kind, properties" --first 1000 --output json | Out-File -Encoding utf8 network-resource-graph.json
```

The command prints the `az graph query` envelope (`count`, `data`, `skip_token`, `total_records`); the pane accepts it
as is, or a bare array. If `skip_token` is not null the export is paged and the pane warns that only the first page was
uploaded. Estates with more than 1,000 network rows (up to the 5,000-row cap) page with the commands below.

Paging, bash:

```bash
az extension add --name resource-graph --upgrade --only-show-errors
q="Resources | where type startswith 'microsoft.network/' | project id, name, type, location, resourceGroup, subscriptionId, tags, zones, sku, kind, properties"
token=""; : > network-resource-graph.ndjson
for page in 1 2 3 4 5; do
  if [ -z "$token" ]; then out=$(az graph query -q "$q" --first 1000 --output json); else out=$(az graph query -q "$q" --first 1000 --skip-token "$token" --output json); fi
  printf '%s\n' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(json.dumps(r)) for r in d["data"]]' >> network-resource-graph.ndjson
  token=$(printf '%s' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("skip_token") or "")')
  [ -z "$token" ] && break
done
python3 -c 'import json; rows=[json.loads(l) for l in open("network-resource-graph.ndjson")]; json.dump(rows, open("network-resource-graph.json","w"))'
```

Paging, PowerShell:

```powershell
az extension add --name resource-graph --upgrade --only-show-errors
$q = "Resources | where type startswith 'microsoft.network/' | project id, name, type, location, resourceGroup, subscriptionId, tags, zones, sku, kind, properties"
$rows = @(); $token = $null
for ($page = 1; $page -le 5; $page++) {
  $out = if ($token) { az graph query -q $q --first 1000 --skip-token $token --output json | ConvertFrom-Json } else { az graph query -q $q --first 1000 --output json | ConvertFrom-Json }
  $rows += $out.data
  $token = $out.skip_token
  if (-not $token) { break }
}
$rows | ConvertTo-Json -Depth 64 | Out-File -Encoding utf8 network-resource-graph.json
```

**Portal, Resource Graph Explorer**: `https://portal.azure.com/#view/HubsExtension/ArgQueryBlade`, paste the same
query, **Run query**, then **Download as CSV**. The CSV has the same columns with JSON in the `tags`, `zones`, `sku` and
`properties` cells; the pane parses them.

**Portal, All resources** (`https://portal.azure.com/#view/HubsExtension/BrowseAll`, filter type to network resources,
**Export to CSV**) is accepted too, with the warning "no properties column": it carries names, types, groups and
locations only, so every rule that reads properties answers `unknown` and only the count-based rules run (a single
ExpressRoute circuit, no Bastion). That is the honest answer; use one of the two exports above to assess configuration.

Limits: 5 MB, 5,000 rows. Rows outside `microsoft.network/` are counted and ignored.

## 2. Upload and run

Drop the file on the pane (or choose it, or use the sample). The pane detects the format, shows the first five rows and
any warnings, asks you to complete the human verification, then **Run assessment**. The upload is processed in memory
and answered within seconds.

## 3. Read the summary

Tiles count the findings by severity and the rules the export could not answer; the topology line names the pattern
(hub-spoke, vWAN, mesh or isolated) with the hub and spoke VNet ids and the rationale, derived from peering flags and
gateway/firewall placement. Ingestion warnings (paged export, references to resources outside the export, unmapped
types) are listed under the tiles.

## 4. Work the findings

Filter by severity and category, or search by resource, rule or title. Open a finding to see the fact the export
carried and the field it came from (`export:<subscription>.<collection>[id=…].<field>`), the description, the
remediation, the traffic plane, the compliance references (marked for verification) and the reference link
(`learn.microsoft.com`, marked for verification until the owner confirms it), plus the resource's own detail: the
facts the rules read on it and the other findings that name it. The **Resources** tab lists every network row with its
findings.

## 5. Rules this export cannot answer, and what it cannot show

Rules that need Azure Monitor metrics, diagnostic settings, BGP state or cost are registered and reported, each with
the reason, never dropped. Beyond those, no Resource Graph export carries: utilisation and saturation; attacks in
progress; effective routes and effective NSG rules per network interface; private endpoint DNS resolution from inside
the VNet; Defender assessments; flow logs when the export has no `networkwatchers/flowlogs` rows; resources outside
`microsoft.network/` (VMs, NVAs by marketplace plan); resources the exporting identity could not read; subscriptions
not in the export.

## 6. Take the results with you, then delete them

**Download bundle** saves `assessment-<id>.zip` (`README.md`, `report.md`, `findings.json`, `topology.json`,
`summary.json`, `rules.json`, `NOT-FOR-PRODUCTION.md`). If a download cannot start inside the embedded pane, **Copy
report** puts the Markdown report on the clipboard and the report is shown in a selectable block. **Delete my data now**
removes the assessment immediately; otherwise it expires after two hours. This is not for production (see
`NOT-FOR-PRODUCTION.md`).

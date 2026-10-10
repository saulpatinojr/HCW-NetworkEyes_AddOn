"""Resource Graph export parsers: JSON (array or `az graph query` envelope) and CSV (Resource Graph Explorer, or the
portal "All resources" export accepted with the "no properties column" warning). Warnings cite row numbers and column
names only, never cell content."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any

from network_assessment.ingestion.arg_row import ArgRow, row_from_dict

DEFAULT_MAX_ROWS = 5_000
PAGED_WARNING = "export is paged (skip_token present); only the first page was uploaded"
NO_PROPERTIES_WARNING = "no properties column: rules that read properties answer unknown for this file"
FORMULA_LEADERS = ("=", "+", "-", "@", "\t", "\r")

HEADER_ALIASES: dict[str, str] = {
    "id": "id",
    "resourceid": "id",
    "name": "name",
    "type": "type",
    "resourcetype": "type",
    "location": "location",
    "region": "location",
    "resourcegroup": "resourceGroup",
    "resource group": "resourceGroup",
    "subscriptionid": "subscriptionId",
    "subscription": "subscriptionId",
    "subscription id": "subscriptionId",
    "tags": "tags",
    "properties": "properties",
    "sku": "sku",
    "kind": "kind",
    "zones": "zones",
}
JSON_COLUMNS = ("tags", "properties", "sku", "zones")

# The portal's "All resources" export writes display names in TYPE; the network ones are mapped to ARM types so the
# rows reach the right collections (and the rules that need properties answer unknown, honestly).
PORTAL_TYPE_NAMES: dict[str, str] = {
    "virtual network": "microsoft.network/virtualnetworks",
    "network security group": "microsoft.network/networksecuritygroups",
    "route table": "microsoft.network/routetables",
    "public ip address": "microsoft.network/publicipaddresses",
    "load balancer": "microsoft.network/loadbalancers",
    "virtual network gateway": "microsoft.network/virtualnetworkgateways",
    "local network gateway": "microsoft.network/localnetworkgateways",
    "connection": "microsoft.network/connections",
    "private endpoint": "microsoft.network/privateendpoints",
    "private dns zone": "microsoft.network/privatednszones",
    "nat gateway": "microsoft.network/natgateways",
    "bastion": "microsoft.network/bastionhosts",
    "firewall": "microsoft.network/azurefirewalls",
    "firewall policy": "microsoft.network/firewallpolicies",
    "application gateway": "microsoft.network/applicationgateways",
    "web application firewall policies (waf)": "microsoft.network/applicationgatewaywebapplicationfirewallpolicies",
    "front door waf policy": "microsoft.network/frontdoorwebapplicationfirewallpolicies",
    "expressroute circuit": "microsoft.network/expressroutecircuits",
    "virtual wan": "microsoft.network/virtualwans",
    "virtual hub": "microsoft.network/virtualhubs",
    "network watcher": "microsoft.network/networkwatchers",
    "network interface": "microsoft.network/networkinterfaces",
}

csv.field_size_limit(16 * 1024 * 1024)


class InvalidExport(ValueError):
    """The document is not a Resource Graph export (400 invalid_export). Message carries no cell content."""


class TooManyRows(ValueError):
    def __init__(self, count: int, max_rows: int) -> None:
        super().__init__(f"export has {count} rows; the limit is {max_rows}")
        self.count = count
        self.max_rows = max_rows


@dataclass
class ParsedRows:
    rows: list[ArgRow]
    warnings: list[str] = field(default_factory=list)
    has_properties: bool = True
    row_count: int = 0  # rows in the file before the network filter


def strip_bom(text: str) -> str:
    return text[1:] if text.startswith("﻿") else text


def neutralise_formula(value: str) -> str:
    """Prefix a leading formula character with a quote so spreadsheet clients treat the cell as text."""
    if value and value[0] in FORMULA_LEADERS:
        return "'" + value
    return value


def rows_from_document(document: Any) -> tuple[list[Any], list[str]]:
    """Accept a bare array or the `az graph query` envelope. Anything else is an invalid export."""
    warnings: list[str] = []
    if isinstance(document, list):
        return document, warnings
    if isinstance(document, dict):
        data = document.get("data")
        if isinstance(data, list):
            if document.get("skip_token") not in (None, ""):
                warnings.append(PAGED_WARNING)
            total = document.get("total_records")
            if isinstance(total, int) and total > len(data):
                warnings.append(f"export reports {total} records; {len(data)} were uploaded")
            return data, warnings
        raise InvalidExport("JSON object is not an az graph query envelope (no data array)")
    raise InvalidExport("JSON document is neither an array nor an az graph query envelope")


def _finish(raw_rows: list[Any], warnings: list[str], *, has_properties: bool, max_rows: int) -> ParsedRows:
    if len(raw_rows) > max_rows:
        raise TooManyRows(len(raw_rows), max_rows)
    rows: list[ArgRow] = []
    for index, raw in enumerate(raw_rows, start=1):
        if not isinstance(raw, dict):
            warnings.append(f"row {index}: not an object; skipped")
            continue
        row = row_from_dict(raw, index)
        if row is None:
            warnings.append(f"row {index}: missing type or id/name; skipped")
            continue
        rows.append(row)
    if not rows:
        raise InvalidExport("export contains no usable rows (every row lacks a type or an id/name)")
    if has_properties and not any(r.properties for r in rows):
        has_properties = False
    if not has_properties:
        warnings.insert(0, NO_PROPERTIES_WARNING)
    return ParsedRows(rows=rows, warnings=warnings, has_properties=has_properties, row_count=len(raw_rows))


def parse_document(document: Any, *, max_rows: int = DEFAULT_MAX_ROWS) -> ParsedRows:
    raw_rows, warnings = rows_from_document(document)
    return _finish(raw_rows, warnings, has_properties=True, max_rows=max_rows)


def parse_json(text: str, *, max_rows: int = DEFAULT_MAX_ROWS) -> ParsedRows:
    text = strip_bom(text)
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidExport(f"invalid JSON at line {exc.lineno}, column {exc.colno}") from None
    return parse_document(document, max_rows=max_rows)


def _sniff_delimiter(sample: str) -> str:
    first_line = sample.splitlines()[0] if sample else ""
    counts = {d: first_line.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=counts.get)  # type: ignore[arg-type]
    return best if counts[best] > 0 else ","


def _parse_json_cell(value: str, column: str, index: int, warnings: list[str]) -> Any:
    if value is None or value.strip() == "":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        warnings.append(f"row {index}: column {column} is not valid JSON; treated as empty")
        return None


def parse_csv(text: str, *, max_rows: int = DEFAULT_MAX_ROWS) -> ParsedRows:
    text = strip_bom(text)
    if "\x00" in text:
        raise InvalidExport("file looks binary")
    delimiter = _sniff_delimiter(text[:4096])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        raise InvalidExport("CSV is empty") from None
    columns = [HEADER_ALIASES.get(h.strip().strip('"').lower()) for h in header]
    if "type" not in columns:
        raise InvalidExport("CSV has no TYPE column")
    has_properties = "properties" in columns
    warnings: list[str] = []
    raw_rows: list[dict[str, Any]] = []
    for index, record in enumerate(reader, start=1):
        if not any(cell.strip() for cell in record):
            continue
        if len(raw_rows) >= max_rows:
            raise TooManyRows(len(raw_rows) + 1, max_rows)
        row: dict[str, Any] = {}
        for column, raw in zip(columns, record, strict=False):
            if column is None:
                continue
            if column in JSON_COLUMNS:
                row[column] = _parse_json_cell(raw, column, index, warnings)
            else:
                row[column] = neutralise_formula(raw.strip())
        if not has_properties:
            rtype = str(row.get("type", "")).strip().lower()
            row["type"] = PORTAL_TYPE_NAMES.get(rtype, rtype)
        raw_rows.append(row)
    if not raw_rows:
        raise InvalidExport("CSV has a header and no rows")
    return _finish(raw_rows, warnings, has_properties=has_properties, max_rows=max_rows)

import json

import pytest

from network_assessment.ingestion import InvalidExport, TooManyRows, parse_csv, parse_document, parse_json, strip_bom
from network_assessment.ingestion.arg_row import row_from_dict
from network_assessment.ingestion.parse import NO_PROPERTIES_WARNING, PAGED_WARNING, neutralise_formula

from ..conftest import SAMPLE_CSV, SAMPLE_JSON, SAMPLE_PORTAL_CSV, SUB_HUB


def test_json_array_and_envelope_and_bom(sample_rows):
    parsed = parse_json("﻿" + json.dumps(sample_rows))
    assert len(parsed.rows) == 48 and parsed.warnings == [] and parsed.has_properties and parsed.row_count == 48
    parsed = parse_json(SAMPLE_JSON.read_text(encoding="utf-8"))
    assert len(parsed.rows) == 48 and parsed.rows[0].type == "microsoft.network/virtualnetworks"
    paged = parse_document({"count": 1, "data": sample_rows[:1], "skip_token": "abc", "total_records": 9})
    assert paged.warnings[0] == PAGED_WARNING and paged.warnings[1].startswith("export reports 9 records")
    assert strip_bom("x") == "x"


def test_invalid_exports():
    with pytest.raises(InvalidExport, match="invalid JSON"):
        parse_json("[{")
    with pytest.raises(InvalidExport, match="envelope"):
        parse_document({"nope": 1})
    with pytest.raises(InvalidExport, match="neither"):
        parse_document("text")
    with pytest.raises(InvalidExport, match="no usable rows"):
        parse_document([{"name": "x"}, 5])
    with pytest.raises(TooManyRows) as exc:
        parse_document([{"type": "a", "name": "n"}] * 3, max_rows=2)
    assert (exc.value.count, exc.value.max_rows) == (3, 2)


def test_rows_skipped_with_row_numbers_only():
    parsed = parse_document(
        [
            {"type": "microsoft.network/virtualnetworks", "id": "/subscriptions/x/resourceGroups/rg/providers/p/v"},
            "junk",
            {"name": "no-type"},
        ]
    )
    assert len(parsed.rows) == 1 and not parsed.has_properties
    assert parsed.warnings == [
        NO_PROPERTIES_WARNING,
        "row 2: not an object; skipped",
        "row 3: missing type or id/name; skipped",
    ]


def test_row_from_dict_derives_ids_and_lowercases_type():
    row = row_from_dict(
        {
            "type": "Microsoft.Network/VirtualNetworks",
            "id": f"/subscriptions/{SUB_HUB}/resourceGroups/RG/providers/x/y",
        },
        1,
    )
    assert row.type == "microsoft.network/virtualnetworks" and row.short_type == "virtualnetworks"
    assert row.subscription_id == SUB_HUB and row.resource_group == "RG" and row.name == "y"
    synthetic = row_from_dict({"type": "a/b", "name": "n", "zones": ["1"], "sku": "notadict", "properties": [1]}, 2)
    assert synthetic.id == "/subscriptions/unknown/resourceGroups/unknown/providers/a/b/n" and synthetic.zones == ["1"]
    assert synthetic.sku == {} and synthetic.properties == {}
    assert row_from_dict({"type": "a/b"}, 3) is None and row_from_dict({"id": "/x"}, 4) is None
    sub_only = row_from_dict({"type": "a/b", "id": f"/subscriptions/{SUB_HUB}/providers/a/b/n"}, 5)
    assert sub_only.subscription_id == SUB_HUB and sub_only.resource_group is None


def test_csv_with_json_cells_matches_json(sample_rows):
    parsed = parse_csv(SAMPLE_CSV.read_text(encoding="utf-8"))
    assert len(parsed.rows) == 48 and parsed.has_properties and parsed.warnings == []
    by_id = {r.id: r for r in parsed.rows}
    original = next(r for r in sample_rows if r["type"] == "microsoft.network/azurefirewalls")
    assert by_id[original["id"]].properties == original["properties"] and by_id[original["id"]].sku == {}
    pip = next(r for r in sample_rows if r["sku"])
    assert by_id[pip["id"]].sku == pip["sku"] and by_id[pip["id"]].zones == (pip["zones"] or [])


def test_portal_all_resources_csv_is_accepted_with_the_warning():
    parsed = parse_csv(SAMPLE_PORTAL_CSV.read_text(encoding="utf-8"))
    assert not parsed.has_properties and parsed.warnings[0] == NO_PROPERTIES_WARNING
    types = {r.type for r in parsed.rows}
    assert "microsoft.network/virtualnetworks" in types and "microsoft.network/azurefirewalls" in types
    assert all(r.properties == {} for r in parsed.rows)


def test_csv_edge_cases():
    with pytest.raises(InvalidExport, match="binary"):
        parse_csv("a,b\n\x00")
    with pytest.raises(InvalidExport, match="empty"):
        parse_csv("")
    with pytest.raises(InvalidExport, match="no TYPE"):
        parse_csv("name,location\nx,y\n")
    with pytest.raises(InvalidExport, match="no rows"):
        parse_csv("name,type\n")
    with pytest.raises(TooManyRows):
        parse_csv("type;name\na/b;x\na/b;y\n", max_rows=1)
    parsed = parse_csv("TYPE\tNAME\tPROPERTIES\na/b\t=cmd\t{bad json\n")
    assert (
        parsed.rows[0].name == "'=cmd"
        and parsed.warnings[-1] == "row 1: column properties is not valid JSON; treated as empty"
    )
    assert neutralise_formula("+1") == "'+1" and neutralise_formula("ok") == "ok"

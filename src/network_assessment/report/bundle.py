"""The output bundle: seven files, zipped with STORE (no compression; the content is small and textual)."""

from __future__ import annotations

import io
import json
import zipfile

from network_assessment.engine import rules_table
from network_assessment.report.markdown import NOT_FOR_PRODUCTION, render_markdown
from network_assessment.report.summary import Assessment

BUNDLE_FILES = (
    "README.md",
    "report.md",
    "findings.json",
    "topology.json",
    "summary.json",
    "rules.json",
    "NOT-FOR-PRODUCTION.md",
)

README = """# Network assessment bundle

| File | Content |
|---|---|
| `report.md` | The report: scope, summary, topology, findings by severity, the rules this export cannot answer |
| `findings.json` | `findings[]` and `unknowns[]` exactly as the API returned them |
| `topology.json` | The normalised topology model the rules ran over (model version inside) |
| `summary.json` | The summary document (counts, topology pattern, versions, warnings) |
| `rules.json` | The rule registry at the time of the assessment (ids, versions, severities, evidence, learn links) |
| `NOT-FOR-PRODUCTION.md` | What this assessment is and is not |

Produced by the Hybrid Cloud Works Network Assessment lab edition from an export you uploaded; returned only to the
holder of the owner token and never written to disk on the server.
"""


def _json(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False, default=str) + "\n").encode("utf-8")


def make_bundle(assessment: Assessment, topology_document: dict) -> dict[str, bytes]:
    doc = assessment.document()
    return {
        "README.md": README.encode("utf-8"),
        "report.md": render_markdown(assessment).encode("utf-8"),
        "findings.json": _json({"findings": doc["findings"], "unknowns": doc["unknowns"]}),
        "topology.json": _json(topology_document),
        "summary.json": _json(doc["summary"]),
        "rules.json": _json({"rulesVersion": assessment.rules_version, "rules": rules_table()}),
        "NOT-FOR-PRODUCTION.md": NOT_FOR_PRODUCTION.encode("utf-8"),
    }


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zf:
        for name in sorted(files):
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError("bundle paths must be relative and without '..'")
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, files[name])
    return buffer.getvalue()

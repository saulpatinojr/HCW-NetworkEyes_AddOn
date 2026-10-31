"""Export parsers (lab-edition code).

The normalizer the API runs is the active engine's (`network_assessment.engine.normalize`). This edition's own
`ingestion/normalize.py` is the one the interim port runs, and the reference the wheel's normalizer was ported from.
"""

from network_assessment.ingestion.arg_row import ArgRow
from network_assessment.ingestion.parse import (
    InvalidExport,
    ParsedRows,
    TooManyRows,
    parse_csv,
    parse_document,
    parse_json,
    strip_bom,
)

__all__ = [
    "ArgRow",
    "InvalidExport",
    "ParsedRows",
    "TooManyRows",
    "parse_csv",
    "parse_document",
    "parse_json",
    "strip_bom",
]

"""Three-file market data source loader.

Authoritative input files:
  - DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx
  - medicines-output-medicines-report_en (1).xlsx
  - tk_lista.csv

Generated artifact:
  datas/static/market_source.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARKET_JSON = ROOT / "datas" / "static" / "market_source.json"


def load_market_rows() -> list[dict[str, Any]]:
    """Load synthesized rows used by the Hungary (NEAK/OGYÉI) static pipeline.

    Returns empty list when artifact does not exist or is invalid.
    """
    if not MARKET_JSON.is_file():
        return []
    try:
        payload = json.loads(MARKET_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = payload.get("rows")
    return rows if isinstance(rows, list) else []


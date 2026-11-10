"""Chinese display text for reviewed summaries, read from data/translations.zh-CN.json."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "data/translations.zh-CN.json"


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8")) if PATH.is_file() else {}


def zh_summary(record) -> str:
    """The record's Chinese summary; a record without an entry shows its English summary."""
    entry = table().get(record["id"])
    return entry["summary"] if entry else record.get("summary_zh") or record.get("summary") or ""

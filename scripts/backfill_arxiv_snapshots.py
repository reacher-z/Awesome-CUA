#!/usr/bin/env python3
"""Backfill arXiv snapshots from original cached receipts, without network access.

The default is a dry run. ``--write`` replaces the input atomically only after
every record and every original arxiv_api receipt has passed validation.
Existing bibliography, editorial decisions, and receipts are never regenerated.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Callable
import xml.etree.ElementTree as ET

import catalog
from arxiv_metadata import ATOM, entry_snapshot
from publication_metadata import authors_omitted

SNAPSHOT_PATH = "details.arxiv_snapshot"
BodyLoader = Callable[[str], bytes]


class BackfillError(ValueError):
    """The whole migration is blocked; no prepared records may be written."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("arXiv snapshot backfill blocked:\n" + "\n".join(self.errors))


@dataclass
class BackfillResult:
    records: list[dict]
    changed_records: int
    snapshots_added: int
    receipts_updated: int
    feeds_parsed: int
    written: bool = False

    def summary(self):
        return {
            "records": len(self.records),
            "changed_records": self.changed_records,
            "snapshots_added": self.snapshots_added,
            "receipts_updated": self.receipts_updated,
            "feeds_parsed": self.feeds_parsed,
            "written": self.written,
        }


def _text(element, name):
    return " ".join(element.findtext(ATOM + name, "").split())


class _OriginalFeeds:
    def __init__(self, load_body):
        self.load_body = load_body
        self.entries = {}
        self.failures = {}

    def get(self, receipt):
        url, digest = receipt.get("url"), receipt.get("sha256")
        if not isinstance(url, str) or not url:
            raise ValueError("arxiv_api receipt has no URL")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("arxiv_api receipt has no valid SHA-256")
        key = (url, digest)
        if key in self.failures:
            raise ValueError(self.failures[key])
        if key not in self.entries:
            try:
                body = self.load_body(url)
                if not body:
                    raise ValueError("original cached response is missing")
                if hashlib.sha256(body).hexdigest() != digest:
                    raise ValueError("cached response SHA-256 does not match original receipt")
                root = ET.fromstring(body)
                if root.tag != ATOM + "feed":
                    raise ValueError("cached response is not an Atom feed")
                indexed = {}
                for entry in root.findall(ATOM + "entry"):
                    identity = catalog.canonical(_text(entry, "id"))
                    if identity and identity[2] == "arxiv":
                        indexed.setdefault(identity[0], []).append(entry)
                self.entries[key] = indexed
            except (OSError, TypeError, ValueError, ET.ParseError) as error:
                message = f"{url}: {error}"
                self.failures[key] = message
                raise ValueError(message) from error
        return self.entries[key]


def _matching_snapshot(record, receipt, feeds):
    candidates = feeds.get(receipt).get(record["id"], [])
    if len(candidates) != 1:
        raise ValueError(
            f"original feed has {len(candidates)} matching entries for {record['id']}; expected one"
        )
    entry = candidates[0]
    facts = {
        "name": _text(entry, "title"),
        "authors": [_text(author, "name") for author in entry.findall(ATOM + "author")],
        # These are the exact date fields retained by catalog.arxiv_entry.
        "published_at": _text(entry, "published")[:10] or None,
        "updated_at": _text(entry, "updated")[:10] or None,
    }
    for field, observed in facts.items():
        if field == "authors" and authors_omitted(record) and observed:
            continue  # The catalog lists no authors for this record; the original entry still names some.
        if not observed or record.get(field) != observed:
            raise ValueError(f"original entry {field} does not match retained record")
    if any(not name for name in facts["authors"]):
        raise ValueError("original entry has an empty author name")
    aid = record["id"].split(":", 1)[1]
    snapshot = entry_snapshot(entry, aid)
    if any(snapshot.get(field) is None for field in (
        "version", "versioned_url", "submitted_at", "updated_at", "abstract_sha256"
    )):
        raise ValueError("original entry lacks a complete version, timestamp, or abstract snapshot")
    return snapshot


def prepare_backfill(records, load_body: BodyLoader | None = None):
    """Validate all input records and return independent, minimally amended copies.

    ``load_body`` defaults to the local-only catalog.cached_body. All arxiv_api
    receipts must match, including when a record already has a snapshot. Multiple
    original receipts must agree on the complete snapshot; none is silently chosen
    over a conflicting or unavailable receipt.
    """
    feeds = _OriginalFeeds(load_body if load_body is not None else catalog.cached_body)
    prepared, errors, seen = [], [], set()
    changed = added = support_updates = 0
    for position, record in enumerate(records, 1):
        rid = record.get("id") if isinstance(record, dict) else None
        label = rid or f"record {position}"
        try:
            if not isinstance(rid, str) or not re.fullmatch(r"arxiv:\d{4}\.\d{4,5}", rid):
                raise ValueError("record has no canonical arXiv ID")
            if rid in seen:
                raise ValueError("duplicate record ID; refusing to deduplicate the archive")
            seen.add(rid)
            identifiers = record.get("identifiers")
            if not isinstance(identifiers, dict) or identifiers.get("arxiv") != rid.split(":", 1)[1]:
                raise ValueError("identifiers.arxiv does not match record ID")
            details = record.get("details", {})
            if not isinstance(details, dict):
                raise ValueError("details must be an object when present")
            evidence = record.get("evidence")
            if not isinstance(evidence, list) or any(not isinstance(e, dict) for e in evidence):
                raise ValueError("evidence must be a list of receipt objects")
            receipt_indices = [i for i, e in enumerate(evidence) if e.get("method") == "arxiv_api"]
            if not receipt_indices:
                raise ValueError("record has no original arxiv_api receipt")

            snapshot = None
            for i in receipt_indices:
                receipt = evidence[i]
                supports = receipt.get("supports", [])
                if not isinstance(supports, list) or any(not isinstance(s, str) for s in supports):
                    raise ValueError("arxiv_api receipt supports must be a list of strings")
                observed = _matching_snapshot(record, receipt, feeds)
                if snapshot is not None and observed != snapshot:
                    raise ValueError("original arxiv_api receipts disagree on snapshot")
                snapshot = observed

            if "arxiv_snapshot" in details and details["arxiv_snapshot"] != snapshot:
                raise ValueError("existing arxiv_snapshot differs from original evidence; refusing to overwrite")
            result = copy.deepcopy(record)
            if "arxiv_snapshot" not in details:
                result.setdefault("details", {})["arxiv_snapshot"] = snapshot
                added += 1
            for i in receipt_indices:
                supports = result["evidence"][i].setdefault("supports", [])
                if SNAPSHOT_PATH not in supports:
                    supports.append(SNAPSHOT_PATH)
                    support_updates += 1
            changed += result != record
            prepared.append(result)
        except (TypeError, ValueError) as error:
            errors.append(f"{label}: {error}")
    if errors:
        raise BackfillError(errors)
    return BackfillResult(prepared, changed, added, support_updates, len(feeds.entries))


def _atomic_replace(path, payload, original):
    """Replace only the unchanged input, using a flushed same-directory temporary."""
    temporary = None
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), mode)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != original:
            raise BackfillError(["input file changed during validation; refusing to replace it"])
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def backfill_file(path, *, write=False, load_body: BodyLoader | None = None):
    """Prepare a whole JSONL file; optionally commit the validated plan atomically."""
    path = Path(path)
    if path.is_symlink():
        raise BackfillError(["input must be a regular file, not a symbolic link"])
    original = path.read_bytes()
    records = []
    try:
        for line_number, line in enumerate(original.decode("utf-8").splitlines(), 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise BackfillError([f"invalid JSON on line {line_number}: {error.msg}"]) from error
    except UnicodeDecodeError as error:
        raise BackfillError(["input is not UTF-8 JSONL"]) from error
    result = prepare_backfill(records, load_body=load_body)
    if write and result.changed_records:
        # Keep input record order and count. Do not use write_jsonl, which sorts.
        payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                          for row in result.records).encode("utf-8")
        _atomic_replace(path, payload, original)
        result.written = True
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--papers", type=Path, default=catalog.DATA / "papers.jsonl",
                        help="JSONL archive to audit (default: data/papers.jsonl)")
    parser.add_argument("--write", action="store_true",
                        help="atomically write only after every original receipt passes")
    args = parser.parse_args(argv)
    try:
        result = backfill_file(args.papers, write=args.write)
    except (BackfillError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({"mode": "write" if args.write else "dry-run", **result.summary()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

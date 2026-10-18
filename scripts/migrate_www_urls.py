#!/usr/bin/env python3
"""Plan/apply the offline leading-www migration; never fetch or reapprove content."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
from pathlib import Path

from catalog import DATA, atomic_write, canonical
from url_identity import url_aliases, www_declaration, candidate_identity_errors


def unique(rows, label, identity=lambda row: row["id"]):
    """Coalesce only equivalent rows; differing input facts require a review."""
    result, owners = [], {}
    for row in rows:
        key = identity(row)
        if key in owners:
            if owners[key] != row:
                raise ValueError(f"{label}: conflicting rows would merge into {key}")
            continue
        owners[key] = row
        result.append(row)
    return result


def plan(data_dir=DATA):
    """Validate every transformation before returning any bytes to write."""
    directory = Path(data_dir)
    originals = {}

    def read(name, default=None):
        path = directory / name
        raw = path.read_bytes() if path.exists() else None
        originals[name] = raw
        if raw is None:
            return copy.deepcopy([] if default is None else default)
        if name.endswith(".jsonl"):
            return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        return json.loads(raw)

    editorial = read("editorial.json")
    candidates = read("candidates.jsonl")
    records = read("catalog.jsonl")
    declarations = read("url-aliases.json")
    url_aliases(declarations, canonical)
    declared = {row["alias_id"]: row for row in declarations}
    for row in [*editorial, *candidates, *records]:
        entry = www_declaration(row.get("url"), canonical)
        if entry:
            previous = declared.setdefault(entry["alias_id"], entry)
            if previous != entry:
                raise ValueError("Conflicting URL normalization declarations")
    declarations = sorted(declared.values(), key=lambda row: row["alias_id"])
    mapping = url_aliases(declarations, canonical)
    outputs = {"url-aliases.json": declarations}

    def remap(identity):
        return mapping.get(identity, identity)

    def clean_reference(url):
        return canonical(url)[1] if www_declaration(url, canonical) else url

    updated = copy.deepcopy(editorial)
    for row in updated:
        for key in ("id", "publisher_id"):
            if key in row:
                row[key] = remap(row[key])
        for key in ("component_of", "family_url"):
            if key in row:
                row[key] = clean_reference(row[key])
        for relation in row.get("reviewed_relations", []):
            relation["target_id"] = remap(relation["target_id"])
    # Primary editorial URLs/approvals are retained verbatim. Only identity
    # fields and semantic references move; source receipts still cite www.
    outputs["editorial.json"] = unique(
        updated, "Editorial", lambda row: row.get("id") or canonical(row["url"], allow_doi=row.get("kind") in {"paper", "survey"})[0])

    for name in ("primary-evidence.jsonl", "enrichment.jsonl"):
        rows = read(name)
        updated = copy.deepcopy(rows)
        for row in updated:
            row["id"] = remap(row["id"])
            if name == "enrichment.jsonl":
                for reference in row.get("references", []):
                    reference["target_id"] = remap(reference["target_id"])
        outputs[name] = unique(updated, name)

    merged = {}
    for original in candidates:
        row = copy.deepcopy(original)
        declaration = www_declaration(row["url"], canonical)
        target = remap(row["id"])
        if declaration:
            if row["id"] not in {declaration["alias_id"], declaration["target_id"]}:
                raise ValueError("Candidate URL does not match its stored ID: " + row["id"])
            target = declaration["target_id"]
        if target != row["id"] or declaration:
            parsed = canonical(row["url"])
            if not parsed or parsed[0] != target:
                raise ValueError("Candidate migration has a mismatched URL: " + row["id"])
            row.update(id=target, url=parsed[1])
        if target not in merged:
            merged[target] = row
            continue
        previous = merged[target]
        flexible = {"first_discovered_at", "discovered_in"}
        if ({k: v for k, v in previous.items() if k not in flexible}
                != {k: v for k, v in row.items() if k not in flexible}):
            raise ValueError("Conflicting candidate facts for " + target)
        previous["first_discovered_at"] = min(
            (previous["first_discovered_at"], row["first_discovered_at"]),
            key=lambda value: dt.datetime.fromisoformat(value.replace("Z", "+00:00")))
        for occurrence in row["discovered_in"]:
            if occurrence not in previous["discovered_in"]:
                previous["discovered_in"].append(occurrence)
    outputs["candidates.jsonl"] = list(merged.values())
    if errors := candidate_identity_errors(outputs["candidates.jsonl"], canonical):
        raise ValueError("\n".join(errors))

    reviews = read("candidate-reviews.json")
    updated = []
    for original in reviews:
        row = copy.deepcopy(original)
        for key in ("id", "target_id"):
            if key in row:
                row[key] = remap(row[key])
        for key in ("url", "url_prefix"):
            if key in row:
                row[key] = clean_reference(row[key])
        # The curated resource now has the same ID: no separate alias candidate
        # remains to set aside. Its original decision stays in git history.
        if row.get("decision") == "alias" and row["id"] == row["target_id"]:
            continue
        updated.append(row)
    outputs["candidate-reviews.json"] = unique(
        updated, "Candidate reviews", lambda row: row.get("id") or row["url_prefix"])

    # These retained inputs have no affected IDs in this migration's reviewed
    # snapshot. Refuse an unexpected dependency instead of changing fingerprints,
    # observations or review evidence by an indiscriminate recursive replacement.
    def old_identity(value):
        if isinstance(value, str):
            return value in mapping
        if isinstance(value, dict):
            return any(old_identity(v) for v in value.values())
        if isinstance(value, list):
            return any(old_identity(v) for v in value)
        return False

    for name in ("exclusions.json", "publications.jsonl", "metadata-updates.jsonl", "repository-aliases.json"):
        if old_identity(read(name)):
            raise ValueError(f"{name}: affected retained identity needs an explicit reviewed migration")

    changes = {}
    for name, rows in outputs.items():
        if name.endswith(".jsonl"):
            content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                              for row in sorted(rows, key=lambda row: row["id"]))
        else:
            content = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
        data = content.encode("utf-8")
        if originals.get(name) != data:
            changes[name] = data
    report = {"aliases": len(mapping), "candidate_rows_before": len(candidates),
              "candidate_rows_after": len(merged),
              "removed_redundant_candidate_reviews": len(reviews) - len(outputs["candidate-reviews.json"]),
              "changed_files": list(changes)}
    return changes, originals, report


def migrate(data_dir=DATA, *, write=False):
    directory = Path(data_dir)
    changes, originals, report = plan(directory)
    if write:
        # Check the whole read set before starting. The alias ledger is written
        # first, so an interrupted per-file atomic migration can be run again.
        for name, expected in originals.items():
            path = directory / name
            current = path.read_bytes() if path.exists() else None
            if current != expected:
                raise ValueError("Input changed while planning: " + name)
        for name, data in changes.items():
            atomic_write(directory / name, data)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="apply the validated plan; default is read-only")
    parser.add_argument("--data-dir", type=Path, default=DATA)
    args = parser.parse_args()
    print(json.dumps(migrate(args.data_dir, write=args.write), indent=2))


if __name__ == "__main__":
    main()

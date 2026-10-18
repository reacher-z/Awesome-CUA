"""Recorded URL normalization migrations, separate from repository observations.

These aliases prove a deterministic catalog policy, not an HTTP redirect,
common ownership, or renewed review of the linked content.
"""
from __future__ import annotations

import copy
import hashlib
import html
import re
import urllib.parse

POLICY = "leading-www-v1"
FIELDS = {"alias_id", "target_id", "url", "policy"}


def www_declaration(url, canonical):
    """Recover the former generic URL hash from its normalized www address."""
    if not isinstance(url, str):
        return None
    try:
        host = urllib.parse.urlsplit(html.unescape(url).strip()).hostname or ""
    except ValueError:
        return None
    host = host.lower()
    current = canonical(url)
    if not host.startswith("www.") or not current or current[2] != "url":
        return None
    parts = urllib.parse.urlsplit(current[1])
    if parts.hostname != re.sub(r"^(?:www\.)+", "", host):
        return None
    former_url = urllib.parse.urlunsplit(("https", host, parts.path, parts.query, ""))
    alias = "url:" + hashlib.sha256(former_url.encode()).hexdigest()[:20]
    if alias == current[0]:
        return None
    return {"alias_id": alias, "target_id": current[0],
            "url": former_url, "policy": POLICY}


def url_aliases(declarations, canonical, records=None):
    """Validate direct policy mappings; an unindexed target remains unindexed."""
    if not isinstance(declarations, list):
        raise ValueError("URL aliases must be a list")
    result = {}
    for entry in declarations:
        if (not isinstance(entry, dict) or set(entry) != FIELDS
                or entry.get("policy") != POLICY
                or www_declaration(entry.get("url"), canonical) != entry):
            raise ValueError("URL alias must match its former URL hash and leading-www policy")
        alias, target = entry["alias_id"], entry["target_id"]
        if alias in result:
            raise ValueError("Duplicate former URL ID: " + alias)
        result[alias] = target
    if set(result) & set(result.values()):
        raise ValueError("URL aliases must resolve directly; chains and cycles are not allowed")
    if records is not None:
        owners = {row["id"]: row for row in records}
        if len(owners) != len(records):
            raise ValueError("Duplicate catalog IDs while resolving URL aliases")
        for alias, target in result.items():
            if alias in owners:
                raise ValueError("Former URL ID is still an active resource: " + alias)
            if target in owners:
                identity = canonical(owners[target]["url"])
                if not identity or identity[0] != target:
                    raise ValueError("URL alias target has a different canonical URL: " + target)
    return result


def attach_url_aliases(records, declarations, canonical):
    """Expose retained former IDs/URLs without adding source-evidence claims."""
    url_aliases(declarations, canonical, records)
    result = copy.deepcopy(records)
    owners = {row["id"]: row for row in result}
    for entry in declarations:
        if entry["target_id"] not in owners:
            continue
        aliases = owners[entry["target_id"]]["aliases"]
        for value in (entry["alias_id"], entry["url"]):
            if value not in aliases:
                aliases.append(value)
    return result


def www_duplicate_errors(rows, label):
    """Detect www-only URL duplicates without merging explicit asset identities."""
    groups = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("id", "")).startswith("url:"):
            continue
        try:
            parts = urllib.parse.urlsplit(row.get("url", ""))
        except (ValueError, TypeError):
            continue
        host = (parts.hostname or "").lower()
        key = (re.sub(r"^(?:www\.)+", "", host), parts.path.rstrip("/"), parts.query)
        groups.setdefault(key, []).append((row["id"], host.startswith("www.")))
    return [f"{label}: www URL duplicates: " + ", ".join(rid for rid, _ in entries)
            for entries in groups.values()
            if len(entries) > 1 and any(was_www for _, was_www in entries)]


def candidate_identity_errors(rows, canonical):
    errors = www_duplicate_errors(rows, "Candidates")
    seen = set()
    for row in rows:
        identity = row["id"]
        if identity in seen:
            errors.append("Duplicate candidate ID: " + identity)
        seen.add(identity)
        parsed = canonical(row["url"])
        if identity.startswith("url:") and parsed and parsed[0] != identity:
            errors.append("Candidate ID differs from its canonical URL: " + identity)
    return errors

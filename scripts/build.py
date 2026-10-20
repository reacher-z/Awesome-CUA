"""Offline materialized views, quality gates, and search for the CUA catalog."""
from __future__ import annotations

import collections
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import urllib.parse

from catalog import ROOT, DATA, KINDS, ENVIRONMENTS, STATUSES, TOPICS, atomic_write, canonical, editorial_identity, publication_identity, read_json, read_jsonl, write_json, write_jsonl
from specifications import PREFIXES, PROFILE_KEYS, validate_profiles
from scope_review import resolve_exclusions, scope_report
from arxiv_metadata import validate_snapshot
from repository_identity import repository_aliases, attach_repository_aliases, unrecorded_hub_renames
from lookup import REVIEWED_RELATION_TYPES
from publication_metadata import (alias_owner_errors, attach_publications, duplicate_publication_errors, publication_aliases,
    publication_links, publication_search_text, record_date_text, record_year, validate_publication)


def source_aliases(rows=None):
    aliases = publication_aliases(read_jsonl(DATA/'publications.jsonl'), publication_identity)
    repositories = repository_aliases(read_json(DATA/'repository-aliases.json', []), rows)
    if any(key in aliases and aliases[key] != value for key, value in repositories.items()):
        raise ValueError('Source identity aliases have conflicting owners')
    return {**aliases, **repositories}


def apply_license_reviews(editorial, primary, licenses, details):
    reviews=editorial.get('reviewed_licenses', {})
    if not isinstance(reviews, dict) or set(reviews)-set(licenses):
        raise ValueError('Invalid reviewed license scopes: '+editorial['name'])
    receipts=[primary,*editorial.get('additional_evidence',[])]
    for slot,decision in reviews.items():
        if not isinstance(decision,dict) or set(decision)!={'value','reason','evidence_urls'}:
            raise ValueError('License review needs value, reason, and evidence URLs: '+editorial['name'])
        if not isinstance(decision['reason'],str) or not decision['reason'].strip() or not decision['evidence_urls']:
            raise ValueError('License review lacks an explanation or evidence: '+editorial['name'])
        for url in decision['evidence_urls']:
            if not any(r['url']==url and ('licenses' in r['supports'] or 'licenses.'+slot in r['supports']) for r in receipts):
                raise ValueError('License review lacks a supporting receipt: '+url)
        value=decision['value']
        if value is not None and (not isinstance(value,dict) or value.get('url') not in decision['evidence_urls']):
            raise ValueError('Reviewed license must cite its retained evidence: '+editorial['name'])
        licenses[slot]=copy.deepcopy(value)
    if reviews:
        details['license_review']={slot:{k:copy.deepcopy(v) for k,v in decision.items() if k!='value'} for slot,decision in reviews.items()}


def source_records(with_scope=False):
    archived = read_jsonl(DATA / "papers.jsonl")
    if len({r['id'] for r in archived}) != len(archived):
        raise ValueError('Duplicate arXiv archive identifier')
    if any(not row['id'].startswith('arxiv:') for row in archived):
        raise ValueError('papers.jsonl is the arXiv archive; publisher facts belong in publications.jsonl')
    if any('publication' in row.get('details',{}) for row in archived):
        raise ValueError('Publisher observations must not be written into the retained arXiv archive')
    observations=read_jsonl(DATA/'publications.jsonl')
    records = attach_publications({r['id']: r for r in archived}, observations, publication_identity)
    aliases=publication_aliases(observations,publication_identity)
    evidence = {r["id"]: r for r in read_jsonl(DATA / "primary-evidence.jsonl")}
    enrichment = {r["id"]: r for r in read_jsonl(DATA / "enrichment.jsonl")}
    pending = []
    for row in records.values():
        bibliography = {key: copy.deepcopy(value) for key,value in row.get('details', {}).items()
                        if key in {'arxiv_snapshot','publication'}}
        row.update(scope="relevance_pending", details=bibliography)
    for editorial in read_json(DATA / "editorial.json", []):
        if 'publication' in editorial.get('details', {}):
            raise ValueError('Publisher bibliographic facts belong in publications.jsonl, separately from editorial relevance approval')
        parsed = editorial_identity(editorial)
        if not parsed:
            raise ValueError(f"Invalid editorial URL: {editorial['url']}")
        rid = editorial.get("id", parsed[0])
        if aliases.get(parsed[0],rid)!=rid:
            raise ValueError('Editorial URL belongs to canonical publication resource '+aliases[parsed[0]]+'; do not create '+rid)
        if editorial.get('kind') in {'paper','survey'} and (rid not in records or parsed[0]!=rid):
            raise ValueError('Paper editorial entry requires its retained canonical bibliography identity: '+rid)
        ev = evidence.get(rid)
        if not editorial.get("editorial_reviewed") or not ev or not ev.get("content_matched") or editorial.get("reviewed_sha256") != ev.get("sha256"):
            reason, cause = editorial.get("review_note", "editorial review pending"), "reviewer_hold"
            if not ev or not ev.get("content_matched"):
                # A failed fetch has no snapshot for the note to go stale against, so the reviewer's decision stays visible.
                reason, cause = "primary evidence unresolved: " + (ev or {}).get("error", "content mismatch") + ("; " + editorial["review_note"] if editorial.get("review_note") else ""), "unresolved_evidence"
            elif editorial.get("reviewed_sha256") != ev.get("sha256"):
                reason, cause = "current source snapshot needs editorial review", "unreviewed_snapshot"
            pending.append({"id": rid, "name": editorial["name"], "url": editorial["url"], "reason": reason, "cause": cause})
            continue
        base = records.get(rid, {})
        extra = enrichment.get(rid, {})
        if extra.get("evidence_sha256") != ev["sha256"]:
            extra = {}
        licenses = {"code": None, "data": None, "weights": None, "document": None}
        licenses.update(extra.get("licenses", {}))
        details = copy.deepcopy(base.get('details', {}))
        details.update(copy.deepcopy(editorial.get("details", {})))
        details.update(extra.get("details", {}))
        relations = copy.deepcopy(editorial.get('reviewed_relations', []))
        for aid in editorial.get("paper_ids", []):
            target = "arxiv:" + aid
            relations.append({"type": "introduced_by", "target_id": target, "evidence_url": ev["url"]})
        for aid in editorial.get("documented_by", []):
            relations.append({"type": "documented_by", "target_id": "arxiv:" + aid, "evidence_url": ev["url"]})
        if editorial.get("publisher_id"):
            relations.append({"type": "published_by", "target_id": editorial["publisher_id"], "evidence_url": ev["url"]})
        if editorial.get("component_of"):
            relations.append({"type": "component_of", "target_id": canonical(editorial["component_of"])[0], "evidence_url": ev["url"]})
        if editorial.get("family_url"):
            relations.append({"type": "variant_of", "target_id": canonical(editorial["family_url"])[0], "evidence_url": ev["url"]})
        primary = {"role": "primary", "method": "editorial_primary_review", "supports": editorial.get("primary_supports", ["name", "kind", "summary", "environments", "topics", "scope", "relations"]),
            "url": ev["url"], "retrieved_at": ev["retrieved_at"], "sha256": ev["sha256"]}
        if editorial.get("details") and "primary_supports" not in editorial:
            primary["supports"].append("details")
        apply_license_reviews(editorial,primary,licenses,details)
        row = {"id": rid, "name": editorial["name"], "kind": editorial["kind"], "url": editorial["url"],
            "aliases": editorial.get("aliases", []), "environments": editorial["environments"], "topics": editorial["topics"],
            "scope": editorial.get("scope", "core"), "summary": editorial["summary"], "review_status": "curated",
            "published_at": base.get("published_at"), "updated_at": base.get("updated_at"), "authors": base.get("authors", []),
            "identifiers": base.get("identifiers", {}), "links": [{"rel": "primary", "url": editorial["url"]}],
            "relations": relations, "licenses": licenses, "evidence": base.get("evidence", []) + [primary] + editorial.get("additional_evidence", []) + extra.get("evidence", []),
            "last_verified_at": ev["retrieved_at"], "notes": editorial.get("notes", ""), "details": details}
        records[rid] = row
        row['links'] = publication_links(row)
    changes = {row['id'] for row in read_jsonl(DATA/'metadata-updates.jsonl')}
    decisions = resolve_exclusions(records, read_json(DATA/'exclusions.json', []), changes)
    excluded = {row['id'] for row in decisions if row['status']=='excluded'}
    pending += [{'id':row['id'],'name':records[row['id']]['name'],'url':row['url'],'reason':row['status_reason'],'cause':'scope_revalidation'} for row in decisions if row['status']=='revalidation_pending']
    rows = sorted((row for rid,row in records.items() if rid not in excluded), key=lambda r:r['id'])
    rows = attach_repository_aliases(rows, read_json(DATA/'repository-aliases.json', []))
    return (rows,pending,decisions) if with_scope else (rows,pending)


FIELD_TYPES = {"id": str, "name": str, "kind": str, "url": str, "aliases": list, "environments": list, "topics": list, "scope": str, "summary": (str, type(None)), "review_status": str,
    "published_at": (str, type(None)), "updated_at": (str, type(None)), "authors": list, "identifiers": dict, "links": list, "relations": list, "licenses": dict, "evidence": list,
    "last_verified_at": str, "notes": str, "details": dict}
EVIDENCE_FIELDS = {"role", "method", "supports", "url", "retrieved_at", "sha256"}
# Read from the published contract, so a new receipt method is declared in one place.
EVIDENCE_METHODS = set(read_json(ROOT / "schemas/resource.schema.json")["properties"]["evidence"]["items"]["properties"]["method"]["enum"])
LICENSE_FIELDS = {"declared", "url", "retrieved_at", "basis"}
RFC3339 = re.compile(r"\d{4}-\d\d-\d\d[Tt](?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)", re.A)


def malformed_fields(r):
    # The semantic checks assume these JSON types; the published schema reports each exact mismatch.
    strings = lambda values: all(isinstance(v, str) for v in values)
    nested = {"aliases": strings, "environments": strings, "topics": strings, "authors": strings, "identifiers": lambda v: strings(v.values()),
        "evidence": lambda v: all(isinstance(e, dict) and strings(e.get(k, "") for k in ("url", "sha256", "retrieved_at", "role", "method")) and isinstance(e.get("supports", []), list) for e in v),
        "relations": lambda v: all(isinstance(e, dict) and strings(e.get(k, "") for k in ("type", "target_id", "evidence_url")) for e in v)}
    return [key for key, kind in FIELD_TYPES.items() if key in r and not (isinstance(r[key], kind) and nested.get(key, lambda v: True)(r[key]))]


def https(url):
    # The schema requires a literal "https://" prefix; canonical() also accepts http:// and rewrites it.
    return isinstance(url, str) and url.startswith("https://")


def timestamp(value):
    """The schema's RFC 3339 date-time; fromisoformat alone also accepts bare dates, missing seconds or offsets, and spaces."""
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        return False
    try:
        dt.datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
    except ValueError:  # An impossible calendar date, such as February 30.
        return False
    return True


def title_author_collisions(rows):
    """Paper/survey groups with the same title letters and author list that no preferred_arxiv decision separates."""
    groups = collections.defaultdict(list)
    for r in rows:
        if not malformed_fields(r) and r.get("kind") in {"paper", "survey"} and isinstance(r.get("name"), str):
            groups["".join(c for c in r["name"].casefold() if c.isalnum()), tuple(" ".join(a.casefold().split()) for a in r.get("authors", []))].append(r)
    collisions = []
    for group in groups.values():
        ids = {r.get("id") for r in group}
        undecided = [r for r in group if "arxiv:" + str(r.get("identifiers", {}).get("preferred_arxiv")) not in ids - {r.get("id")}]
        if len(undecided) > 1:
            collisions.append(undecided)
    return collisions


def validate_records(rows):
    errors, seen, alias_owners = [], set(), {}
    required = set(FIELD_TYPES)
    ids = {r.get("id") for r in rows if isinstance(r.get("id"), str)}
    for r in rows:
        rid = r.get("id", "<missing>")
        def error(message):
            errors.append(f"{rid}: {message}")
        if malformed := malformed_fields(r):
            error("malformed fields " + ", ".join(malformed))
            continue
        if rid in seen:
            error("duplicate identifier")
        seen.add(rid)
        if missing := required - r.keys():
            error("missing fields " + ", ".join(sorted(missing)))
        if unknown := r.keys() - required:
            error("unknown fields " + ", ".join(sorted(unknown)))
        if "id" in r and not re.fullmatch(r"(?:arxiv|github|url|component|organization):\S+", rid):
            error("invalid id prefix or whitespace")
        if r.get("kind") not in KINDS:
            error("invalid kind")
        parsed = canonical(r.get("url", ""), allow_doi=r.get("kind") in {"paper","survey"})
        if not r.get("name") or not parsed:
            error("missing name or invalid URL")
        elif not https(r["url"]):
            error("url must start with https://")
        if "links" in r and (not r["links"] or any(not isinstance(link, dict) or link.keys() != {"rel", "url"} or not isinstance(link["rel"], str) or not https(link["url"]) for link in r["links"])):
            error("links must be a non-empty list of rel and https url pairs")
        # Editors assign component: and organization: identities; every other id is its URL's canonical identity.
        if parsed and rid.split(":", 1)[0] in {"arxiv", "github", "url"} and parsed[0] != rid:
            error(f"url resolves to {parsed[0]}, not to its id")
        # preferred_arxiv may name another paper; arxiv must be this record's own identifier.
        if rid.startswith("arxiv:") and r.get("identifiers", {}).get("arxiv") != rid[6:]:
            error("identifiers.arxiv does not match the arXiv id")
        for alias in r.get("aliases", []):
            if (former := canonical(alias)) and former[0] != rid:
                if former[0] in ids:
                    error(f"alias {alias} is the active record {former[0]}; keep one record")
                elif alias_owners.setdefault(former[0], rid) != rid:
                    error(f"alias {alias} already resolves to {alias_owners[former[0]]}")
        if r.get("review_status") not in STATUSES:
            error("invalid review status")
        if not r.get("environments") or set(r["environments"]) - ENVIRONMENTS:
            error("invalid environments")
        if unknown := set(r.get("topics", [])) - TOPICS.keys():
            error("unknown topics " + ", ".join(sorted(unknown)))
        for key in ("aliases", "environments", "topics"):
            if len(set(r.get(key, []))) != len(r.get(key, [])):
                error("duplicate " + key)
        # Facet rules in docs/data-dictionary.md#environment-facets: OS facets refine desktop, and unspecified stands alone.
        environments, topics = set(r.get("environments", [])), set(r.get("topics", []))
        if "unspecified" in environments and len(environments) > 1:
            error("unspecified environment combined with platform facets")
        if environments & {"windows", "macos", "linux"} and "desktop" not in environments:
            error("windows, macos or linux environment without desktop")
        if "web-navigation" in topics and not environments & {"web", "cross-platform"}:
            error("web-navigation topic without a web or cross-platform environment")
        if "mobile-navigation" in topics and not environments & {"android", "ios", "harmonyos", "cross-platform", "web", "unspecified"}:
            error("mobile-navigation topic with only desktop environments")
        if r.get("scope") not in {"core", "adjacent", "relevance_pending"}:
            error("invalid scope")
        if r.get("review_status") == "curated" and (not r.get("summary") or r.get("scope") == "relevance_pending"):
            error("curated entry lacks an editorial summary/scope")
        if "leaderboard_url" in (r.get("details") or {}) and (r.get("kind") != "benchmark" or r.get("review_status") != "curated" or not https(r["details"]["leaderboard_url"])):
            error("leaderboard_url must be an https URL on a curated benchmark")
        for issue in validate_profiles(r):
            error(issue)
        for issue in validate_snapshot(r):
            error(issue)
        for issue in validate_publication(r):
            error(issue)
        preferred = r.get("identifiers", {}).get("preferred_arxiv")
        if preferred and preferred != r.get("identifiers", {}).get("arxiv"):
            if "arxiv:" + preferred not in ids:
                error("preferred bibliographic identity is missing")
            if r.get("review_status") == "curated":
                error("known duplicate cannot be counted as an additional curated paper")
        if set(r.get("licenses", {})) != {"code", "data", "weights", "document"}:
            error("license scopes must be explicit")
        for scope, license_info in r.get("licenses", {}).items():
            if license_info is None:
                continue
            declared = license_info.get("declared") if isinstance(license_info, dict) else None
            if not declared or not license_info.get("url"):
                error(f"{scope} license lacks a declaration or source")
            elif not https(license_info["url"]):
                error(f"{scope} license url must start with https://: {license_info['url']}")
            elif (license_info.keys() != LICENSE_FIELDS or not isinstance(license_info["basis"], str) or not timestamp(license_info["retrieved_at"])
                  or not (isinstance(declared, str) or isinstance(declared, list) and all(isinstance(name, str) for name in declared))):
                error(f"{scope} license needs exactly a declared name or list, url, retrieved_at timestamp, and basis")
        if not r.get("evidence"):
            error("missing primary evidence")
        for ev in r.get("evidence", []):
            parsed_url = urllib.parse.urlsplit(ev.get("url", ""))
            if ev.get("role") != "primary" or not re.fullmatch(r"[0-9a-f]{64}", ev.get("sha256", "")) or not ev.get("supports") or not https(ev.get("url")) or not parsed_url.netloc:
                error("invalid evidence receipt")
            elif ev.keys() != EVIDENCE_FIELDS or ev["method"] not in EVIDENCE_METHODS or any(not isinstance(s, str) for s in ev["supports"]) or len(set(ev["supports"])) != len(ev["supports"]):
                error("evidence receipt needs exactly role, a known method, distinct supports, url, retrieved_at, and sha256")
            if not timestamp(ev.get("retrieved_at")):
                error("invalid evidence timestamp")
        # Missing or wrongly typed values were reported above; only check the format of strings.
        verified = r.get("last_verified_at") if isinstance(r.get("last_verified_at"), str) else None
        if verified is not None and not timestamp(verified):
            error("invalid last_verified_at")
            verified = None
        relation_keys = set()
        for relation in r.get("relations", []):
            key = (relation.get("type"), relation.get("target_id"))
            if key in relation_keys:
                error(f"duplicate relation {key[0]} {key[1]}")
            relation_keys.add(key)
            if relation.keys() != {"type", "target_id", "evidence_url"} or relation.get("type") not in REVIEWED_RELATION_TYPES:
                error(f"invalid relation {key[0]} {key[1]}")
            if relation.get("target_id") not in ids:
                error(f"dangling reviewed relation {relation.get('target_id')}")
            if not any(e.get('url')==relation.get('evidence_url') and e.get('role')=='primary'
                       and 'relations' in e.get('supports',[]) for e in r.get('evidence',[])):
                error('reviewed relation lacks a retained primary evidence receipt scoped to relations')
        for key in ("published_at", "updated_at"):
            value = r.get(key)
            if value is not None:
                try:
                    if not re.fullmatch(r"\d{4}-\d\d-\d\d", value, re.A):
                        raise ValueError
                    dt.date.fromisoformat(value)
                    if verified and value > verified[:10]:
                        error(f"{key} is after its verification date")
                except ValueError:
                    error(f"invalid {key}")
    errors.extend(duplicate_publication_errors(rows))
    for group in title_author_collisions(rows):
        curated = [r.get("id") for r in group if r.get("review_status") == "curated"]
        errors.extend(f"{rid}: title and authors match curated {curated[0]}; record identifiers.preferred_arxiv on the duplicate" for rid in curated[1:])
    return errors


def validate_sources(sources):
    errors = []
    for source in sources:
        parts = urllib.parse.urlsplit(source["homepage"]) if isinstance(source.get("homepage"), str) else None
        if not parts or parts.scheme != "https" or not parts.netloc:
            errors.append(f"{source.get('id', '<missing>')}: discovery-source homepage must be an https URL")
    return errors


def candidate_reviews(candidates, ids, excluded, aliases):
    """Reviewed set-aside decisions for unresolved discovered identifiers: links that are not resources, or another address of an active record."""
    entries = read_json(DATA / "candidate-reviews.json", [])
    if not isinstance(entries, list):
        raise ValueError("Candidate reviews must be a list")
    exact, prefixes = {}, []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("decision") not in {"not_a_resource", "alias"} or not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
            raise ValueError("Candidate review needs a not_a_resource or alias decision and a reason: " + json.dumps(entry)[:200])
        alias = entry["decision"] == "alias"
        if "url_prefix" in entry:
            prefix = entry["url_prefix"]
            parts = urllib.parse.urlsplit(prefix) if isinstance(prefix, str) else None
            # A prefix covers that URL and the paths or queries below it; aliases are one-to-one, so only non-resources take a prefix.
            if alias or set(entry) != {"url_prefix", "decision", "reason"} or not parts or parts.scheme != "https" or not parts.netloc or parts.query or parts.fragment or prefix.endswith("/"):
                raise ValueError("Invalid candidate-review prefix: " + str(prefix))
            prefixes.append(entry)
            continue
        if set(entry) != {"id", "url", "decision", "reason", *(("target_id",) if alias else ())} or not isinstance(entry["id"], str) or entry["id"] in exact:
            raise ValueError("Invalid or duplicate candidate review: " + str(entry.get("id")))
        if alias and entry["target_id"] not in ids:
            raise ValueError(f"{entry['id']}: candidate alias target is not an active resource: {entry['target_id']}")
        exact[entry["id"]] = entry
    reviews, resolved = {}, ids | excluded
    for row in candidates:
        # Indexing or a scope decision wins; an entry for a since-resolved identifier no longer applies.
        if aliases.get(row["id"], row["id"]) in resolved:
            continue
        entry = exact.get(row["id"]) or next((p for p in prefixes if row["url"] == p["url_prefix"] or row["url"].startswith((p["url_prefix"] + "/", p["url_prefix"] + "?"))), None)
        if not entry:
            continue
        if entry.get("url", row["url"]) != row["url"]:
            raise ValueError(f"{row['id']}: candidate review URL differs from the discovered URL {row['url']}")
        reviews[row["id"]] = {"resolution": entry["decision"], "reason": entry["reason"], **({"alias_of": entry["target_id"]} if "target_id" in entry else {})}
    return reviews


def uncurated_linked_papers(rows):
    """Uncurated papers that a curated resource names as its introduced_by/documented_by paper: the next papers to review."""
    by_id = {r["id"]: r for r in rows}
    linked = collections.defaultdict(set)
    for r in rows:
        for rel in r.get("relations", []) if r["review_status"] == "curated" else []:
            target = by_id.get(rel["target_id"])
            if rel["type"] in {"introduced_by", "documented_by"} and target and target["kind"] in {"paper", "survey"} and target["review_status"] != "curated":
                linked[target["id"]].add(r["id"])
    return [{"id": rid, "name": by_id[rid]["name"], "url": by_id[rid]["url"], "linked_from": sorted(sources)} for rid, sources in sorted(linked.items())]


def print_uncurated_linked_papers(papers):
    for p in papers:
        print(f"Uncurated linked paper: {p['id']} is the paper of curated {', '.join(p['linked_from'])}; curate it or record a scope decision.")


def coverage(rows, pending, scope_decisions):
    ids = {r["id"] for r in rows}
    by_id = {r["id"]: r for r in rows}
    candidates = read_jsonl(DATA / "candidates.jsonl")
    runs = {r["id"]: r for r in read_json(DATA / "discovery-runs.json", [])}
    sources = read_json(DATA / "sources.json", [])
    excluded = {row['id'] for row in scope_decisions if row['status']=='excluded'}
    source_rows = []
    aliases = source_aliases(rows)
    reviews = candidate_reviews(candidates, ids, excluded, aliases)
    for source in sources:
        population = {r["id"] for r in candidates if any(o["source_id"] == source["id"] for o in r["discovered_in"])}
        resolved = {aliases.get(identity, identity) for identity in population}
        present = resolved & ids
        indexed_identifiers = {identity for identity in population if aliases.get(identity,identity) in ids}
        excluded_identifiers = {identity for identity in population if aliases.get(identity,identity) in excluded}
        source_rows.append({"id": source["id"], "name": source["name"], "url": source["homepage"],
            "snapshot": runs.get(source["id"]), "discovered": len(population), "indexed": len(indexed_identifiers),
            "indexed_resources":len(present), "resolved_aliases":sum(aliases.get(identity,identity)!=identity for identity in indexed_identifiers),
            "curated": sum(by_id[aliases.get(i,i)]["review_status"] == "curated" for i in indexed_identifiers),
            "excluded":len(excluded_identifiers), "set_aside":len(population & reviews.keys()), "unindexed":len(population-indexed_identifiers-excluded_identifiers-reviews.keys())})
    latest = max((e["retrieved_at"] for r in rows for e in r["evidence"]), default="")
    return {"as_of_utc": latest, "total_records": len(rows), "curated_records": sum(r["review_status"] == "curated" for r in rows),
        "bibliographic_records": sum(r['kind'] in {'paper','survey'} for r in rows),
        "arxiv_active_records": sum(r['kind'] in {'paper','survey'} and r['id'].startswith('arxiv:') for r in rows),
        "non_arxiv_bibliographic_records": sum(r['kind'] in {'paper','survey'} and not r['id'].startswith('arxiv:') for r in rows),
        "publication_metadata_records": sum(bool(r.get('details',{}).get('publication')) for r in rows),
        "arxiv_archive_records":len(read_jsonl(DATA/'papers.jsonl')),
        "excluded_records":len(excluded),
        "exclusion_revalidation_pending":sum(row['status']=='revalidation_pending' for row in scope_decisions),
        "metadata_only_records": sum(r["review_status"] == "metadata_verified" for r in rows),
        "discovery_identifiers": len(candidates), "unindexed_candidates": len({aliases.get(r['id'],r['id']) for r in candidates if r['id'] not in reviews} - ids - excluded),
        "non_resource_candidates": sum(r["resolution"] == "not_a_resource" for r in reviews.values()), "alias_candidates": sum(r["resolution"] == "alias" for r in reviews.values()),
        "pending_editorial": pending, "uncurated_linked_papers": uncurated_linked_papers(rows), "by_kind": dict(sorted(collections.Counter(r["kind"] for r in rows).items())),
        "curated_by_environment": dict(sorted(collections.Counter(e for r in rows if r["review_status"] == "curated" for e in r["environments"]).items())),
        "curated_by_kind_and_environment": {kind: dict(sorted(collections.Counter(e for r in rows if r["review_status"] == "curated" and r["kind"] == kind for e in set(r["environments"])).items()))
            for kind in sorted({r["kind"] for r in rows if r["review_status"] == "curated"})},
        "license_declarations_by_scope": {slot: sum(r["licenses"][slot] is not None for r in rows) for slot in ("code", "data", "weights", "document")},
        "sources": source_rows, "primary_search": read_json(DATA / "arxiv-search.json", {}),
        "paper_discovery": read_json(DATA / 'paper-discovery-status.json', {}),
        "paper_query_registry": read_json(DATA / 'paper-discovery-queries.json', {}),
        "limits": ["Counts are resources, not distinct projects, companies, or independent discoveries.",
            "Metadata verification does not establish relevance, quality, reproducibility, availability, or endorsement.",
            "Source indexing measures only fetched source snapshots; incidental/out-of-scope links remain in discovery.",
            "Global completeness has no observed denominator and is not claimed.",
            "Environment facets overlap. Unknown license, size, price, or performance fields are not inferred."]}


def md(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("[", "\\[").replace("]", "\\]")


def paper_cell(r, by_id):
    """Reviewed paper relations only; a mention in a README is not a paper link."""
    targets = list(dict.fromkeys(rel["target_id"] for rel in r["relations"] if rel["type"] in {"introduced_by", "documented_by"}
                               and (by_id.get(rel['target_id'],{}).get('kind') in {'paper','survey'}
                                    or (rel['target_id'] not in by_id and re.fullmatch(r'arxiv:\d{4}\.\d{4,5}',rel['target_id'])))))
    cells = []
    for target in targets:
        paper = by_id.get(target)
        year = f" ({record_year(paper)})" if paper and record_year(paper) else ""
        label = target.split(':',1)[1] if target.startswith('arxiv:') else paper['name']
        url=paper['url'] if paper else 'https://arxiv.org/abs/'+target.split(':',1)[1]
        cells.append(f"[{md(label)}]({url}){year}")
    return ", ".join(cells) or "—"


def license_cell(r, lang="en"):
    """Declared licenses per scope; unknown scopes are omitted, never inferred."""
    parts = []
    for scope in ("code", "data", "weights", "document"):
        declared = (r["licenses"].get(scope) or {}).get("declared")
        if declared:
            parts.append(f"{README_TEXT[lang]['scopes'][scope]} {md('/'.join(declared) if isinstance(declared, list) else declared)}")
    return " · ".join(parts) or "—"


def publisher_cell(r, by_id):
    publishers = [by_id[rel["target_id"]] for rel in r["relations"] if rel["type"] == "published_by" and rel["target_id"] in by_id]
    return ", ".join(f"[{md(p['name'])}]({p['url']})" for p in publishers) or "—"


EVIDENCE_NOTE = "*Evidence* links the reviewed first-party snapshot and its retrieval date."
# Columns per generated category page; facts that cannot apply to a kind are not shown as empty columns.
KIND_COLUMNS = {
    None: (("Resource", "Environments", "Paper", "License", "Description", "Evidence"),
        "*Paper* lists reviewed `introduced_by`/`documented_by` relations with the record's year. *License* lists publisher declarations by scope (code, data, weights, document). " + EVIDENCE_NOTE),
    # Each bibliography identity retains its source edition and recorded date precision.
    "paper": (("Date", "Resource", "Environments", "Description"), "*Date* retains the arXiv first-submission date, or the publisher-only record's publication date at its known precision; newest first. Titles link primary sources; receipts are in `data/catalog.jsonl`."),
    "survey": (("Date", "Resource", "Environments", "Description"), "*Date* retains the arXiv first-submission date, or the publisher-only record's publication date at its known precision; newest first. Titles link primary sources; receipts are in `data/catalog.jsonl`."),
    "product": (("Resource", "Publisher", "Environments", "Description", "Evidence"), "*Publisher* is a reviewed `published_by` relation. " + EVIDENCE_NOTE),
    "company": (("Resource", "Environments", "Description", "Evidence"), EVIDENCE_NOTE),
    "benchmark": (("Resource", "Environments", "Paper", "Scale", "License", "Description", "Evidence"),
        "*Scale* is the first publisher-reported or computed count per unit from the reviewed profile, linked to its source; subsets and units are never combined. *Paper* lists reviewed `introduced_by`/`documented_by` relations with the record's year. *License* lists publisher declarations by scope (code, data, weights, document). " + EVIDENCE_NOTE),
}
KIND_COLUMNS["dataset"] = KIND_COLUMNS["benchmark"]
KIND_COLUMNS["benchmark"] = (KIND_COLUMNS["dataset"][0], "A *leaderboard* link after the name is the official leaderboard that the reviewed source links. " + KIND_COLUMNS["dataset"][1])


# Category-page sections; a resource spanning several families is cross-platform by definition.
ENVIRONMENT_FAMILIES = [("web", "Web", {"web"}), ("desktop", "Desktop", {"desktop", "windows", "macos", "linux"}),
    ("mobile", "Mobile", {"android", "ios", "harmonyos"}), ("cross-platform", "Cross-platform", {"cross-platform"}), ("unspecified", "Unspecified", {"unspecified"})]


def environment_family(r):
    families = {slug for slug, _, members in ENVIRONMENT_FAMILIES if members & set(r["environments"])}
    return families.pop() if len(families) == 1 else "cross-platform"


def table_row(r, columns, by_id):
    primary = next(e for e in r["evidence"] if e["method"] == "editorial_primary_review")
    leaderboard = (r.get("details") or {}).get("leaderboard_url")
    cells = {"Resource": f"[{md(r['name'])}]({r['url']})" + (f" · [leaderboard]({leaderboard})" if leaderboard else ""), "Environments": ", ".join(r["environments"]),
        "Paper": paper_cell(r, by_id), "License": license_cell(r), "Publisher": publisher_cell(r, by_id),
        "Date": nowrap(record_date_text(r) or "—"), "Description": md(r["summary"]), "Scale": scale_cell(r),
        "Evidence": f"[✓ {nowrap(primary['retrieved_at'][:10])}]({primary['url']})"}
    return "| " + " | ".join(cells[column] for column in columns) + " |"


def scale_cell(r):
    """First count per unit, keeping its precision qualifier and linking its own source; units are never converted or summed."""
    profile = (r.get("details") or {}).get(PROFILE_KEYS.get(r.get("kind"), "")) or {}
    first = {}
    for count in profile.get("counts", []):
        first.setdefault(count["unit"], count)
    return " · ".join(f"[{PREFIXES[c['qualifier']]}{c['value']:,} {md(c['unit'])}]({c.get('reference_url') or c['evidence_url']})" for c in first.values()) or "—"


def nowrap(date):
    # Non-breaking hyphens keep ISO dates on one line in narrow GitHub table columns.
    return date.replace("-", "\u2011")


def section_table(members, columns, by_id):
    """Table lines for one section; a column whose value is identical on every row is stated once instead."""
    shared = {tuple(r["environments"]) for r in members}
    lines = []
    if "Environments" in columns and len(shared) == 1:
        columns = tuple(c for c in columns if c != "Environments")
        lines = [f"All entries in this section: {', '.join(shared.pop())}.", ""]
    return lines + ["| " + " | ".join(columns) + " |", "|" + " --- |" * len(columns), *(table_row(r, columns, by_id) for r in members)]


TOPIC_LABELS = {topic: entry["en"] for topic, entry in TOPICS.items()}
TOPIC_KINDS = [("benchmark", "Benchmarks"), ("dataset", "Datasets"), ("model", "Models"), ("agent", "Agents"), ("framework", "Frameworks"),
    ("tool", "Tools"), ("infrastructure", "Infrastructure"), ("product", "Products"), ("company", "Publishers"), ("survey", "Surveys"), ("paper", "Papers")]


def topic_label(topic):
    return TOPIC_LABELS.get(topic, topic.replace("-", " ").capitalize())


def topic_vocabulary():
    """The data dictionary's topic table, generated from data/topics.json."""
    return "\n" + "\n".join(["| Topic | English label | Chinese label | Meaning |", "| --- | --- | --- | --- |",
        *(f"| `{topic}` | {md(entry['en'])} | {md(entry['zh'])} | {md(entry['definition'])} |" for topic, entry in TOPICS.items())]) + "\n"


def topic_pages(rows):
    """One generated hub per curated topic, listing every reviewed resource kind tagged with it."""
    by_id = {r["id"]: r for r in rows}
    tagged = collections.defaultdict(list)
    for r in rows:
        if r["review_status"] == "curated":
            for topic in sorted(set(r["topics"])):
                tagged[topic].append(r)
    order = sorted(tagged, key=lambda t: (-len(tagged[t]), t))
    files = {}
    index = ["# Reviewed research by topic", "", "[Home](../README.md) · [Full arXiv bibliography](papers.md) · [Methodology](methodology.md)", "",
        f"{sum(r['review_status'] == 'curated' for r in rows):,} source-reviewed resources across {len(order)} topics. Topic tags are catalog annotations from the editorial review, not author keywords; a resource appears under every topic it carries. Each hub lists benchmarks, data, models, systems, and papers together, newest papers first.", "",
        "| Topic | All | Benchmarks | Datasets | Models | Systems | Papers | Newest reviewed paper |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for topic in order:
        group = tagged[topic]
        kinds = collections.Counter(r["kind"] for r in group)
        papers = sorted((r for r in group if r["kind"] in {"paper", "survey"}), key=lambda r: (record_date_text(r), r["name"]), reverse=True)
        systems = sum(kinds[k] for k in ("agent", "framework", "tool", "infrastructure", "product", "company"))
        newest = f"[{md(papers[0]['name'])}]({papers[0]['url']}) · {record_date_text(papers[0]) or '—'}" if papers else "—"
        cell = lambda n: f"{n:,}" if n else "·"
        index.append(f"| [{topic_label(topic)}](topics/{topic}.md) | {len(group):,} | {cell(kinds['benchmark'])} | {cell(kinds['dataset'])} | {cell(kinds['model'])} | {cell(systems)} | {cell(len(papers))} | {newest} |")
        lines = [f"# {topic_label(topic)}", "", f"[Home](../../README.md) · [All topics](../topics.md) · [Full arXiv bibliography](../papers.md)", "",
            f"{len(group):,} source-reviewed resources tagged `{topic}`. Curated metadata, not a performance ranking; unknown facts are shown as —.", "",
            "**Contents:** " + " · ".join(f"[{label} ({kinds[kind]})](#{label.lower()})" for kind, label in TOPIC_KINDS if kinds[kind]), ""]
        for kind, label in TOPIC_KINDS:
            members = [r for r in group if r["kind"] == kind]
            if not members:
                continue
            columns = KIND_COLUMNS.get(kind, KIND_COLUMNS[None])[0]
            members.sort(key=lambda r: r["name"].casefold())
            if "Date" in columns:
                members.sort(key=record_date_text, reverse=True)
            lines += [f"## {label}", "", *section_table(members, columns, by_id), ""]
        files[f"docs/topics/{topic}.md"] = "\n".join(lines)
    files["docs/topics.md"] = "\n".join(index + [""])
    return files


PLATFORMS = [("web", "Web"), ("desktop", "Desktop"), ("windows", "Windows"), ("macos", "macOS"), ("linux", "Linux"),
    ("android", "Android"), ("ios", "iOS"), ("harmonyos", "HarmonyOS"), ("cross-platform", "Cross-platform")]


def environment_pages(rows):
    """One generated hub per platform facet, listing every reviewed resource that carries it."""
    by_id = {r["id"]: r for r in rows}
    curated = [r for r in rows if r["review_status"] == "curated"]
    files = {}
    index = ["# Reviewed resources by platform", "", "[Home](../README.md) · [Research by topic](topics.md) · [Coverage](coverage.md)", "",
        "Environment facets come from the editorial review and overlap: a resource tagged with several platforms appears in each hub. `unspecified` records are listed only in the category pages.", "",
        "| Platform | All | Benchmarks | Datasets | Models | Systems | Papers |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    cell = lambda n: f"{n:,}" if n else "·"
    for env, label in PLATFORMS:
        group = [r for r in curated if env in r["environments"]]
        if not group:
            continue
        kinds = collections.Counter(r["kind"] for r in group)
        systems = sum(kinds[k] for k in ("agent", "framework", "tool", "infrastructure", "product", "company"))
        index.append(f"| [{label}](environments/{env}.md) | {len(group):,} | {cell(kinds['benchmark'])} | {cell(kinds['dataset'])} | {cell(kinds['model'])} | {cell(systems)} | {cell(kinds['paper'] + kinds['survey'])} |")
        lines = [f"# {label}", "", "[Home](../../README.md) · [All platforms](../environments.md) · [Research by topic](../topics.md)", "",
            f"{len(group):,} source-reviewed resources tagged `{env}`. Curated metadata, not a performance ranking; unknown facts are shown as —.", "",
            "**Contents:** " + " · ".join(f"[{name} ({kinds[kind]})](#{name.lower()})" for kind, name in TOPIC_KINDS if kinds[kind]), ""]
        for kind, name in TOPIC_KINDS:
            members = sorted((r for r in group if r["kind"] == kind), key=lambda r: r["name"].casefold())
            if not members:
                continue
            columns = KIND_COLUMNS.get(kind, KIND_COLUMNS[None])[0]
            if "Date" in columns:
                members.sort(key=record_date_text, reverse=True)
            lines += [f"## {name}", "", *section_table(members, columns, by_id), ""]
        files[f"docs/environments/{env}.md"] = "\n".join(lines)
    files["docs/environments.md"] = "\n".join(index + [""])
    return files


MATRIX_ENVIRONMENTS = ["web", "desktop", "windows", "macos", "linux", "android", "ios", "harmonyos", "cross-platform", "unspecified"]


def matrix_lines(matrix):
    lines = ["| Kind | " + " | ".join(MATRIX_ENVIRONMENTS) + " |", "| --- |" + " ---: |" * len(MATRIX_ENVIRONMENTS)]
    for kind, counts in matrix.items():
        lines.append(f"| [{kind}]({'companies' if kind == 'company' else 'topics' if kind == 'paper' else kind + 's'}.md) | " + " | ".join(str(counts[e]) if counts.get(e) else "·" for e in MATRIX_ENVIRONMENTS) + " |")
    return lines


def pending_breakdown(pending):
    n = collections.Counter(p.get("cause") for p in pending)
    return (f"{len(pending)} proposals: {n['unresolved_evidence']} with unresolved primary evidence, {n['unreviewed_snapshot']} whose current source snapshot awaits review, "
        f"{n['reviewer_hold']} held by a reviewer after reading the current source, and {n['scope_revalidation']} awaiting another scope review.")


def documents(rows, report):
    files = {}
    by_id = {r["id"]: r for r in rows}
    grouped = collections.defaultdict(list)
    for r in rows:
        if r["review_status"] == "curated":
            grouped[r["kind"]].append(r)
    for kind, group in sorted(grouped.items()):
        if kind == "paper":
            # Reviewed papers are published by topic (docs/topics/); docs/papers.md is the full bibliography.
            continue
        columns, legend = KIND_COLUMNS.get(kind, KIND_COLUMNS[None])
        title = f"{kind.title()} catalog"
        sections = collections.defaultdict(list)
        for r in group:
            sections[environment_family(r)].append(r)
        present = [(slug, label) for slug, label, _ in ENVIRONMENT_FAMILIES if sections[slug]]
        lines = [f"# {title}", "", "[Home](../README.md) · [Methodology](methodology.md) · [Machine-readable catalog](../data/catalog.jsonl)", "",
            "Curated metadata, not a performance ranking. Each entry links its first-party evidence. Unknown facts are shown as —.", "", legend, "",
            f"**{len(group)} resources:** " + " · ".join(f"[{label} ({len(sections[slug])})](#{slug})" for slug, label in present), "",
            "Resources tagged with environments from more than one family are listed under *Cross-platform*; their exact environments stay in the table.", ""]
        for slug, label in present:
            ordered = sorted(sections[slug], key=lambda r: r["name"].casefold())
            if "Date" in columns:
                ordered.sort(key=record_date_text, reverse=True)
            lines += [f"## {label}", "", *section_table(ordered, columns, by_id),
                "", f"[↑ Back to top](#{title.lower().replace(' ', '-')})", ""]
        lines += ["Detailed notes and separate code/data/weights license declarations are in `data/catalog.jsonl`.", ""]
        filename = "companies" if kind == "company" else kind + "s"
        files[f"docs/{filename}.md"] = "\n".join(lines)
    paper_lines = ["# Research bibliography", "", "[Home](../README.md) · [Reviewed research by topic](topics.md) · [Curated surveys](surveys.md) · [Query examples](query-guide.md)", "",
        "Bibliographic records from arXiv and retained publication sources. Metadata-only entries have **not** undergone a relevance or methodological review. Discovery includes historical references and adjacent work; this is not a count of confirmed CUA papers.",
        "Dates retain their recorded precision: a year or month does not imply a known day. Explicit arXiv scope exclusions are listed in the [scope-decision ledger](../data/exclusion-status.json). The [arXiv archive](../data/papers.jsonl) and [publication observations](../data/publications.jsonl) retain their separate source facts.", ""]
    years = collections.defaultdict(list)
    for r in rows:
        if r['kind'] in {'paper','survey'}:
            years[record_year(r) or 'Undated'].append(r)
    order = sorted((y for y in years if y != "Undated"), reverse=True) + (["Undated"] if "Undated" in years else [])
    reviewed = lambda group: sum(r["review_status"] == "curated" for r in group)
    paper_lines += ["**Years:** " + " · ".join(f"[{y}](#{y.lower()}) ({len(years[y]):,}; {reviewed(years[y]):,} ⭐)" for y in order), "",
        "⭐ marks papers with an editorial relevance review; their topics link to the [topic hubs](topics.md). Other rows are bibliographic metadata only.", ""]
    for year in order:
        paper_lines += [f"## {year}", "", "| Date | Paper | Review | Topics |", "| --- | --- | --- | --- |"]
        for r in sorted(years[year], key=lambda r: (record_date_text(r), r["name"]), reverse=True):
            curated = r["review_status"] == "curated"
            topics = ", ".join(f"[{t}](topics/{t}.md)" for t in sorted(set(r["topics"]))) if curated else ""
            paper_lines.append(f"| {record_date_text(r) or '—'} | [{md(r['name'])}]({r['url']}) | {'⭐ reviewed' if curated else 'metadata'} | {topics} |")
        paper_lines.append("")
    files["docs/papers.md"] = "\n".join(paper_lines)
    hubs = topic_pages(rows)
    hubs.update(environment_pages(rows))
    if hubs.keys() & files.keys():
        raise ValueError("Generated paths assigned twice: " + ", ".join(sorted(hubs.keys() & files.keys())))
    files.update(hubs)
    lines = ["# Coverage and quality ledger", "", f"Evidence snapshot through **{report['as_of_utc']}**. Generated from committed source receipts.", "",
        f"- {report['total_records']:,} resource records: {report['curated_records']:,} curated; {report['metadata_only_records']:,} bibliographic metadata only.",
        f"- {report['bibliographic_records']:,} paper and survey records, including {report.get('arxiv_active_records',report['bibliographic_records']):,} arXiv identities and {report.get('non_arxiv_bibliographic_records',0):,} publisher-only identities. This count overlaps the status counts above.",
        f"- {report['arxiv_archive_records']:,} retained arXiv metadata records; {report['excluded_records']:,} explicit scope exclusions are outside the active catalog.",
        f"- {report['discovery_identifiers']:,} discovery identifiers; {report['unindexed_candidates']:,} remain unresolved after accounting for scope exclusions and for {report.get('non_resource_candidates',0):,} reviewed non-resource links and {report.get('alias_candidates',0):,} other addresses of indexed resources, which stay in the review queue with their reasons.",
        f"- {len(report['pending_editorial'])} editorial proposals await verification or review.", "",
        "These are distinct resource identifiers, not distinct research projects. Papers, repositories, datasets, products, and publisher entities have different grains.", "",
        "## Curated coverage by kind and environment", "", "Counts of source-reviewed resources. A resource tagged with several environments counts in each column; `·` marks an empty cell, which is where contributions are most needed.", "",
        *matrix_lines(report["curated_by_kind_and_environment"]), "",
        "## Source snapshot coverage", "", "The denominator is the normalized identifiers extracted from each fetched document, including incidental links. Reviewed publisher/PDF aliases and former GitHub names can resolve to one canonical resource; coverage counts matching identifiers, while indexed_resources records distinct resolved resources. Sources overlap. These figures do not measure global completeness or editorial recall.", "",
        "| Source | Discovered | Indexed | Curated | Excluded | Set aside | Unresolved | Fetch |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for s in report["sources"]:
        status = s["snapshot"] or {}
        lines.append(f"| [{md(s['name'])}]({s['url']}) | {s['discovered']} | {s['indexed']} | {s['curated']} | {s['excluded']} | {s.get('set_aside',0)} | {s['unindexed']} | {'OK' if status.get('ok') else 'FAILED'} · {status.get('retrieved_at', '')[:10]} |")
    search = report["primary_search"]
    discovery = report.get('paper_discovery', {})
    if discovery:
        lines += ['', '## Paper-discovery query coverage', '',
            f"Latest pass: {discovery.get('finished_at') or 'in progress'}; **{discovery.get('successful_query_count',0)}/{discovery.get('configured_query_count',0)}** query windows succeeded. {discovery.get('unique_identifiers',0):,} distinct identifiers; {discovery.get('new_candidate_count',0):,} new to the candidate queue.", '',
            'These are ranked search windows, not a field-wide denominator. New identifiers still require primary metadata verification and relevance review.', '',
            '| Area | Query | Returned / limit | State |', '| --- | --- | ---: | --- |']
        for item in discovery.get('queries', []):
            lines.append(f"| {md(item['area'])} | {md(item['query'])} | {item['returned_count']} / {item['limit']} | {md(item['state'])} |")
    lines += ["", "## Primary arXiv discovery", "", f"The recorded title query returned {search.get('unique_returned', 0):,} unique records out of {search.get('reported_total', 0):,} reported matches. Pagination complete: **{search.get('complete', False)}**. This query population overlaps the lists and is not the whole field.", "", "```text", search.get("query", ""), "```", "",
        "## License evidence", "", "| Scope | Recorded declarations |", "| --- | ---: |"]
    lines += [f"| {slot} | {n} |" for slot, n in report["license_declarations_by_scope"].items()]
    lines += ["", "A code license never fills a data or weights field. Hub declarations are publisher metadata, not independently audited legal conclusions. Missing values remain null.", "",
        "## Pending editorial proposals", "", pending_breakdown(report["pending_editorial"]), "", "| Resource | Reason |", "| --- | --- |"]
    for p in report["pending_editorial"]:
        lines.append(f"| [{md(p['name'])}]({p['url']}) | {md(p['reason'])} |")
    linked = report.get("uncurated_linked_papers", [])
    lines += ["", "## Uncurated papers behind curated resources", "", "Papers that a curated resource names as its `introduced_by` or `documented_by` paper but that have no editorial relevance review yet. Review them before other metadata-only papers.", ""]
    lines += ["| Paper | Linked from |", "| --- | --- |", *(f"| [{md(p['name'])}]({p['url']}) | " + ", ".join(f"[{md(by_id[s]['name'])}]({by_id[s]['url']})" for s in p["linked_from"]) + " |" for p in linked)] if linked else ["None: every paper linked from a curated resource is curated."]
    lines += ["", "## Scope exclusions", "", f"{report['excluded_records']} records have an applied scope decision; {report['exclusion_revalidation_pending']} require another review after a change. See the [decision ledger](../data/exclusion-status.json) for each rationale and source fingerprint. These decisions concern catalog relevance, not research quality. Original bibliographic metadata is retained, and previous resource URLs explain the decision rather than silently disappearing.", "", "## Known gaps", "",
        "- Most bibliography records still require relevance review and detailed taxonomy.",
        "- Closed/private datasets, unpublished systems, regional products, and work absent from arXiv/lists are not exhaustively represented.",
        "- Asset sizes, model weights licenses, runtime requirements, and benchmark protocols need additional field-level curation.",
        "- Publisher entries cover selected brands; corporate ownership, funding, usage, revenue, and product pricing are not researched here.",
        "- Download links and available code do not establish that an asset is reproducible or still works.",
        "- Name changes, repository transfers, and related resource families need continuing entity resolution.", "",
        "See [methodology](methodology.md) for the inclusion boundary and [the review queue](../data/review-queue.jsonl) for actionable gaps.", ""]
    files["docs/coverage.md"] = "\n".join(lines)
    return files


def shield(label, message, color):
    escape = lambda text: urllib.parse.quote(str(text).replace("-", "--").replace("_", "__"), safe="")
    return f"https://img.shields.io/badge/{escape(label)}-{escape(message)}-{color}"


def badges(rows, report):
    curated = report["curated_records"]
    # Keep the small status strip secondary to the README's editorial banner.
    # Counts still come from this build; workflow status stays live on main.
    style = '?style=flat-square&labelColor=303447'
    return ("\n" + " ".join([
        f"[![Catalog records]({shield('records', format(report['total_records'], ','), '4856df')}{style})](data/catalog.jsonl)",
        f"[![Source-reviewed records]({shield('source-reviewed', format(curated, ','), '4856df')}{style})](docs/coverage.md)",
        "[![Catalog checks](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml/badge.svg?branch=main)](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml)",
        f"[![MIT license]({shield('license', 'MIT', '606779')}{style})](LICENSE)"]) + "\n")


# README category layout: rows of (left, right) cells; each cell lists (label key, generated page, kind). Counts are curated resources.
EXPLORE = [
    ([("topics", "docs/topics.md", "paper"), ("bibliography", "docs/papers.md", "bibliography")], [("agent", "docs/agents.md", "agent")]),
    ([("survey", "docs/surveys.md", "survey")], [("framework", "docs/frameworks.md", "framework")]),
    ([("dataset", "docs/datasets.md", "dataset")], [("infrastructure", "docs/infrastructures.md", "infrastructure")]),
    ([("benchmark", "docs/benchmarks.md", "benchmark")], [("tool", "docs/tools.md", "tool")]),
    ([("model", "docs/models.md", "model")], [("product", "docs/products.md", "product"), ("company", "docs/companies.md", "company")]),
]
# Generated README wording per language; resource names and reviewed summaries are never translated.
README_TEXT = {
    "en": {"explore_header": "| Research and training | Engineering and industry |",
        "labels": {"topics": "Research by topic", "bibliography": "Full bibliography", "survey": "Surveys", "dataset": "Datasets", "benchmark": "Benchmarks",
            "model": "Models and checkpoint releases", "agent": "Agents", "framework": "Frameworks", "infrastructure": "Infrastructure", "tool": "Tools",
            "product": "Products", "company": "Publishers and brands"},
        "by_platform": "By platform:", "reviewed_papers": "**{n:,}** reviewed papers", "arxiv_records": "{n:,} paper and survey records",
        "kinds": {"benchmark": "Benchmarks", "model": "Models", "dataset": "Datasets", "framework": "Frameworks", "agent": "Agents"},
        "all": "all {n} →", "surveys": "Start with the newest surveys", "survey_header": "| Date | Survey | Environments |", "highlight_header": "| Resource | Mentions | Environments | Paper | License | Description |",
        "recent_header": "| Reviewed | Resource | Kind | Environments | Description |", "kind_names": {},
        "scopes": {"code": "code", "data": "data", "weights": "weights", "document": "document"},
        "stats": ("**{total:,} resource records** · **{curated:,} curated** · **{arxiv:,} paper and survey records** · **{sources} discovery documents**\n\n"
            "Evidence through `{as_of}`. {metadata:,} records have bibliographic verification only; {unindexed:,} discovered identifiers remain unresolved, not counting {set_aside:,} links reviewed as non-resources or other addresses of indexed resources. "
            "{excluded:,} scope exclusions retain their original metadata in the archive. Counts overlap as explained below.")},
    "zh": {"explore_header": "| 研究与训练 | 工程与产业 |",
        "labels": {"topics": "按主题浏览研究", "bibliography": "完整论文目录", "survey": "综述", "dataset": "数据集", "benchmark": "基准",
            "model": "模型与权重版本", "agent": "智能体", "framework": "框架", "infrastructure": "基础设施", "tool": "工具",
            "product": "产品", "company": "发布方与品牌"},
        "by_platform": "按平台：", "reviewed_papers": "**{n:,}** 篇已审阅论文", "arxiv_records": "{n:,} 条论文与综述记录",
        "kinds": {"benchmark": "基准", "model": "模型", "dataset": "数据集", "framework": "框架", "agent": "智能体"},
        "all": "全部 {n} 项 →", "surveys": "从最新综述入门", "survey_header": "| 日期 | 综述 | 环境 |", "highlight_header": "| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |",
        "recent_header": "| 审阅日期 | 资源 | 类型 | 环境 | 简介（英文） |",
        "kind_names": {"benchmark": "基准", "dataset": "数据集", "model": "模型", "agent": "智能体", "framework": "框架", "tool": "工具",
            "infrastructure": "基础设施", "product": "产品", "company": "发布方"},
        "scopes": {"code": "代码", "data": "数据", "weights": "权重", "document": "文档"},
        "stats": ("**{total:,} 条资源记录** · **{curated:,} 条已审阅** · **{arxiv:,} 条论文与综述记录** · **{sources} 个发现来源文档**\n\n"
            "证据截至 `{as_of}`。{metadata:,} 条记录仅完成书目核实；{unindexed:,} 个已发现的标识符尚待处理，另有 {set_aside:,} 个链接经审阅确认为非资源或已收录资源的其他地址，不计入其中。"
            "{excluded:,} 条范围排除记录在归档中保留原始元数据。各项计数存在重叠，详见下文。")},
}


def stats_block(report, lang="en"):
    return "\n\n" + README_TEXT[lang]["stats"].format(total=report["total_records"], curated=report["curated_records"], arxiv=report["bibliographic_records"],
        sources=len(report["sources"]), as_of=report["as_of_utc"], metadata=report["metadata_only_records"], unindexed=report["unindexed_candidates"],
        set_aside=report.get("non_resource_candidates", 0) + report.get("alias_candidates", 0),
        excluded=report["excluded_records"]) + "\n\n"


def task_navigator(lang="en"):
    """Short task-oriented entry points shared by source and publication READMEs."""
    site = "https://awesomecua.github.io"
    if lang == "zh":
        heading, columns, cli = "按任务查找", "| 你的任务 | 从这里开始 | 可以找到什么 |", "本地检索示例（克隆后运行；Python 3.11+，无需安装依赖）"
        items = [
            ("查找论文", f"[论文库]({site}/zh/papers/) · [研究主题]({site}/zh/topics/)", "按年份和主题阅读已审阅论文，查看原始来源。"),
            ("选择评测基准", f"[基准指南]({site}/guides/gui-agent-benchmarks/)", "核对平台、任务、评估器和版本。"),
            ("寻找训练数据", f"[训练数据指南]({site}/guides/gui-agent-training-data/)", "比较监督形式、划分、样本单位和数据许可。"),
            ("构建智能体", f"[智能体]({site}/categories/agent/) · [框架]({site}/categories/framework/)", "找到实现入口、支持的平台和论文依据。"),
            ("接入 RAG 或 Agent", f"[使用指南]({site}/zh/agents/) · [数据中心]({site}/zh/data/)", "下载完整记录或检索文档，保留审阅状态和来源。"),
            ("追溯论文与资产", f"[论文—资产关系]({site}/connections/)", "查看经一手来源支持的代码、数据和模型关联。"),
        ]
    else:
        heading, columns, cli = "Find by task", "| Your task | Start here | What you can find |", "Local examples (after cloning; Python 3.11+, no dependencies required)"
        items = [
            ("Find papers", f"[Research library]({site}/papers/) · [Topics]({site}/topics/)", "Reviewed papers by year and topic, with original sources."),
            ("Choose a benchmark", f"[Benchmark guide]({site}/guides/gui-agent-benchmarks/)", "Platforms, tasks, evaluators, and versions to compare."),
            ("Find training data", f"[Training-data guide]({site}/guides/gui-agent-training-data/)", "Supervision, splits, count units, and data licenses."),
            ("Build an agent", f"[Agents]({site}/categories/agent/) · [Frameworks]({site}/categories/framework/)", "Implementation entry points, supported platforms, and papers."),
            ("Use RAG or an agent", f"[Agent guide]({site}/agents/) · [Data hub]({site}/data/)", "Complete records or retrieval documents with review states and sources."),
            ("Trace papers to assets", f"[Paper–asset connections]({site}/connections/)", "Code, datasets, and models linked through reviewed primary evidence."),
        ]
    commands = [
        'python3 scripts/catalog.py search "grounding" --kind paper --status curated --limit 0 --json',
        'python3 scripts/catalog.py search --kind benchmark --environment web --status curated --limit 0 --json',
        'python3 scripts/catalog.py search --kind dataset --environment android --status curated --limit 0 --json',
        'python3 scripts/catalog.py search --kind framework --status curated --limit 0 --json',
        'python3 scripts/export_rag.py --output dist/rag-documents.jsonl',
        'python3 scripts/catalog.py get arxiv:2404.07972 --related --json',
    ]
    return "\n" + "\n".join(["## " + heading, "", columns, "| --- | --- | --- |", *("| " + " | ".join(item) + " |" for item in items), "", "<details>", "<summary>" + cli + "</summary>", "", "```sh", "cd Awesome-CUA", *commands, "```", "", "</details>", ""]) + "\n"


def explore(rows, report, lang="en"):
    text = README_TEXT[lang]
    curated = collections.Counter(r["kind"] for r in rows if r["review_status"] == "curated")
    def link(key, path, kind):
        label = text["labels"][key]
        if kind == "paper":
            return f"[{label}]({path}) · " + text["reviewed_papers"].format(n=curated[kind])
        if kind == "bibliography":
            return f"[{label}]({path}) · " + text["arxiv_records"].format(n=report["bibliographic_records"])
        return f"[{label}]({path}) · **{curated[kind]:,}**"
    lines = [text["explore_header"], "| --- | --- |"]
    lines += [f"| {' · '.join(link(*item) for item in left)} | {' · '.join(link(*item) for item in right)} |" for left, right in EXPLORE]
    platforms = collections.Counter(e for r in rows if r["review_status"] == "curated" for e in set(r["environments"]))
    lines += ["", f"**{text['by_platform']}** " + " · ".join(f"[{label}](docs/environments/{env}.md) **{platforms[env]:,}**" for env, label in PLATFORMS if platforms[env])]
    return "\n" + "\n".join(lines) + "\n"


HIGHLIGHT_KINDS = [("benchmark", "docs/benchmarks.md"), ("model", "docs/models.md"), ("dataset", "docs/datasets.md"), ("framework", "docs/frameworks.md"), ("agent", "docs/agents.md")]


def highlights(rows, edges, limit=6, lang="en"):
    """Rank curated resources by distinct cataloged resources whose reviewed source mentions them; not a quality ranking."""
    by_id = {r["id"]: r for r in rows}
    cited_by = collections.defaultdict(set)
    for edge in edges:
        if edge["target_in_catalog"] and edge["source_id"] != edge["target_id"]:
            cited_by[edge["target_id"]].add(edge["source_id"])
    lines = [""]
    text = README_TEXT[lang]
    # Surveys come first as the entry point and are ordered by date, not by mentions.
    surveys = sorted((r for r in rows if r["kind"] == "survey" and r["review_status"] == "curated"), key=lambda r: (record_date_text(r), r["name"]), reverse=True)
    if surveys:
        lines += [f"**{text['surveys']}** · [{text['all'].format(n=len(surveys))}](docs/surveys.md)", "", text["survey_header"], "| --- | --- | --- |"]
        lines += [f"| {nowrap(record_date_text(r) or '—')} | [{md(r['name'])}]({r['url']}) | {', '.join(r['environments'])} |" for r in surveys[:5]]
        lines.append("")
    for kind, path in HIGHLIGHT_KINDS:
        curated = [r for r in rows if r["kind"] == kind and r["review_status"] == "curated"]
        ranked = sorted((r for r in curated if cited_by[r["id"]]), key=lambda r: (-len(cited_by[r["id"]]), r["name"].casefold()))[:limit]
        if not ranked:
            continue
        lines += [f"**{text['kinds'][kind]}** · [{text['all'].format(n=len(curated))}]({path})", "", text["highlight_header"], "| --- | ---: | --- | --- | --- | --- |"]
        lines += [f"| [{md(r['name'])}]({r['url']}) | {len(cited_by[r['id']])} | {', '.join(r['environments'])} | {paper_cell(r, by_id)} | {license_cell(r, lang)} | {md(r['summary'])} |" for r in ranked]
        lines.append("")
    return "\n".join(lines) + "\n"


def recently_reviewed(rows, reviewed_at, limit=12, lang="en"):
    """Newest editorial approvals of non-paper resources; papers are listed by date in the topic hubs."""
    recent = sorted((r for r in rows if r["review_status"] == "curated" and r["kind"] not in {"paper", "survey"} and reviewed_at.get(r["id"])),
        key=lambda r: (reviewed_at[r["id"]], r["name"].casefold()), reverse=True)[:limit]
    text = README_TEXT[lang]
    lines = ["", text["recent_header"], "| --- | --- | --- | --- | --- |"]
    lines += [f"| {nowrap(reviewed_at[r['id']][:10])} | [{md(r['name'])}]({r['url']}) | {text['kind_names'].get(r['kind'], r['kind'])} | {', '.join(r['environments'])} | {md(r['summary'])} |" for r in recent]
    return "\n".join(lines) + "\n" if recent else "\n"


def write_sqlite(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    con = sqlite3.connect(temporary)
    try:
        con.executescript("""
            CREATE TABLE resources(id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, url TEXT NOT NULL,
              review_status TEXT NOT NULL, scope TEXT NOT NULL, published_at TEXT, summary TEXT, record_json TEXT NOT NULL);
            CREATE TABLE facets(resource_id TEXT NOT NULL REFERENCES resources(id), facet TEXT NOT NULL, value TEXT NOT NULL,
              PRIMARY KEY(resource_id, facet, value));
            CREATE TABLE relations(source_id TEXT NOT NULL REFERENCES resources(id), relation TEXT NOT NULL, target_id TEXT NOT NULL,
              evidence_url TEXT NOT NULL, PRIMARY KEY(source_id, relation, target_id));
            CREATE VIRTUAL TABLE resource_search USING fts5(id UNINDEXED, name, summary, aliases, authors, topics);
            CREATE INDEX resources_kind ON resources(kind, review_status);
            CREATE INDEX facets_lookup ON facets(facet, value);
        """)
        for row in rows:
            con.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?)", (row["id"], row["name"], row["kind"], row["url"], row["review_status"], row["scope"], row["published_at"], row["summary"], json.dumps(row, ensure_ascii=False)))
            for facet in ("environments", "topics"):
                for value in sorted(set(row[facet])):
                    con.execute("INSERT INTO facets VALUES(?,?,?)", (row["id"], facet, value))
            for relation in row["relations"]:
                con.execute("INSERT INTO relations VALUES(?,?,?,?)", (row["id"], relation["type"], relation["target_id"], relation["evidence_url"]))
            con.execute("INSERT INTO resource_search VALUES(?,?,?,?,?,?)", (row["id"], row["name"], row["summary"] or "", " ".join(row["aliases"]), " ".join(row["authors"]), " ".join(row["topics"])))
        con.commit()
        con.close()
        temporary.replace(path)
    finally:
        con.close()
        temporary.unlink(missing_ok=True)


def build(args):
    rows, pending, scope_decisions = source_records(with_scope=True)
    errors = validate_records(rows)
    errors.extend(alias_owner_errors(rows,publication_aliases(read_jsonl(DATA/'publications.jsonl'),publication_identity),publication_identity))
    if errors:
        raise ValueError("\n".join(errors[:30]))
    report = coverage(rows, pending, scope_decisions)
    print_uncurated_linked_papers(report["uncurated_linked_papers"])
    files = documents(rows, report)
    files["data/catalog.jsonl"] = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    files["data/coverage.json"] = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    files['data/exclusion-status.json'] = json.dumps(scope_report(scope_decisions),ensure_ascii=False,indent=2)+'\n'
    ids = {r["id"] for r in rows}
    excluded = {row['id'] for row in scope_decisions if row['status']=='excluded'}
    candidates = read_jsonl(DATA / "candidates.jsonl")
    aliases=source_aliases(rows)
    reviews = candidate_reviews(candidates, ids, excluded, aliases)
    # Set-aside links stay visible with their reviewed resolution and reason; rows without a resolution await review.
    queue = [{**r, "review_status": "candidate", **reviews.get(r['id'], {"reason": "discovered identifier; primary evidence and relevance need review"})} for r in candidates if aliases.get(r['id'],r['id']) not in ids and aliases.get(r['id'],r['id']) not in excluded]
    editorial_pending = {r["id"]: r for r in pending}
    merged = {r["id"]: r for r in queue}
    for rid, item in editorial_pending.items():
        merged[rid] = {**merged.get(rid, {}), **item, "review_status": "candidate"}
    files["data/review-queue.jsonl"] = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in sorted(merged.values(), key=lambda r: r["id"]))
    edges = []
    row_map = {r["id"]: r for r in rows}
    for r in read_jsonl(DATA / "enrichment.jsonl"):
        if r["id"] not in ids or not any(e["sha256"] == r.get("evidence_sha256") for e in row_map[r["id"]]["evidence"]):
            continue
        for ref in r.get("references", []):
            edges.append({"id": hashlib.sha256((r["id"] + "\0" + ref["target_id"]).encode()).hexdigest()[:24], "source_id": r["id"], **ref, "target_in_catalog": ref["target_id"] in ids})
    files["data/references.jsonl"] = "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in sorted(edges, key=lambda e: e["id"]))
    reviewed_at = {(e.get("id") or editorial_identity(e)[0]): e.get("reviewed_at") for e in read_json(DATA / "editorial.json", []) if e.get("editorial_reviewed")}
    shared_badges = badges(rows, report)
    for filename, lang in (("README.md", "en"), ("README.zh-CN.md", "zh")):
        path = ROOT / filename
        if path.exists():
            blocks = {"STATS": stats_block(report, lang), "BADGES": shared_badges, "TASKS": task_navigator(lang), "EXPLORE": explore(rows, report, lang),
                "HIGHLIGHTS": highlights(rows, edges, lang=lang), "RECENT": recently_reviewed(rows, reviewed_at, lang=lang)}
            content = path.read_text(encoding="utf-8")
            for name, body in blocks.items():
                # A function replacement keeps backslashes in generated Markdown literal.
                content = re.sub(rf"(?<=<!-- {name}:START -->).*?(?=<!-- {name}:END -->)", lambda _: body, content, flags=re.S)
            files[filename] = content
    dictionary = ROOT / "docs/data-dictionary.md"
    if dictionary.exists():
        files["docs/data-dictionary.md"] = re.sub(r"(?<=<!-- TOPICS:START -->).*?(?=<!-- TOPICS:END -->)", lambda _: topic_vocabulary(), dictionary.read_text(encoding="utf-8"), flags=re.S)
    changed = []
    for relative, content in files.items():
        path = ROOT / relative
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            changed.append(relative)
            if not args.check:
                atomic_write(path, content.encode())
    if args.check:
        if changed:
            raise ValueError("Generated files are stale: " + ", ".join(changed))
        print(f"Generated views match {len(rows)} source-backed records.")
        return
    write_sqlite(rows, ROOT / "dist" / "catalog.sqlite")
    write_json(ROOT / "dist" / "catalog.json", rows)
    print(f"Built {len(rows)} records ({report['curated_records']} curated), {len(edges)} reference edges, {len(merged)} review items, and SQLite/JSON exports.")


def validate(args):
    rows = read_jsonl(DATA / "catalog.jsonl")
    if not rows:
        raise ValueError("No catalog. Run build first.")
    # Full published JSON Schema validation is part of the release/CI gate.
    import jsonschema
    from referencing import Registry, Resource
    formats = jsonschema.FormatChecker()
    # Without the format extras, jsonschema silently skips date-time and uri constraints.
    if missing := {"date-time", "uri"} - set(formats.checkers):
        raise ValueError("JSON Schema format checkers unavailable: " + ", ".join(sorted(missing)) + ". Install requirements-dev.txt (jsonschema[format-nongpl]).")
    errors = validate_records(rows) + validate_sources(read_json(DATA / "sources.json", []))
    from catalog import validate_candidate_snapshot
    try:
        validate_candidate_snapshot(DATA)
    except (ValueError, OSError, KeyError, TypeError) as error:
        errors.append('Candidate snapshot integrity: ' + str(error))
    for entry in read_json(DATA / "editorial.json", []):
        if unknown := [str(topic) for topic in entry.get("topics", []) if not isinstance(topic, str) or topic not in TOPICS]:
            errors.append(f"Editorial {entry.get('id') or entry.get('url')}: unknown topics {', '.join(unknown)}")
    resource_contract=read_json(ROOT/'schemas/resource.schema.json')
    validator = jsonschema.Draft202012Validator(resource_contract, format_checker=formats)
    for row in rows:
        errors.extend(f"{row['id']}: {error.message}" for error in validator.iter_errors(row))
    repository_declarations=read_json(DATA/'repository-aliases.json', [])
    repository_validator=jsonschema.Draft202012Validator(read_json(ROOT/'schemas/repository-alias.schema.json'),format_checker=formats)
    repository_errors=['Repository aliases: '+error.message for error in repository_validator.iter_errors(repository_declarations)]
    errors.extend(repository_errors)
    if not repository_errors:
        try:
            if attach_repository_aliases(rows,repository_declarations)!=rows:
                errors.append('Catalog is missing recorded repository aliases or their evidence; rebuild the catalog')
        except (ValueError,KeyError,TypeError) as error:
            errors.append('Repository aliases: '+str(error))
    registry=Registry().with_resource(resource_contract['$id'],Resource.from_contents(resource_contract))
    publication_validator=jsonschema.Draft202012Validator(read_json(ROOT/'schemas/publication-observation.schema.json'),registry=registry,format_checker=formats)
    publication_observations=read_jsonl(DATA/'publications.jsonl')
    publication_errors=[]
    for observation in publication_observations:
        identity=observation.get('id','<missing>') if isinstance(observation,dict) else '<invalid>'
        publication_errors.extend(f"Publication {identity}: {error.message}" for error in publication_validator.iter_errors(observation))
    errors.extend(publication_errors)
    if not publication_errors:
        try:
            attach_publications({row['id']:row for row in read_jsonl(DATA/'papers.jsonl')},publication_observations,publication_identity)
            errors.extend(alias_owner_errors(rows,publication_aliases(publication_observations,publication_identity),publication_identity))
        except ValueError as error:
            errors.append('Publication observations: '+str(error))
    decisions = read_json(DATA/'exclusions.json', [])
    scope_validator = jsonschema.Draft202012Validator(read_json(ROOT/'schemas/scope-decision.schema.json'), format_checker=formats)
    scope_errors = ['Scope decisions: '+error.message for error in scope_validator.iter_errors(decisions)]
    errors.extend(scope_errors)
    if not scope_errors:
        retained = {row['id']:row for row in read_jsonl(DATA/'papers.jsonl')}
        retained.update({row['id']:row for row in rows})
        try:
            outcomes = resolve_exclusions(retained, decisions, {row['id'] for row in read_jsonl(DATA/'metadata-updates.jsonl')})
        except ValueError as error:
            outcomes = []
            errors.append('Scope decisions: '+str(error))
        published = {row['id'] for row in rows}
        for outcome in outcomes:
            if outcome['status']=='excluded' and outcome['id'] in published:
                errors.append(outcome['id']+': scope-excluded record remains in the active catalog')
            if outcome['status']=='revalidation_pending' and outcome['id'] not in published:
                errors.append(outcome['id']+': stale scope decision must not suppress a record')
    if errors:
        raise ValueError("\n".join(errors[:40]))
    print(f"Validated {len(rows)} records: JSON Schema, identifiers, dates, source receipts, scoped licenses, and reviewed relation targets.")
    print_uncurated_linked_papers(uncurated_linked_papers(rows))
    for group in title_author_collisions(rows):
        print("Undecided duplicate: " + ", ".join(str(r.get("id")) for r in group) + " share a title and author list; record identifiers.preferred_arxiv on the duplicate.")
    for rid, path, current in unrecorded_hub_renames(rows, repository_aliases(repository_declarations, rows)):
        print(f"Unrecorded Hub rename: {rid} links {path}, but the Hub API names it {current}; record the rename in data/repository-aliases.json.")


def search(args):
    # Literal AND search is intentionally safe and works without a generated database.
    terms = args.query.casefold().split()
    target = publication_identity(args.query)  # a pasted URL folds to its record id (arXiv versions, GitHub paths)
    rows = read_jsonl(DATA / "catalog.jsonl")
    aliases = source_aliases(rows)
    target_id = aliases.get(target[0],target[0]) if target else None
    result = []
    for row in rows:
        if args.kind and row["kind"] != args.kind:
            continue
        if args.status and row["review_status"] != args.status:
            continue
        if args.environment and args.environment not in row["environments"]:
            continue
        if args.topic and args.topic not in row["topics"]:
            continue
        haystack = " ".join([row["id"], row["url"], row["name"], row["summary"] or "", *row["aliases"], *row["authors"], *row["topics"], *row["identifiers"].values(), publication_search_text(row)]).casefold()
        if all(term in haystack for term in terms) or target_id == row['id']:
            result.append(row)
    result.sort(key=lambda r: (r["review_status"] != "curated", r["name"].casefold()))
    limited = result[:args.limit] if args.limit else result
    if args.json:
        print(json.dumps({"total_matches": len(result), "returned": len(limited), "records": limited}, ensure_ascii=False, indent=2))
    else:
        print(f"{len(result)} matches; showing {len(limited)}")
        for r in limited:
            print(f"{r['name']} [{r['kind']} · {r['review_status']}] {r['id']}\n  {r['url']}")

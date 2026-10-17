#!/usr/bin/env python3
"""Reproducible CUA metadata catalog. Standard library only; no remote code execution."""
from __future__ import annotations

import argparse
from collections import Counter
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
import html
import http.client
import ipaddress
import json
import os
from pathlib import Path
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from arxiv_metadata import entry_snapshot, consider_paper, parse_search_feed

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "http"
DATA = ROOT / "data"
UA = "Awesome-CUA/0.1 (+https://github.com/reacher-z/Awesome-CUA)"
# Matched at the start of the URL path only, so a paper link in a query or fragment is not the URL's identity.
# The ID must end at a non-word character: extra digits or a malformed version never truncate into another ID.
ARXIV_RE = re.compile(r"/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?(?!\w)", re.I | re.A)
HF_PAPER_RE = re.compile(r"/papers/(\d{4}\.\d{4,5})(?:v\d+)?(?!\w)", re.I | re.A)
# A link may contain balanced "(...)", as in Mercury_(planet); the ")" closing a Markdown link is not part of it.
# Backticks, braces and backslashes are never literal URL characters: they end Markdown code, LaTeX/template and escaped-string links.
LINK_RE = re.compile(r"https?://(?:[^\s<>\[\]()\"'`{}\\]|\([^\s<>\[\]()\"'`{}\\]*\)|\()+")
KINDS = {"paper", "survey", "model", "dataset", "benchmark", "agent", "framework", "infrastructure", "product", "company", "tool", "learning"}
ENVIRONMENTS = {"web", "desktop", "android", "ios", "harmonyos", "windows", "macos", "linux", "cross-platform", "unspecified"}
STATUSES = {"curated", "metadata_verified"}
# The one topic vocabulary: key -> English and Chinese labels and a one-line definition.
TOPICS = json.loads((DATA / "topics.json").read_text(encoding="utf-8"))
SHRINK_FLOOR = 0.5  # A successful source response below this share of its retained candidates is held for review.
REFERENCE_SOURCE = "curated-references"  # Discovery provenance for arXiv papers that curated records cite in data/references.jsonl.
# MIN_RETRY_DELAY matches the 3.1 s spacing kept between arXiv requests (at most one per 3 s).
RETRY_STATUSES, MAX_ATTEMPTS, MAX_RETRY_AFTER, MIN_RETRY_DELAY = {429, 500, 502, 503, 504}, 3, 60, 3.1


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def read_jsonl(path):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines() if path.exists() else [], 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: {error.msg} (column {error.colno})") from error
    return rows


def write_json(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def write_jsonl(path, rows):
    atomic_write(path, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in sorted(rows, key=lambda r: r["id"])).encode())


def atomic_write(path, data):
    """Replace path through a flushed same-directory temporary, so a kill or full disk leaves the old file whole."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.urandom(6).hex()}.tmp")
    try:
        # Mode 0o666 lets the umask decide a new file's permissions, as Path.write_bytes would. Windows needs O_BINARY to keep LF bytes.
        with open(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o666), "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():  # os.fchmod only reached Windows in Python 3.13.
            os.chmod(temporary, path.stat().st_mode & 0o7777)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def retry_delay(error, attempt):
    """Seconds to wait before retrying a transient failure; None means stop now."""
    if isinstance(error, urllib.error.HTTPError) and error.code not in RETRY_STATUSES:
        return None
    if not isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return None
    header = str((getattr(error, "headers", None) or {}).get("Retry-After") or "").strip()
    if header.isdigit():
        delay = int(header)
    else:
        try:
            when = email.utils.parsedate_to_datetime(header)
            delay = max(0, (when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)).timestamp() - time.time())
        except (TypeError, ValueError):
            return MIN_RETRY_DELAY * 2 ** (attempt - 1) + random.uniform(0, 0.25)
    # A longer pause than one run should spend is left to the caller's rate-limit handling.
    return max(MIN_RETRY_DELAY, delay) if delay <= MAX_RETRY_AFTER else None


def fetch(url, refresh=False):
    """Cache successful GETs; persist failures as evidence, never as successful content."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    info_path, body_path = CACHE / f"{key}.json", CACHE / f"{key}.body"
    try:
        old = {} if refresh else read_json(info_path, {})
    except ValueError:  # Torn metadata is a cache miss; a successful fetch rewrites it.
        old = {}
    body = body_path.read_bytes() if old.get("ok") and body_path.exists() else None
    # The body is replaced before its metadata, so a run killed in between leaves a digest mismatch: refetch.
    if body is not None and hashlib.sha256(body).hexdigest() == old.get("sha256"):
        return old, body
    for attempt in range(1, MAX_ATTEMPTS + 1):
        info = {"url": url, "retrieved_at": now(), "ok": False, "request_attempts": attempt}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/atom+xml, text/html, text/plain, */*"})
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read(10_000_001)
                if len(body) > 10_000_000:
                    raise ValueError("response exceeds 10 MB metadata budget")
                info.update(ok=True, status=response.status, final_url=response.url,
                            content_type=response.headers.get("Content-Type", ""),
                            sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
            atomic_write(body_path, body)
            write_json(info_path, info)
            return info, body
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ValueError, OSError) as error:
            info.update(error=str(error), status=getattr(error, "code", None))
            headers = getattr(error, "headers", None)
            if headers and headers.get('Retry-After'):
                info['retry_after'] = headers.get('Retry-After')
            delay = retry_delay(error, attempt) if attempt < MAX_ATTEMPTS else None
            if delay is None:
                break
            time.sleep(delay)
    # Keep the previous successful cache intact when a refresh fails.
    write_json(CACHE / f"{key}.error.json", info)
    return info, b""


def canonical(url, *, allow_doi=False):
    """Resource identity: arXiv version folding, GitHub repo folding, URL cleanup."""
    if not isinstance(url,str):return None
    candidate=html.unescape(url).strip()
    try:
        doi_parts=urllib.parse.urlsplit(candidate)
        if (doi_parts.hostname or '').lower() in {'doi.org','www.doi.org','dx.doi.org'}:
            if doi_parts.scheme not in {'http','https'} or doi_parts.username is not None or doi_parts.password is not None:
                return None
            if any(not key.startswith('utm_') for key,_ in urllib.parse.parse_qsl(doi_parts.query)):
                return None
            doi=urllib.parse.unquote(doi_parts.path.lstrip('/'),errors='strict')
            # arXiv's DataCite DOI names the preprint itself, so it folds into the arXiv record even where bare DOIs are ignored.
            arxiv_doi=re.match(r'10\.48550/arxiv\.(\d{4}\.\d{4,5})(?:v\d+)?(?!\w)',doi,re.I|re.A)
            if arxiv_doi:return f'arxiv:{arxiv_doi[1]}',f'https://arxiv.org/abs/{arxiv_doi[1]}','arxiv'
            if not allow_doi or not re.fullmatch(r'10\.\d{4,9}/[^\s\\]+',doi,re.I):return None
            clean='https://doi.org/'+urllib.parse.quote(doi.casefold(),safe='/():;._-')
            return 'url:'+hashlib.sha256(clean.encode()).hexdigest()[:20],clean,'url'
    except (ValueError,UnicodeError):
        return None
    url = html.unescape(url).strip()
    # Trailing prose punctuation is not part of a link; a ")" is only when it closes nothing in the URL.
    # Backticks, braces and backslashes, raw or percent-encoded, are Markdown, LaTeX or string-escape residue.
    while tail := re.search(r"(?:[.,;:`{}\\)]|%(?:60|7B|7D|5C))\Z", url, re.I):
        if tail[0] == ")" and url.count(")") <= url.count("("):
            break
        url = url[:tail.start()]
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    host = parts.hostname.lower() if parts.hostname else ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    # Loopback, private-network and other non-public addresses are local services in instructions, not resources.
    if host == "localhost" or host.endswith((".localhost", ".local")) or address is not None and not address.is_global:
        return None
    hub = host in {"huggingface.co", "www.huggingface.co", "hf.co"}
    # arXiv mirrors and services (web3., browse., export., ar5iv.labs.) all serve the same IDs.
    if hub or host in {"arxiv.org", "ar5iv.org"} or host.endswith(".arxiv.org"):
        match = (HF_PAPER_RE if hub else ARXIV_RE).match(parts.path)
        if match:
            aid = match.group(1)
            return f"arxiv:{aid}", f"https://arxiv.org/abs/{aid}", "arxiv"
    if host in {"github.com", "www.github.com"}:
        segments = parts.path.strip("/").split("/")
        if len(segments) < 2 or segments[0].lower() in {"topics", "orgs", "users", "settings", "sponsors", "features", "collections", "marketplace", "user-attachments"}:
            return None
        owner, repo = segments[:2]
        repo = re.sub(r"\.git$", "", repo, flags=re.I)
        if not re.fullmatch(r"[\w.-]+", owner) or not re.fullmatch(r"[\w.-]+", repo):
            return None
        if len(segments) > 2 and segments[2] not in {"tree", "blob"}:
            return None
        return f"github:{owner.lower()}/{repo.lower()}", f"https://github.com/{owner}/{repo}", "github"
    if host.endswith(("shields.io", "githubusercontent.com")) or host in {"doi.org", "img.shields.io", "badge.fury.io", "twitter.com", "x.com", "discord.gg", "linkedin.com", "www.linkedin.com", "youtube.com", "www.youtube.com"}:
        return None
    if re.search(r"\.(png|svg|jpg|jpeg|gif|webp)$", parts.path, re.I):
        return None
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.startswith("utm_")])
    clean = urllib.parse.urlunsplit(("https", host, parts.path.rstrip("/"), query, ""))
    return "url:" + hashlib.sha256(clean.encode()).hexdigest()[:20], clean, "url"


def publication_identity(url):
    """Explicit bibliography identity; general discovery still ignores bare DOI links."""
    return canonical(url,allow_doi=True)


def editorial_identity(row):
    return canonical(row['url'],allow_doi=isinstance(row.get('kind'),str) and row['kind'] in {'paper','survey'})


def source_links(source, body):
    """Parse only declared source formats; provider metadata remains a candidate."""
    parser = source.get('parser', 'links')
    if parser == 'huggingface_models':
        url = urllib.parse.urlsplit(source['url'])
        params = urllib.parse.parse_qs(url.query)
        if url.scheme != 'https' or url.hostname != 'huggingface.co' or url.path != '/api/models':
            raise ValueError('Model-index source must be the official Hugging Face models API')
        author = params.get('author', [''])[0]
        limit = params.get('limit', [''])[0]
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', author) or not limit.isdigit() or not 1 <= int(limit) <= 100:
            raise ValueError('Model-index source requires one publisher and a limit of 1..100')
        payload = json.loads(body)
        if not isinstance(payload, list) or len(payload) > int(limit):
            raise ValueError('Model-index response exceeds its declared window or is not a list')
        result = []
        for item in payload:
            identity = item.get('id') if isinstance(item, dict) else None
            if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', identity):
                raise ValueError('Model-index entry has an invalid repository identifier')
            if identity.split('/')[0].casefold() != author.casefold():
                raise ValueError('Model-index entry is outside the declared publisher')
            result.append((None, 'Publisher model index; relevance and variant identity await review', 'https://huggingface.co/' + identity))
        return result
    if parser != 'links':
        raise ValueError('Unknown discovery source parser: ' + str(parser))
    result, heading = [], ''
    for line_no, line in enumerate(body.decode('utf-8', errors='replace').splitlines(), 1):
        if line.startswith('#'):
            heading = re.sub(r'[#*_]', '', line).strip()[:140]
        result.extend((line_no, heading, url) for url in LINK_RE.findall(line))
    return result


def discovery_occurrence(source_id, info, line=None, section=''):
    """Keep source facts with the occurrence, even after its latest run fails."""
    evidence = {key: info[key] for key in ('url', 'sha256', 'retrieved_at')}
    identity = json.dumps([source_id, evidence['url'], evidence['sha256']], separators=(',', ':'))
    return {'source_id': source_id, 'line': line, 'section': section,
            'snapshot_sha256': evidence['sha256'],
            'receipt_id': 'discovery:' + hashlib.sha256(identity.encode()).hexdigest(),
            'evidence': evidence}


def retain_discovery_evidence(rows, previous_runs):
    """Backfill only matching old receipts; never relabel old content as current."""
    for row in rows:
        for occurrence in row.get('discovered_in', []):
            if occurrence.get('evidence'):
                continue
            previous = previous_runs.get(occurrence['source_id'], {})
            info = previous.get('evidence', previous)
            if (info.get('ok') and not previous.get('parse_error')
                    and info.get('sha256') == occurrence.get('snapshot_sha256')
                    and all(info.get(key) for key in ('url', 'sha256', 'retrieved_at'))):
                receipt = discovery_occurrence(occurrence['source_id'], info)
                occurrence.update({key: receipt[key] for key in ('receipt_id', 'evidence')})


def reconcile_candidates(rows):
    """Apply the current URL rules to stored candidates: a row whose URL they now clean merges into that URL's identity; one they reject is dropped."""
    parsed = [(row, canonical(row["url"])) for row in rows]
    result = {row["id"]: row for row, identity in parsed if identity and identity[1] == row["url"]}
    for row, identity in parsed:
        if identity and identity[1] != row["url"]:
            rid, clean, provider = identity
            target = result.setdefault(rid, {"id": rid, "url": clean, "provider": provider, "first_discovered_at": row["first_discovered_at"], "discovered_in": []})
            target["first_discovered_at"] = min(target["first_discovered_at"], row["first_discovered_at"])
            target["discovered_in"] += [o for o in row["discovered_in"] if o not in target["discovered_in"]]
    return result


def reference_candidates(rows):
    """Add arXiv papers cited by curated records to the discovery population: harvest verifies their metadata, never their relevance."""
    curated = {r["id"] for r in read_jsonl(DATA / "catalog.jsonl") if r["review_status"] == "curated"}
    refs = sorted((e for e in read_jsonl(DATA / "references.jsonl") if e["relation"] == "mentions" and e["source_id"] in curated
                   and e["target_id"].startswith("arxiv:")), key=lambda e: (e["target_id"], e["source_id"]))
    first = {}
    for e in refs:
        first[e["target_id"]] = min(first.get(e["target_id"], e["retrieved_at"]), e["retrieved_at"])
    # Like a source refresh, the current references replace the old ones; an uncited paper stays a historical candidate.
    for row in rows.values():
        row["discovered_in"] = [o for o in row["discovered_in"] if o["source_id"] != REFERENCE_SOURCE]
    for e in refs:
        rid = e["target_id"]
        row = rows.setdefault(rid, {"id": rid, "url": "https://arxiv.org/abs/" + rid.split(":", 1)[1], "provider": "arxiv",
            "first_discovered_at": first[rid], "discovered_in": []})
        row["discovered_in"].append(discovery_occurrence(REFERENCE_SOURCE, {"url": e["source_url"], "sha256": e["source_sha256"],
            "retrieved_at": e["retrieved_at"]}, section=f"Cited by {e['source_id']}; relevance awaits review"))
    print(f"{REFERENCE_SOURCE}: {len(refs)} citations of {len(first)} arXiv identifiers", flush=True)


def discover(args):
    sources = read_json(DATA / "sources.json", [])
    existing = reconcile_candidates(read_jsonl(DATA / "candidates.jsonl"))
    previous = {r["id"]: r for r in read_json(DATA / "discovery-runs.json", [])}
    retain_discovery_evidence(existing.values(), previous)
    # Count retained provenance rather than the last manifest, which a failed run resets to zero.
    retained = Counter(sid for row in existing.values() for sid in {o["source_id"] for o in row["discovered_in"]})
    accepted = set(getattr(args, "accept_shrink", None) or ())
    manifests, rate_limited_hosts = {}, set()
    started = now()
    for source in sources:
        host = urllib.parse.urlsplit(source['url']).hostname
        deferred = host in rate_limited_hosts
        if deferred:
            info, body = {'url': source['url'], 'retrieved_at': now(), 'ok': False,
                'error': 'Deferred after an HTTP 429 from this host; no request made.'}, b''
        else:
            info, body = fetch(source["url"], args.refresh)
        manifest = {"id": source["id"], **info, "unique_resources": 0,
            'run_started_at': started, 'provider_host': host,
            'request_attempted': not deferred, 'state': 'deferred' if deferred else 'failed'}
        if info.get('status') == 429:
            rate_limited_hosts.add(host)
        if not info["ok"]:
            manifests[source["id"]] = manifest
            print(f"FAILED {source['id']}: {info['error']}", flush=True)
            continue
        try:
            links = source_links(source, body)
        except (ValueError, TypeError) as error:
            manifests[source['id']] = {**manifest, 'ok': False, 'parse_error': str(error)}
            print(f"FAILED {source['id']}: {error}", flush=True)
            continue
        seen, found = set(), []
        for line_no, heading, url in links:
            parsed = canonical(url)
            if not parsed:
                continue
            rid, clean, provider = parsed
            if rid in seen or clean.lower() == source["homepage"].rstrip("/").lower():
                continue
            seen.add(rid)
            found.append((line_no, heading, rid, clean, provider))
        before = retained[source["id"]]
        if len(seen) < before * SHRINK_FLOOR and source["id"] not in accepted:
            error = f"suspicious shrink: {before} -> {len(seen)}; previous provenance retained (rerun with --accept-shrink {source['id']} to apply)"
            manifests[source["id"]] = {**manifest, "ok": False, "error": error}
            print(f"FAILED {source['id']}: {error}", flush=True)
            continue
        # Replace this source's old occurrences so deleted links remain historical candidates,
        # but cannot inflate current source coverage.
        for row in existing.values():
            row["discovered_in"] = [o for o in row["discovered_in"] if o["source_id"] != source["id"]]
        for line_no, heading, rid, clean, provider in found:
            row = existing.setdefault(rid, {"id": rid, "url": clean, "provider": provider,
                "first_discovered_at": info["retrieved_at"], "discovered_in": []})
            row["discovered_in"].append(discovery_occurrence(source['id'],
                {**info, 'url': source['url']}, line_no, heading))
        manifest["unique_resources"] = len(seen)
        manifest['state'] = 'success'
        manifests[source["id"]] = manifest
        print(f"{source['id']}: {len(seen)} unique identifiers", flush=True)
    reference_candidates(existing)
    for row in existing.values():
        row["discovered_in"].sort(key=lambda x: (x["source_id"], x["line"]))
    write_jsonl(DATA / "candidates.jsonl", existing.values())
    write_json(DATA / "discovery-runs.json", sorted(manifests.values(), key=lambda r: r["id"]))
    print(json.dumps(Counter(r["provider"] for r in existing.values())))


def arxiv_entry(entry, evidence):
    ns = {"a": "http://www.w3.org/2005/Atom", "ar": "http://arxiv.org/schemas/atom"}
    get = lambda key: " ".join((entry.findtext("a:" + key, default="", namespaces=ns)).split())
    parsed = canonical(get("id"))
    if not parsed or parsed[2] != "arxiv":
        return None
    rid, url, _ = parsed
    title = get("title")
    if not title:
        return None
    return {"id": rid, "name": title, "kind": "paper", "url": url,
        "aliases": [], "environments": ["unspecified"], "topics": [],
        "summary": None, "review_status": "metadata_verified",
        "published_at": get("published")[:10] or None, "updated_at": get("updated")[:10] or None,
        "authors": [" ".join((a.findtext("a:name", default="", namespaces=ns)).split()) for a in entry.findall("a:author", ns)],
        "identifiers": {"arxiv": rid.split(":", 1)[1]},
        "details": {"arxiv_snapshot": entry_snapshot(entry, rid.split(":", 1)[1])},
        "links": [{"rel": "paper", "url": url}], "relations": [],
        "licenses": {"code": None, "data": None, "weights": None, "document": None},
        "evidence": [{"role": "primary", "method": "arxiv_api", "supports": ["name", "authors", "published_at", "updated_at", "identifiers.arxiv", "details.arxiv_snapshot"], **evidence}],
        "last_verified_at": evidence["retrieved_at"],
        "notes": "Bibliographic metadata checked against arXiv. Relevance and taxonomy await editorial review; presence is not an endorsement."}


def harvest(args):
    candidates = read_jsonl(DATA / "candidates.jsonl")
    records = {r["id"]: r for r in read_jsonl(DATA / "papers.jsonl")}
    proposals = {r['id']: r for r in read_jsonl(DATA / 'metadata-updates.jsonl')}
    ids = sorted({r["id"].split(":", 1)[1] for r in candidates if r["provider"] == "arxiv" and (args.refresh or r["id"] not in records)})
    if args.limit:
        ids = ids[:args.limit]
    failures = []
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": ",".join(batch), "max_results": len(batch)})
        info, body = fetch(url, args.refresh)
        got, invalid = set(), {}
        if info["ok"]:
            try:
                root = ET.fromstring(body)
                if root.tag != '{http://www.w3.org/2005/Atom}feed':
                    raise ValueError('arXiv response is not an Atom feed')
                for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                    try:
                        row = arxiv_entry(entry, {k: info[k] for k in ("url", "retrieved_at", "sha256")})
                    except ValueError as error:
                        parsed = canonical(entry.findtext("{http://www.w3.org/2005/Atom}id", ""))
                        if parsed and parsed[2] == "arxiv":
                            invalid[parsed[0].split(":", 1)[1]] = f"invalid Atom entry: {error}"
                        continue
                    if row and row["id"].split(":", 1)[1] in batch:
                        consider_paper(row, records, proposals, info['retrieved_at'])
                        got.add(row["id"].split(":", 1)[1])
            except (ET.ParseError, ValueError) as error:
                info["error"] = str(error)
        for aid in sorted(set(batch) - got):
            failures.append({"id": f"arxiv:{aid}", "checked_at": info["retrieved_at"], "error": invalid.get(aid) or info.get("error", "identifier absent from API response")})
        print(f"arXiv {start + 1}-{start + len(batch)}/{len(ids)}: {len(got)} metadata records", flush=True)
        write_jsonl(DATA / "papers.jsonl", records.values())
        write_jsonl(DATA / "metadata-updates.jsonl", proposals.values())
        if info.get('status') == 429:
            for aid in ids[start + len(batch):]:
                failures.append({'id': 'arxiv:' + aid, 'checked_at': info['retrieved_at'],
                    'deferred': True, 'request_attempted': False,
                    'error': 'Deferred after an arXiv HTTP 429; no additional request made in this harvest.'})
            break
        if start + 50 < len(ids):
            time.sleep(3.1)
    write_jsonl(DATA / "harvest-failures.jsonl", failures)
    print(f"Stored {len(records)} papers; {len(failures)} unresolved in this run.")


def search_arxiv(args):
    """Primary-source discovery with persisted queries and explicit pagination limits."""
    query = 'ti:"computer use" OR ti:"computer-use" OR ti:"GUI agent" OR ti:"GUI agents" OR ti:"GUI grounding" OR ti:"web agents" OR ti:"browser agent"'
    cutoff = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M")
    query = f'({query}) AND submittedDate:[200001010000 TO {cutoff}]'
    records = {r["id"]: r for r in read_jsonl(DATA / "papers.jsonl")}
    proposals = {r['id']: r for r in read_jsonl(DATA / 'metadata-updates.jsonl')}
    candidates = {r["id"]: r for r in read_jsonl(DATA / "candidates.jsonl")}
    pages, seen = [], set()
    start, total = 0, None
    ceiling = args.limit or 5000
    while start < ceiling and (total is None or start < total):
        batch_size = min(100, ceiling-start)
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": query, "start": start, "max_results": batch_size, "sortBy": "submittedDate", "sortOrder": "descending"})
        info, body = fetch(url, args.refresh)
        if not info["ok"]:
            pages.append(info)
            break
        try:
            entries,total = parse_search_feed(body,total,batch_size)
        except (ET.ParseError,ValueError) as error:
            pages.append({**info, "ok": False, "error": str(error)})
            break
        page = {**info, "start": start, "returned": len(entries)}
        pages.append(page)
        for entry in entries:
            try:
                row = arxiv_entry(entry, {k: info[k] for k in ("url", "retrieved_at", "sha256")})
            except ValueError as error:
                page.setdefault("entry_errors", []).append({"id": " ".join(entry.findtext("{http://www.w3.org/2005/Atom}id", "").split()), "error": str(error)})
                continue
            if not row:
                continue
            rid = row["id"]
            consider_paper(row,records,proposals,info['retrieved_at'])
            seen.add(rid)
            candidate = candidates.setdefault(rid, {"id": rid, "url": row["url"], "provider": "arxiv", "first_discovered_at": info["retrieved_at"], "discovered_in": []})
            candidate["discovered_in"] = [o for o in candidate["discovered_in"] if o["source_id"] != "arxiv-title-search"]
            candidate["discovered_in"].append({"source_id": "arxiv-title-search", "line": None, "section": "Title query; relevance not reviewed", "snapshot_sha256": info["sha256"]})
        print(f"arXiv search {start + len(entries)}/{total}", flush=True)
        write_jsonl(DATA / "papers.jsonl", records.values())
        write_jsonl(DATA / "metadata-updates.jsonl", proposals.values())
        write_jsonl(DATA / "candidates.jsonl", candidates.values())
        if not entries:
            break
        start += len(entries)
        if start < min(total, ceiling):
            time.sleep(3.1)
    write_json(DATA / "arxiv-search.json", {"id": "arxiv-title-search", "query": query, "cutoff_utc": cutoff,
        "reported_total": total, "unique_returned": len(seen), "complete": total is not None and len(seen) == total and bool(pages) and all(page.get('ok') and not page.get('entry_errors') for page in pages),
        "pages": pages, "warning": "A title query is a discovery population, not the whole field. Search results are metadata-verified, not editorially curated."})


def require_editorial_identities(rows):
    """Stop before any network work if an editorial URL has no resource identity."""
    invalid = [f"INVALID {row.get('name', '')}: {row['url']} has no canonical identity" for row in rows if not editorial_identity(row)]
    if invalid:
        raise SystemExit("\n".join(invalid))


def select_editorial(rows, ids):
    """Keep only the entries named by --id; an unknown ID stops the run before any network work."""
    if not ids:
        return rows
    known = {row.get("id", editorial_identity(row)[0]) for row in rows}
    unknown = [rid for rid in ids if rid not in known]
    if unknown:
        raise SystemExit("\n".join(f"UNKNOWN {rid}: no entry in data/editorial.json has this ID" for rid in unknown))
    return [row for row in rows if row.get("id", editorial_identity(row)[0]) in ids]


def verify_editorial(args):
    """Retrieve first-party evidence for editorial entries; never promote on HTTP status alone."""
    rows = read_json(DATA / "editorial.json", [])
    require_editorial_identities(rows)
    rows = select_editorial(rows, getattr(args, "id", None))
    previous = {r["id"]: r for r in read_jsonl(DATA / "primary-evidence.jsonl")}

    def one(row):
        rid, url, provider = editorial_identity(row)
        rid = row.get("id", rid)
        url = row["url"]
        urls = row.get("evidence_urls", [])
        if not urls:
            if provider == "github":
                repo = url.split("github.com/", 1)[1]
                urls = [f"https://raw.githubusercontent.com/{repo}/HEAD/README.md", f"https://raw.githubusercontent.com/{repo}/HEAD/README.MD", f"https://raw.githubusercontent.com/{repo}/HEAD/readme.md", url]
            elif url.startswith("https://huggingface.co/datasets/"):
                urls = [url.replace("huggingface.co/datasets/", "huggingface.co/api/datasets/")]
            elif url.startswith("https://huggingface.co/") and "/collections/" not in url:
                urls = [url.replace("huggingface.co/", "huggingface.co/api/models/")]
            else:
                urls = [url]
        attempts = []
        for evidence_url in urls:
            info, body = fetch(evidence_url, args.refresh)
            attempts.append(info)
            if info["ok"]:
                if body.startswith(b"%PDF-"):
                    # Binary PDF text is not a title check. Only unchanged, already
                    # reviewed bytes may retain their content verification.
                    matched = []
                    ok = (row.get("editorial_reviewed") is True
                          and info.get("sha256") == row.get("reviewed_sha256")
                          and info.get("sha256") == hashlib.sha256(body).hexdigest())
                    match_method = "reviewed_pdf_sha256" if ok else None
                else:
                    text = body.decode("utf-8", errors="replace")
                    terms = row.get("verify_terms", [row["name"]])
                    matched = [term for term in terms if " ".join(term.casefold().split()) in " ".join(text.casefold().split())]
                    # A soft-200 challenge/landing page must not be treated as primary evidence.
                    blocked = any(s in text[:15000].lower() for s in ("just a moment...", "checking your browser", "verify you are human"))
                    ok = bool(matched) and not blocked
                    match_method = "text_terms" if ok else None
                result = {"id": rid, "source_url": url, **info, "content_matched": ok, "matched_terms": matched,
                          "content_match_method": match_method, "attempts": len(attempts)}
                if ok:
                    for supporting in row.get("additional_evidence", []):
                        supporting_info, _ = fetch(supporting["url"], args.refresh)
                        if not supporting_info["ok"] or supporting_info.get("sha256") != supporting["sha256"]:
                            result.update(content_matched=False, error="supporting source unavailable or changed; editorial review required: " + supporting["url"])
                            break
                    return result
        return {"id": rid, "source_url": url, **attempts[-1], "content_matched": False, "attempts": len(attempts)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(one, rows):
            previous[result["id"]] = result
            print(f"{'MATCH' if result['content_matched'] else 'REVIEW'} {result['id']} {result.get('status')}", flush=True)
    write_jsonl(DATA / "primary-evidence.jsonl", previous.values())


def cached_body(url):
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".body")
    return path.read_bytes() if path.exists() else b""


def string_list(value):
    """Hub card fields may hold a scalar or a list; keep only the strings."""
    return [value] if isinstance(value, str) else [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def card_license(card):
    """The top-level `license` of a Hub card's YAML header: a plain or quoted name, or a flow or block list of names."""
    header = re.match(r"\A---\n(.*?)\n---", card.replace("\r\n", "\n"), re.S)
    found = re.search(r"^license:([^\n]*)((?:\n[ \t]*-[^\n]*)*)", header[1], re.M) if header else None
    uncomment = lambda text: re.sub(r"(?:^|[ \t])#.*", "", text).strip()
    value = uncomment(found[1]) if found else ""
    flow = value.startswith("[") and value.endswith("]")
    items = value[1:-1].split(",") if flow else [value] if value else re.findall(r"-([^\n]*)", found[2]) if found else []
    names = [uncomment(item).strip("\"'") for item in items]
    if not names or not all(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name) for name in names):
        return None
    return names if flow or not value else names[0]


LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENSE.rst", "LICENCE", "COPYING")
# A GNU title must open the verbatim FSF text, not a project notice; that text does not say whether
# later versions apply, so these identifiers name the text, not -only or -or-later.
FSF_TEXT = r"\s+Copyright \(C\) [\d, ]+Free Software Foundation, Inc\."
LICENSE_HEADERS = (
    ("GPL-2.0", r"GNU GENERAL PUBLIC LICENSE\s+Version 2, June 1991" + FSF_TEXT),
    ("GPL-3.0", r"GNU GENERAL PUBLIC LICENSE\s+Version 3, 29 June 2007" + FSF_TEXT),
    ("AGPL-3.0", r"GNU AFFERO GENERAL PUBLIC LICENSE\s+Version 3, 19 November 2007" + FSF_TEXT),
    ("LGPL-2.1", r"GNU LESSER GENERAL PUBLIC LICENSE\s+Version 2\.1, February 1999" + FSF_TEXT),
    ("LGPL-3.0", r"GNU LESSER GENERAL PUBLIC LICENSE\s+Version 3, 29 June 2007" + FSF_TEXT),
    ("MPL-2.0", r"Mozilla Public License,? Version 2\.0\s+(?:=+\s+)?1\. Definitions\b"),
    ("ISC", r"(?:The )?ISC License(?: \(ISC\))?\s+(?:Copyright\b[^\n]*\s+)+Permission to use, copy, modify, and(?:/or)? distribute this software for any\s+purpose with or without fee is hereby granted"),
    ("Unlicense", r"This is free and unencumbered software released into the public domain\.\s+Anyone is free to copy, modify, publish, use, compile, sell, or\s+distribute this software"),
)


def detect_code_license(text):
    """Identify a standard code license from the opening header of a LICENSE file."""
    head = text[:1000]
    composite_or_custom = bool(
        re.search(
            r"\b(?:Apache License|BSD [23]-Clause|GNU (?:Affero |Lesser )?General Public License|[AL]?GPL(?:v[23])?|Mozilla Public License|Creative Commons|CC-BY|Proprietary)\b",
            head,
            re.I,
        )
    )
    if not composite_or_custom and re.search(r"^[ \t]*(?:The )?MIT License[ \t]*\r?$", head, re.I | re.M):
        return "MIT"
    if "Apache License" in text[:250] and "Version 2.0" in text[:300]:
        return "Apache-2.0"
    if "BSD 3-Clause" in text[:100]:
        return "BSD-3-Clause"
    if "BSD 2-Clause" in text[:100]:
        return "BSD-2-Clause"
    # Other standard texts must open the file: their title, then a fixed line of the standard body.
    for spdx, header in LICENSE_HEADERS:
        if re.match(r"\s*" + header, text, re.I):
            return spdx
    cc = re.match(r"\s*Attribution(-NonCommercial)?(-ShareAlike|-NoDerivatives)? 4\.0 International\s+=+\s+Creative Commons Corporation\b", text)
    if cc:
        return "CC-BY" + ("-NC" if cc[1] else "") + {"-ShareAlike": "-SA", "-NoDerivatives": "-ND"}.get(cc[2], "") + "-4.0"
    return None


def enrich(args):
    """Extract declared licenses and outbound references without inferring semantic relationships."""
    rows = read_json(DATA / "editorial.json", [])
    require_editorial_identities(rows)
    rows = select_editorial(rows, getattr(args, "id", None))
    evidence = {r["id"]: r for r in read_jsonl(DATA / "primary-evidence.jsonl")}
    previous = {r["id"]: r for r in read_jsonl(DATA / "enrichment.jsonl")}
    stale, invalid = [], []

    def one(row):
        rid, url, provider = editorial_identity(row)
        rid = row.get("id", rid)
        ev = evidence.get(rid)
        if not ev or not ev.get("content_matched"):
            return None
        body = cached_body(ev["url"])
        # Results are stamped with the receipt digest, so derive them only from that exact body.
        if hashlib.sha256(body).hexdigest() != ev["sha256"]:
            stale.append(rid)
            return None
        raw = body.decode("utf-8", errors="replace")
        if provider == "github" and "<html" in raw.lower():
            # Restrict reference extraction to the rendered README, excluding site navigation.
            article = re.search(r"<article\b[^>]*>(.*?)</article>", raw, re.S)
            raw = article.group(1) if article else ""
        result = {"id": rid, "evidence_sha256": ev["sha256"], "licenses": {}, "details": {}, "references": [], "evidence": []}
        source = urllib.parse.urlsplit(ev["url"])
        hub_source = source.hostname == "huggingface.co"
        # A raw Hub card may be the reviewed primary source rather than the API.
        # Read only an explicit declaration in its metadata header; do not
        # inherit a dataset/model license from a linked repository or prose.
        # A dataset repository's card covers data whatever the catalog kind, e.g. a benchmark.
        if hub_source and "/raw/" in source.path:
            declaration = card_license(raw)
            slot = "data" if source.path.startswith("/datasets/") or row["kind"] == "dataset" else "weights" if row["kind"] == "model" else None
            if declaration and slot:
                result["licenses"][slot] = {"declared": declaration, "url": ev["url"], "retrieved_at": ev["retrieved_at"], "basis": "publisher model/dataset card metadata; third-party assets retain their own terms"}
                result["evidence"].append({"role": "primary", "method": "huggingface_card", "supports": [f"licenses.{slot}"], **{k: ev[k] for k in ("url", "sha256", "retrieved_at")}})
        if hub_source and source.path.startswith(("/api/datasets/", "/api/models/")):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = None
            if not isinstance(payload, dict):
                invalid.append(rid)
            else:
                card = payload.get("cardData") if isinstance(payload.get("cardData"), dict) else {}
                slot = "data" if source.path.startswith("/api/datasets/") else "weights"
                license_name = card.get("license")
                # A card may declare one license or a list of them; keep the string, or the list's string entries.
                declared = string_list(license_name) if isinstance(license_name, list) else license_name if isinstance(license_name, str) and license_name.strip() else None
                if declared:
                    result["licenses"][slot] = {"declared": declared, "url": row["url"], "retrieved_at": ev["retrieved_at"], "basis": "publisher model/dataset card"}
                result["details"] = {"hub_id": payload.get("id"), "gated": payload.get("gated"), "disabled": payload.get("disabled"),
                    "languages": string_list(card.get("language")), "modalities": [t.split(":", 1)[1] for t in string_list(payload.get("tags")) if t.startswith("modality:")],
                    "size_category_reported": string_list(card.get("size_categories")) or None, "download_url": row["url"] + "/tree/main"}
                # Dataset size tags may count archive files, not samples; never convert them into sample counts.
                result["evidence"].append({"role": "primary", "method": "huggingface_api", "url": ev["url"], "sha256": ev["sha256"], "retrieved_at": ev["retrieved_at"], "supports": ["details", f"licenses.{slot}"]})
        elif row["kind"] == "dataset" and source.hostname == "dataverse.harvard.edu" and source.path.startswith("/api/datasets/"):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = None
            dataset = payload.get("data") if isinstance(payload, dict) and payload.get("status") == "OK" else None
            version = dataset.get("latestVersion") if isinstance(dataset, dict) else None
            if (isinstance(version, dict) and dataset.get("datasetType") == "dataset"
                    and version.get("datasetType") == "dataset" and isinstance(version.get("metadataBlocks"), dict)):
                license_metadata = version.get("license")
                if not isinstance(license_metadata, dict):
                    license_metadata = None
                result["details"]["dataverse"] = {
                    "publisher": dataset.get("publisher"), "persistent_url": dataset.get("persistentUrl"),
                    "publication_date": dataset.get("publicationDate"), "version_number": version.get("versionNumber"),
                    "version_minor_number": version.get("versionMinorNumber"), "version_state": version.get("versionState"),
                    "released_at": version.get("releaseTime"), "license": license_metadata,
                    "file_count": len(version["files"]) if isinstance(version.get("files"), list) else None,
                }
                # Keep the publisher's license text/URI verbatim, including its scheme.
                # The HTTPS API receipt is the license source; files are not samples,
                # and neither fileAccessRequest nor a DOI establishes a download URL.
                supports = ["details.dataverse"]
                license_name = license_metadata.get("name") if license_metadata else None
                if isinstance(license_name, str) and license_name.strip():
                    result["licenses"]["data"] = {"declared": license_name, "url": ev["url"], "retrieved_at": ev["retrieved_at"],
                        "basis": "publisher Dataverse dataset-version license metadata; original declaration and URI retained in details.dataverse.license"}
                    supports.append("licenses.data")
                result["evidence"].append({"role": "primary", "method": "dataverse_api", "supports": supports,
                    **{k: ev[k] for k in ("url", "sha256", "retrieved_at")}})
        if provider == "github":
            repo = url.split("github.com/", 1)[1]
            for filename in LICENSE_FILES:
                license_url = f"https://raw.githubusercontent.com/{repo}/HEAD/{filename}"
                info, body = fetch(license_url, args.refresh)
                if not info["ok"]:
                    if info.get("status") == 404:
                        continue
                    # An unreachable candidate is unknown, not absent, and a later candidate must not outrank it:
                    # keep the recorded code license and its receipt.
                    old = previous.get(rid, {})
                    if "code" in old.get("licenses", {}):
                        result["licenses"]["code"] = old["licenses"]["code"]
                        result["evidence"] += [e for e in old.get("evidence", []) if e.get("method") == "license_header"]
                    break
                license_text = body.decode("utf-8", errors="replace")
                declared = detect_code_license(license_text)
                # Ambiguous/custom/composite declarations stay unknown rather than being guessed.
                if declared:
                    result["licenses"]["code"] = {"declared": declared, "url": license_url, "retrieved_at": info["retrieved_at"], "basis": "repository LICENSE header; " + ("GNU text does not say -only or -or-later; " if "GPL" in declared else "") + "not a weights/data license"}
                    result["evidence"].append({"role": "primary", "method": "license_header", "supports": ["licenses.code"], **{k: info[k] for k in ("url", "sha256", "retrieved_at")}})
                break
        seen = set()
        if provider == "arxiv":
            # A batched API response is not a paper's reference list.
            return result
        for link in LINK_RE.findall(raw):
            parsed = canonical(link)
            if not parsed:
                continue
            target, clean, target_provider = parsed
            if target == rid or target in seen or not (target_provider in {"arxiv", "github"} or clean.startswith("https://huggingface.co/")):
                continue
            seen.add(target)
            result["references"].append({"target_id": target, "target_url": clean, "relation": "mentions", "source_url": ev["url"], "source_sha256": ev["sha256"], "retrieved_at": ev["retrieved_at"]})
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(one, rows):
            if result:
                previous[result["id"]] = result
    write_jsonl(DATA / "enrichment.jsonl", previous.values())
    for rid in sorted(invalid):
        print(f"INVALID {rid}: Hugging Face API body is not a JSON object; no Hub metadata extracted")
    for rid in sorted(stale):
        print(f"STALE {rid}: cached evidence body is missing or differs from its receipt; previous enrichment kept, rerun verify")
    print(f"Enrichment receipts: {len(previous)}; {len(stale)} skipped for missing or stale evidence bodies")


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or greater: {value}")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, function in [("discover", discover), ("harvest", harvest), ("search-arxiv", search_arxiv), ("verify", verify_editorial), ("enrich", enrich)]:
        command = sub.add_parser(name)
        command.add_argument("--refresh", action="store_true", help="fetch new snapshots instead of reusing local cache")
        command.add_argument("--limit", type=int, default=0)
        if function in (verify_editorial, enrich):
            command.add_argument("--id", action="append", metavar="ID", help="only the editorial entry with this catalog ID (repeatable); other receipts are left unchanged")
        if function is discover:
            command.add_argument("--accept-shrink", action="append", metavar="SOURCE_ID", help="apply a successful response that drops this source below half its retained candidates")
        command.set_defaults(function=function)
    from build import build, validate, search
    command = sub.add_parser("build", help="generate catalog, category docs, coverage, JSON and SQLite exports offline")
    command.add_argument("--check", action="store_true", help="fail if generated committed views differ")
    command.set_defaults(function=build)
    command = sub.add_parser("validate", help="validate catalog against JSON Schema and quality invariants")
    command.set_defaults(function=validate)
    from summary_lint import SHORT_LIMIT, SUMMARY_LIMIT, lint
    command = sub.add_parser("lint", help=f"report curated summaries over {SUMMARY_LIMIT} characters, non-paper summaries under {SHORT_LIMIT}, or summaries without a terminal period or with superlatives; never fails")
    command.set_defaults(function=lint)
    command = sub.add_parser("search", help="search names, descriptions, aliases, authors, curated topics, ids and URLs")
    command.add_argument("query", nargs="?", default="")
    command.add_argument("--kind", choices=sorted(KINDS))
    command.add_argument("--status", choices=sorted(STATUSES))
    command.add_argument("--environment", choices=sorted(ENVIRONMENTS))
    command.add_argument("--topic")
    command.add_argument("--limit", type=nonnegative, default=20, help="0 returns every match")
    command.add_argument("--json", action="store_true")
    command.set_defaults(function=search)
    from lookup import get_resource
    command = sub.add_parser("get", help="read one exact active resource ID; report applied scope exclusions separately")
    command.add_argument("resource_id", help="stable catalog ID, such as arxiv:2404.07972")
    command.add_argument("--json", action="store_true", help="emit the original record, or an explicit non-active status")
    command.add_argument("--related", action="store_true", help="include incoming and outgoing reviewed relations with their evidence")
    command.set_defaults(function=get_resource)
    args = parser.parse_args(argv)
    result = args.function(args)
    return result if type(result) is int else 0


if __name__ == "__main__":
    # Catalog text is UTF-8; print it as such even where the locale encoding cannot represent it.
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

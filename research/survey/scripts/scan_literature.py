"""Retain a bounded, timestamped arXiv title search for the survey, without editing the catalog."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / ".cache/survey-20261018/root-search"
OUTPUT = ROOT / "research/survey/evidence/title-search.json"
QUERY = '(ti:"computer use" OR ti:"computer-use" OR ti:"GUI agent" OR ti:"GUI agents" OR ti:"GUI grounding" OR ti:"web agents" OR ti:"browser agent" OR ti:"mobile agent" OR ti:"UI agent" OR ti:"desktop agent" OR ti:"screen grounding") AND submittedDate:[200001010000 TO 202610180000]'
SOURCE_COMMIT = '87166fe8ad9c8e832f7a90ee84b2e93c6e0e40db'
NS = {"a": "http://www.w3.org/2005/Atom", "o": "http://a9.com/-/spec/opensearch/1.1/"}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    source = subprocess.check_output(['git','show',SOURCE_COMMIT+':data/catalog.jsonl'],cwd=ROOT)
    assert hashlib.sha256(source).hexdigest() == '7f71a1683ab013e587a20086c3e357956981f517a24ae8bc8e81791108c66e4f'
    existing = {row["id"] for row in map(json.loads, source.splitlines())}
    report = {"query": QUERY, "cutoff_utc": "2026-10-18T00:00:00Z", "search_fields": "title",
              "platform": "arXiv API", "page_size": 100, "maximum_pages": 40,
              "catalog_source_commit": SOURCE_COMMIT, "catalog_sha256": hashlib.sha256(source).hexdigest(),
              "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "purpose": "Supplementary discovery for an evidence-traced narrative survey; not proof of global completeness.",
              "pages": [], "records": [], "complete": False}
    by_id = {}
    total = None
    for page in range(report["maximum_pages"]):
        if page:
            time.sleep(3.2)
        start = page * 100
        params = {"search_query": QUERY, "start": start, "max_results": 100,
                  "sortBy": "submittedDate", "sortOrder": "descending"}
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
        receipt = {"start": start, "url": url, "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "AwesomeCUA-Survey/1.0 (research catalog; https://github.com/reacher-z/Awesome-CUA)"}), timeout=45) as response:
                body = response.read()
                receipt.update(http_status=response.status, final_url=response.url, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
            path = CACHE / f"page-{start:05d}.atom"
            path.write_bytes(body)
            receipt["retained_body"] = str(path.relative_to(ROOT))
            feed = ET.fromstring(body)
            observed_total = int(feed.findtext("o:totalResults", namespaces=NS))
            if total is None:
                total = observed_total
            receipt["reported_total"] = observed_total
            entries = feed.findall("a:entry", NS)
            receipt["returned"] = len(entries)
            for entry in entries:
                versioned = entry.findtext("a:id", "", NS)
                arxiv_id = versioned.rsplit("/abs/", 1)[-1]
                base = arxiv_id.rsplit("v", 1)[0] if "v" in arxiv_id else arxiv_id
                key = "arxiv:" + base
                if not re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z][a-z.-]*/\d{7})", base):
                    raise ValueError("Unexpected arXiv entry identity: " + versioned)
                title = " ".join(entry.findtext("a:title", "", NS).split())
                abstract = " ".join(entry.findtext("a:summary", "", NS).split())
                by_id.setdefault(key, {"id": key, "title": title, "versioned_url": versioned.replace("http://", "https://"),
                                      "published": entry.findtext("a:published", "", NS),
                                      "updated": entry.findtext("a:updated", "", NS),
                                      "authors": [a.findtext("a:name", "", NS) for a in entry.findall("a:author", NS)],
                                      "abstract_sha256": hashlib.sha256(abstract.encode()).hexdigest(),
                                      "already_active_in_frozen_catalog": key in existing,
                                      "source_page": page})
            report["pages"].append(receipt)
            print(f"page={page} returned={len(entries)} unique={len(by_id)} reported={observed_total}", flush=True)
            if start + len(entries) >= observed_total or not entries:
                report["complete"] = len(by_id) == observed_total and all(p["reported_total"] == observed_total for p in report["pages"])
                break
        except Exception as error:
            receipt["error"] = f"{type(error).__name__}: {error}"
            report["pages"].append(receipt)
            report["failure"] = receipt["error"]
            print(receipt["error"], flush=True)
            break
        finally:
            report.update(records=list(by_id.values()), unique_returned=len(by_id), reported_total=total)
            OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report.update(records=list(by_id.values()), unique_returned=len(by_id), reported_total=total,
                  completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  absent_from_frozen_active_catalog=sum(not r["already_active_in_frozen_catalog"] for r in by_id.values()))
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("pages", "records", "query")}), flush=True)


if __name__ == "__main__":
    main()

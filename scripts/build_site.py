#!/usr/bin/env python3
"""Build the portable AwesomeCUA site from the committed catalog; no network required."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build import validate_records, write_sqlite
from catalog import TOPICS, canonical
from search_pages import build_search_pages, resource_path
from export_rag import build_exports
from export_citations import build_citation_exports
from site_files import reconcile_generated_pages
from publication_metadata import record_date_text, publication_search_text
from repository_identity import attach_repository_aliases
from url_identity import attach_url_aliases, url_aliases


def version_script_imports(destination):
    # Version dependencies before hashing their consumers for the generated HTML.
    core_version=hashlib.sha256((destination/'catalog-core.js').read_bytes()).hexdigest().encode()
    pattern=rb"(\bfrom\s*)(['\"])\./catalog-core\.js(?:\?[^'\"\r\n]*)?\2"
    for name in ('app.js','compare.js'):
        target=destination/name
        content=re.sub(pattern,lambda m:m[1]+m[2]+b'./catalog-core.js?v='+core_version+m[2],target.read_bytes())
        target.write_bytes(content)


def compact_facts(row):
    # Index rows carry only recorded facts: the paper ID (the record's own, else the first arXiv paper that introduces or documents it) and declared licenses.
    papers=sorted((r for r in row['relations'] if r['type'] in ('introduced_by','documented_by') and r['target_id'].startswith('arxiv:')),key=lambda r:r['type']!='introduced_by')
    licenses={slot:', '.join(l['declared']) if isinstance(l['declared'],list) else l['declared'] for slot in ('code','data','weights','document') if (l:=row['licenses'].get(slot)) and l.get('declared')}
    return {'paper_arxiv':row['identifiers'].get('arxiv') or (papers[0]['target_id'][6:] if papers else None),'declared_licenses':licenses}


def replaceable(destination):
    # The build replaces its whole output directory, so it never takes over a checkout or a folder it did not create.
    return not destination.exists() or destination.is_dir() and not destination.is_symlink() and (not any(destination.iterdir()) or (destination/'data/search-manifest.json').is_file() and not (destination/'.git').exists())


def build_site(output=None):
    destination=Path(output) if output else ROOT/'dist'/'site'
    if not replaceable(destination):raise ValueError(f'Refusing to replace {destination}: build into an empty directory or a previous site build.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Build beside the output and swap it in whole: removed pages cannot survive, and a failed build keeps the previous site.
    staging=Path(tempfile.mkdtemp(prefix=f'.{destination.name}-',dir=destination.parent))
    try:
        staging.chmod(0o755)
        manifest,count=write_site(staging)
        if destination.exists():shutil.rmtree(destination)
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True);raise
    print(f'Built {count:,} searchable resources and {sum(x["indexable"] for x in manifest)} indexable HTML pages → {destination}')
    return destination


def write_site(destination):
    rows=[json.loads(line) for line in (ROOT/'data/catalog.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    coverage=json.loads((ROOT/'data/coverage.json').read_text(encoding='utf-8'))
    alias_file=ROOT/'data/repository-aliases.json'
    repository_declarations=json.loads(alias_file.read_text(encoding='utf-8')) if alias_file.exists() else []
    url_file=ROOT/'data/url-aliases.json'
    url_declarations=json.loads(url_file.read_text(encoding='utf-8')) if url_file.exists() else []
    errors=validate_records(rows)
    if attach_repository_aliases(rows,repository_declarations)!=rows:
        errors.append('Catalog repository aliases differ from their reviewed source declarations; rebuild catalog first.')
    if attach_url_aliases(rows,url_declarations,canonical)!=rows:
        errors.append('Catalog URL aliases differ from their normalization declarations; rebuild catalog first.')
    if errors:raise ValueError('\n'.join(errors[:10]))
    if len(rows)!=coverage['total_records']:raise ValueError('Catalog/coverage count mismatch; rebuild catalog first.')
    for path in (ROOT/'web').iterdir():
        if path.is_file():shutil.copy2(path,destination/path.name)
    version_script_imports(destination)
    (destination/'data').mkdir(exist_ok=True)
    (destination/'downloads').mkdir(exist_ok=True)
    (destination/'schemas').mkdir(exist_ok=True)
    for contract in ('resource.schema.json','scope-decision.schema.json','publication-observation.schema.json','download-manifest.schema.json','repository-alias.schema.json','url-alias.schema.json'):
        shutil.copy2(ROOT/'schemas'/contract,destination/'schemas'/contract)
    # index.json carries only fields the catalog list reads; the detail dialog fetches each record's own record.json.
    keys=['id','name','kind','url','aliases','environments','topics','summary','review_status','authors']
    related={row['id']:set() for row in rows}
    incoming={row['id']:[] for row in rows}
    for row in rows:
        for relation in row['relations']:
            if relation['target_id'] in related:
                related[relation['target_id']].add(row['id']);related[row['id']].add(relation['target_id'])
                incoming[relation['target_id']].append({'source_id':row['id'],'type':relation['type'],'evidence_url':relation['evidence_url']})
    index={'coverage':{k:coverage[k] for k in ['as_of_utc','total_records','curated_records','metadata_only_records','by_kind','unindexed_candidates','sources','excluded_records','arxiv_archive_records']},
        'topics':{topic:[entry['en'],entry['zh']] for topic,entry in TOPICS.items()},'records':[{**{k:row[k] for k in keys},'page_url':resource_path(row),
        'paper_version':row.get('details',{}).get('arxiv_snapshot',{}).get('version'),
        'paper_source_url':row.get('details',{}).get('arxiv_snapshot',{}).get('versioned_url'),
        'paper_date':record_date_text(row),
        'publication_search_text':publication_search_text(row),
        'related_count':len(related[row['id']]),'incoming_relations':incoming[row['id']],**compact_facts(row)} for row in rows]}
    for filename,payload in [('index.json',index),('records.json',rows)]:
        (destination/'data'/filename).write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    for name in ['catalog.jsonl','coverage.json','sources.json']:
        shutil.copy2(ROOT/'data'/name,destination/'downloads'/name)
    shutil.copy2(ROOT/'data/exclusion-status.json',destination/'downloads/exclusions.json')
    shutil.copy2(ROOT/'data/papers.jsonl',destination/'downloads/arxiv-archive.jsonl')
    (destination/'downloads/publications.jsonl').write_bytes((ROOT/'data/publications.jsonl').read_bytes() if (ROOT/'data/publications.jsonl').exists() else b'')
    (destination/'downloads/repository-aliases.json').write_text(json.dumps(repository_declarations,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (destination/'downloads/url-aliases.json').write_text(json.dumps(url_declarations,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_sqlite(rows,destination/'downloads'/'catalog.sqlite')
    build_exports(rows,destination/'downloads',(ROOT/'data/catalog.jsonl').read_bytes())
    build_citation_exports(rows,destination/'downloads',(ROOT/'data/catalog.jsonl').read_bytes())
    shutil.copy2(ROOT/'AGENTS.md',destination/'AGENTS.md')
    for name in ('paper-discovery-queries.json','paper-discovery-status.json','conference-discovery.json'):
        if (ROOT/'data'/name).exists():shutil.copy2(ROOT/'data'/name,destination/'downloads'/name)
    shutil.copy2(ROOT/'LICENSE',destination/'LICENSE')
    (destination/'.nojekyll').write_text('',encoding='utf-8')
    manifest=build_search_pages(destination,rows,coverage,ROOT,url_migrations=url_aliases(url_declarations,canonical,rows))
    reconcile_generated_pages(destination,manifest)
    return manifest,len(rows)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    build_site(sys.argv[1] if len(sys.argv)>1 else None)

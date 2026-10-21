#!/usr/bin/env python3
"""Export one citation-preserving retrieval document per catalog resource; no embeddings or network."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from publication_metadata import publication, record_date_text, format_date_parts

ROOT = Path(__file__).resolve().parents[1]


def record_digest(record):
    return hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def documents(records, include_metadata=False):
    seen=set()
    for record in records:
        rid=record['id']
        if rid in seen:raise ValueError('Duplicate resource identifier: '+rid)
        seen.add(rid)
        if record['review_status'] not in {'curated','metadata_verified'}:
            raise ValueError('Unrecognized catalog review status: '+rid)
        if not include_metadata and record['review_status']!='curated':continue
        # Use the same stable permalink convention as the website builder.
        from search_pages import resource_path, SITE
        snapshot=record.get('details',{}).get('arxiv_snapshot')
        source_url=(snapshot or {}).get('versioned_url') or record['url']
        lines=[record['name'],f"Resource type: {record['kind']}",f"Review status: {record['review_status']}",f"Scope: {record['scope']}"]
        if record.get('summary'):lines.extend(['',record['summary']])
        if record.get('aliases'):lines.append('Recorded aliases: '+', '.join(record['aliases']))
        if record['environments']:lines.append('Platforms: '+', '.join(record['environments']))
        if record['topics']:lines.append('Topics: '+', '.join(record['topics']))
        if record.get('published_at'):lines.append('Published: '+record['published_at'])
        elif record_date_text(record):lines.append('Record publication date (recorded precision): '+record_date_text(record))
        if record.get('authors'):lines.append('Authors: '+', '.join(record['authors']))
        if snapshot and snapshot.get('version'):lines.append(f"Recorded arXiv version: v{snapshot['version']}")
        pub=publication(record)
        if pub:
            lines.extend(['', 'Publication edition: '+pub['title'], 'Publication authors: '+', '.join(pub['authors'])])
            if pub['date_parts']:lines.append('Publication edition date (recorded precision): '+format_date_parts(pub['date_parts']))
            for key in ('venue','publisher','volume','issue','pages','doi','date_basis','event_dates','notes'):
                if pub.get(key):lines.append('Publication '+key.replace('_',' ')+': '+pub[key])
            lines.append('Publication source: '+pub['url'])
        specifications={key:value for key,value in record['details'].items() if key not in {'arxiv_snapshot','publication'} and value is not None and value!=[] and value!=''}
        if specifications:lines.extend(['','Recorded specifications: '+json.dumps(specifications,ensure_ascii=False,sort_keys=True)])
        if record.get('notes'):lines.extend(['',record['notes']])
        if record['review_status']=='metadata_verified':
            lines.append('Bibliographic facts only; this record has no approved editorial annotation. Relevance and findings remain pending.')
        lines.extend(['','Primary source: '+source_url,'Catalog record: '+SITE+resource_path(record)])
        yield {'id':rid,'text':'\n'.join(lines),'metadata':{
            'schema_version':1,'resource_id':rid,'name':record['name'],'kind':record['kind'],
            'review_status':record['review_status'],'scope':record['scope'],
            'citation_url':SITE+resource_path(record),'source_url':source_url,'canonical_source_url':record['url'],
            'published_at':record['published_at'],'updated_at':record['updated_at'],'identifiers':record['identifiers'],
            'last_verified_at':record['last_verified_at'],
            'environments':record['environments'],'topics':record['topics'],'aliases':record['aliases'],
            'arxiv_snapshot':snapshot,'publication':pub,'details':record['details'],'links':record['links'],'authors':record['authors'],
            'licenses':record['licenses'],'relations':record['relations'],
            'evidence':record['evidence'],'record_sha256':record_digest(record)}}


def encode_documents(records, include_metadata=False):
    # Materialize before writing so invalid or duplicate IDs cannot produce a partial export.
    return ''.join(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n' for row in documents(records,include_metadata)).encode()


def build_exports(records, destination, catalog_bytes):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    exports=[]
    for filename,include_metadata in [('rag-documents.jsonl',False),('rag-all-records.jsonl',True)]:
        body=encode_documents(records,include_metadata)
        (destination/filename).write_bytes(body)
        exports.append({'file':filename,'records':len(body.splitlines()),'includes_metadata_only':include_metadata,
                        'sha256':hashlib.sha256(body).hexdigest()})
    manifest={'schema_version':1,'catalog_sha256':hashlib.sha256(catalog_bytes).hexdigest(),
        'document_grain':'One resource per document; related papers, code, models, and datasets remain separate resources.',
        'text_policy':'Catalog metadata and original annotations; no paper full text, copied full abstracts, weights, or training examples.',
        'review_policy':'Use review_status=curated for reviewed retrieval. metadata_verified records require an editorial relevance decision and can include source-reviewed holds.',
        'exports':exports}
    (destination/'rag-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'data/catalog.jsonl')
    parser.add_argument('--output',type=Path,help='Output path; defaults to standard output.')
    parser.add_argument('--include-metadata',action='store_true',help='Include all active records, preserving their unreviewed status.')
    args=parser.parse_args()
    if args.output and args.output.resolve()==args.input.resolve():parser.error('Output must not overwrite the source catalog')
    records=[json.loads(line) for line in args.input.read_text(encoding='utf-8').splitlines() if line.strip()]
    body=encode_documents(records,args.include_metadata)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(body)
        print(f'Exported {len(body.splitlines())} retrieval documents to {args.output}',file=sys.stderr)
    else:sys.stdout.buffer.write(body)


if __name__=='__main__':main()

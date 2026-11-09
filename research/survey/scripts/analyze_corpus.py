"""Reproduce descriptive survey inventory statistics from the pinned catalog."""
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from publication_metadata import record_year
from paper_library import connected_assets
from specifications import selected_profiles

EXPECTED_SHA = '7f71a1683ab013e587a20086c3e357956981f517a24ae8bc8e81791108c66e4f'
SOURCE_COMMIT = '87166fe8ad9c8e832f7a90ee84b2e93c6e0e40db'
HERE = ROOT / 'research/survey'


def main():
    def pinned(path):
        return subprocess.check_output(['git','show',SOURCE_COMMIT+':'+path],cwd=ROOT)
    body = pinned('data/catalog.jsonl')
    assert hashlib.sha256(body).hexdigest() == EXPECTED_SHA, 'Use the pinned v2026.10.18 source snapshot.'
    rows = [json.loads(line) for line in body.splitlines() if line]
    papers = [r for r in rows if r['kind'] in {'paper', 'survey'}]
    reviewed = [r for r in papers if r['review_status'] == 'curated']
    coverage = json.loads(pinned('data/coverage.json'))
    assets = connected_assets(rows)
    years = Counter(record_year(r) or 'unknown' for r in reviewed)
    topics = Counter(t for r in reviewed for t in r['topics'])
    envs = Counter(t for r in reviewed for t in r['environments'])
    result = {
        'source_repository': 'https://github.com/reacher-z/Awesome-CUA',
        'source_commit': SOURCE_COMMIT, 'release': 'v2026.10.18',
        'catalog_sha256': EXPECTED_SHA, 'snapshot_as_of_utc': coverage['as_of_utc'],
        'active_resources': len(rows), 'active_bibliographic_resources': len(papers),
        'reviewed_resources': sum(r['review_status'] == 'curated' for r in rows),
        'reviewed_papers_and_surveys': len(reviewed),
        'metadata_only_bibliographic_resources': sum(r['review_status'] == 'metadata_verified' for r in papers),
        'reviewed_papers': sum(r['kind'] == 'paper' for r in reviewed),
        'reviewed_surveys': sum(r['kind'] == 'survey' for r in reviewed),
        'reviewed_nonbibliographic_resources': sum(r['kind'] not in {'paper','survey'} and r['review_status']=='curated' for r in rows),
        'reviewed_bibliography_scope': dict(Counter(r['scope'] for r in reviewed)),
        'reviewed_bibliography_year': dict(sorted(years.items())),
        'reviewed_bibliography_environment_memberships': dict(envs.most_common()),
        'reviewed_bibliography_topic_memberships': dict(topics.most_common()),
        'asset_linked_papers': len(assets), 'paper_asset_pairs': sum(map(len, assets.values())),
        'asset_linked_paper_ids': sorted(assets),
        'benchmark_profiles': len(selected_profiles(rows,'benchmark')),
        'dataset_profiles': len(selected_profiles(rows,'dataset')),
        'benchmarks': sum(r['kind']=='benchmark' for r in rows),
        'datasets': sum(r['kind']=='dataset' for r in rows),
        'primary_discovery_sources': len(json.loads(pinned('data/sources.json'))),
        'active_kind_counts': dict(sorted(Counter(r['kind'] for r in rows).items())),
        'boundary': 'These statistics describe this selected catalog snapshot, not field-wide prevalence, completeness, publication quality, or independently reproduced results. Topic and environment memberships overlap.',
        'year_policy': 'First-submission year for arXiv records; supplied publication year for publisher-only records. Partial dates retain their precision.',
        'record_fingerprint_method': 'SHA256 of the original full record serialized as UTF-8 JSON with sorted keys, no ASCII escaping, and compact separators.',
        'reviewed_records': [{
            'id':r['id'], 'title':r['name'], 'year':record_year(r), 'kind':r['kind'],
            'scope':r['scope'], 'topics':r['topics'], 'environments':r['environments'],
            'source_url':r['url'],
            'record_sha256':hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        } for r in reviewed]
    }
    (HERE/'evidence/corpus-statistics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig, ax = plt.subplots(1,2,figsize=(11,3.5),layout='constrained',gridspec_kw={'width_ratios':[1,1.25]})
    groups=['Through 2022','2023','2024','2025','2026*']
    values=[sum(v for k,v in years.items() if k!='unknown' and int(k)<=2022),years['2023'],years['2024'],years['2025'],years['2026']]
    bars=ax[0].bar(groups,values,color=['#a7b7d6','#829ac5','#607fba','#405fa3','#654bc1'],width=.65)
    ax[0].bar_label(bars,padding=4,fontsize=10)
    ax[0].set_title('A. First-publication year',loc='left',fontweight='bold',pad=14)
    ax[0].set_ylabel('Reviewed papers and surveys');ax[0].set_ylim(0,max(values)*1.18)
    ax[0].tick_params(axis='x',labelsize=9);ax[0].grid(axis='y',alpha=.15);ax[0].set_axisbelow(True)
    chosen=['evaluation','data-generation','grounding','planning','web-navigation','mobile-navigation','reinforcement-learning','safety-security']
    labels=['Evaluation','Data generation','GUI grounding','Planning','Web navigation','Mobile navigation','Reinforcement learning','Safety and security']
    bars=ax[1].barh(labels[::-1],[topics[t] for t in chosen][::-1],color='#25837d',height=.64)
    ax[1].bar_label(bars,padding=5,fontsize=9)
    ax[1].set_title('B. Selected topic memberships',loc='left',fontweight='bold',pad=14)
    ax[1].set_xlabel('Reviewed paper/survey memberships (overlapping)')
    ax[1].set_xlim(0,max(topics[t] for t in chosen)*1.14);ax[1].grid(axis='x',alpha=.15);ax[1].set_axisbelow(True)
    fig.savefig(HERE/'figures/corpus.svg',metadata={'Date':None,'Creator':'AwesomeCUA survey: analyze_corpus.py'})
    svg = HERE/'figures/corpus.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k not in ('reviewed_records','asset_linked_paper_ids')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

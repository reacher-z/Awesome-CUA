#!/usr/bin/env python3
"""Prepare existing public website/profile checkouts. Does not commit, push, or change visibility."""
from pathlib import Path
import argparse
import json
import shutil
from search_pages import KINDS, SITE, REPO, SOURCE_REPO, clean_text, resource_path
from agent_pages import CLONE_COMMAND
from site_files import MANAGED_FILES, reconcile_generated_pages
from publication_metadata import record_date_text
from build import task_navigator
from topic_pages import reconcile_topic_exports
from export_candidates import candidate_publication_plan, candidate_copy_ignores, apply_candidate_publication
from survey_bundle import PAGE as SURVEY_PAGE, publication_plan as survey_publication_plan, apply_publication as apply_survey_publication

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir',type=Path,default=ROOT/'.cache/github-pages-publish')
    parser.add_argument('--profile-dir',type=Path,default=ROOT/'.cache/github-profile')
    parser.add_argument('--skip-profile',action='store_true')
    parser.add_argument('--install-workflow',action='store_true',help='Install the publication workflow during an authorized manual setup.')
    args=parser.parse_args()
    site=args.site_dir.resolve();profile=args.profile_dir.resolve()
    if not (site/'.git').exists() or (not args.skip_profile and not (profile/'.git').exists()):
        raise SystemExit('Clone AwesomeCUA/awesomecua.github.io and AwesomeCUA/.github into the documented .cache checkout paths first.')
    build=ROOT/'dist/site'
    if not (build/'data/search-manifest.json').is_file():raise SystemExit(f'No website build in {build}; run python3 scripts/build_site.py first.')
    incoming=json.loads((build/'data/search-manifest.json').read_text(encoding='utf-8'))
    # Validate the bundle, source fingerprints and every owned path before any deletion or copy.
    survey_plan=survey_publication_plan(build,site,source_root=ROOT,site_url=SITE,pages=incoming['pages'])
    candidate_plan=candidate_publication_plan(build,site)
    old_path=site/'data/search-manifest.json'
    if old_path.exists():
        old=json.loads(old_path.read_text(encoding='utf-8'));new_paths={p['path'] for p in incoming['pages']}
        stale=[(site/item['path'].lstrip('/')).resolve() for item in old.get('pages',[]) if item['path'] not in new_paths and item['path']!=SURVEY_PAGE]
        # Any page the new build dropped is removed, whatever its section, but never outside the checkout or in .git or another dot folder.
        # Every path is checked before the first deletion.
        for folder in stale:
            if not folder.is_relative_to(site) or any(part.startswith('.') for part in folder.relative_to(site).parts):
                raise ValueError('Old manifest page outside the generated website pages: '+str(folder))
        for folder in stale:
            for filename in MANAGED_FILES:(folder/filename).unlink(missing_ok=True)
    for item in incoming['pages']:
        if item['path'].startswith('/resources/'):
            if '..' in Path(item['path']).parts:raise ValueError('Invalid generated resource path')
            for filename in MANAGED_FILES-{'index.html','index.md'}:
                if not (build/item['path'].lstrip('/')/filename).exists():
                    (site/item['path'].lstrip('/')/filename).unlink(missing_ok=True)
    # Survey files have their own ownership manifest; orphaned build files must not leak through copytree.
    shutil.copytree(build,site,dirs_exist_ok=True,ignore=lambda folder,names:
        (['survey'] if Path(folder)==build else []) + candidate_copy_ignores(build,folder,names))
    apply_survey_publication(survey_plan)
    apply_candidate_publication(candidate_plan)
    reconcile_generated_pages(site,incoming['pages'])
    if (build/'downloads/topics.json').exists():
        topics=json.loads((build/'downloads/topics.json').read_text(encoding='utf-8'))
        reconcile_topic_exports(site,{item['id'] for item in topics['topics']})
    ignore=site/'.gitignore';ignore_text=ignore.read_text(encoding='utf-8') if ignore.exists() else ''
    for pattern in ['.pipeline/','.cache/','__pycache__/','.DS_Store']:
        if pattern not in ignore_text.splitlines():ignore_text=ignore_text.rstrip()+'\n'+pattern+'\n'
    ignore.write_text(ignore_text.lstrip('\n'),encoding='utf-8')
    if args.install_workflow:
        (site/'.github/workflows').mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'automation/publish.yml',site/'.github/workflows/publish.yml')
    (site/'.github/ISSUE_TEMPLATE').mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'.github/ISSUE_TEMPLATE/resource.yml',site/'.github/ISSUE_TEMPLATE/resource.yml')
    (site/'schemas').mkdir(exist_ok=True)
    for name in ['resource.schema.json','scope-decision.schema.json','publication-observation.schema.json']:
        shutil.copy2(ROOT/'schemas'/name,site/'schemas'/name)
    report=json.loads((ROOT/'data/coverage.json').read_text(encoding='utf-8'))
    scan_config=json.loads((ROOT/'data/scan-config.json').read_text(encoding='utf-8'))
    scan_times=', '.join(scan_config['scan_times_local'])+' '+scan_config['timezone']
    publish_times=', '.join(scan_config['publish_times_local'])+' '+scan_config['timezone']
    rows=[json.loads(l) for l in (ROOT/'data/catalog.jsonl').read_text(encoding='utf-8').splitlines()]
    readme=['# Awesome Computer-Use Agents · AwesomeCUA','', '**A source-backed catalog of computer-use, GUI, browser, and mobile agents.**','', f'[Website]({SITE}/) · [Research papers]({SITE}/papers/) · [中文指南]({SITE}/zh/) · [GitHub organization](https://github.com/AwesomeCUA)','',f'**{report["total_records"]:,} resource records** · **{report["curated_records"]:,} curated** · **{report["bibliographic_records"]:,} paper and survey records** · **{len(report["sources"])} discovery documents**','',f'Evidence snapshot: {report["as_of_utc"]}. Bibliography counts overlap review-state counts. Resources are not independent projects.','', '## What is a computer-use agent?','', 'A computer-use agent observes software interfaces, chooses and executes actions, and checks progress toward a user goal. It may operate a browser, desktop application, or phone, sometimes combining graphical interaction with code and tools. See [the primary-source introduction]('+SITE+'/guides/what-are-computer-use-agents/) and [reviewed research]('+SITE+'/papers/).','', '## Explore the ecosystem','', '| Category | Records | Browse |','| --- | ---: | --- |']
    readme[6:6]=['## For people, RAG systems, and agents','','```sh',CLONE_COMMAND,'```','',f'[Agent instructions]({SITE}/AGENTS.md) · [Agent and RAG guide]({SITE}/agents/) · [中文使用指南]({SITE}/zh/agents/) · [Complete JSONL]({SITE}/downloads/catalog.jsonl)','',task_navigator().strip(),'']
    if survey_plan['payloads']:
        readme[5:5]=[f'[Read the English research survey]({SITE}/survey/) — an evidence-traced working manuscript with its own frozen research snapshot.','']
    for kind,name in KINDS.items():readme.append(f'| {name} | {report["by_kind"].get(kind,0):,} | [Open directory]({SITE}/categories/{kind}/) |')
    readme+=['','Category pages highlight reviewed resources; the [interactive catalog]('+SITE+'/#catalog) and downloads also expose metadata-only records with their review state.','', '## Research reading list','']
    selected=sorted([r for r in rows if r['kind']=='paper' and r['review_status']=='curated'],key=record_date_text,reverse=True)
    for r in selected[:10]:readme.append(f'- [{r["name"]}]({SITE}{resource_path(r)}) — {r["summary"]} [Original paper]({r["url"]}).')
    readme+=['',f'[All reviewed papers and surveys]({SITE}/papers/). Annotations do not independently reproduce experimental findings.','', '## Papers connected to code and data','',f'[Browse reviewed paper–asset relationships]({SITE}/connections/) · [Download relationships JSON]({SITE}/downloads/relationships.json)','','## Choose a benchmark or training dataset','', f'- [GUI-agent benchmark guide]({SITE}/guides/gui-agent-benchmarks/): distinguish grounding, web tasks, mobile interaction, and desktop execution.', f'- [Training-data guide]({SITE}/guides/gui-agent-training-data/): compare supervision types, platform, splits, count units, and licenses.',f'- [Editorial policy]({SITE}/about/) and [coverage ledger]({SITE}/coverage/): understand what was verified and what is still missing.','', '## Download and reuse the data','',f'- [Full resource catalog — JSONL]({SITE}/downloads/catalog.jsonl)',f'- [Queryable database — SQLite]({SITE}/downloads/catalog.sqlite)',f'- [Data documentation]({SITE}/data/) · [JSON Schema](schemas/resource.schema.json)',f'- [Coverage JSON]({SITE}/downloads/coverage.json) · [Source registry]({SITE}/downloads/sources.json)',f'- [Scope decisions]({SITE}/downloads/exclusions.json) · [Raw arXiv archive, including excluded candidates]({SITE}/downloads/arxiv-archive.jsonl)',f'- [Machine-readable navigation]({SITE}/llms.txt) · [Curated Markdown]({SITE}/llms-full.txt) · [Research feed]({SITE}/feed.xml)','', 'The downloads contain metadata and original catalog annotations, not upstream training data, model weights, or paper PDFs. Code, data, weights, and document licenses remain separate.','', '## Website and contributions','', 'This repository hosts the published static website and metadata snapshot. Complete resource pages and guides work without JavaScript; interactive search adds filtering, pagination, and detail dialogs. No API keys, account, paid backend, or external analytics are required.','', '```bash','python3 -m http.server 4173 --bind 127.0.0.1','```','', 'GitHub Pages deploys the validated static artifact through the publication workflow. The `main` branch keeps an inspectable snapshot. Original code and annotations use [MIT](LICENSE); linked assets retain their own terms.', '',f'[Suggest a resource or correction]({SOURCE_REPO}/issues/new?template=resource.yml). Supply a primary source and explain uncertain facts. Global completeness is a goal, not a verified claim.','']
    readme+=['## Automatic updates','',f'[Source catalog and scan code](https://github.com/reacher-z/Awesome-CUA) · [Scan status]({SITE}/updates/)','', f'Discovery is scheduled three times daily at {scan_times}. This website rebuilds at {publish_times} from validated source data. Publication is scheduled 90 minutes after each scan slot and retains its own quality gate. GitHub scheduling can be delayed; the status page records actual completion times.','', 'New discoveries are bibliographic metadata or candidates until a separate editorial review. The publishing workflow uses repository-scoped GitHub tokens and does not require a stored personal access token.','']
    readme[0:0]=['<p align="center">',f'  <a href="{SITE}/"><img src="badges/featured-by-awesomecua-laurel.svg" alt="Featured by Awesome CUA" width="220"></a>','</p>','']
    (site/'README.md').write_text(clean_text('\n'.join(readme)),encoding='utf-8')
    if args.skip_profile:
        print(f'Prepared {incoming["indexable_pages"]} indexable pages and the public README; profile left to its own checkout.')
        return
    profile_path=profile/'profile/README.md';profile_path.parent.mkdir(exist_ok=True)
    profile_path.write_text(f'''# AwesomeCUA\n\n### The computer-use agent ecosystem, with sources.\n\nResearch papers, GUI models, training datasets, evaluation benchmarks, frameworks, tools, and products — searchable and traceable in one catalog.\n\n**[Explore the website →]({SITE}/)** · **[Research papers →]({SITE}/papers/)** · **[中文指南 →]({SITE}/zh/)**\n\n| Research & training | Engineering & industry |\n| --- | --- |\n| [Papers]({SITE}/papers/) · [Surveys]({SITE}/categories/survey/) | [Agents]({SITE}/categories/agent/) · [Frameworks]({SITE}/categories/framework/) |\n| [Models]({SITE}/categories/model/) · [Datasets]({SITE}/categories/dataset/) | [Tools]({SITE}/categories/tool/) · [Infrastructure]({SITE}/categories/infrastructure/) |\n| [Benchmarks]({SITE}/categories/benchmark/) · [Learning resources]({SITE}/categories/learning/) | [Products]({SITE}/categories/product/) · [Publishers]({SITE}/categories/company/) |\n\n**{report['total_records']:,} resource records** · **{report['curated_records']:,} reviewed** · **{len(KINDS)} categories**\n\n[Download data]({SITE}/data/) · [Practical guides]({SITE}/guides/) · [Coverage]({SITE}/coverage/) · [Contribute]({SOURCE_REPO}/issues/new?template=resource.yml)\n\n每条资源保留一手来源与审阅状态。支持论文检索、分类筛选、来源追溯与结构化数据下载。\n\nCurated means AI-assisted editorial review; metadata verification does not establish research quality or reproducibility. Counts refer to resources, not distinct projects. Comprehensive global coverage is a goal, not a verified claim.\n\n<sub>Source snapshots: <a href="{SITE}/coverage/">coverage ledger</a>. Original annotations and code: MIT. Linked assets retain their own terms.</sub>\n''',encoding='utf-8')
    profile_text=profile_path.read_text(encoding='utf-8')
    profile_text=profile_text.replace('\n| Research & training',f'\nFor people, RAG systems, and agents — clone the complete catalog:\n\n```sh\n{CLONE_COMMAND}\n```\n\n[Agent instructions]({SITE}/AGENTS.md) · [Agent & RAG guide]({SITE}/agents/) · [中文使用指南]({SITE}/zh/agents/)\n\n| Research & training')
    profile_text=profile_text.replace(f"**{report['total_records']:,} resource records** · **{report['curated_records']:,} reviewed** · **{len(KINDS)} categories**",f'![Live catalog counts]({SITE}/badges/catalog.svg)')
    profile_text+=f'\n[Scan status · 3 runs daily]({SITE}/updates/) · [Source and contribution workflow](https://github.com/reacher-z/Awesome-CUA)\n'
    profile_path.write_text(profile_text,encoding='utf-8')
    print(f'Prepared {incoming["indexable_pages"]} indexable pages and updated public README/profile. Review diffs before committing.')


if __name__=='__main__':main()

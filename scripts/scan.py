#!/usr/bin/env python3
"""Run one bounded public-source scan and persist an auditable update report."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

from catalog import ROOT, DATA, arxiv_entry, fetch, now, read_json, read_jsonl, write_json, write_jsonl, validate_candidate_snapshot
from arxiv_metadata import consider_paper, parse_search_feed, timestamp
from network_budget import (RoundBudget, budget_from_environment, ENV_PHASE,
                            DEFAULT_REQUESTS, DEFAULT_SECONDS)
import scan_candidate_stage as candidate_stage
from site_config import scan_schedule


def counts():
    rows=read_jsonl(DATA/'catalog.jsonl')
    report=read_json(DATA/'coverage.json',{})
    return {'resources':len(rows),'bibliographic_records':sum(row['id'].startswith('arxiv:') for row in rows),
        'arxiv_archive_records':len(read_jsonl(DATA/'papers.jsonl')),'excluded_records':report.get('excluded_records',0),
        'curated_papers':sum(r['kind'] in {'paper','survey'} and r['review_status']=='curated' for r in rows),
        'curated_resources':sum(r['kind'] not in {'paper','survey'} and r['review_status']=='curated' for r in rows),
        'candidates':len(read_jsonl(DATA/'candidates.jsonl'))}


# Phase caps never extend the single network-round deadline. Offline build/validation
# retain separate time, leaving room for the workflow's remaining quality gate.
STAGE_TIMEOUTS={'discovery':600,'huggingface':600,'recent_arxiv':600,'harvest':600,'github_candidates':220,'build':300,'validate':300}
NETWORK_STAGES=frozenset({'discovery','huggingface','recent_arxiv','harvest','github_candidates'})
# Precise title terms miss methods whose interface setting appears only in the
# abstract. Keep this a discovery query: every new hit still needs scope review.
RECENT_ARXIV_TERMS=(
    'ti:"computer use"', 'ti:"computer-use"', 'ti:"GUI agent"',
    'ti:"GUI agents"', 'ti:"GUI grounding"', 'ti:"web agent"',
    'ti:"browser agent"', 'ti:GUI', 'ti:"Android agent"',
    'abs:"computer-use agents"', 'abs:"GUI agents"',
    'abs:"browser agents"', 'abs:"mobile GUI"',
    'abs:"web navigation"', 'abs:AndroidWorld', 'abs:Mind2Web',
)


def stage(name,command,timeout=None):
    started=now();timeout=min(timeout,STAGE_TIMEOUTS[name]) if timeout is not None else STAGE_TIMEOUTS[name]
    budget=budget_from_environment()
    if budget and name in NETWORK_STAGES:
        timeout=min(timeout,budget.remaining_seconds())
        if timeout<=0:
            return {'name':name,'started_at':started,'finished_at':now(),'ok':False,'deferred':True,
                    'request_attempted':False,'error':'Network round wall budget exhausted; no phase started.'}
    env={**os.environ,ENV_PHASE:name}
    try:
        result=subprocess.run([sys.executable,*command],cwd=ROOT,encoding='utf-8',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
        print(result.stdout[-6000:],flush=True)
        return {'name':name,'started_at':started,'finished_at':now(),'ok':result.returncode==0,'exit_code':result.returncode,
            'error':result.stdout[-1600:] if result.returncode else None}
    except subprocess.TimeoutExpired:
        return {'name':name,'started_at':started,'finished_at':now(),'ok':False,
                'error':f'Stage exceeded {timeout:g} seconds; last verified records retained.'}


def recent_result_path(budget):
    return budget.path.with_name(budget.run_id+'-recent-result.json')


def recent_phase():
    """Run the recent search under the same hard outer timeout as other network phases."""
    budget=budget_from_environment()
    if budget is None:raise ValueError('Recent scan phase requires a network-round context')
    output=recent_result_path(budget)
    output.unlink(missing_ok=True)
    result=stage('recent_arxiv',['scripts/scan.py','--recent-only'])
    if not result['ok']:return result
    receipt=read_json(output,{})
    phase=receipt.get('phase')
    if (receipt.get('round_id')!=budget.run_id or not isinstance(phase,dict)
            or phase.get('name')!='recent_arxiv' or type(phase.get('ok')) is not bool):
        return {**result,'ok':False,'error':'No complete recent-search receipt for this network round.'}
    return {**result,**phase}


def candidate_phase(config):
    """Validate a new child result without installing it before the catalog build."""
    limits=candidate_stage.settings(config)
    started=now()
    idle={'name':candidate_stage.PHASE,'started_at':started,'finished_at':started,
          'ok':True,'request_attempted':False,'requests_attempted':0,'published':False,
          'new_unique_repositories':0,'warnings':[]}
    if not limits['enabled']:return {**idle,'state':'disabled'}
    budget=budget_from_environment()
    if budget is None:raise ValueError('Candidate phase requires a network-round context')
    reserved=budget.summary()['requests_reserved']
    if (reserved>=budget.summary()['max_requests'] or budget.remaining_seconds()<=candidate_stage.FINALIZE_SECONDS):
        return {**idle,'state':'deferred_budget','deferred':True,
                'reason':'The shared network allowance is exhausted; durable candidate state is unchanged.'}
    import candidate_state
    baseline=candidate_state.load_snapshot(DATA)
    if budget.remaining_seconds()<=candidate_stage.FINALIZE_SECONDS:
        return {**idle,'state':'deferred_budget','deferred':True,
                'reason':'The shared time allowance expired during checkpoint validation; durable files are unchanged.'}
    output=candidate_stage.result_path(budget);output.unlink(missing_ok=True)
    result=stage(candidate_stage.PHASE,['scripts/scan_candidate_stage.py'],timeout=limits['max_seconds'])
    if not result['ok']:return {**result,'published':False}
    receipt=read_json(output,{})
    phase=receipt.get('phase')
    if (type(receipt.get('schema_version')) is not int or receipt['schema_version']!=1
            or receipt.get('round_id')!=budget.run_id or receipt.get('baseline_files')!=baseline.fingerprints
            or not isinstance(phase,dict) or phase.get('name')!=candidate_stage.PHASE
            or phase.get('ok') is not True or phase.get('published') is not False):
        return {**result,'ok':False,'published':False,'error':'No complete candidate receipt for this network round.'}
    if phase.get('state')=='deferred_budget':
        if (phase.get('requests_attempted')!=0 or phase.get('request_attempted') is not False
                or phase.get('files')!=baseline.fingerprints or phase.get('run_id') is not None
                or budget.summary()['requests_reserved']!=reserved):
            return {**result,'ok':False,'published':False,'error':'Invalid candidate budget-deferral receipt.'}
        return {**result,**phase}
    candidate_stage.checked_summary({**phase,'status':phase.get('scan_status')})
    staged=candidate_state.load_snapshot(candidate_stage.runtime_path(budget)/'public')
    reservations=budget.summary()['requests_reserved']-reserved
    new_receipts=staged.state['receipts'][len(baseline.state['receipts']):]
    successful=sum(r['outcome']=='accepted' and r['status']==200 and r['raw_body_retained'] for r in new_receipts)
    current_run=staged.state['runs'][-1]
    query_statuses=dict(collections.Counter(q['status'] for q in staged.state['queries']))
    if (phase.get('files')!=staged.fingerprints or len(staged.state['runs'])!=len(baseline.state['runs'])+1
            or phase.get('run_id')!=current_run['id'] or phase.get('scan_status')!=current_run['status']
            or any(phase.get(key)!=current_run[key] for key in ('requests_attempted','new_unique_repositories','unknown_requests','rejected_rows'))
            or phase.get('request_attempted') is not (current_run['requests_attempted']>0)
            or phase.get('total_unique_repositories')!=len(staged.state['records'])
            or phase.get('pending_queries')!=query_statuses.get('pending',0)
            or phase.get('query_status_counts')!=query_statuses or phase.get('epoch_id')!=staged.state.get('current_epoch_id')
            or type(phase.get('successful_responses')) is not int or phase['successful_responses']!=successful
            or phase.get('requests_attempted')>reservations or reservations>limits['max_requests']):
        return {**result,'ok':False,'published':False,'error':'Candidate child result differs from its staged state or shared request ledger.'}
    from scan_github_candidates import settled_unknown_requests
    settled=settled_unknown_requests(new_receipts,current_run['id'])
    if phase.get('settled_unknown_requests',0)!=settled:
        return {**result,'ok':False,'published':False,'error':'Candidate child result differs from its staged settled-answer receipts.'}
    # Derive alerts from the verified counts/status rather than trusting a child's display fields.
    verified=candidate_stage.phase_summary({**phase,'status':current_run['status'],'settled_unknown_requests':settled,
        'verification':{'successful_receipts_replayed':successful}},phase['started_at'])
    phase.update({key:verified[key] for key in ('warnings','notices','settled_unknown_requests','state','complete')})
    return {**result,**phase,'baseline_files':baseline.fingerprints,'ready_to_publish':True,
            'network_reservations':reservations}


def publish_candidate_phase(phase,budget):
    """Install only a validated child result, rebound to the final catalog bytes."""
    if not phase.get('ready_to_publish'):return
    import candidate_state
    staged=candidate_state.load_snapshot(candidate_stage.runtime_path(budget)/'public')
    if staged.fingerprints!=phase['files']:
        raise ValueError('Candidate staged files changed after the child receipt')
    publication=candidate_state.publish_snapshot(candidate_stage.runtime_path(budget)/'public',DATA,
        expected_prior_hashes=phase['baseline_files'],catalog_bytes=(DATA/'catalog.jsonl').read_bytes())
    if publication['staged_files']!=phase['files']:
        raise ValueError('Candidate publication differs from the validated child output')
    phase.update(staged_files=phase['files'],files=publication['files'],published=True,
                 comparison_context_rebound=True,ready_to_publish=False)


def candidate_consistency(config):
    """Final durable-state gate, independent of this round's candidate outcome."""
    try:
        result=validate_candidate_snapshot(DATA,require_checkpoint=candidate_stage.settings(config)['enabled'])
        return {'ok':True,'checked_at':now(),**result}
    except Exception as error:
        return {'ok':False,'checked_at':now(),'error':str(error)}


def reusable_recent_snapshot(report, query, since, cutoff, day):
    """Reuse only a complete, successful snapshot for this UTC publication cycle."""
    if not isinstance(report,dict) or report.get('schema_version')!=2 or report.get('scan_day_utc')!=day:
        return False
    if (report.get('query'),report.get('since_utc'),report.get('cutoff_utc'))!=(query,since,cutoff):
        return False
    total=report.get('reported_total')
    pages=report.get('pages')
    def valid_page(page):
        if not isinstance(page,dict) or page.get('ok') is not True:return False
        try:retrieved=timestamp(page.get('retrieved_at'))
        except (ValueError,TypeError,AttributeError):return False
        return bool(retrieved and retrieved[:10]==day and isinstance(page.get('sha256'),str)
                    and re.fullmatch('[0-9a-f]{64}',page['sha256']))
    return (report.get('complete') is True and not report.get('warnings') and type(total) is int and total>=0
        and type(report.get('unique_returned')) is int and report['unique_returned']==total and isinstance(pages,list) and bool(pages)
        and all(valid_page(page) for page in pages))


def recent_papers(config):
    current=dt.datetime.now(dt.timezone.utc)
    cycle=current.replace(hour=0,minute=0,second=0,microsecond=0)
    begin=cycle-dt.timedelta(days=config['recent_lookback_days'])
    cutoff=cycle.strftime('%Y%m%d%H%M');since=begin.strftime('%Y%m%d%H%M');day=cycle.date().isoformat()
    terms=' OR '.join(RECENT_ARXIV_TERMS)
    query=f'({terms}) AND submittedDate:[{since} TO {cutoff}]'
    previous=read_json(DATA/'recent-paper-search.json',{})
    if reusable_recent_snapshot(previous,query,since,cutoff,day):
        return {'name':'recent_arxiv','ok':True,'complete':True,'new_count':0,'warnings':[],
                'cache_used':True,'source_retrieved_at':max(page['retrieved_at'] for page in previous['pages'])}
    records={r['id']:r for r in read_jsonl(DATA/'papers.jsonl')}
    candidates={r['id']:r for r in read_jsonl(DATA/'candidates.jsonl')}
    proposals={r['id']:r for r in read_jsonl(DATA/'metadata-updates.jsonl')}
    start=0;total=None;seen=set();new_ids=[];pages=[];warnings=[]
    ceiling=config['recent_max_results']
    while start<ceiling and (total is None or start<total):
        batch_size=min(200,ceiling-start)
        url='https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'search_query':query,'start':start,'max_results':batch_size,'sortBy':'submittedDate','sortOrder':'descending'})
        info,body=fetch(url,refresh=True)
        if not info['ok']:
            pages.append(info);warnings.append(info.get('error','arXiv fetch failed'));break
        try:
            entries,total=parse_search_feed(body,total,batch_size)
        except (ET.ParseError,ValueError) as error:
            pages.append({**info,'ok':False,'error':str(error)});warnings.append(str(error));break
        pages.append({**info,'start':start,'returned':len(entries)})
        for entry in entries:
            try:
                row=arxiv_entry(entry,{k:info[k] for k in ('url','retrieved_at','sha256')})
                if not row:raise ValueError('unrecognized article identity')
                submitted=row['details']['arxiv_snapshot']['submitted_at']
                if not submitted:raise ValueError('missing submission timestamp')
                submitted=dt.datetime.fromisoformat(submitted.replace('Z','+00:00'))
            except (ValueError,TypeError,KeyError) as error:
                warnings.append('Ignored an invalid arXiv entry: '+str(error));continue
            if not begin<=submitted<=cycle:
                warnings.append('Ignored an out-of-window search result: '+row['id']);continue
            seen.add(row['id'])
            if consider_paper(row,records,proposals,info['retrieved_at']):new_ids.append(row['id'])
            c=candidates.setdefault(row['id'],{'id':row['id'],'url':row['url'],'provider':'arxiv','first_discovered_at':info['retrieved_at'],'discovered_in':[]})
            c['discovered_in']=[o for o in c['discovered_in'] if o['source_id']!='arxiv-recent-scan']
            c['discovered_in'].append({'source_id':'arxiv-recent-scan','line':None,'section':'Recent title and abstract search; relevance awaits review','snapshot_sha256':info['sha256']})
        start+=len(entries)
        if not entries:break
        if start<min(total,ceiling):time.sleep(3.1)
    complete=total is not None and len(seen)==total and bool(pages) and all(p.get('ok') for p in pages) and not warnings
    if total is not None and not complete:warnings.append(f'Recent search delivered {len(seen)} unique in-window records out of {total} reported; completeness is not claimed.')
    write_jsonl(DATA/'papers.jsonl',records.values());write_jsonl(DATA/'candidates.jsonl',candidates.values());write_jsonl(DATA/'metadata-updates.jsonl',proposals.values())
    limited=any(p.get('status')==429 for p in pages)
    report={'schema_version':2,'scan_day_utc':day,'query':query,'since_utc':since,'cutoff_utc':cutoff,
        'polling_policy':'Complete arXiv snapshots are reused within one UTC publication day; failed or incomplete searches are retried by a later scheduled scan.',
        'reported_total':total,'unique_returned':len(seen),'complete':complete,'deferred':limited,
        'pages':pages,'new_ids':new_ids,'warnings':warnings}
    write_json(DATA/'recent-paper-search.json',report)
    return {'name':'recent_arxiv','ok':any(p.get('ok') for p in pages),'complete':complete,'new_count':len(new_ids),'warnings':warnings,'cache_used':False,
            'rate_limited':limited,'deferred':limited}


PAUSE_WARNING='GitHub candidate observations paused'
KNOWN_GAPS=('Discovery sources failed:','GitHub candidate requests have no accepted','GitHub metadata rows were rejected','arXiv identifiers remain unresolved')
MAX_THROTTLE_SOURCE_FAILURE_RATIO=0.05
PERSISTENT_RUNS=6


def gap_keys(row):
    """Independent gaps of a scan, one key each: a failed source id, or another warning with its numbers removed."""
    keys=set()
    for warning in row.get('warnings',[]):
        if warning.startswith(PAUSE_WARNING):continue
        if warning.startswith('Discovery sources failed:'):
            keys.update('source:'+name.strip() for name in warning.split(':',1)[1].split(','))
        else:keys.add(re.sub(r'\d+','N',warning))
    return keys


def throttle_pause(row,previous=()):
    """True for a partial scan whose only candidate gap is a provider rate-limit pause that still moved the cursor.

    The pause is expected while thousands of candidates are walked within the provider's allowance, so it must not count
    as an outage. It is not a throttle pause, and keeps counting toward repeated partial scans, when the cursor made no
    progress, another phase failed, source fetch failures exceed MAX_THROTTLE_SOURCE_FAILURE_RATIO, any warning is not a
    known gap, or an independent gap (a source, unanswered requests, rejected rows) also appeared in each of the
    PERSISTENT_RUNS scans before this one, because a gap that never clears is not transient."""
    if row.get('status')!='partial':return False
    candidate=row.get('candidate_observations') or {}
    if candidate.get('state')!='rate_limited':return False
    if not (candidate.get('successful_responses',0)>0 or candidate.get('new_unique_repositories',0)>0):return False
    fetches=row.get('source_fetches') or {}
    total=fetches.get('total',0)
    if total and (total-fetches.get('successful',0))/total>MAX_THROTTLE_SOURCE_FAILURE_RATIO:return False
    if not all(w.startswith(PAUSE_WARNING) or any(k in w for k in KNOWN_GAPS) for w in row.get('warnings',[])):return False
    recent=list(previous)[-PERSISTENT_RUNS:]
    if len(recent)==PERSISTENT_RUNS:
        persistent=gap_keys(row).intersection(*(gap_keys(r) for r in recent))
        if persistent:return False
    return True


def partial_streak(history):
    """Consecutive partial scans ending at the newest, ignoring rate-limit pauses that made progress."""
    streak=0
    for index in range(len(history)-1,-1,-1):
        row=history[index]
        if row.get('status')=='partial' and row.get('rate_limit_only'):continue
        if throttle_pause(row,history[:index]):continue
        if row.get('status')!='partial':break
        streak+=1
    return streak


RECORD_FILES=('candidates.jsonl','papers.jsonl','metadata-updates.jsonl','catalog.jsonl')
SCAN_TIMES=frozenset({'retrieved_at','last_verified_at','last_observed_at'})


def without_scan_times(value):
    if isinstance(value,dict):return {k:without_scan_times(v) for k,v in value.items() if k not in SCAN_TIMES}
    if isinstance(value,list):return [without_scan_times(v) for v in value]
    return value


def record_state():
    """Every record a scan can change, apart from the times it last looked at each one."""
    return {name:without_scan_times(read_jsonl(DATA/name)) for name in RECORD_FILES}


def nothing_to_commit(report,previous,config,current=None):
    """True when a healthy scan adds nothing to the last committed one; the caller also compares record_state().

    The next scan reads every source again, so dropping this run's files loses nothing. A scan still commits when it adds a
    record, moves the candidate cursor, records a gap or a provider cooldown that the next scan must honor, or follows
    an unhealthy scan, and when the last committed receipt reaches scan_commit_heartbeat_hours, so the freshness check and the
    updates page keep seeing recent scans."""
    limit=config.get('scan_commit_heartbeat_hours')
    if not limit or report['status']!='success' or previous.get('status')!='success' or report['warnings']:return False
    if report['new_papers'] or report['new_candidate_count'] or report['before']!=report['after']:return False
    if report['pending_metadata_changes']!=previous.get('pending_metadata_changes'):return False
    candidate=report.get('candidate_observations') or {}
    if any(candidate.get(key) for key in ('successful_responses','new_unique_repositories','settled_unknown_requests')):return False
    if report['network_budget'].get('provider_cooldowns'):return False
    try:finished=dt.datetime.fromisoformat(previous['finished_at'].replace('Z','+00:00'))
    except (KeyError,AttributeError,ValueError):return False
    return ((current or dt.datetime.now(dt.timezone.utc))-finished).total_seconds()/3600<limit


def summarize_phases(phases,source_runs,hf_runs,harvest_failures):
    problems=[]
    for phase in phases:
        if not phase.get('ok'):problems.append(phase['name']+': '+(phase.get('error') or ('deferred' if phase.get('deferred') else 'failed')))
        problems.extend(phase.get('warnings',[]))
        validation=phase.get('durable_validation',{})
        if validation.get('ok') is False:
            problems.append('Candidate snapshot integrity: '+(validation.get('error') or 'invalid durable triplet'))
    # A retired source is documented in the registry and no longer fetched, so it is not a gap of this scan.
    failed_sources=[r['id'] for r in source_runs if not r.get('ok') and r.get('state')!='retired']
    successful_query=lambda r:r.get('state')=='success' and r.get('evidence',{}).get('ok') and not r.get('parse_error')
    failed_queries=[r['id'] for r in hf_runs if not successful_query(r)]
    if failed_sources:problems.append('Discovery sources failed: '+', '.join(failed_sources))
    if failed_queries:problems.append('Paper searches failed: '+', '.join(failed_queries))
    if harvest_failures:problems.append(f'{len(harvest_failures)} arXiv identifiers remain unresolved in the retained harvest ledger.')
    phase_ok={p['name']:p.get('ok',False) for p in phases}
    candidate_usable=any(p['name']==candidate_stage.PHASE and p.get('ok') and p.get('published')
        and p.get('successful_responses',0)>0 for p in phases)
    usable=(phase_ok.get('discovery') and any(r.get('ok') and not r.get('parse_error') for r in source_runs)) or (phase_ok.get('huggingface') and any(successful_query(r) for r in hf_runs)) or phase_ok.get('recent_arxiv') or candidate_usable
    fatal=not usable or any(p['name'] in {'build','validate'} and not p.get('ok') for p in phases) or any(
        p.get('durable_validation',{}).get('ok') is False for p in phases)
    return ('failed' if fatal else 'partial' if problems else 'success'),problems


def workflow_message(text):
    """Escape text for a GitHub workflow command, which ends at the first newline."""
    return text.replace('%','%25').replace('\r','%0D').replace('\n','%0A')


def run_scan():
    config=read_json(DATA/'scan-config.json')
    if not 1<=config['recent_lookback_days']<=31 or not 1<=config['recent_max_results']<=2000:raise ValueError('Unbounded recent-search configuration')
    candidate_stage.settings(config)
    cooldowns=read_json(DATA/'scan-status.json',{}).get('network_budget',{}).get('provider_cooldowns',{})
    budget=RoundBudget.create(ROOT/'.cache/scan-rounds',
        max_requests=config.get('network_max_requests',DEFAULT_REQUESTS),
        max_seconds=config.get('network_max_seconds',DEFAULT_SECONDS),cooldowns=cooldowns)
    with budget.activate():
        return run_round(config,budget)


def run_round(config,budget):
    previous=read_json(DATA/'scan-status.json',{});records=record_state()
    started=now();before=counts();old_papers={r['id'] for r in read_jsonl(DATA/'papers.jsonl')};old_candidates={r['id'] for r in read_jsonl(DATA/'candidates.jsonl')}
    repo=os.getenv('GITHUB_REPOSITORY','');run_id=os.getenv('GITHUB_RUN_ID','')
    run_url=f'https://github.com/{repo}/actions/runs/{run_id}' if repo and run_id else None
    # Replaced when the scan finishes; a run killed before then leaves this receipt instead of the previous run's.
    write_json(DATA/'scan-status.json',{'id':'scan:'+started,'schema_version':1,'status':'running','started_at':started,'finished_at':None,'run_url':run_url,
        'network_budget':budget.summary()})
    phases=[stage('discovery',['scripts/catalog.py','discover','--refresh'])]
    source_runs=read_json(DATA/'discovery-runs.json',[])
    hf_limited=phases[0]['ok'] and any(r.get('status')==429 and r.get('provider_host')=='huggingface.co'
        and r.get('run_started_at','')>=phases[0].get('started_at',started) for r in source_runs)
    if hf_limited:
        phases.append({'name':'huggingface','started_at':now(),'ok':False,'deferred':True,
            'request_attempted':False,'error':'Deferred after the publisher-source phase returned Hugging Face HTTP 429.'})
    else:
        phases.append(stage('huggingface',['scripts/discover_papers.py','--refresh']))
    try:phases.append(recent_phase())
    except Exception as error:phases.append({'name':'recent_arxiv','ok':False,'error':str(error)})
    if phases[-1].get('rate_limited'):
        phases.append({'name':'harvest','ok':False,'deferred':True,
            'error':'Deferred after the recent arXiv query returned HTTP 429; discovered identifiers remain queued.'})
    else:
        phases.append(stage('harvest',['scripts/catalog.py','harvest','--limit',str(config['harvest_limit'])]))
    try:phases.append(candidate_phase(config))
    except Exception as error:phases.append({'name':candidate_stage.PHASE,'ok':False,'published':False,'error':str(error)})
    candidate=phases[-1]
    phases.append(stage('build',['scripts/catalog.py','build']))
    if phases[-1]['ok']:
        try:publish_candidate_phase(candidate,budget)
        except Exception as error:candidate.update(ok=False,published=False,error='Candidate publication rejected: '+str(error))
    elif candidate.get('ready_to_publish'):
        candidate['publication_deferred']='Catalog build failed; durable candidate files remain unchanged.'
    phases.append(stage('validate',['scripts/catalog.py','validate']))
    # A writer can fail during both replacement and rollback. Do not allow
    # usable legacy sources or a deferred candidate phase to mask torn state.
    candidate['durable_validation']=candidate_consistency(config)
    if not candidate['durable_validation']['ok']:
        candidate['ok']=False
        candidate.setdefault('error','Durable candidate snapshot failed its final integrity gate.')
    source_runs=read_json(DATA/'discovery-runs.json',[])
    hf_report=read_json(DATA/'paper-discovery-status.json',{})
    hf_current=(hf_report.get('schema_version')==1 and hf_report.get('finished_at')
                and hf_report.get('started_at','')>=phases[1].get('started_at',started))
    hf_runs=hf_report.get('queries',[]) if hf_current else []
    if phases[1]['ok'] and not hf_current:
        phases[1].update(ok=False,error='No complete receipt for the current paper-discovery run; previous successes are not reused.')
    harvest_failures=read_jsonl(DATA/'harvest-failures.jsonl')
    status,problems=summarize_phases(phases,source_runs,hf_runs,harvest_failures)
    rate_limited_seen=(any(r.get('status')==429 for r in source_runs)
        or any(r.get('evidence',{}).get('status')==429 for r in hf_runs)
        or any(p.get('rate_limited') for p in phases))
    def rate_limit_deferral(receipt):
        return (receipt.get('status')==429 or receipt.get('deferred_reason')=='provider_cooldown'
            or '429' in str(receipt.get('error') or ''))
    rate_limit_only=bool(status=='partial' and rate_limited_seen and all(
        p.get('ok') or p.get('rate_limited') or p.get('deferred') and rate_limit_deferral(p) for p in phases)
        and all(r.get('ok') or r.get('state')=='retired' or
            r.get('state')=='deferred' and rate_limit_deferral(r) for r in source_runs)
        and all(r.get('state')=='success' or r.get('state')=='deferred' and
            rate_limit_deferral(r.get('evidence',{})) for r in hf_runs)
        and all(r.get('deferred') for r in harvest_failures)
        and all('429' in warning for p in phases for warning in p.get('warnings',[])))
    papers=read_jsonl(DATA/'papers.jsonl');candidates=read_jsonl(DATA/'candidates.jsonl');finished=now()
    retired_sources=sum(r.get('state')=='retired' for r in source_runs)
    new_papers=[{'id':r['id'],'name':r['name'],'url':r['url'],'review_status':'metadata_verified'} for r in papers if r['id'] not in old_papers]
    report={'id':'scan:'+started,'schema_version':1,'status':status,'started_at':started,'finished_at':finished,'run_url':run_url,
        'schedule':{'timezone':config['timezone'],'times_local':config['scan_times_local']},'before':before,'after':counts(),
        'new_papers':new_papers,'new_candidate_count':sum(r['id'] not in old_candidates for r in candidates),
        'pending_metadata_changes':len(read_jsonl(DATA/'metadata-updates.jsonl')),'source_fetches':{'successful':sum(bool(r.get('ok')) for r in source_runs) if phases[0]['ok'] else 0,'total':len(source_runs)-retired_sources,**({'retired':retired_sources} if retired_sources else {})},
        'paper_searches':{'successful':sum(r.get('state')=='success' for r in hf_runs),'total':hf_report.get('configured_query_count',0) if hf_current else 0,
            'unique_identifiers':hf_report.get('unique_identifiers',0) if hf_current else 0,'new_candidates':hf_report.get('new_candidate_count',0) if hf_current else 0},
        'candidate_observations':{k:v for k,v in candidate.items() if k not in {'name','baseline_files','ready_to_publish'}},
        'phases':phases,'warnings':problems,'rate_limit_only':rate_limit_only,'policy':config['policy'],'network_budget':budget.summary()}
    write_json(DATA/'scan-status.json',report)
    history=read_jsonl(DATA/'scan-history.jsonl');history.append({k:v for k,v in report.items() if k!='phases'})
    write_jsonl(DATA/'scan-history.jsonl',history[-config['history_limit']:])
    summary=f'Scan {status}: {len(new_papers)} new paper metadata records; {report["new_candidate_count"]} new candidates; {report["after"]["curated_papers"]} reviewed papers.'
    streak=partial_streak(history)
    repeated=streak>=config.get('max_consecutive_partial',float('inf'))
    notes=problems+([f'The last {streak} scans were all partial; the recorded gaps are not clearing on their own.'] if repeated else [])
    # Notices are final answers worth reading (for example renamed candidate repositories); they are not scan gaps.
    notices=[n for p in phases for n in p.get('notices',[])]
    print(summary);print(''.join('- '+n+'\n' for n in notes+notices),end='')
    summary_file=os.getenv('GITHUB_STEP_SUMMARY')
    if summary_file:
        # In Actions, annotations put each gap on the run page; a partial scan still exits 0 so its verified data is committed.
        for problem in problems:print(f'::{"error" if status=="failed" else "warning"} title=Scan {status}::'+workflow_message(problem))
        if repeated:print('::error title=Repeated partial scans::'+notes[-1])
        for notice in notices:print('::notice title=Scan note::'+workflow_message(notice))
        with open(summary_file,'a',encoding='utf-8') as f:
            f.write('## AwesomeCUA scan\n\n'+summary+'\n\n'+f'Scheduled {scan_schedule(config)}.\n\n')
            f.write('\n'.join('- '+n for n in notes+notices)+'\n')
    if os.getenv('GITHUB_OUTPUT'):
        # The health-tracking job copies the status and recorded gaps into the scan tracking issue.
        delimiter='SCAN_NOTES_'+os.urandom(8).hex()
        with open(os.getenv('GITHUB_OUTPUT'),'a',encoding='utf-8') as f:
            f.write(f'status={status}\nnotes<<{delimiter}\n'+''.join(n.replace('\r',' ').replace('\n',' ')+'\n' for n in notes)+delimiter+'\n')
            # scan.yml fails a separate job on this output, after the scan job has committed this run's data.
            if repeated:f.write('repeated_partial=true\n')
            if nothing_to_commit(report,previous,config) and record_state()==records:f.write('nothing_new=true\n')
    return 1 if status=='failed' else 0


def check_freshness(current=None):
    """Exit status 1 unless a completed scan finished within max_scan_age_hours; GitHub can delay or drop the scheduled runs."""
    limit=read_json(DATA/'scan-config.json')['max_scan_age_hours']
    parse=lambda value:dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    # A failed scan commits nothing, and a running receipt has no finish time; only success and partial scans refreshed the catalog.
    finished=[r['finished_at'] for r in [read_json(DATA/'scan-status.json',{}),*read_jsonl(DATA/'scan-history.jsonl')] if r.get('status') in {'success','partial'} and r.get('finished_at')]
    last=max(finished,key=parse,default=None)
    age=((current or dt.datetime.now(dt.timezone.utc))-parse(last)).total_seconds()/3600 if last else None
    if age is not None and age<=limit:
        print(f'The last completed scan finished at {last}, {age:.1f} h ago, within the {limit} h limit.');return 0
    message=(f'The last completed scan finished at {last}, {age:.1f} h ago' if last else 'No completed scan is recorded')+f'; scans are expected at least every {limit} h, so a scheduled scan was delayed or dropped.'
    print(('::error title=Stale scan::' if os.getenv('GITHUB_STEP_SUMMARY') else '')+message)
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.getenv('GITHUB_OUTPUT'),'a',encoding='utf-8') as f:f.write('stale=true\n')
    return 1


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-freshness',action='store_true',help='Only check that a completed scan finished within max_scan_age_hours of data/scan-config.json; writes no data.')
    parser.add_argument('--recent-only',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args.recent_only:
        if args.check_freshness:parser.error('Recent phase and freshness check are mutually exclusive')
        budget=budget_from_environment()
        if budget is None:parser.error('Recent phase requires a network-round context')
        phase=recent_papers(read_json(DATA/'scan-config.json'))
        write_json(recent_result_path(budget),{'round_id':budget.run_id,'phase':phase})
        return 0
    return check_freshness() if args.check_freshness else run_scan()


if __name__=='__main__':
    raise SystemExit(main())

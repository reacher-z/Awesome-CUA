import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normalize,matches,filtered,parseState,serializeState,escapeHTML,safeURL,PAGE_SIZE,bibliographicDate} from '../web/catalog-core.js';
import {FEATURED} from '../web/catalog-core.js';
import {TOPIC_ALIASES,searchText,recordSearchText,KIND_ORDER,KINDS,PLATFORMS,profileVisible} from '../web/catalog-core.js';
import {FACT_LABELS,formatFact} from '../web/catalog-core.js';

const rows=readFileSync(new URL('../data/catalog.jsonl',import.meta.url),'utf8').trim().split('\n').map(JSON.parse);
const vocabulary=JSON.parse(readFileSync(new URL('../data/topics.json',import.meta.url),'utf8'));
// The same topic labels the website receives in index.json.
const topicLabels=Object.fromEntries(Object.entries(vocabulary).map(([key,entry])=>[key,[entry.en,entry.zh]]));
rows.forEach(r=>r.search_text=recordSearchText(r,topicLabels));
const initial=()=>parseState('');

test('all published resources are searchable without dropping metadata-only records',()=>{
  assert.equal(filtered(rows,initial()).length,rows.length);
  assert.equal(filtered(rows,{...initial(),review:'metadata_verified'}).length,rows.filter(r=>r.review_status==='metadata_verified').length);
});
test('platform, kind, review, and topic filters intersect',()=>{
  const state={...initial(),kind:'dataset',platform:'android',review:'curated',topic:'data-generation'};
  const actual=filtered(rows,state);
  assert.ok(actual.length>0);
  assert.ok(actual.every(r=>r.kind==='dataset'&&r.environments.includes('android')&&r.review_status==='curated'&&r.topics.includes('data-generation')));
  assert.equal(matches(actual[0],{...state,kind:'model'}),false);
});
test('source-pending papers are not silently labeled as Android',()=>{
  const papers=filtered(rows,{...initial(),kind:'paper',platform:'android',review:'metadata_verified'});
  assert.equal(papers.length,0);
});
test('search uses all terms and normalizes punctuation',()=>{
  assert.ok(filtered(rows,{...initial(),q:'UI-TARS'}).some(r=>r.name==='UI-TARS'));
  assert.equal(filtered(rows,{...initial(),q:'this resource does not exist xyzq987654'}).length,0);
  assert.equal(normalize('GUI－定位'),'gui 定位');
});
test('newest publication sorts known dates first and unknown dates last',()=>{
  const result=filtered(rows,{...initial(),sort:'newest'});
  assert.ok(bibliographicDate(result[0]));
  const index=result.findIndex(r=>!bibliographicDate(r));
  assert.ok(index>0);
  assert.ok(result.slice(index).every(r=>!bibliographicDate(r)));
});
test('publisher years and months filter and sort without invented days or arXiv date substitution',()=>{
  const make=(id,parts)=>({id,name:id,kind:'paper',review_status:'curated',environments:['web'],topics:[],search_text:'',published_at:null,details:{publication:{date_parts:parts}}});
  const year=make('url:year',[2017]),month=make('url:month',[2017,8]),day=make('url:day',[2017,8,10]),unknown=make('url:unknown',null);
  assert.equal(bibliographicDate(year),'2017');assert.equal(bibliographicDate(month),'2017-08');
  assert.deepEqual(filtered([unknown,year,month,day],{...initial(),kind:'paper',year:'2017',sort:'newest'}).map(r=>r.id),['url:day','url:month','url:year']);
  const compact={...year,details:undefined,paper_date:'2017'};
  assert.ok(matches(compact,{...initial(),year:'2017'}));
  const preprint={...month,id:'arxiv:2001.00001',published_at:'2020-01-02'};
  assert.equal(bibliographicDate(preprint),'2020-01-02');
  assert.equal(matches(preprint,{...initial(),year:'2017'}),false);
});
test('deep links round-trip search, filters, layout, language, and a selected record',()=>{
  const state={q:'GUI 定位',kind:'model',platform:'desktop',review:'curated',topic:'grounding',year:'',sort:'name',page:2,view:'list'};
  const encoded=serializeState(state,'zh','github:bytedance/ui-tars');
  assert.deepEqual(parseState(encoded),state);
  assert.equal(new URLSearchParams(encoded).get('record'),'github:bytedance/ui-tars');
  assert.equal(new URLSearchParams(encoded).get('lang'),'zh');
  for(const platform of new Set(rows.flatMap(row=>row.environments))) {
    const roundTrip=serializeState({...state,platform},'en','');
    assert.equal(parseState(roundTrip).platform,platform);
  }
});
test('learning deep links preserve kind, reviewed facets and bilingual search labels',()=>{
  const make=(id,kind,review_status='curated')=>({id,kind,review_status,name:id,url:'https://example.org/'+id,aliases:[],authors:[],summary:'Browser practice.',environments:['web'],topics:['web-navigation'],published_at:null});
  const lessons=[make('course','learning'),make('unreviewed','learning','metadata_verified'),make('paper','paper')];
  lessons.forEach(row=>row.search_text=recordSearchText(row,topicLabels));
  for(const q of ['Learning resources','学习资源']){
    const state=parseState('?kind=learning&review=curated&platform=web&topic=web-navigation&q='+encodeURIComponent(q));
    assert.equal(state.kind,'learning');
    assert.deepEqual(filtered(lessons,state).map(row=>row.id),['course']);
    const encoded=serializeState(state,'zh','course');
    assert.deepEqual(parseState(encoded),state);
    assert.equal(new URLSearchParams(encoded).get('record'),'course');
  }
  assert.equal(filtered(lessons,initial()).length,3);
  assert.deepEqual(filtered(lessons,{...initial(),kind:'learning',review:'metadata_verified'}).map(row=>row.id),['unreviewed']);
});
test('learning category, cards and directory link render in both languages',async()=>{
  const source={id:'url:course',name:'Browser course',kind:'learning',url:'https://example.org/course',page_url:'/resources/course/',aliases:[],authors:[],environments:['web'],topics:['web-navigation'],summary:'A source-reviewed browser tutorial.',review_status:'curated',published_at:null,scope:'core',related_count:0};
  const other={...source,id:'arxiv:2401.00001',kind:'paper',name:'Pending paper',review_status:'metadata_verified',summary:null,topics:[]};
  const elements=new Map(),element=selector=>{
    if(!elements.has(selector))elements.set(selector,{dataset:{},listeners:{},classList:{toggle(){}},addEventListener(type,fn){this.listeners[type]=fn;},setAttribute(){},focus(){}});
    return elements.get(selector);
  };
  const directory=element('learning-directory');directory.dataset.i18n='directoryLearning';
  const location={search:'?kind=learning&review=curated&lang=en',pathname:'/',hash:'#catalog'};
  const globals={
    document:{documentElement:{},body:{classList:{toggle(){}}},querySelector:element,querySelectorAll:selector=>selector==='[data-i18n]'?[directory]:[],addEventListener(){}},
    window:{addEventListener(){}},location,
    history:{state:null,replaceState(_,__,url){location.search=url.includes('?')?'?'+url.split('?')[1].split('#')[0]:'';}},
    localStorage:{getItem:()=>null,setItem(){}},
    fetch:async()=>({ok:true,json:async()=>({records:structuredClone([source,other]),topics:topicLabels,coverage:{curated_records:1,by_kind:{learning:1,paper:1},sources:[],as_of_utc:'2026-10-20T00:00:00Z'}})}),
  };
  const saved=Object.keys(globals).map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  try{
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import('../web/app.js?learning-kind-render');
    await new Promise(resolve=>setImmediate(resolve));
    assert.match(element('#categories').innerHTML,/data-kind="learning" aria-pressed="true"[^]*?▥[^]*?Learning resources[^]*?category-count">1</);
    assert.match(element('#results').innerHTML,/data-kind="learning"/);
    assert.match(element('#results').innerHTML,/kind-chip">Learning resources</);
    assert.doesNotMatch(element('#results').innerHTML,/Pending paper/);
    assert.equal(directory.textContent,'Learning resources');
    element('#language').listeners.click();
    assert.match(element('#categories').innerHTML,/data-kind="learning" aria-pressed="true"[^]*?学习资源/);
    assert.match(element('#results').innerHTML,/kind-chip">学习资源</);
    assert.equal(directory.textContent,'学习资源');
    assert.equal(parseState(location.search).kind,'learning');
    assert.equal(new URLSearchParams(location.search).get('lang'),'zh');
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('unrecognized sort/type and invalid pages fall back safely',()=>{
  const state=parseState('?kind=bad&sort=bad&page=-10&review=unverified');
  assert.equal(state.page,1);assert.equal(state.kind,'');assert.equal(state.sort,'featured');assert.equal(state.review,'');
  assert.equal(parseState('?page=Infinity').page,1);
  assert.ok(PAGE_SIZE>0);
});
test('numbered pagination keeps first, last and neighbouring pages one click away',async()=>{
  const {pageWindow}=await import('../web/catalog-core.js');
  assert.deepEqual(pageWindow(1,1),[1]);
  assert.deepEqual(pageWindow(1,3),[1,2,3]);
  assert.deepEqual(pageWindow(1,107),[1,2,null,107]);
  assert.deepEqual(pageWindow(4,107),[1,2,3,4,5,null,107]);
  assert.deepEqual(pageWindow(53,107),[1,null,52,53,54,null,107]);
  assert.deepEqual(pageWindow(105,107),[1,null,104,105,106,107]);
  assert.deepEqual(pageWindow(107,107),[1,null,106,107]);
  for(let pages=1;pages<=12;pages++)for(let page=1;page<=pages;page++){
    const shown=pageWindow(page,pages),numbers=shown.filter(n=>n!==null);
    for(const n of [1,page-1,page,page+1,pages].filter(n=>n>=1&&n<=pages))assert.ok(numbers.includes(n),`${page}/${pages} shows ${n}`);
    assert.deepEqual(numbers,[...numbers].sort((a,b)=>a-b));
    shown.forEach((n,i)=>{if(n===null)assert.ok(shown[i+1]-shown[i-1]>2,`${page}/${pages} hides at least two pages behind a gap`);});
  }
});
test('opening a record adds one history entry, so Back closes the dialog and keeps the filters',async()=>{
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const base={kind:'dataset',url:'https://example.org/',aliases:[],environments:['web'],topics:[],authors:[],summary:'Fixture.',review_status:'curated',published_at:null,scope:'core',paper_version:null,paper_source_url:null,paper_date:null,related_count:1,incoming_relations:[]};
  const records=[{...base,id:'url:first',name:'First fixture',page_url:'/resources/first/'},{...base,id:'url:second',name:'Second fixture',page_url:'/resources/second/'}];
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const settle=()=>new Promise(resolve=>setImmediate(resolve));
  const boot=async(search,name)=>{
    const clicks=[],popstate=[],location={search,pathname:'/',hash:''},entries=[{state:null,search}];let index=0;
    const go=delta=>{index+=delta;location.search=entries[index].search;popstate.forEach(listener=>listener());};
    const write=(state,url)=>{entries[index]={state,search:url.replace(/^[^?]*/,'')};location.search=entries[index].search;};
    const history={get state(){return entries[index].state;},get length(){return entries.length;},pushState(state,_,url){entries.splice(++index);entries.push({});write(state,url);},replaceState(state,_,url){write(state,url);},back(){go(-1);},forward(){go(1);}};
    const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,{dataset:{},listeners:{},classList:{toggle(){}},open:false,addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},setAttribute(){},focus(){},showModal(){this.open=true;},close(){if(!this.open)return;this.open=false;(this.listeners.close||[]).forEach(fn=>fn());}});return elements.get(selector);};
    const globals={document:{documentElement:{},body:{classList:{toggle(){}}},addEventListener(type,fn){if(type==='click')clicks.push(fn);},querySelector:element,querySelectorAll:()=>[]},window:{addEventListener(type,fn){if(type==='popstate')popstate.push(fn);}},location,history,localStorage:{getItem:()=>null,setItem(){}},fetch:async url=>({ok:true,json:async()=>url.endsWith('record.json')?{...records.find(r=>url===r.page_url+'record.json'),licenses:{},details:{},identifiers:{},relations:[],notes:'',evidence:[],last_verified_at:'2026-10-01'}:{coverage,records:structuredClone(records)}})};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?${name}`);await settle();
    const open=async id=>{for(const listener of clicks)listener({target:{closest:selector=>selector==='[data-record]'?{tagName:'A',dataset:{record:id}}:null},button:0,preventDefault(){}});await settle();};
    return {dialog:element('#detail-dialog'),entries,history,location,open,where:()=>`${index}/${entries.length} ${location.search}`};
  };
  try {
    const list=await boot('?q=fixture&kind=dataset','history-list');
    assert.equal(list.where(),'0/1 ?q=fixture&kind=dataset');
    await list.open('url:first');
    assert.equal(list.dialog.open,true);assert.equal(list.where(),'1/2 ?q=fixture&kind=dataset&record=url%3Afirst');
    await list.open('url:second');
    assert.equal(list.where(),'1/2 ?q=fixture&kind=dataset&record=url%3Asecond');
    list.history.back();await settle();
    assert.equal(list.dialog.open,false);assert.equal(list.where(),'0/2 ?q=fixture&kind=dataset');
    list.history.forward();await settle();
    assert.equal(list.dialog.open,true);assert.equal(list.where(),'1/2 ?q=fixture&kind=dataset&record=url%3Asecond');
    list.dialog.close();await settle();
    assert.equal(list.where(),'0/2 ?q=fixture&kind=dataset');
    const deep=await boot('?record=url%3Afirst','history-deep-link');
    assert.equal(deep.dialog.open,true);assert.equal(deep.where(),'0/1 ?record=url%3Afirst');
    deep.dialog.close();await settle();
    assert.equal(deep.where(),'0/1 ');
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('untrusted names and source URLs cannot inject active HTML',()=>{
  assert.equal(escapeHTML('<img src=x onerror="alert(1)">'),'&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
  assert.equal(safeURL('javascript:alert(1)'),'#');
  assert.equal(safeURL('data:text/html,hello'),'#');
  assert.equal(safeURL('https://example.org/path'),'https://example.org/path');
});
test('card monograms use only letters and digits from the name',async()=>{
  const {initials}=await import('../web/catalog-core.js');
  const cases={'"Are We Done Yet?": A Vision-Based Judge':'AW','DSBC : Data Science task Benchmarking':'DD','UI-TARS':'UT','\\textsc{GUI-Spotlight}: Adaptive Iterative Focus':'GS','CALA-$n$: A Quantum Library':'CN','$C^3$-Bench: The Things':'CB','Ponder & Press: Advancing':'PP','[CLS] Token Tells Everything':'CT','Human + AI for Accelerating':'HA','BrowserOS / BrowserOS neo':'BB','GUIOdyssey — current data release':'GC','Qwen2.5-VL':'QV','OSWorld':'O','面向界面 理解':'面理','𝕏 Agent':'𝕏A'};
  for(const [name,expected] of Object.entries(cases))assert.equal(initials(name),expected,name);
  for(const name of ['','— / —','$$',null])assert.equal(initials(name),'',String(name));
  for(const r of rows)assert.match(initials(r.name),/^[\p{L}\p{N}]{1,4}$/u,r.name);
});
test('featured project names do not accidentally feature identically named publishers',()=>{
  const result=filtered(rows,initial());
  const framework=result.findIndex(r=>r.name==='Browser Use'&&r.kind==='framework');
  const company=result.findIndex(r=>r.name==='Browser Use'&&r.kind==='company');
  assert.ok(framework<company);
});

test('paper browsing defaults to dense rows but explicit layout and year round-trip',()=>{
  assert.equal(parseState('?kind=paper').view,'list');
  assert.equal(parseState('?kind=survey').view,'list');
  assert.equal(parseState('?kind=model').view,'grid');
  const state={...parseState('?kind=paper'),year:'2026',view:'grid'};
  assert.deepEqual(parseState(serializeState(state,'zh')),state);
  const result=filtered(rows,{...state,review:'curated'});
  assert.ok(result.length>0);assert.ok(result.every(r=>bibliographicDate(r).slice(0,4)==='2026'));
  assert.equal(parseState('?year=hello').year,'');
});
test('paper curated-first order puts reviewed recent work before older reviewed work',()=>{
  const result=filtered(rows,parseState('?kind=paper'));
  const reviewed=result.filter(r=>r.review_status==='curated');
  assert.ok(reviewed.length>0);assert.ok(reviewed.slice(1).every((r,i)=>bibliographicDate(reviewed[i])>=bibliographicDate(r)));
  assert.ok(result.slice(reviewed.length).every(r=>r.review_status!=='curated'));
});

const rankingRecord=(id,name,date,extra={})=>{
  const row={id,name,published_at:date,kind:'paper',review_status:'curated',aliases:[],authors:[],
    environments:['web'],topics:['evaluation'],summary:'A computer-use evaluation.',...extra};
  return {...row,search_text:recordSearchText(row,topicLabels)};
};
test('named paper and acronym titles outrank newer incidental mentions without hiding them',()=>{
  for(const name of ['OSWorld','WebArena','AndroidWorld','Agent S']){
    const original=rankingRecord('original',name+'： A benchmark for computer-use agents','2024-01-01');
    const related=rankingRecord('related',name+' 2: Further evaluation','2025-01-01');
    const mention=rankingRecord('mention','Recent evaluation study','2026-01-01',{summary:'Evaluated using '+name+'.'});
    const input=[mention,related,original],result=filtered(input,{...initial(),q:name,kind:'paper'});
    assert.deepEqual(result.map(r=>r.id),['original','related','mention'],name);
    assert.deepEqual(input,[mention,related,original],'input order is not mutated');
  }
});
test('exact aliases and title-term matches precede summary-only matches',()=>{
  const aliased=rankingRecord('alias','A workspace benchmark','2024-01-01',{aliases:['DeskBench']});
  const title=rankingRecord('title','Revisiting DeskBench evaluation','2025-01-01');
  const mention=rankingRecord('mention','Recent evaluation study','2026-01-01',{summary:'Evaluated using DeskBench.'});
  assert.deepEqual(filtered([mention,title,aliased],{...initial(),q:'deskbench',kind:'paper'}).map(r=>r.id),['alias','title','mention']);
});
test('already-searchable spaced compound names rank their titles and aliases above incidental mentions',()=>{
  for(const [name,query] of [['WebArena','Web Arena'],['AndroidWorld','Android World'],['MobileWorld','Mobile World']]){
    const original=rankingRecord('original',name+': A benchmark','2023-01-01');
    const alias=rankingRecord('alias','A prior benchmark','2022-01-01',{aliases:[name]});
    const mention=rankingRecord('mention','Latest study','2026-01-01',{summary:'Experiments use '+query+'.'});
    const input=[mention,alias,original],state={...initial(),q:query,kind:'paper'};
    assert.deepEqual(filtered(input,state).map(r=>r.id),['original','alias','mention'],query);
    assert.deepEqual(input.filter(r=>matches(r,state)).map(r=>r.id),['mention','alias','original']);
    assert.deepEqual(filtered(input,{...state,sort:'newest'}).map(r=>r.id),['mention','original','alias']);
  }
});
test('acronym-to-word boundaries make OSWorld and GUIOdyssey searchable as spaced names',()=>{
  for(const [name,query] of [['OSWorld','OS World'],['GUIOdyssey','GUI Odyssey']]){
    const original=rankingRecord('original',name+': A benchmark','2024-01-01');
    const mention=rankingRecord('mention','Recent study','2026-01-01',{summary:'We evaluate '+query+'.'});
    assert.ok(matches(original,{...initial(),q:query}),query);
    assert.ok(matches(original,{...initial(),q:name}),name);
    assert.deepEqual(filtered([mention,original],{...initial(),kind:'paper',q:query}).map(r=>r.id),['original','mention']);
  }
});
test('acronym expansion retains original and earlier camel-case forms for macOSWorld',()=>{
  const record=rankingRecord('original','macOSWorld','2024-01-01');
  for(const form of ['macosworld','mac osworld','macos world','mac os world'])assert.ok(record.search_text.includes(form),form);
  for(const query of ['macOSWorld','osworld','mac OSWorld','macOS World','mac OS World','OS World']){
    assert.ok(matches(record,{...initial(),q:query}),query);
  }
});
test('single-word compound title and alias fragments outrank incidental summary mentions',()=>{
  for(const [name,alias,query] of [['WebArena: A benchmark',null,'Arena'],['A prior benchmark','GUIOdyssey','Odyssey']]){
    const original=rankingRecord('original',name,'2024-01-01',{aliases:alias?[alias]:[]});
    const mention=rankingRecord('mention','Recent study','2026-01-01',{summary:'We evaluate '+query+'.'});
    assert.deepEqual(filtered([mention,original],{...initial(),kind:'paper',q:query}).map(r=>r.id),['original','mention'],query);
  }
});
test('new acronym forms preserve AND filters, review priority and explicit date sorting',()=>{
  const original=rankingRecord('original','GUIOdyssey: Mobile tasks','2024-01-01',{environments:['android']});
  const mention=rankingRecord('mention','Recent study','2026-01-01',{summary:'GUI Odyssey tasks.',environments:['android']});
  const pending=rankingRecord('pending','GUI Odyssey','2027-01-01',{review_status:'metadata_verified',environments:['android']});
  const wrongPlatform=rankingRecord('web','GUIOdyssey','2024-01-01');
  const input=[mention,pending,wrongPlatform,original],state={...initial(),kind:'paper',q:'GUI Odyssey',platform:'android'};
  assert.deepEqual(filtered(input,state).map(r=>r.id),['original','mention','pending']);
  assert.deepEqual(filtered(input,{...state,sort:'newest'}).map(r=>r.id),['pending','mention','original']);
  assert.deepEqual(filtered(input,{...state,review:'curated',year:'2024',topic:'evaluation'}).map(r=>r.id),['original']);
  assert.equal(filtered(input,{...state,q:'GUI Odyssey absent-token'}).length,0);
});
test('query relevance preserves review groups and explicit newest and empty-query ordering',()=>{
  const older=rankingRecord('old','OSWorld: Original benchmark','2024-01-01');
  const recent=rankingRecord('recent','Recent study','2026-01-01',{summary:'Evaluated using OSWorld.'});
  const pending=rankingRecord('pending','OSWorld','2027-01-01',{review_status:'metadata_verified'});
  const input=[pending,recent,older],state={...initial(),kind:'paper',q:'OSWorld'};
  assert.deepEqual(filtered(input,state).map(r=>r.id),['old','recent','pending']);
  assert.deepEqual(filtered(input,{...state,sort:'newest'}).map(r=>r.id),['pending','recent','old']);
  assert.deepEqual(filtered(input,{...state,q:''}).map(r=>r.id),['recent','old','pending']);
});
test('query ranking never broadens literal AND matching or changes intersected filters',()=>{
  const records=[rankingRecord('named','OSWorld: Mobile evaluation','2024-01-01',{environments:['android']}),
    rankingRecord('mention','Recent study','2026-01-01',{summary:'OSWorld mobile evaluation.',environments:['android']}),
    rankingRecord('wrong-platform','OSWorld: Mobile benchmark','2025-01-01'),
    rankingRecord('missing-term','OSWorld','2024-01-01',{environments:['android']}),
    rankingRecord('pending','OSWorld: Mobile benchmark','2024-01-01',{review_status:'metadata_verified',environments:['android']})];
  const state={...initial(),kind:'paper',q:'OSWorld mobile',platform:'android',review:'curated',topic:'evaluation'};
  assert.deepEqual(filtered(records,state).map(r=>r.id),['named','mention']);
  assert.deepEqual(filtered(records,state).map(r=>r.id).sort(),records.filter(r=>matches(r,state)).map(r=>r.id).sort());
  assert.equal(filtered(records,{...state,q:'OSWorld missing-token'}).length,0);
});

test('details request only their own JSON and share concurrent/cached requests',async()=>{
  const {createRecordLoader}=await import('../web/catalog-core.js');
  const calls=[];let release;
  const load=createRecordLoader(url=>{calls.push(url);return new Promise(resolve=>{release=resolve;});});
  const record={id:'arxiv:2404.07972',page_url:'/resources/arxiv-2404-07972/'};
  const first=load(record),second=load(record);
  assert.deepEqual(calls,['/resources/arxiv-2404-07972/record.json']);
  const full={id:record.id,review_status:'curated',details:{example:true}};
  release({ok:true,json:async()=>full});
  assert.deepEqual(await first,full);assert.deepEqual(await second,full);assert.deepEqual(await load(record),full);
  assert.equal(calls.length,1);
});
test('failed, mismatched, or scope-excluded detail payloads are not cached as active records',async()=>{
  const {createRecordLoader}=await import('../web/catalog-core.js');
  const record={id:'arxiv:2404.07972',page_url:'/resources/arxiv-2404-07972/'};
  for(const bad of [{ok:false,status:503},{ok:true,json:async()=>({id:'arxiv:other',review_status:'curated'})},{ok:true,json:async()=>({id:record.id,status:'excluded'})}]){
    let calls=0;const load=createRecordLoader(async()=>++calls===1?bad:{ok:true,json:async()=>({id:record.id,review_status:'curated'})});
    await assert.rejects(load(record));assert.equal((await load(record)).id,record.id);assert.equal(calls,2);
  }
});
test('related records opened inside the dialog start at the top with focus on the new title',async()=>{
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const base={kind:'dataset',url:'https://example.org/',aliases:[],environments:['web'],topics:[],authors:[],summary:'Fixture.',review_status:'curated',published_at:null,scope:'core',paper_version:null,paper_source_url:null,paper_date:null,related_count:1,incoming_relations:[]};
  const records=[{...base,id:'url:first',name:'First fixture',page_url:'/resources/first/'},{...base,id:'url:second',name:'Second fixture',page_url:'/resources/second/'}];
  const full=r=>({...r,licenses:{},details:{},identifiers:{},relations:[{type:'related_to',target_id:r.id==='url:first'?'url:second':'url:first'}],notes:'',evidence:[],last_verified_at:'2026-10-01'});
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const clicks=[],doc={documentElement:{},body:{classList:{toggle(){}}},addEventListener(type,fn){if(type==='click')clicks.push(fn);},querySelectorAll:()=>[]};
  const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,{dataset:{},classList:{toggle(){}},open:false,addEventListener(){},setAttribute(){},focus(){doc.activeElement=this;},showModal(){this.open=true;},close(){this.open=false;}});return elements.get(selector);};
  doc.querySelector=element;
  const globals={document:doc,window:{addEventListener(){}},location:{search:'',pathname:'/',hash:''},history:{state:null,pushState(){},replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async url=>({ok:true,json:async()=>url.endsWith('record.json')?full(records.find(r=>url===r.page_url+'record.json')):{coverage,records:structuredClone(records)}})};
  const settle=()=>new Promise(resolve=>setImmediate(resolve));
  const open=async(id,tagName)=>{for(const listener of clicks)listener({target:{closest:selector=>selector==='[data-record]'?{tagName,dataset:{record:id}}:null},button:0,preventDefault(){}});await settle();};
  try {
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import('../web/app.js?related-focus');await settle();
    const dialog=element('#detail-dialog'),content=()=>element('#detail-content').innerHTML;
    dialog.scrollTop=120;
    await open('url:first','A');
    assert.equal(dialog.open,true);assert.equal(dialog.scrollTop,120);assert.equal(doc.activeElement,undefined);
    assert.match(content(),/^<h2 id="detail-title" tabindex="-1">First fixture<\/h2>[\s\S]*data-record="url:second">Second fixture<\/button>/);
    dialog.scrollTop=591;
    await open('url:second','BUTTON');
    assert.equal(dialog.scrollTop,0);assert.equal(doc.activeElement,element('#detail-title'));
    assert.match(content(),/^<h2 id="detail-title" tabindex="-1">Second fixture<\/h2>/);
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('explicit sorts and empty-query order stay stable without per-comparison normalization',()=>{
  const alpha=(a,b)=>a.name.localeCompare(b.name,'en',{sensitivity:'base'}),newer=(a,b)=>bibliographicDate(b).localeCompare(bibliographicDate(a));
  const legacy=state=>{
    const result=rows.filter(r=>matches(r,state)),rank=r=>r.kind!=='company'&&FEATURED.includes(r.name)?FEATURED.indexOf(r.name):FEATURED.length,exact=r=>state.q&&normalize(r.name)===normalize(state.q)?-1:0;
    if(state.sort==='name')return result.sort(alpha);
    if(state.sort==='newest')return result.sort((a,b)=>newer(a,b)||alpha(a,b));
    return result.sort((a,b)=>Number(a.review_status!=='curated')-Number(b.review_status!=='curated')||(['paper','survey'].includes(state.kind)?newer(a,b)||alpha(a,b):exact(a)-exact(b)||rank(a)-rank(b)||alpha(a,b)));
  };
  for(const sort of ['featured','name','newest'])for(const q of ['','g','browser use'])for(const kind of ['','paper']){
    const state={...initial(),sort,q,kind};
    const actual=filtered(rows,state).map(r=>r.id),previous=legacy(state).map(r=>r.id);
    // Only the default queried ranking changed; every query still has the same population.
    assert.deepEqual(sort==='featured'&&q?actual.toSorted():actual,sort==='featured'&&q?previous.toSorted():previous,JSON.stringify(state));
  }
  const {normalize:nativeNormalize,localeCompare}=String.prototype;let normalized=0,collated=0;
  String.prototype.normalize=function(...args){normalized++;return nativeNormalize.apply(this,args);};
  String.prototype.localeCompare=function(...args){collated++;return localeCompare.apply(this,args);};
  try{for(const sort of ['featured','name','newest'])filtered(rows,{...initial(),sort,q:'g'});}finally{String.prototype.normalize=nativeNormalize;String.prototype.localeCompare=localeCompare;}
  assert.equal(collated,0);
  assert.ok(normalized<=5*rows.length,`${normalized} normalizations for ${rows.length} records`);
});
test('desktop and mobile platforms include their operating systems',()=>{
  const ids=platform=>new Set(filtered(rows,{...initial(),platform}).map(r=>r.id));
  const desktop=ids('desktop'),mobile=ids('mobile');
  for(const r of rows){
    assert.equal(desktop.has(r.id),r.environments.some(x=>['desktop','windows','macos','linux'].includes(x)),r.name);
    assert.equal(mobile.has(r.id),r.environments.some(x=>['android','ios','harmonyos'].includes(x)),r.name);
  }
  assert.ok(rows.some(r=>mobile.has(r.id)&&r.environments.includes('ios')&&!r.environments.includes('android')));
  // The catalog lists desktop with every desktop OS, so the group's expansion is checked on a record tagged only with one.
  assert.ok(matches({...rows[0],environments:['windows']},{...initial(),platform:'desktop'}));
  assert.ok(filtered(rows,{...initial(),platform:'windows'}).every(r=>r.environments.includes('windows')));
  assert.equal(parseState(serializeState({...initial(),platform:'mobile'},'en')).platform,'mobile');
});
test('hero shortcuts and the platform menu offer grouped platforms in order',()=>{
  const html=readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
  assert.deepEqual(Object.keys(PLATFORMS),['web','desktop','windows','macos','linux','mobile','android','ios','harmonyos','cross-platform','unspecified']);
  assert.deepEqual([...html.matchAll(/data-environment="([^"]+)"/g)].map(m=>m[1]),['web','desktop','mobile']);
  assert.ok(filtered(rows,{...initial(),platform:'mobile'}).some(r=>r.name==='iOSWorld'));
  assert.ok(filtered(rows,{...initial(),platform:'desktop'}).some(r=>r.name.startsWith('Windows Agent Arena')));
});
test('search finds records by their English and Chinese kind, platform and topic labels',()=>{
  const grounding=rows.filter(r=>r.topics.includes('grounding')),datasets=rows.filter(r=>r.kind==='dataset'),web=rows.filter(r=>r.environments.includes('web'));
  for(const [q,expected] of [['GUI 定位',grounding],['GUI grounding',grounding],['数据集',datasets],['Datasets',datasets],['浏览器',web]]){
    const result=new Set(filtered(rows,{...initial(),q}));
    assert.ok(expected.length>0&&expected.every(r=>result.has(r)),q);
  }
  const record={name:'Fixture',summary:null,aliases:[],authors:[],kind:'benchmark',environments:['unspecified','harmonyos'],topics:['reinforcement-learning']};
  record.search_text=recordSearchText(record,topicLabels);
  for(const q of ['评测基准','Benchmarks','待标注','Unassigned','鸿蒙','强化学习','Reinforcement learning','RL'])assert.ok(matches(record,{...initial(),q}),q);
  assert.equal(matches(record,{...initial(),q:'unspecified'}),false);
});
test('every catalog kind, platform and topic has English and Chinese labels',()=>{
  const labelled=labels=>Array.isArray(labels)&&labels.slice(0,2).filter(x=>typeof x==='string'&&x.trim()).length===2;
  for(const kind of new Set([...KIND_ORDER,...rows.map(r=>r.kind)]))assert.ok(labelled(KINDS[kind]),`kind ${kind}`);
  for(const platform of new Set(rows.flatMap(r=>r.environments)))assert.ok(labelled(PLATFORMS[platform]),`platform ${platform}`);
  for(const topic of new Set(rows.flatMap(r=>r.topics)))assert.ok(labelled(topicLabels[topic]),`topic ${topic}`);
});
test('comparison profiles must be in the chosen environment and contain every term',()=>{
  const text=normalize('AndroidControl android screenshots accessibility-tree JSON annotations'),terms=q=>normalize(q).split(' ').filter(Boolean);
  assert.ok(profileVisible(text,['android'],[],''));
  assert.ok(profileVisible(text,['android'],terms('json SCREENSHOTS'),'android'));
  assert.ok(profileVisible(text,['android','web'],terms('accessibility tree'),'web'));
  assert.equal(profileVisible(text,['android'],terms('json video'),''),false);
  assert.equal(profileVisible(text,['android'],terms('json'),'web'),false);
});
test('the comparison page hides rows outside the filter and keeps it in the URL',async()=>{
  const keys=['document','location','history'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const profiles=[['OSWorld desktop screenshots execution-based checks','desktop linux'],['AndroidWorld android screenshots programmatic state checks','android'],['WebArena web accessibility tree','web']].map(([search,environments])=>({dataset:{search,environments},hidden:false}));
  const listeners={},control=name=>({value:'',addEventListener:(type,listener)=>listeners[name]=listener});
  const query=control('query'),environment={...control('environment'),options:['','android','desktop','linux','web'].map(value=>({value}))},output={textContent:''},urls=[];
  const elements={'#compare-query':query,'#compare-environment':environment,'#compare-results':output};
  const globals={document:{querySelector:selector=>elements[selector],querySelectorAll:selector=>selector==='[data-profile-row]'?profiles:[]},
    location:{search:'?q=screenshots&environment=android',href:'https://awesomecua.github.io/compare/benchmarks/?q=screenshots&environment=android'},history:{replaceState:(data,title,url)=>urls.push(String(url))}};
  for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
  try {
    await import('../web/compare.js?filter');
    assert.deepEqual([query.value,environment.value],['screenshots','android']);
    assert.deepEqual(profiles.map(row=>row.hidden),[true,false,true]);
    assert.equal(output.textContent,'Showing 1 of 3 profiles.');
    query.value='checks';environment.value='';listeners.environment();
    assert.deepEqual(profiles.map(row=>row.hidden),[false,false,true]);
    assert.equal(output.textContent,'Showing 2 of 3 profiles.');
    assert.equal(new URL(urls.at(-1)).search,'?q=checks');
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('search matches Latin terms at word starts while keeping CJK substrings and topic abbreviations',()=>{
  const rl=filtered(rows,{...initial(),q:'rl'}),tagged=rows.filter(r=>r.topics.includes('reinforcement-learning'));
  assert.ok(!rl.some(r=>r.name==='OSWorld'));
  assert.ok(tagged.length>0&&tagged.every(r=>rl.includes(r)));
  assert.ok(filtered(rows,{...initial(),q:'osworld'}).some(r=>r.name==='OSWorld'));
  assert.ok(filtered(rows,{...initial(),q:'UI-TARS'}).some(r=>r.name==='UI-TARS'));
  const record={search_text:searchText(['macOSWorld SpreadsheetLLM','面向界面理解的 GUI 定位'])};
  for(const q of ['osworld','macosworld','llm','GUI 定位','理解','界面理解 gui'])assert.ok(matches(record,{...initial(),q}),q);
  for(const q of ['sworld','preadsheet','ui','gent'])assert.equal(matches(record,{...initial(),q}),false,q);
});
test('record facts label every published detail and never print raw objects',()=>{
  for(const r of rows)for(const [key,value] of Object.entries(r.details)){
    if(['arxiv_snapshot','publication','license_review'].includes(key))continue;
    assert.ok(FACT_LABELS[key]?.[0]&&FACT_LABELS[key]?.[1],`${key} needs English and Chinese labels`);
    for(const lang of ['en','zh'])assert.doesNotMatch(formatFact(key,value,lang),/\[object |undefined/,`${r.id} ${key}`);
  }
  assert.equal(formatFact('reported_scale',{comparison:'>',unit:'demonstrations',value:15000},'en'),'> 15,000 demonstrations');
  const profile={counts:[{basis:'reported',qualifier:'more-than',unit:'demonstrations',value:15000,population:'AndroidControl collection'},{basis:'computed',qualifier:'exact',unit:'applications',value:833,population:'app list'}],evidence_urls:['https://example.org'],formats:[],modalities:['screenshots','accessibility trees'],notes:'n',splits:[],supervision:['trajectories']};
  assert.equal(formatFact('dataset_profile',profile,'en'),'Supervision: trajectories\nModalities: screenshots, accessibility trees\nScale: > 15,000 demonstrations (AndroidControl collection); 833 applications (app list, computed)');
  assert.ok(formatFact('dataset_profile',profile,'zh').startsWith('监督信号：trajectories\n'));
  assert.equal(formatFact('gated','auto','en'),'Yes, approved automatically');
  assert.equal(formatFact('gated',false,'zh'),'否');
  for(const lang of ['en','zh'])assert.equal(formatFact('repository_id',1079441024,lang),'1079441024');
  assert.equal(formatFact('platform_constraints',{harmonyos:'HarmonyOS 4 or earlier'},'en'),'harmonyos: HarmonyOS 4 or earlier');
  assert.equal(formatFact('dataverse',{publisher:'Harvard Dataverse',version_number:5,version_minor_number:0,file_count:261,license:{name:'CC0 1.0'},publication_date:'2025-05-15'},'en'),'Harvard Dataverse · v5.0 · 261 files · CC0 1.0 · published May 15, 2025');
  for(const empty of [null,'',[]])assert.equal(formatFact('languages',empty,'en'),'');
});
test('compact card facts list only recorded year, arXiv paper and declared licenses',async()=>{
  const {compactFacts}=await import('../web/catalog-core.js');
  const osworld={id:'github:xlang-ai/osworld',published_at:null,paper_arxiv:'2404.07972',declared_licenses:{code:'Apache-2.0',weights:'MIT'}};
  assert.deepEqual(compactFacts(osworld),[{key:'paper',text:'arXiv 2404.07972',url:'https://arxiv.org/abs/2404.07972'},{key:'license',text:'code Apache-2.0'},{key:'license',text:'weights MIT'}]);
  assert.deepEqual(compactFacts({...osworld,published_at:'2024-04-11'},slot=>({code:'代码',weights:'模型权重'})[slot]).map(f=>f.text),['2024','arXiv 2404.07972','代码 Apache-2.0','模型权重 MIT']);
  assert.deepEqual(compactFacts({id:'url:bare',published_at:null,paper_arxiv:null,declared_licenses:{}}),[]);
  assert.deepEqual(compactFacts({id:'url:bare',published_at:null}),[]);
  for(const r of rows)for(const fact of compactFacts(r))assert.match(fact.text,/^\d{4}$/,r.id);
});
test('cards and list rows render compact facts without placeholders',async()=>{
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const base={aliases:[],environments:['desktop'],topics:[],authors:[],scope:'core',review_status:'curated',summary:'Fixture summary.',paper_version:null,paper_source_url:null,paper_date:null,related_count:0,incoming_relations:[]};
  const records=[{...base,id:'github:xlang-ai/osworld',name:'OSWorld',kind:'benchmark',url:'https://github.com/xlang-ai/OSWorld',page_url:'/resources/osworld/',published_at:null,paper_arxiv:'2404.07972',declared_licenses:{code:'Apache-2.0'}},
    {...base,id:'url:bare',name:'Bare tool',kind:'tool',url:'https://example.org/',page_url:'/resources/bare/',published_at:null,paper_arxiv:null,declared_licenses:{}}];
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const render=async(search,name)=>{
    const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,{dataset:{},classList:{toggle(){}},addEventListener(){},setAttribute(){},showModal(){},close(){}});return elements.get(selector);};
    const globals={document:{documentElement:{},body:{classList:{toggle(){}}},addEventListener(){},querySelector:element,querySelectorAll:()=>[]},window:{addEventListener(){}},location:{search,pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>({ok:true,json:async()=>({coverage,records:structuredClone(records)})})};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?${name}`);await new Promise(resolve=>setImmediate(resolve));
    return element('#results').innerHTML.split(/(?=<article )/);
  };
  try {
    const [card,bare]=await render('','facts-grid');
    assert.match(card,/<p class="card-facts"><a href="https:\/\/arxiv\.org\/abs\/2404\.07972"[^>]*>arXiv 2404\.07972<\/a>\u00a0· <span title="Code Apache-2\.0">Code Apache-2\.0<\/span><\/p>/);
    assert.doesNotMatch(bare,/card-facts/);
    const [row,bareRow]=await render('?view=list&lang=zh','facts-list');
    assert.match(row,/>arXiv 2404\.07972<\/a><span title="代码 Apache-2\.0">代码 Apache-2\.0<\/span>/);
    for(const html of [row,bareRow])assert.doesNotMatch(html,/—|<time|row-date-value/);
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
const css=readFileSync(new URL('../web/styles.css',import.meta.url),'utf8');
const declaration=(selector,prop)=>{const block=css.match(new RegExp(`(?:^|[}\\n])${selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}\\{([^}]*)`))[1];const value=block.match(new RegExp(`(?:^|;)${prop}:([^;]+)`))[1].replace(/^var\(--([\w-]+)\)$/,(_,name)=>declaration(':root','--'+name));return value.length===4?'#'+[...value.slice(1)].map(c=>c+c).join(''):value;};
const luminance=hex=>{const [r,g,b]=hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return .2126*r+.7152*g+.0722*b;};
const contrast=(a,b)=>{const [x,y]=[luminance(a),luminance(b)].sort((m,n)=>n-m);return (x+.05)/(y+.05);};
test('small secondary text meets WCAG AA contrast on its surface',()=>{
  const bg=declaration(':root','--bg'),map=declaration('.ecosystem-map','background-color'),white='#ffffff';
  const pairs=[['.brand-label',white],['.hero-caption',bg],['.map-label',map],['.map-coordinates',map],['.map-foot',map],['.map-node small',white],['.section-eyebrow',declaration('.about-section','background')],['.sidebar-label',bg],['.category-count',bg],['.select-wrap>span',white],['.search-box input::placeholder',white],['.popular-topics',bg],['.popular-topics>button',declaration('.popular-topics>button','background')],['.card-tags span',white],['.card-bottom',white],['.card-bottom.is-curated',white],['.catalog-footnote',bg],['footer',bg],['.license-item span',white],['.coverage-table th',white],['.fact-list dt',white]];
  for(const kind of ['','.resource-card[data-kind=model] ','.resource-card[data-kind=dataset] ','.resource-card[data-kind=benchmark] ','.resource-card[data-kind=agent] '])pairs.push([kind+'.resource-monogram',declaration(kind+'.resource-monogram','background')]);
  for(const [selector,surface] of pairs)assert.ok(contrast(declaration(selector,'color'),surface)>=4.5,`${selector} is ${contrast(declaration(selector,'color'),surface).toFixed(2)}:1`);
});
test('pagination is a nav of numbered page buttons with the current page marked in both languages',async()=>{
  const current='.pagination .page-numbers button[aria-current=page]';
  assert.ok(contrast(declaration(current,'color'),declaration(current,'background'))>=4.5);
  const size=css.match(/\}\.pagination \.page-numbers button\{([^}]*)\}/)[1];
  for(const prop of ['min-width','min-height'])assert.ok(Number(size.match(new RegExp(`(?:^|;)${prop}:(\\d+)px`))?.[1])>=24,prop);
  assert.match(readFileSync(new URL('../web/index.html',import.meta.url),'utf8'),/<nav id="pagination" class="pagination" aria-label="[^"]+"[^>]*>/);
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const records=Array.from({length:PAGE_SIZE*7+1},(_,i)=>({id:`url:page-${i}`,name:`Fixture ${String(i).padStart(3,'0')}`,kind:'tool',url:'https://example.org/',page_url:`/resources/page-${i}/`,aliases:[],environments:['web'],topics:[],authors:[],summary:'Fixture.',review_status:'curated',published_at:null,scope:'core',paper_version:null,paper_source_url:null,paper_date:null,related_count:0,incoming_relations:[]}));
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const boot=async(search,name)=>{
    const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,{dataset:{},listeners:{},classList:{toggle(){}},addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},setAttribute(){},scrollIntoView(){},focus(){},showModal(){},close(){}});return elements.get(selector);};
    const globals={document:{documentElement:{},body:{classList:{toggle(){}}},addEventListener(){},querySelector:element,querySelectorAll:()=>[]},window:{addEventListener(){}},location:{search,pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>({ok:true,json:async()=>({coverage,records:structuredClone(records)})})};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?${name}`);await new Promise(resolve=>setImmediate(resolve));
    return element('#pagination');
  };
  try {
    const nav=await boot('?page=4','pager-en'),html=()=>nav.innerHTML;
    assert.deepEqual([...html().matchAll(/<button type="button" data-page="(\d+)"/g)].map(m=>Number(m[1])),[3,1,2,3,4,5,8,5]);
    assert.match(html(),/data-page="4" aria-label="Page 4" aria-current="page">4<\/button>/);
    assert.equal(html().match(/aria-current/g).length,1);
    assert.match(html(),/<span class="page-gap" aria-hidden="true">…<\/span><button type="button" data-page="8"/);
    nav.listeners.click[0]({target:{closest:()=>({disabled:false,dataset:{page:'8'}})}});
    assert.match(html(),/data-page="8" aria-label="Page 8" aria-current="page">8<\/button><\/span><button type="button" data-page="9" disabled>/);
    const zh=await boot('?page=2&lang=zh','pager-zh');
    assert.match(zh.innerHTML,/data-page="2" aria-label="第 2 页" aria-current="page">2<\/button>/);
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('keyboard focus lands on a control and paging is announced after categories, pages and resets re-render',async()=>{
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const records=Array.from({length:PAGE_SIZE*2+1},(_,i)=>({id:`url:focus-${i}`,name:`Fixture ${i}`,kind:i%2?'tool':'dataset',url:'https://example.org/',page_url:`/resources/focus-${i}/`,aliases:[],environments:['web'],topics:[],authors:[],summary:'Fixture.',review_status:'curated',published_at:null,scope:'core',paper_version:null,paper_source_url:null,paper_date:null,related_count:0,incoming_relations:[]}));
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const boot=async(search,name)=>{
    const doc={documentElement:{},body:{classList:{toggle(){}}},addEventListener(){},querySelectorAll:()=>[]};
    const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,{dataset:{},listeners:{},classList:{toggle(){}},addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},setAttribute(){},scrollIntoView(){},focus(){doc.activeElement=this;},showModal(){},close(){}});return elements.get(selector);};
    doc.querySelector=element;
    const globals={document:doc,window:{addEventListener(){}},location:{search,pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>({ok:true,json:async()=>({coverage,records:structuredClone(records)})})};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?${name}`);await new Promise(resolve=>setImmediate(resolve));
    return {doc,element,status:()=>element('#results-count').innerHTML};
  };
  try {
    const {doc,element,status}=await boot('?kind=tool','focus-en');
    for(const kind of ['dataset','']){
      doc.activeElement={dataset:{kind},closest:()=>doc.activeElement};
      element('#categories').listeners.click[0]({target:doc.activeElement});
      assert.equal(doc.activeElement,element(`#categories [data-kind="${kind}"]`),`category ${kind}`);
    }
    assert.match(status(),/<span class="sr-only"> · Page 1 of 3<\/span>$/);
    element('#pagination').listeners.click[0]({target:{closest:()=>({disabled:false,dataset:{page:'2'}})}});
    assert.equal(doc.activeElement,element('#results-count'));
    assert.match(status(),/<span class="sr-only"> · Page 2 of 3<\/span>$/);
    for(const id of ['#clear-filters','#empty-reset']){
      element('#search').listeners.input[0]({target:{value:'Fixture 7'}});
      assert.doesNotMatch(status(),/sr-only/);
      doc.activeElement=element(id);element(id).listeners.click[0]();
      assert.equal(doc.activeElement,element('#results-count'),id);
      assert.match(status(),/Page 1 of 3/);
    }
    assert.match((await boot('?page=2&lang=zh','focus-zh')).status(),/<span class="sr-only"> · 第 2 页，共 3 页<\/span>$/);
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('primary navigation stays reachable on narrow screens',()=>{
  const styles=readFileSync(new URL('../web/styles.css',import.meta.url),'utf8');
  const narrow=[...styles.matchAll(/@media\(max-width:(\d+)px\)\{/g)].filter(m=>Number(m[1])<=760).map(m=>{let depth=1,i=m.index+m[0].length;const start=i;while(depth)depth+=({'{':1,'}':-1}[styles[i++]]||0);return styles.slice(start,i-1);}).join('');
  const nav=[...narrow.matchAll(/(?:^|\})\.site-header nav\{([^}]*)\}/g)].map(m=>m[1]).join(';');
  assert.doesNotMatch(nav,/display:none/);
  assert.match(nav,/overflow-x:auto/);
});
test('data and coverage buttons respond while the catalog loads and after it fails',async()=>{
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]),consoleError=console.error;
  const boot=async name=>{
    let respond;const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,{dataset:{},listeners:{},classList:{toggle(){}},open:false,addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},setAttribute(){},showModal(){this.open=true;},close(){this.open=false;}});return elements.get(selector);};
    const globals={document:{documentElement:{},body:{classList:{toggle(){}}},addEventListener(){},querySelector:element,querySelectorAll:()=>[]},window:{addEventListener(){}},location:{search:'',pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:()=>new Promise(resolve=>respond=resolve)};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?${name}`);
    const dialog=element('#info-dialog');
    const content=()=>element('#info-content').innerHTML;
    return {dialog,content,respond:async value=>{respond(value);await new Promise(resolve=>setImmediate(resolve));},open:id=>{dialog.close();element('#'+id).listeners.click[0]();return content();}};
  };
  try {
    console.error=()=>{};
    const slow=await boot('loading');
    assert.match(slow.open('hero-download'),/\.\/downloads\/catalog\.jsonl/);assert.equal(slow.dialog.open,true);
    assert.match(slow.open('footer-method'),/Loading the catalog[\s\S]*href="\/coverage\/"/);
    await slow.respond({ok:true,json:async()=>({coverage,records:[]})});
    assert.equal(slow.dialog.open,true);assert.match(slow.content(),/coverage-table/);
    const failed=await boot('failed');
    assert.match(failed.open('coverage-button'),/Loading the catalog/);
    await failed.respond({ok:false,status:503});
    assert.equal(failed.dialog.open,true);assert.match(failed.content(),/could not be loaded[\s\S]*href="\/coverage\/"/);
    assert.match(failed.open('footer-method'),/could not be loaded/);
    assert.match(failed.open('sidebar-download'),/\.\/downloads\/catalog\.sqlite/);
  } finally {
    console.error=consoleError;
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('load failures and toasts are announced through live regions that exist before their text changes',async t=>{
  const html=readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
  assert.match(html,/<div id="toast" class="toast" role="status" aria-live="polite"><\/div>/);
  for(const id of ['detail','info'])assert.match(html,new RegExp(`<dialog id="${id}-dialog"[^>]*>.*<div class="toast" role="status" aria-live="polite"></div></dialog>`),id);
  assert.match(css,/(?:^|[}\n])\.toast:empty\{padding:0;box-shadow:none\}/);
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const records=[{id:'url:toast',name:'Toast fixture',kind:'tool',url:'https://example.org/',page_url:'/resources/toast/',aliases:[],environments:['web'],topics:[],authors:[],summary:'Fixture.',review_status:'curated',published_at:null,scope:'core',paper_version:null,paper_source_url:null,paper_date:null,related_count:0,incoming_relations:[]}];
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]),consoleError=console.error;
  const boot=async(name,ok)=>{
    const make=extra=>({dataset:{},listeners:{},textContent:'',classList:{toggle(){}},open:false,addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},setAttribute(){},showModal(){this.open=true;},close(){this.open=false;},...extra});
    const toasts=[make(),make(),make()],clicks=[],elements=new Map([['#toast',toasts[0]],['#detail-dialog',make({querySelector:()=>toasts[1]})],['#info-dialog',make({querySelector:()=>toasts[2]})]]);
    const element=selector=>{if(!elements.has(selector))elements.set(selector,make());return elements.get(selector);};
    const lists={dialog:[element('#detail-dialog'),element('#info-dialog')],'.toast':toasts};
    const globals={document:{documentElement:{},body:{classList:{toggle(){}}},addEventListener(type,fn){if(type==='click')clicks.push(fn);},querySelector:element,querySelectorAll:selector=>lists[selector]||[]},window:{addEventListener(){}},location:{search:'',pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>ok?{ok:true,json:async()=>({coverage,records:structuredClone(records)})}:{ok:false,status:503}};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?${name}`);await new Promise(resolve=>setImmediate(resolve));
    return {element,toasts,clicks};
  };
  try {
    console.error=()=>{};
    const failed=await boot('announce-failure',false);
    assert.equal(failed.element('#load-error').hidden,false);
    assert.equal(failed.element('#results-count').innerHTML,'<span class="sr-only">The catalog could not be loaded.</span>');
    t.mock.timers.enable({apis:['setTimeout']});
    const {element,toasts,clicks}=await boot('announce-toast',true),texts=()=>toasts.map(x=>x.textContent);
    const dialog=element('#detail-dialog');dialog.showModal();
    await Promise.all(dialog.listeners.click.map(listener=>listener({target:{closest:selector=>selector==='[data-copy-link]'?{}:null}})));
    assert.deepEqual(texts(),['','Copy the URL from your address bar.','']);
    dialog.close();
    t.mock.timers.tick(2600);
    assert.deepEqual(texts(),['','','']);
  } finally {
    console.error=consoleError;
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('homepage text stays at least 12px at every width',()=>{
  const pages=readFileSync(new URL('../web/pages.css',import.meta.url),'utf8');
  const rules=[...css.matchAll(/([^{}]*)\{([^{}]*)\}/g),...[...pages.matchAll(/([^{}]*)\{([^{}]*)\}/g)].filter(m=>/static-directory|directory-links|resource-page-link/.test(m[1]))];
  for(const [,selector,body] of rules)for(const [,value] of body.matchAll(/(?:^|;)font(?:-size)?:([^;]*)/g)){const px=value.match(/(\d+(?:\.\d+)?)px/);if(px)assert.ok(Number(px[1])>=12,`${selector.trim()} sets ${px[1]}px`);}
});
test('result cards drop to one column on phones instead of squeezing two',()=>{
  const blocks=[...css.matchAll(/@media\(max-width:(\d+)px\)\{/g)].map(m=>{let depth=1,i=m.index+m[0].length;const start=i;while(depth)depth+=({'{':1,'}':-1}[css[i++]]||0);return [Number(m[1]),css.slice(start,i-1)];});
  const single=blocks.filter(([,body])=>/(?:^|\})\.resource-grid\{grid-template-columns:1fr\}/.test(body)).map(([width])=>width);
  assert.ok(Math.max(...single)>=560,`single-column cards start at ${Math.max(...single)}px`);
});

test('header switches to the compact two-row layout before the full nav overflows', () => {
  const css = readFileSync(new URL('../web/styles.css', import.meta.url), 'utf8');
  const block = css.match(/@media\(max-width:900px\)\{(.*?)\}\}/s);
  assert.ok(block, 'expected a 900px header breakpoint');
  assert.match(block[1], /\.site-header nav\{order:1;flex-basis:100%;[^}]*overflow-x:auto/);
  assert.match(block[1], /\.header-inner\{[^}]*flex-wrap:wrap/);
});
test('Chinese mode localizes the title, accessible names, skip link, static directory and pagination',async()=>{
  const index=readFileSync(new URL('../web/index.html',import.meta.url),'utf8'),markup=index+readFileSync(new URL('../scripts/search_pages.py',import.meta.url),'utf8');
  for(const [tag] of index.matchAll(/<[^>]*\saria-label="[^>]*>/g))assert.match(tag,/data-i18n-label="/,tag);
  const language=index.match(/<button id="language"[^>]*>/)[0];assert.doesNotMatch(language,/aria-label/);assert.match(language,/lang="zh-CN"/);
  const english={};for(const [tag,label,key,text] of markup.matchAll(/<[^<>]*\sdata-i18n(-label)?="([^"]+)"[^<>]*>([^<]*)/g))english[key]??=label?tag.match(/aria-label="([^"]*)"/)[1]:text.replaceAll('&amp;','&');
  const keys=['data-i18n','data-i18n-label'].map(attr=>[...new Set([...markup.matchAll(new RegExp(`${attr}="([^"]+)"`,'g'))].map(m=>m[1]))]);
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const names=['document','window','location','history','localStorage','fetch'],saved=names.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const make=dataset=>({dataset,attributes:{},classList:{toggle(){}},addEventListener(){},setAttribute(name,value){this.attributes[name]=value;},showModal(){},close(){}});
  const boot=async search=>{
    const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,make({}));return elements.get(selector);};
    const lists={'[data-i18n]':keys[0].map(i18n=>make({i18n})),'[data-i18n-label]':keys[1].map(i18nLabel=>make({i18nLabel}))};
    const globals={document:{title:'',documentElement:{},body:{classList:{toggle(){}}},addEventListener(){},querySelector:element,querySelectorAll:selector=>lists[selector]||[]},window:{addEventListener(){}},location:{search,pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>({ok:true,json:async()=>({coverage,records:structuredClone(rows.slice(0,30))})})};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?i18n-${search}`);await new Promise(resolve=>setImmediate(resolve));
    return {title:globals.document.title,texts:lists['[data-i18n]'],labels:lists['[data-i18n-label]'],element};
  };
  try {
    const en=await boot(''),zh=await boot('?lang=zh'),han=/[　-鿿＀-￯]/;
    assert.equal(en.title,index.match(/<title>([^<]*)<\/title>/)[1]);assert.match(zh.title,han);
    for(const item of en.texts)assert.equal(item.textContent,english[item.dataset.i18n],item.dataset.i18n);
    for(const item of en.labels)assert.equal(item.attributes['aria-label'],english[item.dataset.i18nLabel],item.dataset.i18nLabel);
    for(const item of zh.texts)assert.match(item.textContent,han,item.dataset.i18n);
    for(const item of zh.labels)assert.match(item.attributes['aria-label'],han,item.dataset.i18nLabel);
    assert.ok(keys[0].includes('skipToCatalog')&&keys[0].includes('directoryHeading')&&keys[1].includes('mainNavigation'));
    assert.equal(zh.element('#language').textContent,'EN');assert.equal(zh.element('#language').lang,'en');
    assert.match(en.element('#pagination').innerHTML,/aria-label="Page 1" aria-current="page">1<\/button>/);
    assert.match(zh.element('#pagination').innerHTML,/aria-label="第 1 页" aria-current="page">1<\/button>/);
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});
test('topic labels come from data/topics.json through the index payload',async()=>{
  const vocabulary=JSON.parse(readFileSync(new URL('../data/topics.json',import.meta.url),'utf8'));
  assert.deepEqual([...new Set(rows.flatMap(r=>r.topics))].filter(key=>!Object.hasOwn(vocabulary,key)),[]);
  assert.deepEqual(Object.keys(TOPIC_ALIASES).filter(key=>!Object.hasOwn(vocabulary,key)),[]);
  assert.doesNotMatch(readFileSync(new URL('../web/app.js',import.meta.url),'utf8'),/'(?:grounding|ui-design|world-models)':\[/);
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const topics=Object.fromEntries(Object.entries(vocabulary).map(([key,entry])=>[key,[entry.en,entry.zh]]));
  const record={id:'url:design',name:'Design study',kind:'paper',url:'https://example.org/',page_url:'/resources/design/',aliases:[],environments:['web'],topics:['ui-design','grounding'],authors:[],scope:'core',review_status:'curated',summary:'Fixture summary.',published_at:null,paper_version:null,paper_source_url:null,paper_date:null,related_count:0,incoming_relations:[],paper_arxiv:null,declared_licenses:{}};
  const keys=['document','window','location','history','localStorage','fetch'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const render=async(search,name)=>{
    const elements=new Map(),element=selector=>{if(!elements.has(selector))elements.set(selector,{dataset:{},classList:{toggle(){}},addEventListener(){},setAttribute(){},showModal(){},close(){}});return elements.get(selector);};
    const globals={document:{documentElement:{},body:{classList:{toggle(){}}},addEventListener(){},querySelector:element,querySelectorAll:()=>[]},window:{addEventListener(){}},location:{search,pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>({ok:true,json:async()=>({coverage,topics,records:[structuredClone(record)]})})};
    for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
    await import(`../web/app.js?${name}`);await new Promise(resolve=>setImmediate(resolve));
    return {options:element('#topic').innerHTML,results:element('#results').innerHTML};
  };
  try {
    const en=await render('','topics-en'),zh=await render('?lang=zh','topics-zh');
    for(const [view,language] of [[en,0],[zh,1]]){
      assert.match(view.options,new RegExp(`<option value="ui-design">${topics['ui-design'][language]}</option>`));
      assert.match(view.options,new RegExp(`<option value="grounding">${topics.grounding[language]}</option>`));
      assert.ok(view.results.includes(topics['ui-design'][language]));
    }
    // app.js indexes the same labels it shows, in both languages, whichever language is active.
    for(const [index,q] of ['界面设计','GUI 定位','UI design','论文','Papers','浏览器'].entries())assert.ok((await render('?q='+encodeURIComponent(q),'search-'+index)).results.includes('Design study'),q);
    assert.equal((await render('?q=xyzq987654&lang=zh','search-none')).results.includes('Design study'),false);
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});


test('clone commands copy exactly once and announce scoped bilingual success or manual fallback',async()=>{
  const command='git clone https://github.com/reacher-z/Awesome-CUA.git';
  const html=readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
  assert.match(html,/<code[^>]*>git clone https:\/\/github.com\/reacher-z\/Awesome-CUA.git<\/code>/);
  assert.match(html,/id="clone-status-home"[^>]*data-clone-status[^>]*role="status"[^>]*aria-live="polite"[^>]*aria-atomic="true"/);
  assert.match(html,/<details class="agent-search"><summary data-i18n="localSearch">Try a local search<\/summary>/);
  const localSearch='python3 scripts/catalog.py search "grounding" --kind model --status curated --json';
  assert.ok(readFileSync(new URL('../AGENTS.md',import.meta.url),'utf8').includes(localSearch));
  assert.ok(html.includes(`cd Awesome-CUA\n${localSearch}`));
  for(const path of ['/agents/','/AGENTS.md','/downloads/rag-manifest.json'])assert.ok(html.includes(`href="${path}"`));
  const coverage=JSON.parse(readFileSync(new URL('../data/coverage.json',import.meta.url),'utf8'));
  const keys=['document','window','location','history','localStorage','fetch','navigator'],saved=keys.map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]);
  const settle=()=>new Promise(resolve=>setImmediate(resolve));
  try {
    for(const language of ['en','zh']){
      const clicks=[],elements=new Map(),make=()=>({dataset:{},listeners:{},textContent:'',classList:{toggle(){}},open:false,addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);},setAttribute(){},showModal(){this.open=true;},close(){this.open=false;}});
      const element=selector=>{if(!elements.has(selector))elements.set(selector,make());return elements.get(selector);};
      const writes=[];let resolveCopy;
      const globals={document:{documentElement:{},body:{classList:{toggle(){}}},addEventListener(type,fn){if(type==='click')clicks.push(fn);},querySelector:element,querySelectorAll:()=>[]},window:{addEventListener(){}},location:{search:`?lang=${language}`,pathname:'/',hash:''},history:{replaceState(){}},localStorage:{getItem:()=>null,setItem(){}},fetch:async()=>({ok:true,json:async()=>({coverage,records:[]})}),navigator:{clipboard:{writeText:value=>{writes.push(value);return new Promise(resolve=>resolveCopy=resolve);}}}};
      for(const [key,value] of Object.entries(globals))Object.defineProperty(globalThis,key,{value,configurable:true,writable:true});
      await import(`../web/app.js?clone-scoped-${language}`);await settle();
      const home=make(),modal=make(),button=(status,dialog=null)=>({isConnected:true,_disabled:false,focusCalls:0,get disabled(){return this._disabled;},set disabled(value){this._disabled=value;if(value&&document.activeElement===this)document.activeElement=document.body;},focus(){this.focusCalls++;document.activeElement=this;},closest:selector=>selector==='[data-clone-entry]'?{querySelector:()=>status}:selector==='dialog'?dialog:null});
      const homeButton=button(home),modalButton=button(modal,element('#info-dialog'));
      const click=button=>Promise.all(clicks.map(listener=>listener({target:{closest:selector=>selector==='[data-copy-clone]'?button:null}})));
      document.activeElement=homeButton;
      const pending=click(homeButton);
      assert.equal(homeButton.disabled,true);assert.equal(modal.textContent,'');
      assert.equal(document.activeElement,document.body);
      await click(homeButton);assert.deepEqual(writes,[command]);
      resolveCopy();await pending;
      assert.equal(homeButton.disabled,false);assert.equal(home.textContent,language==='zh'?'命令已复制，可粘贴到终端。':'Command copied. Paste it into your terminal.');
      assert.equal(document.activeElement,homeButton);assert.equal(homeButton.focusCalls,1);
      assert.equal(home.dataset.i18n,'commandCopied');assert.equal(element('#toast').textContent,'');
      element('#hero-download').listeners.click[0]();
      const content=element('#info-content').innerHTML;
      assert.match(content,/id="clone-status-download"[^>]*data-clone-status[^>]*role="status"[^>]*aria-live="polite"/);
      for(const path of [language==='zh'?'/zh/agents/':'/agents/','/AGENTS.md','/downloads/rag-manifest.json'])assert.ok(content.includes(`href="${path}"`));
      assert.ok(content.includes(language==='zh'?'导出数量与快照指纹。':'Export counts and snapshot fingerprints.'));
      assert.ok(content.includes(`<details class="agent-search"><summary>${language==='zh'?'试一次本地检索':'Try a local search'}</summary>`));
      assert.ok(content.includes(`cd Awesome-CUA\n${escapeHTML(localSearch)}`));
      assert.ok(content.includes(language==='zh'?'需要 Python 3.11+，无需安装软件包或注册账号。':'Python 3.11+; no package installation or account needed.'));
      navigator.clipboard.writeText=async value=>{writes.push(value);throw new Error('Permission denied');};
      document.activeElement=modalButton;
      await click(modalButton);
      assert.equal(modalButton.disabled,false);assert.equal(modal.textContent,language==='zh'?'复制失败，请选中命令后手动复制。':'Copy failed. Select and copy the command manually.');
      assert.equal(document.activeElement,modalButton);assert.equal(modalButton.focusCalls,1);
      assert.equal(modal.dataset.i18n,'commandCopyFailed');assert.equal(home.dataset.i18n,'commandCopied');
      assert.equal(element('#toast').textContent,'');assert.deepEqual(writes,[command,command]);
      navigator.clipboard=undefined;
      await click(homeButton);assert.equal(homeButton.disabled,false);assert.equal(home.dataset.i18n,'commandCopyFailed');
      navigator.clipboard={writeText:()=>new Promise(resolve=>resolveCopy=resolve)};
      document.activeElement=homeButton;const moved=click(homeButton),nextControl=make();
      document.activeElement=nextControl;resolveCopy();await moved;
      assert.equal(document.activeElement,nextControl);assert.equal(homeButton.focusCalls,1);
      document.activeElement=homeButton;const detached=click(homeButton);homeButton.isConnected=false;resolveCopy();await detached;
      assert.equal(document.activeElement,document.body);assert.equal(homeButton.focusCalls,1);
      document.activeElement=modalButton;const closed=click(modalButton);element('#info-dialog').close();resolveCopy();await closed;
      assert.equal(document.activeElement,document.body);assert.equal(modalButton.focusCalls,1);
    }
  } finally {
    for(const [key,descriptor] of saved)if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];
  }
});

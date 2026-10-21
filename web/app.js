import { KIND_ORDER, KINDS, PLATFORMS, PAGE_SIZE, FACT_LABELS, createRecordLoader, bibliographicDate, compactFacts, initials, matches, filtered, pageWindow, parseState, serializeState, recordSearchText, escapeHTML as e, safeURL, formatDate, formatFact } from './catalog-core.js';

const TEXT = {
  en: {
    navPapers:'Papers',navGuides:'Guides',navExplore:'Explore',navCoverage:'Coverage',navAbout:'About',eyebrow:'COMPUTER-USE AGENT RESOURCES',heroLine1:'Computer-use agents.',heroLine2:'Papers, data, and tools.',heroDescription:'Find research, models, benchmarks, and software for web, desktop, and mobile agents. Filter by task or platform, then inspect the primary sources.',exploreButton:'Search the catalog',getData:'Data & RAG',heroCaption:'Reviewed and metadata-only records are labeled.',mapLabel:'BROWSE BY ENVIRONMENT',webLabel:'Web',webCaption:'Browser navigation & interaction',desktopLabel:'Desktop',desktopCaption:'Windows, macOS & Linux',mobileLabel:'Mobile',mobileCaption:'Android, iOS & HarmonyOS',mapFoot:'OBSERVE',reason:'REASON',act:'ACT',resources:'Resources indexed',curatedResources:'Source-reviewed',categories:'Resource categories',discoverySources:'Source documents',snapshot:'DATA SNAPSHOT',viewCoverage:'View coverage',catalogEyebrow:'THE CATALOG',catalogTitle:'Explore the collection',suggest:'Suggest a resource',browseByType:'BROWSE BY TYPE',useDataTitle:'Choose an export',useDataCopy:'Full catalog or reviewed-only RAG, with sources and review states.',downloadData:'View export formats',searchLabel:'Search the catalog',searchPlaceholder:'Search tasks or names: grounding, AndroidWorld…',platform:'Platform',allPlatforms:'All platforms',review:'Review',allStates:'All states',curated:'Reviewed',metadata:'Metadata only',topic:'Topic',allTopics:'All topics',clearFilters:'Reset filters',try:'Tasks',grounding:'UI grounding',rl:'RL training',safety:'Agent safety',loading:'Loading the catalog…',sortBy:'Sort results',curatedFirst:'Reviewed first',nameSort:'Name A–Z',newest:'Newest publication',errorTitle:'The catalog could not be loaded.',errorCopy:'Check your connection and try again.',retry:'Try again',emptyTitle:'No resources match these filters.',emptyCopy:'Try a broader term or clear a filter. Many papers have not yet been assigned platform or topic tags.',catalogFootnote:'Reviewed: relevance and annotations checked against a primary source. Metadata only: bibliography verified; relevance pending. Neither status means experiments were reproduced.',coverageEyebrow:'REVIEW & COVERAGE',coverageTitle:'Review status and known gaps',coverageCopy:'See which records have source review, which have metadata only, and which identifiers remain unresolved.',coverageButton:'Inspect the coverage ledger',principle1Title:'Follow the evidence',principle1Copy:'Every record points to a first-party source, with a retrieval date and content fingerprint.',principle2Title:'Keep the distinctions',principle2Copy:'Papers are not projects. Code licenses are not data licenses. A model checkpoint is not a model family.',principle3Title:'Make the gaps visible',principle3Copy:'Comprehensive coverage is our goal. The unreviewed queue and source boundaries stay visible along the way.',aboutEyebrow:'AN OPEN FIELD DESERVES AN OPEN MAP',aboutTitle:'Help map what comes next.',aboutCopy:'Found a paper, dataset, tool, or a detail we missed? Add your knowledge to the computer-use community.',contribute:'Contribute a resource',footerCopy:'A source-backed map of the computer-use ecosystem.',methodology:'Methodology',allResources:'All resources',showing:'resources',previous:'← Previous',next:'Next →',openSource:'Visit primary source',copyLink:'Copy link',copied:'Link copied',copyFailed:'Copy the URL from your address bar.',verified:'Evidence checked',published:'Published',unassigned:'Unassigned platform',topics:'Topics',authors:'Authors',licenses:'License declarations',code:'Code',data:'Data',weights:'Weights',document:'Document',unknown:'Not recorded',evidence:'Source evidence',notes:'Notes & scope',details:'Resource facts',relations:'Related resources',viewRecord:'View record',sourceLanguage:'Original source metadata',scopeCore:'Core resource',scopeAdjacent:'Adjacent resource',scopePending:'Relevance not reviewed',fullCatalog:'Full catalog · JSONL',fullCatalogCopy:'All records, evidence, licenses, and relationships.',sqlite:'SQL database · SQLite',sqliteCopy:'Resources, facets, reviewed relations, and full-text search.',coverageFile:'Coverage ledger · JSON',coverageFileCopy:'Source populations, review states, and known gaps.',sourcesFile:'Discovery sources · JSON',sourcesFileCopy:'Attribution and URLs for the discovery documents.',downloadTitle:'Download catalog data',downloadCopy:'These downloads contain catalog metadata, not model weights, papers, or training datasets. Follow the primary links for the original assets.',licenseNote:'Original catalog code and annotations use the MIT license. Linked assets keep their own terms.',coverageDialogTitle:'What is in the index?',coverageDialogCopy:'Counts describe resources, not independent projects. A paper, a repository, and a model checkpoint can be separate related records. Source populations overlap.',unindexed:'Unresolved identifiers',excluded:'Scope exclusions',exclusionCopy:'Reviewed exclusions are outside the active index. Original bibliographic snapshots remain in the archive.',exclusionFile:'Scope decisions and evidence',archiveFile:'Raw arXiv metadata archive',source:'Discovery document',indexed:'Indexed',discovered:'Found',limitations:'Known boundaries',boundaries:'Most bibliography entries still need relevance review. Closed assets and work missing from the discovery sources are not exhaustively represented. Global completeness has not been established.',reviewExplanation:'Curated entries receive AI-assisted editorial review against a primary source. Metadata-only entries have verified bibliographic facts, not verified methods or findings.',sourceEmpty:'No source evidence recorded.',noTaxonomy:'Platform and topic tagging is still pending for this bibliography entry.',licenseCaution:'Public access does not imply a permissive license. Code, data, weights, and document declarations are recorded separately.',referenceDate:'Retrieved',recordID:'Record ID',curatedBadge:'Source reviewed',metadataBadge:'Metadata checked',errorDetail:'This record could not be loaded. Please try again.',noRecord:'This resource is not in the current snapshot.'
  },
  zh: {
    navPapers:'论文',navGuides:'指南',navExplore:'资源目录',navCoverage:'覆盖范围',navAbout:'关于',eyebrow:'COMPUTER-USE AGENT 资源目录',heroLine1:'计算机操作智能体',heroLine2:'论文、数据与工具。',heroDescription:'查找面向浏览器、桌面和移动智能体的研究、模型、基准与软件。按任务或平台筛选，再查看一手来源。',exploreButton:'检索资源目录',getData:'数据与 RAG',heroCaption:'已审阅与仅元数据条目均有明确标注。',mapLabel:'按交互环境浏览',webLabel:'浏览器',webCaption:'浏览器导航与交互',desktopLabel:'桌面',desktopCaption:'Windows、macOS 与 Linux',mobileLabel:'移动设备',mobileCaption:'Android、iOS 与鸿蒙',mapFoot:'观察',reason:'推理',act:'行动',resources:'已收录资源',curatedResources:'已审阅来源',categories:'资源分类',discoverySources:'来源文档',snapshot:'数据快照',viewCoverage:'查看覆盖范围',catalogEyebrow:'资源目录',catalogTitle:'浏览完整资源集合',suggest:'推荐资源',browseByType:'按类型浏览',useDataTitle:'选择导出内容',useDataCopy:'完整目录或仅含已审阅条目的 RAG，均保留来源与审阅状态。',downloadData:'查看导出格式',searchLabel:'搜索资源目录',searchPlaceholder:'按任务或名称检索：GUI 定位、AndroidWorld…',platform:'平台',allPlatforms:'全部平台',review:'审阅',allStates:'全部状态',curated:'已审阅',metadata:'仅元数据',topic:'主题',allTopics:'全部主题',clearFilters:'重置筛选',try:'任务',grounding:'界面定位',rl:'强化学习训练',safety:'智能体安全',loading:'正在加载资源目录…',sortBy:'结果排序',curatedFirst:'已审阅优先',nameSort:'名称 A–Z',newest:'论文发表时间',errorTitle:'暂时无法加载目录。',errorCopy:'请检查网络连接后重试。',retry:'重新加载',emptyTitle:'没有符合条件的资源。',emptyCopy:'试试更宽泛的关键词，或清除部分筛选。很多论文的主题和平台尚未完成标注。',catalogFootnote:'已审阅：相关性与注释经过一手来源核对。仅元数据：书目信息已核实，相关性待审阅。两种状态均不表示实验已经复现。',coverageEyebrow:'审阅与覆盖范围',coverageTitle:'审阅状态与已知缺口',coverageCopy:'查看哪些条目经过来源审阅、哪些仅有元数据，以及哪些标识符尚待核实。',coverageButton:'查看覆盖台账',principle1Title:'追溯一手证据',principle1Copy:'每条记录都指向一手来源，并保留获取日期与内容指纹。',principle2Title:'保留必要的区分',principle2Copy:'论文不等于项目，代码许可不等于数据许可，模型权重版本也不等于模型家族。',principle3Title:'让缺口清晰可见',principle3Copy:'全面覆盖是建设目标。待审队列与来源边界始终公开记录。',aboutEyebrow:'开放的领域，需要开放的知识地图',aboutTitle:'一起补全下一块拼图。',aboutCopy:'发现了遗漏的论文、数据集、工具或信息错误？把你的知识带给 Computer-Use 社区。',contribute:'贡献一条资源',footerCopy:'有来源可查的 Computer-Use 生态地图。',methodology:'收录方法',allResources:'全部资源',showing:'条资源',previous:'← 上一页',next:'下一页 →',openSource:'访问一手来源',copyLink:'复制链接',copied:'链接已复制',copyFailed:'请复制浏览器地址栏中的链接。',verified:'证据核验日期',published:'发表日期',unassigned:'平台待标注',topics:'研究主题',authors:'作者',licenses:'许可声明',code:'代码',data:'数据',weights:'模型权重',document:'文档',unknown:'尚未记录',evidence:'来源证据',notes:'说明与范围',details:'资源规格',relations:'关联资源',viewRecord:'查看记录',sourceLanguage:'保留原始资料语言',scopeCore:'核心资源',scopeAdjacent:'相关基础资源',scopePending:'相关性待审阅',fullCatalog:'完整目录 · JSONL',fullCatalogCopy:'全部资源、来源证据、许可与关联关系。',sqlite:'可查询数据库 · SQLite',sqliteCopy:'资源、标签、已审阅关系与全文搜索。',coverageFile:'覆盖台账 · JSON',coverageFileCopy:'来源范围、审阅状态与已知缺口。',sourcesFile:'发现来源 · JSON',sourcesFileCopy:'发现资料的归属信息与原始链接。',downloadTitle:'下载目录数据',downloadCopy:'下载内容是资源元数据，不包含模型权重、论文全文或训练数据集。请通过一手来源获取原始资产。',licenseNote:'原创代码与目录注释使用 MIT 许可。所链接的资产保留各自的许可条款。',coverageDialogTitle:'目录里有哪些内容？',coverageDialogCopy:'数量以资源为单位，不代表独立项目数。一篇论文、一个仓库和一个模型权重版本可以分别收录。不同发现来源的条目互有重叠。',unindexed:'待核实标识',excluded:'范围排除',exclusionCopy:'经过范围审阅的排除项不计入当前目录，原始书目快照保留在档案中。',exclusionFile:'排除决定与来源',archiveFile:'原始 arXiv 元数据档案',source:'发现来源文档',indexed:'已收录',discovered:'发现数',limitations:'已知边界',boundaries:'多数论文尚待相关性审阅。闭源资产、未发表成果，以及发现来源之外的资料仍未全面覆盖。目前不能证明已达到全球最全。',reviewExplanation:'已审阅条目经过 AI 辅助的一手来源编辑审阅。论文元数据核实的是书目信息，不表示实验方法或结论经过验证。',sourceEmpty:'尚未记录来源证据。',noTaxonomy:'这篇论文的平台和主题仍待标注。',licenseCaution:'可公开访问不代表可自由使用。代码、数据、权重和文档的许可分别记录。',referenceDate:'获取日期',recordID:'资源 ID',curatedBadge:'已审阅来源',metadataBadge:'元数据已核验',errorDetail:'暂时无法加载此条目，请重试。',noRecord:'当前数据快照中没有此条目。'
  }
};
// Topic labels come from data/topics.json through data/index.json.
let TOPICS = {};
Object.assign(TEXT.en, {resourceBadges:'Resource badges',relatedResearch:'Related research',jevScope:'System One & typed decisions',agentEyebrow:'USE THE DATA',agentTitle:'Clone the complete catalog',agentCopy:'Clone for local search and RAG exports. Records retain source evidence, review states, and scoped licenses.',agentGuide:'Agent & RAG guide',agentGuideCopy:'Search records and export retrieval documents.',agentInstructions:'Agent instructions',agentInstructionsCopy:'AGENTS.md · Search, export, and cite.',localSearch:'Try a local search',localSearchRequirements:'Python 3.11+; no package installation or account needed.',agentManifest:'RAG manifest',agentManifestCopy:'Export counts and snapshot fingerprints.',agentDownloads:'Browse download formats',cloneCommandLabel:'Git clone command',copyCommand:'Copy command',commandCopying:'Copying…',commandCopied:'Command copied. Paste it into your terminal.',commandCopyFailed:'Copy failed. Select and copy the command manually.',ragReviewed:'RAG documents · reviewed',ragReviewedCopy:'One retrieval document per reviewed resource, with citations and provenance.',ragAll:'RAG documents · all records',ragAllCopy:'Every active record, including metadata-only entries with their review state.'});
Object.assign(TEXT.zh, {resourceBadges:'资源徽章',relatedResearch:'相关研究',jevScope:'System One 与类型化决策',agentEyebrow:'使用数据',agentTitle:'克隆完整资源目录',agentCopy:'克隆后可在本地检索或导出 RAG 文档；记录保留来源证据、审阅状态与分项许可。',agentGuide:'Agent 与 RAG 指南',agentGuideCopy:'检索记录并导出检索文档。',agentInstructions:'Agent 使用说明',agentInstructionsCopy:'AGENTS.md · 检索、导出与引用。',localSearch:'试一次本地检索',localSearchRequirements:'需要 Python 3.11+，无需安装软件包或注册账号。',agentManifest:'RAG 导出清单',agentManifestCopy:'导出数量与快照指纹。',agentDownloads:'查看下载格式',cloneCommandLabel:'Git 克隆命令',copyCommand:'复制命令',commandCopying:'正在复制…',commandCopied:'命令已复制，可粘贴到终端。',commandCopyFailed:'复制失败，请选中命令后手动复制。',ragReviewed:'RAG 文档 · 已审阅',ragReviewedCopy:'每项已审阅资源对应一份检索文档，保留引用和来源。',ragAll:'RAG 文档 · 全部记录',ragAllCopy:'包含全部当前记录，并保留仅有元数据条目的审阅状态。'});
Object.assign(TEXT.en,{topicDirectory:'Browse topics'});
Object.assign(TEXT.zh,{topicDirectory:'浏览主题'});
Object.assign(TEXT.en,{pageNumber:'Page %s',pageStatus:'Page %s of %s'});
Object.assign(TEXT.zh,{pageNumber:'第 %s 页',pageStatus:'第 %s 页，共 %s 页'});
const CLONE_COMMAND = 'git clone https://github.com/reacher-z/Awesome-CUA.git';
const LOCAL_SEARCH_COMMAND = 'cd Awesome-CUA\npython3 scripts/catalog.py search "grounding" --kind model --status curated --json';
Object.assign(TEXT.en,{publicationBib:'Publication editions · BibTeX',publicationBibCopy:'Reviewed publication editions with their own title, authors, venue and date.',publicationCSL:'Publication editions · CSL JSON',publicationCSLCopy:'Source-backed publication metadata with its original date precision.'});
Object.assign(TEXT.zh,{publicationBib:'出版版引用 · BibTeX',publicationBibCopy:'已审阅出版版，保留该版本的题名、作者、会议／期刊和日期。',publicationCSL:'出版版引用 · CSL JSON',publicationCSLCopy:'有来源可查的出版元数据，保留原日期精度。'});
Object.assign(TEXT.en,{citePaper:'Cite this paper',copyBibtex:'Copy BibTeX',citationCopied:'BibTeX copied',citationFailed:'Could not copy the citation. Use the download link.',citationNote:'Exports preserve the cited edition, its authors and recorded date precision.',paperBibtex:'Paper citations · BibTeX',paperBibtexCopy:'Reviewed papers and surveys, with recorded versions and original authors.',paperCSL:'Paper citations · CSL JSON',paperCSLCopy:'Structured citations for reference managers and research tools.'});
Object.assign(TEXT.zh,{citePaper:'引用这篇论文',copyBibtex:'复制 BibTeX',citationCopied:'BibTeX 已复制',citationFailed:'暂时无法复制引用，请使用下载链接。',citationNote:'引用保留所选版本的作者、日期精度和来源。',paperBibtex:'论文引用 · BibTeX',paperBibtexCopy:'已审阅论文与综述，保留记录的版本及原作者。',paperCSL:'论文引用 · CSL JSON',paperCSLCopy:'可供文献管理工具和研究工作流使用的结构化引用。'});
Object.assign(TEXT.en,{paperLibrary:'Research library',navData:'Data / RAG',dataHub:'Data hub',downloadInventory:'All formats, counts and file fingerprints',year:'Year',allYears:'All years',related:'related',primaryLink:'Primary source',recordLink:'Details',reviewedCount:'reviewed',pendingCount:'metadata only',directoryTitle:'Resource directory'});
Object.assign(TEXT.zh,{paperLibrary:'论文库',navData:'数据 / RAG',dataHub:'数据中心',downloadInventory:'全部格式、条数与文件指纹',year:'年份',allYears:'全部年份',related:'项关联',primaryLink:'一手来源',recordLink:'详情',reviewedCount:'已审阅',pendingCount:'仅元数据',directoryTitle:'资源目录'});
Object.assign(TEXT.en,{pageTitle:'AwesomeCUA — Computer-use research, data, and tools',skipToCatalog:'Skip to catalog',homeLabel:'AwesomeCUA home',brandLabel:'THE INDEX',mainNavigation:'Main navigation',mapLabelAria:'Explore web, desktop, and mobile agents',statsLabel:'Catalog statistics',layoutLabel:'Result layout',gridView:'Grid view',listView:'List view',resultsLabel:'Catalog results',paginationLabel:'Results pagination',closeDetails:'Close details',closeDialog:'Close dialog',dataEyebrow:'AWESOMECUA / DATA'});
Object.assign(TEXT.zh,{pageTitle:'AwesomeCUA — 计算机操作智能体的研究、数据与工具',skipToCatalog:'跳到资源目录',homeLabel:'AwesomeCUA 首页',brandLabel:'资源索引',mainNavigation:'主导航',mapLabelAria:'探索浏览器、桌面和移动设备上的智能体',statsLabel:'目录统计',layoutLabel:'结果布局',gridView:'网格视图',listView:'列表视图',resultsLabel:'目录结果',paginationLabel:'结果分页',closeDetails:'关闭详情',closeDialog:'关闭对话框',dataEyebrow:'AWESOMECUA / 数据'});
Object.assign(TEXT.en,{readSurvey:'Read the survey'});
Object.assign(TEXT.zh,{readSurvey:'阅读英文综述'});
Object.assign(TEXT.en,{loadingSlow:'The catalog is still loading…',loadingAlternatives:'You can browse the library or download the data while it loads.',staticCatalog:'Browse all resource pages'});
Object.assign(TEXT.zh,{loadingSlow:'资源目录仍在加载…',loadingAlternatives:'等待时可以先浏览论文库、资源页面或下载数据。',staticCatalog:'浏览全部资源页面'});
Object.assign(TEXT.en,{directoryEyebrow:'READ, EXPLORE, AND CITE',directoryHeading:'Computer-use agent research and resources',directoryCopy:'Browse source-backed pages directly, with or without JavaScript. Reviewed entries include concise annotations, provenance, and separate license declarations.',directoryPapers:'Research papers',directoryTopics:'Browse by topic',directoryConnections:'Papers → code & data',directoryUpdates:'Three daily updates',directoryModels:'Models',directoryDatasets:'Datasets',directoryBenchmarks:'Benchmarks',directoryLearning:'Learning resources',compareBenchmarks:'Compare benchmarks',compareDatasets:'Compare datasets',directoryFrameworks:'Frameworks',directoryProducts:'Products',directoryData:'Download data',editorialPolicy:'Editorial policy',startHeading:'Where should I start?',startConcepts:'Understand computer-use agents',startBenchmarks:'choose a benchmark for the capability you need',startData:'find training data with the right supervision and license',listComma:', ',listOr:', or ',sentenceEnd:'.'});
Object.assign(TEXT.zh,{directoryEyebrow:'阅读、探索与引用',directoryHeading:'Computer-Use Agent 研究与资源',directoryCopy:'无论是否启用 JavaScript，都可以直接浏览有来源可查的页面。已审阅条目附有简明注释、来源记录和分项许可声明。',directoryPapers:'研究论文',directoryTopics:'按主题浏览',directoryConnections:'论文 → 代码与数据',directoryUpdates:'每日三次更新',directoryModels:'模型',directoryDatasets:'数据集',directoryBenchmarks:'评测基准',directoryLearning:'学习资源',compareBenchmarks:'对比评测基准',compareDatasets:'对比数据集',directoryFrameworks:'框架',directoryProducts:'产品',directoryData:'下载数据',editorialPolicy:'编辑方针',startHeading:'从哪里开始？',startConcepts:'了解 Computer-Use Agent',startBenchmarks:'为所需能力选择评测基准',startData:'寻找监督方式和许可都合适的训练数据',listComma:'、',listOr:'，或',sentenceEnd:'。'});
Object.assign(TEXT.en,{pageDescription:"Find research, models, benchmarks, and software for web, desktop, and mobile agents. Filter by task or platform, then inspect the primary sources.",pageImageAlt:'AwesomeCUA — Computer-use agents. Papers, data, and tools.',pageLocale:'en_US'});
Object.assign(TEXT.zh,{pageDescription:"查找面向浏览器、桌面和移动智能体的研究、模型、基准与软件。按任务或平台筛选，再查看一手来源。",pageImageAlt:'AwesomeCUA — 计算机操作智能体。论文、数据与工具。',pageLocale:'zh_CN'});
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
let lang = new URLSearchParams(location.search).get('lang') === 'zh' ? 'zh' : 'en';
if (!new URLSearchParams(location.search).has('lang')) {try {if (localStorage.getItem('cua-language') === 'zh') lang='zh';} catch {}}
const t = key => TEXT[lang][key] || TEXT.en[key] || key;
const label = (dict,key) => dict[key]?.[lang === 'zh' ? 1 : 0] || key;
const num = n => Number(n).toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US');
let state = parseState(location.search), records = [], report, activeRecord='', loading=true, toastTimer, pendingInfo='';
const getDetails=createRecordLoader(url=>fetch(url));
const dates = value => value ? formatDate(value,lang) : t('unknown');
function updateURL(push=false) {const query=serializeState(state,lang,activeRecord),url=location.pathname+(query?'?'+query:'')+location.hash;if(push)history.pushState({record:true},'',url);else history.replaceState(history.state,'',url);}
// Live regions must exist before their text changes, and an open modal dialog makes the rest of the page inert, so write to the open dialog's own region.
function toast(message) {clearTimeout(toastTimer);const box=$$('dialog').find(dialog=>dialog.open)?.querySelector('.toast')||$('#toast');$$('.toast').forEach(other=>other.textContent='');box.textContent=message;toastTimer=setTimeout(()=>box.textContent='',2600);}
function translate() {
  document.documentElement.lang=lang==='zh'?'zh-CN':'en';
  document.title=t('pageTitle');
  $$('[data-i18n-content]').forEach(el=>el.setAttribute('content',t(el.dataset.i18nContent)));
  $$('[data-i18n]').forEach(el=>el.textContent=t(el.dataset.i18n));
  $$('[data-i18n-label]').forEach(el=>el.setAttribute('aria-label',t(el.dataset.i18nLabel)));
  $$('[data-placeholder]').forEach(el=>el.placeholder=t(el.dataset.placeholder));
  $('#language').textContent=lang==='zh'?'EN':'中文';$('#language').lang=lang==='zh'?'en':'zh-CN';
  $$('[data-agent-guide]').forEach(link=>link.href=lang==='zh'?'/zh/agents/':'/agents/');
  $$('[data-data-hub]').forEach(link=>link.href=lang==='zh'?'/zh/data/':'/data/');
  $$('[data-paper-library]').forEach(link=>link.href=lang==='zh'?'/zh/papers/':'/papers/');
  $$('[data-topic-directory]').forEach(link=>link.href=lang==='zh'?'/zh/topics/':'/topics/');
  if(report) $('#snapshot-date').textContent=dates(report.as_of_utc);
  fillSelects();
}
function fillSelects() {
  $('#platform').innerHTML=`<option value="">${e(t('allPlatforms'))}</option>`+Object.keys(PLATFORMS).map(key=>`<option value="${e(key)}">${e(label(PLATFORMS,key))}</option>`).join('');
  const topics=[...new Set(records.flatMap(r=>r.topics))].sort((a,b)=>label(TOPICS,a).localeCompare(label(TOPICS,b)));
  $('#topic').innerHTML=`<option value="">${e(t('allTopics'))}</option>`+topics.map(key=>`<option value="${e(key)}">${e(label(TOPICS,key))}</option>`).join('');
  const years=[...new Set(records.map(r=>bibliographicDate(r).slice(0,4)).filter(Boolean))].sort().reverse();
  if(state.year&&!years.includes(state.year)){years.push(state.year);years.sort().reverse();}
  $('#year').innerHTML=`<option value="">${e(t('allYears'))}</option>`+years.map(year=>`<option value="${year}">${year}</option>`).join('');
  syncControls();
}
function syncControls() {$('#search').value=state.q;$('#platform').value=state.platform;$('#review').value=state.review;$('#topic').value=state.topic;$('#year').value=state.year;$('#sort').value=state.sort;}
function change(patch,scroll=false) {
  Object.assign(state,{page:1},patch);syncControls();render();updateURL();
  if(scroll) $('#catalog').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
function renderCategories() {
  const focused=document.activeElement?.closest?.('.category-button')?.dataset.kind;
  const eligible=records.filter(r=>matches(r,state,true));
  const counts=Object.fromEntries(KIND_ORDER.map(k=>[k,0]));eligible.forEach(r=>counts[r.kind]++);
  const item=(kind,name,icon,count)=>`<button type="button" class="category-button" data-kind="${kind}" aria-pressed="${state.kind===kind}"><span class="category-icon" aria-hidden="true">${icon}</span><span>${e(name)}</span><span class="category-count">${num(count)}</span></button>`;
  $('#categories').innerHTML=item('',t('allResources'),'⊞',eligible.length)+KIND_ORDER.map(k=>item(k,label(KINDS,k),KINDS[k][2],counts[k])).join('');
  // Rebuilding the list destroys the focused button; refocus its replacement so keyboard users keep their place.
  if(focused!==undefined)$(`#categories [data-kind="${focused}"]`).focus();
}
function card(r) {
  const monogram=initials(r.name) || KINDS[r.kind]?.[2] || '';
  const curated=r.review_status==='curated';
  const summary=r.summary || (r.authors.slice(0,3).join(' · ')+(r.authors.length>3?' et al.':''));
  const tags=r.environments.filter(x=>x!=='unspecified').slice(0,2).map(x=>label(PLATFORMS,x)), facts=compactFacts(r,t);
  if(curated && r.topics.length && tags.length<3) tags.push(label(TOPICS,r.topics[0]));
  return `<article class="resource-card" data-kind="${e(r.kind)}"><div class="card-top"><div class="resource-monogram" aria-hidden="true">${e(monogram)}</div><span class="kind-chip">${e(label(KINDS,r.kind))}</span></div><h3 class="card-title"><a href="${e(r.page_url)}" data-record="${e(r.id)}">${e(r.name)}</a></h3>${facts.length?`<p class="card-facts">${facts.map(factMarkup).join('\u00a0· ')}</p>`:''}<p class="resource-summary ${curated?'':'is-bibliography'}">${e(summary)}</p><div class="card-tags">${tags.map(x=>`<span>${e(x)}</span>`).join('')}</div><div class="card-bottom ${curated?'is-curated':''}"><span class="review-dot"></span><span>${e(t(curated?'curatedBadge':'metadataBadge'))}</span><a class="card-external" href="${e(safeURL(r.url))}" target="_blank" rel="noopener noreferrer" aria-label="${e(t('openSource'))}: ${e(r.name)}">↗</a></div></article>`;
}
const factMarkup=fact=>fact.url?`<a href="${e(safeURL(fact.url))}" target="_blank" rel="noopener noreferrer">${e(fact.text)}</a>`:`<span title="${e(fact.text)}">${e(fact.text)}</span>`;
function render() {
  if(loading) return;
  const focused=Boolean(state.kind||state.q||state.platform||state.review||state.topic||state.year);
  document.body.classList.toggle('catalog-focused',focused);
  $('.hero [data-i18n="heroLine1"]').textContent=focused?(state.kind?label(KINDS,state.kind):t('directoryTitle')):t('heroLine1');
  renderCategories();
  const result=filtered(records,state), pages=Math.max(1,Math.ceil(result.length/PAGE_SIZE));
  state.page=Math.min(state.page,pages);
  const begin=(state.page-1)*PAGE_SIZE;
  $('#results').innerHTML=result.slice(begin,begin+PAGE_SIZE).map(state.view==='list'?denseRow:card).join('');
  $('#results').classList.toggle('list-view',state.view==='list');
  $('#view-grid').setAttribute('aria-pressed',String(state.view==='grid'));$('#view-list').setAttribute('aria-pressed',String(state.view==='list'));
  const reviewed=result.filter(r=>r.review_status==='curated').length;
  $('#results-count').innerHTML=`<strong>${num(result.length)}</strong> ${e(t('showing'))} <span class="result-breakdown">· ${num(reviewed)} ${e(t('reviewedCount'))}${result.length>reviewed?` · ${num(result.length-reviewed)} ${e(t('pendingCount'))}`:''}</span>${pages>1?`<span class="sr-only"> · ${e(t('pageStatus').replace('%s',state.page).replace('%s',pages))}</span>`:''}`;
  $('#results').setAttribute('aria-busy','false');$('#empty').hidden=result.length!==0;
  $('#clear-filters').hidden=![state.q,state.kind,state.platform,state.review,state.topic,state.year].some(Boolean);
  $('#pagination').hidden=result.length===0;
  $('#pagination').innerHTML=`<button type="button" data-page="${state.page-1}" ${state.page===1?'disabled':''}>${e(t('previous'))}</button><span class="page-numbers">${pageWindow(state.page,pages).map(n=>n===null?'<span class="page-gap" aria-hidden="true">…</span>':`<button type="button" data-page="${n}" aria-label="${e(t('pageNumber').replace('%s',n))}"${n===state.page?' aria-current="page"':''}>${n}</button>`).join('')}</span><button type="button" data-page="${state.page+1}" ${state.page===pages?'disabled':''}>${e(t('next'))}</button>`;
}
function denseRow(r) {
  const reviewed=r.review_status==='curated',isPaper=['paper','survey'].includes(r.kind);
  const date=bibliographicDate(r);
  const dateMarkup=!date?'':date.length===10?`<time datetime="${e(date)}">${e(date)}</time>`:`<span class="row-date-value">${e(date)}</span>`;
  const authors=r.authors.slice(0,2).join(', ')+(r.authors.length>2?' et al.':'');
  const facets=[...r.environments.filter(x=>x!=='unspecified').map(x=>label(PLATFORMS,x)),...r.topics.slice(0,2).map(x=>label(TOPICS,x))];
  const summary=r.summary || t('noTaxonomy');
  return `<article class="resource-row" data-kind="${e(r.kind)}"><div class="row-date">${dateMarkup}<span>${r.paper_version?`arXiv v${r.paper_version}`:e(label(KINDS,r.kind))}</span></div><div class="row-main"><h3><a href="${e(r.page_url)}" data-record="${e(r.id)}">${e(r.name)}</a></h3><p class="row-summary">${e(summary)}</p><div class="row-meta">${authors?`<span class="row-authors">${e(authors)}</span>`:''}${facets.map(x=>`<span class="row-tag">${e(x)}</span>`).join('')}${!isPaper?`<span>${e(label(KINDS,r.kind))}</span>`:''}${compactFacts(r,t).filter(f=>f.key!=='year').map(factMarkup).join('')}</div></div><div class="row-actions"><span class="row-review ${reviewed?'is-reviewed':''}">${e(t(reviewed?'curatedBadge':'metadataBadge'))}</span><a href="${e(safeURL(r.paper_source_url || r.url))}" target="_blank" rel="noopener noreferrer">${e(t('primaryLink'))} ↗</a><a href="${e(r.page_url)}" data-record="${e(r.id)}">${r.related_count?`${num(r.related_count)} ${e(t('related'))} · `:''}${e(t('recordLink'))}</a></div></article>`;
}
async function load() {
  const slowNotice=$('#load-slow');
  loading=true;$('#load-error').hidden=true;if(slowNotice)slowNotice.hidden=true;$('#results').setAttribute('aria-busy','true');$('#results-count').textContent=t('loading');$('#results').innerHTML=Array.from({length:6},()=>'<div class="skeleton-card" aria-hidden="true"></div>').join('');
  const slowTimer=setTimeout(()=>{if(loading&&slowNotice){slowNotice.hidden=false;$('#results-count').textContent=t('loadingSlow');}},8000);
  try {
    const response=await fetch('./data/index.json');if(!response.ok)throw new Error('HTTP '+response.status);
    const data=await response.json();report=data.coverage;records=data.records;TOPICS=data.topics || {};
    records.forEach(r=>r.search_text=recordSearchText(r,TOPICS));
    if(!Object.hasOwn(PLATFORMS,state.platform))state.platform='';
    if(!records.some(r=>r.topics.includes(state.topic)))state.topic='';
    $('#stat-resources').textContent=num(records.length);$('#stat-curated').textContent=num(report.curated_records);$('#stat-kinds').textContent=num(Object.keys(report.by_kind).length);$('#stat-sources').textContent=num(report.sources.length);
    loading=false;clearTimeout(slowTimer);if(slowNotice)slowNotice.hidden=true;translate();render();updateURL();
    if(pendingInfo&&$('#info-dialog').open)info(pendingInfo);
    const rid=new URLSearchParams(location.search).get('record');if(rid)await showRecord(rid,false);
  } catch(error) {loading=false;$('#results').innerHTML='';$('#results').setAttribute('aria-busy','false');$('#load-error').hidden=false;$('#results-count').innerHTML=`<span class="sr-only">${e(t('errorTitle'))}</span>`;console.error('Catalog loading failed:',error);if(pendingInfo&&$('#info-dialog').open)info(pendingInfo);}
  finally {clearTimeout(slowTimer);if(slowNotice)slowNotice.hidden=true;}
}
const external=(url,text)=>`<a href="${e(safeURL(url))}" target="_blank" rel="noopener noreferrer">${e(text)} ↗</a>`;
function resourceFacts(details) {
  return '<dl class="fact-list">'+Object.entries(details).map(([key,v])=>[key,v,formatFact(key,v,lang)]).filter(([,,text])=>text).map(([key,v,text])=>'<div><dt>'+e(label(FACT_LABELS,key))+'</dt><dd>'+(key.endsWith('_url')&&typeof v==='string'?external(v,lang==='zh'?'打开链接':'Open link'):e(text).replaceAll('\n','<br>'))+'</dd></div>').join('')+'</dl>';
}
async function showRecord(id,setURL=true) {
  const found=records.find(r=>r.id===id);if(!found){activeRecord='';if($('#detail-dialog').open)$('#detail-dialog').close();toast(t('noRecord'));return;}
  // Opening the dialog adds one history entry so Back closes it; records opened inside the dialog replace that entry.
  activeRecord=id;if(setURL)updateURL(!$('#detail-dialog').open);
  $('#detail-overline').textContent=label(KINDS,found.kind);
  $('#detail-content').innerHTML=`<h2 id="detail-title" tabindex="-1">${e(found.name)}</h2><p>${e(t('loading'))}</p>`;
  // A record opened from inside the dialog replaces the activated link, so start it at the top and move focus to its title once rendered.
  const inside=$('#detail-dialog').open;if(inside)$('#detail-dialog').scrollTop=0;else $('#detail-dialog').showModal();
  try {
    const r=await getDetails(found);if(activeRecord!==id)return;
    const scope={core:'scopeCore',adjacent:'scopeAdjacent',relevance_pending:'scopePending'}[r.scope];
    let content=`<h2 id="detail-title" tabindex="-1">${e(r.name)}</h2><p class="detail-description">${e(r.summary || t('noTaxonomy'))}</p><div class="detail-badges"><span>${e(t(r.review_status==='curated'?'curated':'metadata'))}</span><span>${e(t(scope))}</span>${r.environments.filter(x=>x!=='unspecified').map(x=>`<span>${e(label(PLATFORMS,x))}</span>`).join('')}</div><div class="detail-actions"><a class="button primary" href="${e(safeURL(r.url))}" target="_blank" rel="noopener noreferrer">${e(t('openSource'))} ↗</a><button class="button secondary" type="button" data-copy-link>${e(t('copyLink'))} ⧉</button><a class="resource-page-link" href="${e(found.page_url)}">${lang==='zh'?'打开完整资源页':'Open full resource page'} ↗</a></div><div class="detail-dates"><div>${e(t('verified'))}<strong>${e(dates(r.last_verified_at))}</strong></div>${r.published_at?`<div>${e(t('published'))}<strong>${e(dates(r.published_at))}</strong></div>`:''}</div>`;
    if(r.topics.length)content+=`<section class="detail-section"><h3>${e(t('topics'))}</h3><p>${r.topics.map(x=>e(label(TOPICS,x))).join(' · ')}</p></section>`;
    if(r.authors.length)content+=`<section class="detail-section"><h3>${e(t('authors'))}</h3><p>${r.authors.map(e).join(', ')}</p></section>`;
    if(r.kind!=='paper'&&r.kind!=='survey')content+=`<section class="detail-section"><h3>${e(t('licenses'))}</h3><div class="license-grid">${['code','data','weights','document'].map(slot=>{const l=r.licenses[slot];return `<div class="license-item"><span>${e(t(slot))}</span>${l?external(l.url,Array.isArray(l.declared)?l.declared.join(', '):l.declared):e(t('unknown'))}</div>`;}).join('')}</div><p>${e(t('licenseCaution'))}</p></section>`;
    const snapshot=r.details.arxiv_snapshot;
    const preferred=r.identifiers.preferred_arxiv?records.find(row=>row.id==='arxiv:'+r.identifiers.preferred_arxiv):null;
    if(preferred)content+=`<section class="detail-section"><h3>${lang==='zh'?'首选论文记录':'Preferred paper record'}</h3><p>${lang==='zh'?'原始来源明确指出另一个首选 arXiv 标识；这些书目记录不应算作独立成果。':'The original source identifies a preferred arXiv record; these bibliographic identities should not be counted as independent works.'}</p><a class="subtle-link" href="${e(preferred.page_url)}" data-record="${e(preferred.id)}">${e(preferred.name)} ↗</a></section>`;
    if(snapshot)content+=`<section class="detail-section"><h3>${lang==='zh'?'已记录的论文版本':'Recorded paper version'}</h3><p>${snapshot.versioned_url?external(snapshot.versioned_url,`arXiv v${snapshot.version}`):e(t('unknown'))}</p>${snapshot.updated_at?`<p>${lang==='zh'?'版本更新时间':'Version updated'}: ${e(dates(snapshot.updated_at))}</p>`:''}</section>`;
    if(['paper','survey'].includes(r.kind))content+=`<section class="detail-section citation-section"><h3>${e(t('citePaper'))}</h3><div class="citation-actions"><button type="button" class="button secondary" data-copy-citation="${e(found.page_url)}citation.bib">${e(t('copyBibtex'))}</button><a href="${e(found.page_url)}citation.bib" download>BibTeX ↓</a><a href="${e(found.page_url)}citation.csl.json" download>CSL JSON ↓</a></div><p>${e(t('citationNote'))}</p></section>`;
    const pub=r.details.publication;
    if(pub){
      const issued=(pub.date_parts||[]).map((part,index)=>String(part).padStart(index?2:4,'0')).join('-');
      const fields=[[lang==='zh'?'出版题名':'Publication title',pub.title],[lang==='zh'?'出版作者':'Publication authors',(pub.authors||[]).join(', ')],[lang==='zh'?'出版日期（原精度）':'Publication date (recorded precision)',issued],[lang==='zh'?'会议／期刊':'Venue',pub.venue],[lang==='zh'?'出版社':'Publisher',pub.publisher],[lang==='zh'?'卷／期':'Volume / issue',[pub.volume,pub.issue].filter(Boolean).join(' / ')],[lang==='zh'?'页码':'Pages',pub.pages],['DOI',pub.doi]].filter(([,value])=>value);
      content+=`<section class="detail-section publication-section"><h3>${lang==='zh'?'出版记录':'Publication record'}</h3><dl class="fact-list">${fields.map(([key,value])=>`<div><dt>${e(key)}</dt><dd>${e(value)}</dd></div>`).join('')}</dl><p>${external(pub.url,lang==='zh'?'出版来源':'Publication source')}</p><div class="citation-actions"><button type="button" class="button secondary" data-copy-citation="${e(found.page_url)}publication-citation.bib">${lang==='zh'?'复制出版版 BibTeX':'Copy publication BibTeX'}</button><a href="${e(found.page_url)}publication-citation.bib" download>BibTeX ↓</a><a href="${e(found.page_url)}publication-citation.csl.json" download>CSL JSON ↓</a></div>${r.id.startsWith('arxiv:')?`<p>${lang==='zh'?'出版版与上方保留的 arXiv 版本分别引用；作者、题名和日期可能不同。':'Cite this publication separately from the retained arXiv version above; its title, authors and date can differ.'}</p>`:''}${pub.notes?`<p>${e(pub.notes)}</p>`:''}</section>`;
    }
    if(r.details.license_review)content+=`<section class="detail-section"><h3>${lang==='zh'?'许可审阅说明':'License review notes'}</h3>${Object.entries(r.details.license_review).map(([slot,review])=>`<p><strong>${e(t(slot))}:</strong> ${e(review.reason)}</p><p>${review.evidence_urls.map((url,i)=>external(url,`${lang==='zh'?'来源':'Source'} ${i+1}`)).join(' · ')}</p>`).join('')}</section>`;
    const specifications=Object.fromEntries(Object.entries(r.details).filter(([key])=>!['arxiv_snapshot','publication','license_review'].includes(key)));
    if(Object.entries(specifications).some(([key,v])=>formatFact(key,v,lang)))content+=`<section class="detail-section"><h3>${e(t('details'))}</h3>${resourceFacts(specifications)}</section>`;
    if(r.notes)content+=`<section class="detail-section"><h3>${e(t('notes'))}</h3><p>${e(r.notes)}</p></section>`;
    if(r.relations.length)content+=`<section class="detail-section"><h3>${e(t('relations'))}</h3><ul>${r.relations.map(rel=>{const target=records.find(row=>row.id===rel.target_id);return `<li>${e(rel.type.replaceAll('_',' '))} → <button class="subtle-link" type="button" data-record="${e(rel.target_id)}">${e(target?.name || rel.target_id)}</button></li>`;}).join('')}</ul></section>`;
    const connected=(found.incoming_relations||[]).map(relation=>({source:records.find(row=>row.id===relation.source_id),relation})).filter(item=>item.source);
    if(connected.length)content+=`<section class="detail-section"><h3>${lang==='zh'?'关联资产':'Connected assets'}</h3><ul>${connected.map(({source,relation})=>`<li><a class="subtle-link" href="${e(records.find(x=>x.id===source.id)?.page_url || '#')}" data-record="${e(source.id)}">${e(source.name)}</a> · ${e(label(KINDS,source.kind))} · ${external(relation.evidence_url,lang==='zh'?'关联证据':'Evidence')}</li>`).join('')}</ul></section>`;
    content+=`<section class="detail-section"><h3>${e(t('evidence'))}</h3>${r.evidence.map(ev=>`<div class="evidence-item">${external(ev.url,new URL(ev.url).hostname)}<p>${e(t('referenceDate'))}: ${e(dates(ev.retrieved_at))} · ${e(ev.method.replaceAll('_',' '))}</p><details><summary>SHA-256</summary><p class="detail-meta">${e(ev.sha256)}</p></details></div>`).join('')}</section><section class="detail-section"><h3>${e(t('recordID'))}</h3><div class="detail-meta">${e(r.id)}</div></section>`;
    $('#detail-content').innerHTML=content;
  }catch(error){if(activeRecord!==id)return;$('#detail-content').innerHTML=`<h2 id="detail-title" tabindex="-1">${e(found.name)}</h2><p>${e(t('errorDetail'))}</p><button type="button" class="button secondary" data-record="${e(id)}">${e(t('retry'))}</button>`;}
  if(inside)$('#detail-title').focus();
}
function localSearchStep() {
  return `<details class="agent-search"><summary>${e(t('localSearch'))}</summary><pre><code>${e(LOCAL_SEARCH_COMMAND)}</code></pre><p>${e(t('localSearchRequirements'))}</p></details>`;
}
function cloneCommand(scope) {
  return `<div class="clone-entry-command" data-clone-entry><div class="clone-command"><code aria-label="${e(t('cloneCommandLabel'))}">${e(CLONE_COMMAND)}</code><button type="button" data-copy-clone aria-describedby="clone-status-${scope}">${e(t('copyCommand'))}</button></div><p id="clone-status-${scope}" class="clone-feedback" data-clone-status role="status" aria-live="polite" aria-atomic="true"></p>${localSearchStep()}</div>`;
}
function agentRelated() {
  return `<div class="agent-related"><span>${e(t('relatedResearch'))}</span><a href="https://github.com/reacher-z/Awesome-Jev" target="_blank" rel="noopener noreferrer">Awesome-Jev <span>${e(t('jevScope'))}</span> <span aria-hidden="true">↗</span></a></div>`;
}
function agentLinks() {
  return `<ul class="agent-entry-links"><li><a href="${lang==='zh'?'/zh/agents/':'/agents/'}"><strong>${e(t('agentGuide'))} ↗</strong><span>${e(t('agentGuideCopy'))}</span></a></li><li><a href="/AGENTS.md"><strong>${e(t('agentInstructions'))} ↗</strong><span>${e(t('agentInstructionsCopy'))}</span></a></li><li><a href="/downloads/rag-manifest.json"><strong>${e(t('agentManifest'))} ↗</strong><span>${e(t('agentManifestCopy'))}</span></a></li></ul>`;
}
function info(type) {
  let content='';
  // Downloads are static files; only the coverage view waits for index.json, and it re-renders once loading settles.
  pendingInfo=type!=='download'&&!report?type:'';
  if(type==='download') {
    const options=[['catalog.jsonl','fullCatalog','fullCatalogCopy','JSONL'],['catalog.sqlite','sqlite','sqliteCopy','SQLite'],['rag-documents.jsonl','ragReviewed','ragReviewedCopy','JSONL'],['rag-all-records.jsonl','ragAll','ragAllCopy','JSONL'],['citations.bib','paperBibtex','paperBibtexCopy','BibTeX'],['citations.csl.json','paperCSL','paperCSLCopy','JSON'],['publication-citations.bib','publicationBib','publicationBibCopy','BibTeX'],['publication-citations.csl.json','publicationCSL','publicationCSLCopy','JSON'],['coverage.json','coverageFile','coverageFileCopy','JSON'],['sources.json','sourcesFile','sourcesFileCopy','JSON']];
    content=`<h2 id="info-title">${e(t('downloadTitle'))}</h2><section class="agent-download"><h3>${e(t('agentTitle'))}</h3><p class="agent-entry-copy">${e(t('agentCopy'))}</p>${cloneCommand('download')}${agentLinks()}${agentRelated()}</section>`;
    content+=`<div class="download-section-heading"><h3>${e(t('agentDownloads'))}</h3><a href="${lang==='zh'?'/zh/data/':'/data/'}">${e(t('dataHub'))} ↗</a></div><p>${e(t('downloadCopy'))}</p><div class="download-options">${options.map(([file,title,copy,format])=>`<a class="download-option" href="./downloads/${file}" download><span><strong>${e(t(title))}</strong><small>${e(t(copy))}</small></span><span class="download-format">${e(format)}<span aria-hidden="true">↓</span></span></a>`).join('')}</div><p><a href="/downloads/manifest.json">${e(t('downloadInventory'))} ↗</a></p><p>${e(t('licenseNote'))}</p>`;
  }else if(!report) {
    content=`<h2 id="info-title">${e(t('coverageDialogTitle'))}</h2><p role="status">${e(t(loading?'loading':'errorTitle'))}</p><p><a href="/coverage/">${e(t('viewCoverage'))} ↗</a></p>`;
  }else {
    content=`<h2 id="info-title">${e(t('coverageDialogTitle'))}</h2><p>${e(t('coverageDialogCopy'))}</p><div class="info-stat-grid"><div><strong>${num(report.curated_records)}</strong><span>${e(t('curatedResources'))}</span></div><div><strong>${num(report.metadata_only_records)}</strong><span>${e(t('metadata'))}</span></div><div><strong>${num(report.unindexed_candidates)}</strong><span>${e(t('unindexed'))}</span></div></div><p>${e(t('reviewExplanation'))}</p><table class="coverage-table"><thead><tr><th>${e(t('source'))}</th><th>${e(t('discovered'))}</th><th>${e(t('indexed'))}</th></tr></thead><tbody>${report.sources.map(s=>`<tr><td>${external(s.url,s.name)}</td><td>${num(s.discovered)}</td><td>${num(s.indexed)}</td></tr>`).join('')}</tbody></table><h3>${e(t('limitations'))}</h3><p>${e(t('boundaries'))}</p><a class="button secondary" href="./downloads/coverage.json" download>${e(t('coverageFile'))} ↓</a>`;
  }
  if(type!=='download' && report?.excluded_records)content+=`<h3>${e(t('excluded'))}: ${num(report.excluded_records)}</h3><p>${e(t('exclusionCopy'))}</p><p><a href="./downloads/exclusions.json">${e(t('exclusionFile'))}</a> · <a href="./downloads/arxiv-archive.jsonl">${e(t('archiveFile'))}</a></p>`;
  $('#info-content').innerHTML=content;if(!$('#info-dialog').open)$('#info-dialog').showModal();
}
document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-copy-clone]');if(!button||button.disabled)return;
  const status=button.closest('[data-clone-entry]')?.querySelector('[data-clone-status]');if(!status)return;
  const wasFocused=document.activeElement===button,dialog=button.closest('dialog');
  const announce=key=>{status.dataset.i18n=key;status.textContent=t(key);};
  button.disabled=true;announce('commandCopying');
  try{await navigator.clipboard.writeText(CLONE_COMMAND);announce('commandCopied');}
  catch{announce('commandCopyFailed');}finally{
    button.disabled=false;
    if(wasFocused&&button.isConnected&&(!dialog||dialog.open)&&document.activeElement===document.body)button.focus({preventScroll:true});
  }
});
document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-copy-citation]');if(!button)return;
  button.disabled=true;
  try{const response=await fetch(button.dataset.copyCitation);if(!response.ok)throw new Error('Citation unavailable');const text=await response.text();if(!text.trim())throw new Error('Empty citation');await navigator.clipboard.writeText(text);toast(t('citationCopied'));}
  catch{toast(t('citationFailed'));}finally{button.disabled=false;}
});
$('#search').addEventListener('input',event=>change({q:event.target.value}));
for(const [id,key] of [['platform','platform'],['review','review'],['topic','topic'],['year','year'],['sort','sort']])$('#'+id).addEventListener('change',event=>change({[key]:event.target.value}));
// Both reset buttons hide themselves, so focus moves to the result summary, which announces the restored count.
const reset=()=>{change({q:'',kind:'',platform:'',review:'',topic:'',year:'',sort:'featured'});$('#results-count').focus();};
$('#clear-filters').addEventListener('click',reset);$('#empty-reset').addEventListener('click',reset);
$('#view-grid').addEventListener('click',()=>change({view:'grid',page:state.page}));$('#view-list').addEventListener('click',()=>change({view:'list',page:state.page}));
$('#categories').addEventListener('click',event=>{const button=event.target.closest('[data-kind]');if(button)change({kind:button.dataset.kind,view:['paper','survey'].includes(button.dataset.kind)?'list':state.view});});
$$('[data-environment]').forEach(button=>button.addEventListener('click',()=>change({platform:button.dataset.environment,kind:'',q:''},true)));
$$('[data-search]').forEach(button=>button.addEventListener('click',()=>change({q:button.dataset.search,topic:''})));
$$('[data-topic]').forEach(button=>button.addEventListener('click',()=>change({topic:button.dataset.topic,q:''})));
document.addEventListener('click',event=>{const button=event.target.closest('[data-record]');if(!button)return;if(button.tagName==='A'&&(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||event.button!==0))return;event.preventDefault();showRecord(button.dataset.record);});
$('#pagination').addEventListener('click',event=>{const button=event.target.closest('[data-page]');if(button&&!button.disabled){change({page:Number(button.dataset.page)});$('.results-toolbar').scrollIntoView({block:'start',behavior:'instant'});$('#results-count').focus();}});
$('#language').addEventListener('click',()=>{lang=lang==='en'?'zh':'en';try{localStorage.setItem('cua-language',lang);}catch{}translate();render();updateURL();if(activeRecord)showRecord(activeRecord,false);});
for(const id of ['hero-download','sidebar-download'])$('#'+id).addEventListener('click',()=>info('download'));
for(const id of ['coverage-button','footer-method'])$('#'+id).addEventListener('click',()=>info('coverage'));
$$('.dialog-close').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
$$('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}}));
// Back has already removed ?record= when it closes the dialog. Closing it in the page steps back over the entry it opened; a deep link just drops the parameter.
$('#detail-dialog').addEventListener('close',()=>{activeRecord='';if(!new URLSearchParams(location.search).has('record'))return;if(history.state?.record)history.back();else updateURL();});
$('#detail-dialog').addEventListener('click',async event=>{if(event.target.closest('[data-copy-link]')){try{await navigator.clipboard.writeText(new URL(records.find(r=>r.id===activeRecord)?.page_url || location.href,location.origin).href);toast(t('copied'));}catch{toast(t('copyFailed'));}}});
document.addEventListener('keydown',event=>{if(event.key==='/'&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName)&&!$$('dialog').some(d=>d.open)){event.preventDefault();$('#search').focus();$('#catalog').scrollIntoView({block:'start'});}});
window.addEventListener('popstate',()=>{
  const p=new URLSearchParams(location.search),next=parseState(location.search),nextLang=p.get('lang')==='zh'?'zh':'en';
  // Re-render only when the filters changed, so closing the dialog can return focus to the card that opened it.
  if(serializeState(next,nextLang)!==serializeState(state,lang)){state=next;lang=nextLang;translate();render();}
  const id=p.get('record');if(id)showRecord(id,false);else if($('#detail-dialog').open)$('#detail-dialog').close();
});
$('#retry').addEventListener('click',load);
translate();
// Preserve a deep-linked record before normalizing the filter URL during initial loading.
activeRecord=new URLSearchParams(location.search).get('record') || '';
load();

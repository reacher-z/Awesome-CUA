"""Category-page guides: a short definition, a "how to choose" table and FAQs, all computed from the reviewed records."""
from __future__ import annotations

from collections import Counter, defaultdict
import html
import re

import home_page
from publication_metadata import record_date_text
from site_config import SITE
from site_shell import ic
from specifications import PREFIXES
from topic_pages import topic_name

# What each category holds, in at most two sentences; the facts come from the records the page lists.
DEFINITIONS = {
    'benchmark': ('Computer-use benchmarks are task suites and environments that score agents operating web browsers, desktop applications or mobile devices. Each pairs a fixed set of tasks with an evaluator, such as execution-based state checks, answer matching or target localization.',
                  '计算机使用评测基准是一组任务与环境，用来给操作网页浏览器、桌面应用或移动设备的智能体打分。每个基准都把固定的任务集与评估器配在一起，评估方式包括基于执行的状态检查、答案匹配和目标定位。'),
    'dataset': ('Computer-use datasets supply screenshots, instructions, element annotations and action trajectories for training or evaluating GUI agents. Supervision ranges from single-element grounding to complete multi-step trajectories.',
                '计算机使用数据集提供截图、指令、界面元素标注和动作轨迹，用于训练或评估 GUI 智能体。监督信号从单个元素的定位到完整的多步轨迹不等。'),
    'model': ('Computer-use models are vision-language and GUI-specialized checkpoints that read screens and output target coordinates or actions. Entries cover model families and released checkpoints, many hosted on Hugging Face.',
              '计算机使用模型是读取屏幕、输出目标坐标或动作的视觉语言模型和 GUI 专用检查点。条目包括模型系列和已发布的检查点，其中许多托管在 Hugging Face。'),
    'agent': ('Computer-use agents are complete systems that observe a screen or web page, plan, and act through clicks, typing, browser commands or shell tools to finish a user task.',
              '计算机使用智能体是完整的系统：观察屏幕或网页，制定计划，再通过点击、输入、浏览器命令或命令行工具完成用户任务。'),
    'framework': ('Frameworks are libraries and SDKs for building, running, evaluating or training computer-use agents, from browser-automation agent libraries to reinforcement-learning training stacks.',
                  '框架是用于构建、运行、评估或训练计算机使用智能体的库和 SDK，从浏览器自动化智能体库到强化学习训练栈。'),
    'tool': ('Tools are utilities that an agent or developer calls to control, observe or inspect an interface: MCP servers, browser and device controllers, screen parsers and recorders.',
             '工具是智能体或开发者调用的实用程序，用来控制、观察或检查界面，包括 MCP 服务器、浏览器与设备控制器、屏幕解析器和录制工具。'),
    'infrastructure': ('Infrastructure covers the browsers, sandboxes, virtual machines, emulators and input-automation libraries that computer-use agents run inside or act through.',
                       '基础设施指计算机使用智能体在其中运行或借以操作的浏览器、沙箱、虚拟机、模拟器和输入自动化库。'),
    'product': ('Products are commercial and hosted computer-use offerings, such as browser agents, desktop assistants and agent APIs, run by their publishers.',
                '产品是由发布方运营的商业化或托管式计算机使用服务，例如浏览器智能体、桌面助手和智能体 API。'),
    'company': ('Publishers are the labs and companies behind catalogued resources. Each publisher entry collects the products, models, frameworks and tools that name it as their publisher.',
                '发布方是目录中各项资源背后的实验室和公司。每个发布方条目汇总了将其列为发布方的产品、模型、框架和工具。'),
    'learning': ('Learning resources are courses, cookbooks, tutorials, example collections and curated lists for building and studying computer-use agents.',
                 '学习资源是用于构建和研究计算机使用智能体的课程、实践手册、教程、示例合集和精选列表。'),
    'survey': ('Surveys are review articles that map computer-use and GUI-agent research: its methods, benchmarks, datasets, safety questions and open problems.',
               '综述是梳理计算机使用与 GUI 智能体研究的文章，涵盖方法、评测基准、数据集、安全问题和待解决的问题。'),
}

ROWS = 6
FACETS = ('web', 'desktop', 'mobile', 'cross')
SETTINGS = {'interactive': ('Interactive', '交互式'), 'offline': ('Offline', '离线'), 'mixed': ('Mixed', '混合')}
SCOPES = {'code': ('code', '代码'), 'data': ('data', '数据'), 'weights': ('weights', '权重'), 'document': ('document', '文档')}
# The license a category's readers look for first; the other scopes follow in this order.
LICENSE_ORDER = {'model': ('weights', 'code'), 'dataset': ('data', 'code'), 'learning': ('document', 'code')}
COLUMNS = {
    'benchmark': ('platform', 'setting', 'scale', 'leaderboard'),
    'dataset': ('platform', 'supervision', 'scale', 'license'),
    'model': ('platform', 'license', 'paper', 'links'),
    'product': ('platform', 'access', 'pricing'),
    'company': ('resources', 'kinds'),
    'survey': ('date', 'platform', 'topics'),
}
HEADINGS = {'platform': ('Platform', '平台'), 'setting': ('Setting', '设置'), 'scale': ('Scale', '规模'), 'leaderboard': ('Leaderboard', '排行榜'),
            'supervision': ('Supervision', '监督信号'), 'license': ('License', '许可证'), 'paper': ('Paper', '论文'), 'links': ('Linked records', '关联记录'),
            'publisher': ('Publisher', '发布方'), 'access': ('Access', '访问方式'), 'pricing': ('Pricing', '定价'), 'resources': ('Resources', '资源'), 'kinds': ('Kinds', '类型'),
            'date': ('Date', '日期'), 'topics': ('Topics', '主题')}
KIND_NAMES = {'paper': ('paper', 'papers', '论文'), 'survey': ('survey', 'surveys', '综述'), 'learning': ('learning resource', 'learning resources', '学习资源'),
              'model': ('model', 'models', '模型'), 'dataset': ('dataset', 'datasets', '数据集'), 'benchmark': ('benchmark', 'benchmarks', '评测基准'),
              'agent': ('agent', 'agents', '智能体'), 'framework': ('framework', 'frameworks', '框架'), 'infrastructure': ('infrastructure resource', 'infrastructure resources', '基础设施'),
              'tool': ('tool', 'tools', '工具'), 'product': ('product', 'products', '产品'), 'company': ('publisher', 'publishers', '发布方')}


def esc(value):
    return html.escape(str(value), quote=True)


def plain(markup):
    """Visible text of an answer, for FAQPage JSON-LD."""
    return html.unescape(re.sub(r'<[^>]+>', '', markup))


def resource_path(record):
    return f'/resources/{home_page.slug(record["id"])}/'


def a(record, zh):
    return f'<a href="{esc(resource_path(record))}">{esc(home_page.clean_title(record["name"]))}</a>'


def series(items, zh):
    """A, B and C / A、B 和 C."""
    items = list(items)
    if len(items) < 2:
        return ''.join(items)
    return ('、'.join(items[:-1]) + '和' + items[-1]) if zh else (', '.join(items[:-1]) + ' and ' + items[-1])


CJK = '\u3400-\u9fff'


def spaced(markup):
    """Chinese copy: one space between Han characters and Latin letters or digits, including at link edges."""
    markup = re.sub(f'([{CJK}])((?:<a [^>]*>)?[A-Za-z0-9])', r'\1 \2', markup)
    return re.sub(f'([A-Za-z0-9.)](?:</a>)?)([{CJK}])', r'\1 \2', markup)


def license_name(spellings):
    """The declared spelling to show for a case-insensitive license group, in SPDX-like case when one was recorded."""
    best = max(spellings, key=lambda value: (sum(ch.isupper() for ch in value), spellings[value]))
    if best != best.lower():
        return best
    if best in LICENSE_CASE:
        return LICENSE_CASE[best]
    return 'Apache-' + best[7:] if best.startswith('apache-') else best.upper() if best != 'other' else best


LICENSE_CASE = {'unlicense': 'Unlicense', 'openrail': 'OpenRAIL', 'odc-by': 'ODC-By'}


def n(value):
    return f'{value:,}'


def facets(record):
    return home_page.env_facets(record['environments'])


def platform_text(record, zh):
    labels = home_page.ENV_ZH if zh else home_page.ENV_LABEL
    return ' · '.join(labels[f] for f in facets(record)) or '—'


def license_scopes(kind):
    preferred = LICENSE_ORDER.get(kind, ('code', 'document'))
    return preferred + tuple(scope for scope in SCOPES if scope not in preferred)


def primary_license(record):
    """First declared license in the category's scope order, as (scope, value)."""
    for scope in license_scopes(record['kind']):
        declared = (record['licenses'].get(scope) or {}).get('declared')
        if declared:
            return scope, ' / '.join(declared) if isinstance(declared, list) else declared
    return None


def first_count(record, key):
    counts = ((record['details'].get(key) or {}).get('counts') or [])
    return counts[0] if counts else None


def paper_record(record, by_id):
    for relation in sorted(record['relations'], key=lambda rel: rel['type'] != 'introduced_by'):
        if relation['type'] in ('introduced_by', 'documented_by') and relation['target_id'].startswith('arxiv:'):
            return relation['target_id'], by_id.get(relation['target_id'])
    return None


def publishers(record, by_id):
    return [by_id[rel['target_id']] for rel in record['relations'] if rel['type'] == 'published_by' and rel['target_id'] in by_id]


def published(view, company_id):
    return [r for r in view['reviewed'] if any(rel['type'] == 'published_by' and rel['target_id'] == company_id for rel in r['relations'])]


def cell(column, record, view, zh):
    by_id = view['by_id']
    details = record['details']
    if column == 'platform':
        return esc(platform_text(record, zh))
    if column == 'setting':
        setting = (details.get('benchmark_protocol') or {}).get('setting')
        return esc(SETTINGS[setting][zh]) if setting in SETTINGS else '—'
    if column == 'scale':
        count = first_count(record, 'benchmark_protocol' if record['kind'] == 'benchmark' else 'dataset_profile')
        if not count:
            return '—'
        return f'<a href="{esc(count.get("reference_url") or count["evidence_url"])}">{esc(PREFIXES[count["qualifier"]] + n(count["value"]) + " " + count["unit"])}</a>'
    if column == 'leaderboard':
        url = details.get('leaderboard_url')
        return f'<a href="{esc(url)}">{"排行榜" if zh else "Leaderboard"}</a>' if url else '—'
    if column == 'supervision':
        values = (details.get('dataset_profile') or {}).get('supervision') or []
        return esc(', '.join(values[:2])) if values else '—'
    if column == 'license':
        found = primary_license(record)
        if not found:
            return '—'
        scope, value = found
        url = (record['licenses'].get(scope) or {}).get('url')
        label = esc(' / '.join(license_name({part: 1}) for part in value.split(' / '))) + (f'（{SCOPES[scope][1]}）' if zh else f' ({SCOPES[scope][0]})')
        return f'<a href="{esc(url)}">{label}</a>' if url else label
    if column == 'paper':
        found = paper_record(record, by_id)
        if not found:
            return '—'
        identifier, paper = found
        label = 'arXiv ' + identifier.split(':', 1)[1]
        return f'<a href="{esc(resource_path(paper))}">{esc(label)}</a>' if paper else esc(label)
    if column == 'links':
        return n(len(linked(view)[record['id']]))
    if column == 'publisher':
        return ', '.join(a(p, zh) for p in publishers(record, by_id)) or '—'
    if column == 'access':
        return ('发布方托管' if zh else 'Publisher-managed') if details.get('access') == 'publisher-managed' else '—'
    if column == 'pricing':
        url = details.get('pricing_url')
        return f'<a href="{esc(url)}">{"定价页" if zh else "Pricing page"}</a>' if url else '—'
    if column == 'resources':
        return n(len(published(view, record['id'])))
    if column == 'kinds':
        kinds = Counter(r['kind'] for r in published(view, record['id']))
        return esc(', '.join((f'{KIND_NAMES[k][2]} {c}' if zh else f'{c} {KIND_NAMES[k][0 if c == 1 else 1]}') for k, c in kinds.most_common())) or '—'
    if column == 'date':
        return esc(record_date_text(record) or '—')
    if column == 'topics':
        return esc(('、' if zh else ', ').join([topic_name(t, 'zh' if zh else 'en') for t in record['topics'] if t != 'survey'][:2])) or '—'
    raise KeyError(column)


FALLBACK_COLUMNS = ('publisher', 'license', 'links')


def linked(view):
    """Distinct other reviewed records linked to each record, by a mention in their reviewed source or a relation either way."""
    if 'linked' not in view:
        ids = {r['id'] for r in view['reviewed']}
        links = defaultdict(set)
        for record in view['reviewed']:
            for rel in record['relations']:
                if rel['target_id'] in ids and rel['target_id'] != record['id']:
                    links[rel['target_id']].add(record['id'])
                    links[record['id']].add(rel['target_id'])
        for target, sources in view['mentions'].items():
            links[target] |= {i for i in sources if i in ids and i != target}
        view['linked'] = links
    return view['linked']


def publisher_sizes(view):
    """Reviewed records each publisher has in the catalog."""
    if 'publisher_sizes' not in view:
        view['publisher_sizes'] = Counter(rel['target_id'] for r in view['reviewed'] for rel in r['relations'] if rel['type'] == 'published_by')
    return view['publisher_sizes']


def prominent(records, view):
    """The rows to compare: most linked records first; ties go to entries whose publisher has more catalog records, then by name."""
    links, sizes = linked(view), publisher_sizes(view)
    def key(record):
        size = max((sizes[rel['target_id']] for rel in record['relations'] if rel['type'] == 'published_by'), default=0)
        return (-len(links[record['id']]), -size, record['name'].casefold())
    return sorted(records, key=key)[:ROWS]


def columns_for(kind, rows, view):
    """The kind's preferred columns that at least two shown rows fill and that differ across rows, topped up from shared fallbacks."""
    preferred = COLUMNS.get(kind, ('platform', 'license', 'links'))
    needed = min(2, len(rows))

    def useful(column):
        values = [cell(column, r, view, False) for r in rows]
        return sum(v != '—' for v in values) >= needed and (len(rows) < 2 or len(set(values)) > 1)
    return tuple([c for c in dict.fromkeys(preferred + FALLBACK_COLUMNS) if useful(c)][:len(preferred)])


def ordered_by_mentions(kind):
    return kind not in ('survey',)


def choose_table(kind, records, view, *, zh, snapshot):
    rows = prominent(records, view)
    columns = columns_for(kind, rows, view)
    name_heading = KIND_NAMES[kind][2] if zh else KIND_NAMES[kind][0].capitalize()
    head = f'<th scope="col">{esc(name_heading)}</th>' + ''.join(f'<th scope="col">{HEADINGS[c][zh]}</th>' for c in columns)
    body = ''.join('<tr>' + f'<th scope="row">{a(r, zh)}</th>' + ''.join(f'<td data-label="{esc(HEADINGS[c][zh])}">{cell(c, r, view, zh)}</td>' for c in columns) + '</tr>' for r in rows)
    caption = '怎么选' if zh else 'How to choose'
    if zh:
        measure = {'company': '个', 'product': '款', 'survey': '篇'}.get(kind, '条')
        tie = '' if kind == 'company' else '；数量相同时，发布方在目录中记录更多者在前'
        source = (f'行：与其他已审核记录关联（提及或关系）最多的 {len(rows)} {measure}{KIND_NAMES[kind][2]}{tie}。'
                  f'数据见 <a href="/api/v1/resources.json">resources.json</a>，快照 {esc(snapshot[:10])}。每行链接到该条目的一手证据。')
    else:
        tie = '' if kind == 'company' else '; ties go to entries whose publisher has more catalog records'
        source = (f'Rows: the {len(rows)} {KIND_NAMES[kind][1 if len(rows) != 1 else 0]} linked to the most other reviewed records, by mention or relation{tie}. '
                  f'Data from <a href="/api/v1/resources.json">resources.json</a>, '
                  f'snapshot {esc(snapshot[:10])}. Each row links to its entry and primary evidence.')
    return f'<div class="choose"><table><caption id="choose-h">{caption}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table><p class="src">{source}</p></div>'


def mentioned_answer(kind, records, view, zh):
    top = [r for r in records if view['mentions'].get(r['id'])][:3]
    if len(top) < 2 or len(view['mentions'][top[0]['id']]) < 3:
        return None
    label = KIND_NAMES[kind]
    items = [f'{a(r, zh)}（{n(len(view["mentions"][r["id"]]))} 条记录）' if zh else f'{a(r, zh)} ({n(len(view["mentions"][r["id"]]))} records)' for r in top]
    if zh:
        return (f'目录中被提及最多的{label[2]}有哪些？', f'{series(items, zh)}在其他目录记录的已审核来源中被提及最多。')
    return (f'Which {label[1]} are mentioned most in the catalog?', f'{series(items, zh)} are mentioned in the reviewed sources of the most other catalog records.')


def platform_answer(kind, records, zh):
    counts = Counter(f for r in records for f in facets(r))
    if not counts:
        return None
    unrecorded = sum(not facets(r) for r in records)
    label = KIND_NAMES[kind]
    order = [f for f in FACETS if counts[f]]
    order.sort(key=lambda f: -counts[f])
    if zh:
        parts = [f'{home_page.ENV_ZH[f]} {n(counts[f])} 条' for f in order]
        tail = f'；{n(unrecorded)} 条未记录平台' if unrecorded else ''
        return (f'这些{label[2]}覆盖哪些平台？', f'在 {n(len(records))} 条已审核{label[2]}中，{"、".join(parts)}{tail}。标注多个平台的条目在每个平台下各计一次。')
    names = {'web': 'web', 'desktop': 'desktop', 'mobile': 'mobile', 'cross': 'cross-platform'}
    parts = [f'{n(counts[f])} {names[f]}' for f in order]
    parts[0] = f'{n(counts[order[0]])} {"is" if counts[order[0]] == 1 else "are"} tagged {names[order[0]]}'
    tail = (f'; {n(unrecorded)} {"has" if unrecorded == 1 else "have"} no platform recorded') if unrecorded else ''
    return (f'Which platforms do these {label[1]} cover?', f'Of {n(len(records))} reviewed {label[1]}, {series(parts, zh)}{tail}. An entry tagged with several platforms counts under each.')


def license_answer(kind, records, zh):
    spelled = {}
    counts = Counter()
    for r in records:
        found = primary_license(r)
        if found:
            key = found[1].casefold()
            counts[key] += 1
            spelled.setdefault(key, Counter())[found[1]] += 1
    if not counts:
        return None
    top = counts.most_common(3)
    missing = sum(primary_license(r) is None for r in records)
    label = KIND_NAMES[kind]
    names = [license_name(spelled[key]) for key, _ in top]
    if zh:
        items = [(f'标为 other 的许可证（{n(c)} 条）' if name == 'other' else f'{esc(name)}（{n(c)} 条）') for name, (_, c) in zip(names, top)]
        tail = f'{n(len(records))} 条中有 {n(missing)} 条未记录声明的许可证。' if missing else ''
        return (f'{label[2]}使用哪些许可证？', f'最常见的声明许可证是{series(items, zh)}。{tail}')
    items = [(f'licenses marked “other” ({n(c)})' if name == 'other' else f'{esc(name)} ({n(c)})') for name, (_, c) in zip(names, top)]
    tail = f' {n(missing)} of {n(len(records))} have no declared license in their record.' if missing else ''
    return (f'Which licenses do {label[1]} declare?', f'The most common declared licenses are {series(items, zh)}.{tail}')


def paper_answer(kind, records, view, zh):
    linked = [r for r in records if paper_record(r, view['by_id'])]
    if not linked:
        return None
    label = KIND_NAMES[kind]
    examples = series([a(r, zh) for r in linked[:3]], zh)
    if zh:
        return (f'哪些{label[2]}有对应的论文？', f'{n(len(records))} 条中有 {n(len(linked))} 条链接到提出或说明它的 arXiv 论文，{"即" if len(linked) == 1 else "例如"}{examples}。')
    if len(linked) == 1:
        return (f'Which {label[1]} come with a research paper?', f'1 of {n(len(records))} links the arXiv paper that introduces or documents it: {examples}.')
    return (f'Which {label[1]} come with a research paper?', f'{n(len(linked))} of {n(len(records))} link the arXiv paper that introduces or documents them, for example {examples}.')


def order_answer(kind, zh):
    if zh:
        return ('这个列表按什么排序？', '按在已审核来源中提及该条目的目录记录数排序，多者在前，数量相同时按名称排序。列表上方的排序菜单可切换为 A–Z。')
    return ('How is this list ordered?', 'By the number of catalog records whose reviewed sources mention each entry, most first, then by name. The sort menu above the list switches to A–Z.')


def benchmark_answers(records, view, zh):
    total = len(records)
    boards = [r for r in records if r['details'].get('leaderboard_url')]
    profiled = [r for r in records if r['details'].get('benchmark_protocol')]
    settings = Counter(r['details']['benchmark_protocol']['setting'] for r in profiled)
    examples = series([a(r, zh) for r in boards[:4]], zh)
    compare = '<a href="/compare/benchmarks/">' + ('评测基准对比页' if zh else 'benchmark comparison page') + '</a>'
    split = [(SETTINGS[s][zh], settings[s]) for s in ('interactive', 'offline', 'mixed') if settings[s]]
    if zh:
        return [('哪些评测基准有官方排行榜？', f'{n(total)} 条评测基准中有 {n(len(boards))} 条在已审核来源中链接了官方排行榜，包括{examples}。'),
                ('交互式评测和离线评测各有多少？', f'在 {n(len(profiled))} 条记录了评测协议的基准中，' + '、'.join(f'{label} {n(c)} 条' for label, c in split) + f'。{compare}列出每个协议的观察、动作、评估器和计数。')]
    return [('Which benchmarks have an official leaderboard?', f'{n(len(boards))} of {n(total)} benchmarks link an official leaderboard from their reviewed source, including {examples}.'),
            ('How many benchmarks are interactive and how many offline?', f'Of {n(len(profiled))} benchmarks with a recorded protocol, ' + series([f'{n(c)} are {label.lower()}' for label, c in split], zh) + f'. The {compare} lists each protocol\'s observations, actions, evaluator and counts.')]


def dataset_answers(records, view, zh):
    profiled = [r for r in records if r['details'].get('dataset_profile')]
    supervision = Counter(s for r in profiled for s in r['details']['dataset_profile']['supervision']).most_common(3)
    compare = '<a href="/compare/datasets/">' + ('数据集对比页' if zh else 'dataset comparison page') + '</a>'
    if zh:
        items = series([f'{esc(s)}（{n(c)} 条）' for s, c in supervision], zh)
        return [('哪些数据集记录了监督信号和规模？', f'{n(len(records))} 条数据集中有 {n(len(profiled))} 条附有数据集档案，记录监督信号、模态、格式、划分以及带单位的计数。最常见的监督信号是{items}。{compare}可逐项比较。')]
    items = series([f'{esc(s)} ({n(c)})' for s, c in supervision], zh)
    return [('Which datasets record their supervision and scale?', f'{n(len(profiled))} of {n(len(records))} datasets have a profile with supervision, modalities, formats, splits and counts with units. The most common supervision types are {items}. The {compare} sets them side by side.')]


def model_answers(records, view, zh):
    hosted = [r for r in records if r['details'].get('hub_id')]
    examples = series([a(r, zh) for r in hosted[:3]], zh)
    if zh:
        return [('有多少模型托管在 Hugging Face？', f'{n(len(records))} 条模型中有 {n(len(hosted))} 条链接到 Hugging Face 模型仓库，例如{examples}。')]
    return [('How many models are hosted on Hugging Face?', f'{n(len(hosted))} of {n(len(records))} models link a Hugging Face model repository, for example {examples}.')]


def product_answers(records, view, zh):
    by_id = view['by_id']
    named = [r for r in records if publishers(r, by_id)]
    top = [(i, c) for i, c in Counter(p['id'] for r in named for p in publishers(r, by_id)).most_common(3) if c > 1]
    priced = [r for r in records if r['details'].get('pricing_url')]
    managed = [r for r in records if r['details'].get('access') == 'publisher-managed']
    if zh:
        lead = series([f'{a(by_id[i], zh)}（{n(c)} 款）' for i, c in top], zh)
        return [('这些产品由谁发布？', f'{n(len(records))} 款产品中有 {n(len(named))} 款通过已审核的发布方关系标明了发布方' + (f'，其中产品最多的是{lead}。' if top else '。')),
                ('哪些产品公开了定价？', f'{n(len(records))} 款产品中有 {n(len(priced))} 款链接了官方定价页，{n(len(managed))} 款记录为由发布方托管的服务。')]
    lead = series([f'{a(by_id[i], zh)} ({n(c)})' for i, c in top], zh)
    return [('Who publishes these products?', f'{n(len(named))} of {n(len(records))} products name their publisher through a reviewed published-by relation' + (f'; {lead} publish the most.' if top else '.')),
            ('Which products publish pricing?', f'{n(len(priced))} of {n(len(records))} products link an official pricing page, and {n(len(managed))} are recorded as publisher-managed services.')]


def company_answers(records, view, zh):
    counts = sorted(((len(published(view, r['id'])), r) for r in records), key=lambda item: (-item[0], item[1]['name'].casefold()))
    top = [(c, r) for c, r in counts if c][:3]
    kinds = Counter(x['kind'] for r in records for x in published(view, r['id']))
    total = sum(kinds.values())
    if zh:
        lead = series([f'{a(r, zh)}（{n(c)} 条）' for c, r in top], zh)
        mix = '、'.join(f'{KIND_NAMES[k][2]} {n(c)} 条' for k, c in kinds.most_common())
        return [('哪些发布方在目录中的资源最多？', f'{lead}名下的已审核资源最多。'),
                ('发布方发布哪些类型的资源？', f'共有 {n(total)} 条已审核资源通过发布方关系指向这 {n(len(records))} 个发布方：{mix}。')]
    lead = series([f'{a(r, zh)} ({n(c)} resources)' for c, r in top], zh)
    mix = series([f'{n(c)} {KIND_NAMES[k][0 if c == 1 else 1]}' for k, c in kinds.most_common()], zh)
    return [('Which publishers have the most resources in the catalog?', f'{lead} have the most reviewed resources that name them as publisher.'),
            ('What kinds of resources do publishers release?', f'{n(total)} reviewed resources name one of these {n(len(records))} publishers: {mix}.')]


def survey_answers(records, view, zh):
    dated = sorted((r for r in records if record_date_text(r)), key=lambda r: record_date_text(r), reverse=True)[:3]
    topics = Counter(t for r in records for t in r['topics'] if t != 'survey').most_common(4)
    if zh:
        newest = series([f'{a(r, zh)}（{esc(record_date_text(r))}）' for r in dated], zh)
        common = '、'.join(f'{esc(topic_name(t, "zh"))}（{n(c)} 篇）' for t, c in topics)
        return [('最新的综述有哪些？', f'按记录日期，最新的综述是{newest}。'),
                ('综述最常涉及哪些主题？', f'最常见的主题标签是{common}。一篇综述可带多个主题标签。')]
    newest = series([f'{a(r, zh)} ({esc(record_date_text(r))})' for r in dated], zh)
    common = series([f'{esc(topic_name(t))} ({n(c)})' for t, c in topics], zh)
    return [('What are the newest surveys?', f'By recorded date, the newest are {newest}.'),
            ('Which topics do surveys cover most?', f'The most common topic tags are {common}. A survey can carry several topics.')]


def faqs(kind, records, view, *, zh):
    """Three to five (question, answer HTML) pairs for one category."""
    specific = {'benchmark': benchmark_answers, 'dataset': dataset_answers, 'model': model_answers, 'product': product_answers,
                'company': company_answers, 'survey': survey_answers}
    found = []
    if kind == 'company':
        found += company_answers(records, view, zh)
    elif kind == 'survey':
        found += survey_answers(records, view, zh)
        found += [mentioned_answer(kind, records, view, zh), platform_answer(kind, records, zh)]
    elif kind == 'product':
        found += [platform_answer(kind, records, zh)] + product_answers(records, view, zh)
    else:
        found += [mentioned_answer(kind, records, view, zh), platform_answer(kind, records, zh)]
        found += specific[kind](records, view, zh) if kind in specific else [paper_answer(kind, records, view, zh)]
        found += [license_answer(kind, records, zh)]
    if kind != 'survey':
        found.append(order_answer(kind, zh))
    found = [item for item in found if item][:5]
    return [(q, spaced(answer)) for q, answer in found] if zh else found


def faq_html(items, *, zh):
    heading = '常见问题' if zh else 'Questions'
    entries = ''.join(f'<details><summary>{esc(q)}{ic("down")}</summary><p>{answer}</p></details>' for q, answer in items)
    return f'<div class="cat-faq"><h2 id="faq-h">{heading}</h2><div class="faq">{entries}</div></div>'


def faq_schema(items, url, language):
    return {'@type': 'FAQPage', '@id': url + '#faq', 'url': url, 'inLanguage': language,
            'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': plain(answer)}} for q, answer in items]}


def definition(kind, zh):
    return DEFINITIONS[kind][1 if zh else 0]


def guide(kind, records, view, *, zh, snapshot, url):
    """The guide section and its FAQPage node for page 1 of a category."""
    items = faqs(kind, records, view, zh=zh)
    section = (f'<section class="wrap cat-guide" id="how-to-choose" aria-labelledby="choose-h"><div class="cat-intro">'
               f'{choose_table(kind, records, view, zh=zh, snapshot=snapshot)}{faq_html(items, zh=zh)}</div></section>')
    return section, faq_schema(items, url, 'zh-CN' if zh else 'en'), items


def guide_markdown(kind, records, view, *, zh, snapshot):
    """The same definition, table and questions for the category's Markdown twin."""
    rows = prominent(records, view)
    columns = columns_for(kind, rows, view)
    name_heading = KIND_NAMES[kind][2] if zh else KIND_NAMES[kind][0].capitalize()

    def md(markup):
        text = re.sub(r'<a href="([^"]+)">(.*?)</a>', lambda m: f'[{m[2]}]({SITE + m[1] if m[1].startswith("/") else m[1]})', markup)
        return html.unescape(re.sub(r'<[^>]+>', '', text)).replace('|', '\\|')

    lines = ['## 怎么选' if zh else '## How to choose', '',
             '| ' + ' | '.join([name_heading, *(HEADINGS[c][zh] for c in columns)]) + ' |', '|' + ' --- |' * (len(columns) + 1)]
    lines += ['| ' + ' | '.join([md(a(r, zh)), *(md(cell(c, r, view, zh)) for c in columns)]) + ' |' for r in rows]
    lines += ['', '## 常见问题' if zh else '## Questions', '']
    for q, answer in faqs(kind, records, view, zh=zh):
        lines += [f'### {q}', '', md(answer), '']
    return '\n'.join(lines).rstrip('\n')

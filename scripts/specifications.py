"""Evidence-linked dataset and benchmark profiles, preserving count units and scopes."""
from __future__ import annotations
import html
import json
import math
import urllib.parse
from field_labels import field_label

PROFILE_KEYS = {'benchmark': 'benchmark_protocol', 'dataset': 'dataset_profile'}
PREFIXES = {'exact': '', 'approximately': '≈ ', 'at-least': '≥ ', 'more-than': '> '}
# Rendered list fields, each mapped to whether it needs at least one entry.
PROFILE_LISTS = {'benchmark': {'focus': True, 'observations': False, 'actions': False}, 'dataset': {'supervision': True, 'modalities': False, 'formats': False, 'splits': False}}
PROFILE_TEXT = {'benchmark': ('evaluation', 'notes'), 'dataset': ('notes',)}
SETTINGS = ('interactive', 'offline', 'mixed')
COUNT_FIELDS = {'value', 'unit', 'qualifier', 'population', 'basis', 'evidence_url', 'reference_url'}


def validate_profiles(record):
    errors = []
    known_sources = {source.get('url') for source in record.get('evidence', [])}
    for kind, key in PROFILE_KEYS.items():
        profile = record.get('details', {}).get(key)
        if profile is None:
            continue
        if record.get('kind') != kind or record.get('review_status') != 'curated':
            errors.append(f'{key} requires a curated {kind} record')
        if not isinstance(profile, dict):
            errors.append(f'{key} must be an object'); continue
        if unknown := set(profile) - {'counts', 'evidence_urls', *PROFILE_LISTS[kind], *PROFILE_TEXT[kind], *(('setting',) if kind == 'benchmark' else ())}:
            errors.append(f'{key} has unknown fields ' + ', '.join(sorted(unknown)))
        for field, required in PROFILE_LISTS[kind].items():
            values = profile.get(field)
            if not isinstance(values, list) or (required and not values) or any(not isinstance(value, str) or not value.strip() for value in values) or len(set(values)) != len(values):
                errors.append(f'{key} {field} must be a {"non-empty " if required else ""}list of distinct non-empty strings')
        for field in PROFILE_TEXT[kind]:
            if not isinstance(profile.get(field), str):
                errors.append(f'{key} {field} must be a string')
        if kind == 'benchmark' and profile.get('setting') not in SETTINGS:
            errors.append(f'{key} setting must be one of ' + ', '.join(SETTINGS))
        sources = profile.get('evidence_urls', [])
        if not isinstance(sources, list) or not sources or any(not isinstance(url, str) or url not in known_sources for url in sources):
            errors.append(f'{key} references missing evidence receipts')
            sources = []
        elif len(set(sources)) != len(sources):
            errors.append(f'{key} has duplicate evidence receipts')
        counts = profile.get('counts')
        if not isinstance(counts, list):
            errors.append(f'{key} counts must be a list'); continue
        seen = set()
        for count in counts:
            if not isinstance(count, dict):
                errors.append(f'{key} count must be an object'); continue
            if unknown := set(count) - COUNT_FIELDS:
                errors.append(f'{key} count has unknown fields ' + ', '.join(sorted(unknown)))
            value = count.get('value')
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                errors.append(f'{key} count must be a finite nonnegative number')
            if not isinstance(count.get('qualifier'), str) or count['qualifier'] not in PREFIXES or count.get('basis') not in ('reported', 'computed'):
                errors.append(f'{key} count lacks a precision qualifier or counting basis')
            if not isinstance(count.get('unit'), str) or not count['unit'].strip() or not isinstance(count.get('population'), str) or not count['population'].strip():
                errors.append(f'{key} count lacks its unit or population')
                continue
            if count.get('evidence_url') not in sources:
                errors.append(f'{key} count lacks a linked primary source')
            reference = count.get('reference_url')
            if 'reference_url' in count:
                parsed = urllib.parse.urlsplit(reference) if isinstance(reference,str) else None
                if not parsed or parsed.scheme != 'https' or not parsed.netloc or parsed.username:
                    errors.append(f'{key} count has an invalid readable source link')
            grain = (count.get('unit'), count.get('population'))
            if grain in seen:
                errors.append(f'{key} has duplicate count grain')
            seen.add(grain)
    return errors


def esc(value):
    return html.escape(str(value), quote=True)


def safe_href(value):
    # Data-supplied links render on the site origin; any other scheme (javascript:, data:) would run there.
    parts = urllib.parse.urlsplit(str(value or ''))
    if parts.scheme not in {'https', 'http'} or not parts.netloc:
        raise ValueError(f'Refusing to render a non-web link: {value!r}')
    return esc(value)


def words(values, zh=False):
    if not values:
        return '未记录' if zh else 'Not recorded'
    return ('、' if zh else ', ').join(values)


def count_text(count):
    value = f'{count["value"]:,}'
    return f'{PREFIXES[count["qualifier"]]}{value} {count["unit"]} — {count["population"]}' + (' (computed)' if count['basis']=='computed' else '')


def counts_html(profile, zh=False):
    if not profile['counts']:
        return '<span class="unknown-value">' + ('未记录' if zh else 'Not recorded') + '</span>'
    source, label = ('来源', '来源：') if zh else ('source', 'Source for ')
    return '<ul class="measure-list">' + ''.join(f'<li>{esc(count_text(count))} <a href="{safe_href(count.get("reference_url") or count["evidence_url"])}" aria-label="{label}{esc(count["population"])}">{source}</a></li>' for count in profile['counts']) + '</ul>'


def selected_profiles(rows, kind):
    key = PROFILE_KEYS[kind]
    return sorted([row for row in rows if row['kind'] == kind and row['review_status'] == 'curated' and row['details'].get(key)], key=lambda row: row['name'].casefold())


def profile_export(rows, kind):
    key = PROFILE_KEYS[kind]
    selected = selected_profiles(rows, kind)
    return {
        'schema_version': 1,
        'kind': kind,
        'profile_count': len(selected),
        'curated_resource_count': sum(row['kind'] == kind and row['review_status'] == 'curated' for row in rows),
        'unit': 'resource profile; count observations retain their own units and populations',
        'limitations': 'Source-reviewed descriptions and reported or computed inventory counts. No performance ranking, independent reproduction, or global-completeness claim.',
        'records': [{
            'id': row['id'], 'name': row['name'], 'url': row['url'], 'environments': row['environments'],
            'profile': row['details'][key], 'licenses': row['licenses'],
            'evidence': [source for source in row['evidence'] if source['url'] in row['details'][key]['evidence_urls']],
        } for row in selected],
    }


def resource_profile_html(row, zh=False):
    key = PROFILE_KEYS.get(row['kind'])
    profile = row['details'].get(key) if key else None
    if not profile:
        return ''
    language = 'zh' if zh else 'en'
    label = lambda name: field_label(name, language)
    if row['kind'] == 'benchmark':
        facts = [(label('focus'), words(profile['focus'], zh)), (label('setting'), profile['setting']), (label('observations'), words(profile['observations'], zh)), (label('actions'), words(profile['actions'], zh)), (label('evaluation'), profile['evaluation'] or ('未记录' if zh else 'Not recorded'))]
    else:
        facts = [(label(name), words(profile[name], zh)) for name in ('supervision', 'modalities', 'formats', 'splits')]
    if zh:
        title = '评测协议' if row['kind'] == 'benchmark' else '数据集概况'
        scale, compare = '规模与计数单位', '比较已审阅的规格'
    else:
        title = 'Evaluation protocol' if row['kind'] == 'benchmark' else 'Dataset profile'
        scale, compare = 'Scale and counting units', 'Compare source-reviewed profiles'
    body = f'<h2>{title}</h2><dl class="page-facts">' + ''.join(f'<div><dt>{esc(name)}</dt><dd>{esc(value)}</dd></div>' for name, value in facts) + '</dl>'
    body += f'<h3>{scale}</h3>' + counts_html(profile, zh)
    body += '<p>' + esc(profile['notes']) + '</p><p><a href="/compare/' + ('benchmarks' if row['kind'] == 'benchmark' else 'datasets') + f'/">{compare}</a></p>'
    return body


def comparison_body(rows, kind, link_for, zh=False, env_label=None):
    key = PROFILE_KEYS[kind]
    selected = selected_profiles(rows, kind)
    total = sum(row['kind'] == kind and row['review_status'] == 'curated' for row in rows)
    plural = 'benchmarks' if kind == 'benchmark' else 'datasets'
    env_label = env_label or (lambda env: env)
    if zh:
        prefix = '/zh'
        noun = '评测基准' if kind == 'benchmark' else '数据集'
        title = 'GUI 智能体评测基准协议对比' if kind == 'benchmark' else 'GUI 智能体训练数据集对比'
        purpose = '根据要测量的能力，对照任务设置、可用观测、动作接口与评测方式。' if kind == 'benchmark' else '根据训练目标，对照监督信号、模态、数据格式、数据划分与许可证。'
        body = f'<div class="eyebrow">来源审阅对比</div><h1>{title}</h1><p class="answer-lead">{purpose}</p><p>目录中 {total} 个已审阅{noun}里，{len(selected)} 个附有规格档案。其余条目见<a href="{prefix}/categories/{kind}/">完整目录</a>。空缺值表示尚未记录。</p>'
        body += '<p>计数保留各自的单位与子集；除标注为计算得出的数值外，均为发布方报告的数字。不同资源可能描述同一项目的不同部分。</p>'
        search_label, placeholder, environment_label, every_environment = '搜索规格档案', '名称、接口、监督方式或格式…', '运行环境', '全部运行环境'
        status = f'显示 {len(selected)} / {len(selected)} 个规格档案。'
        columns = ['资源 / 任务设置', '观测 / 动作', '评测方式', '规模与范围'] if kind == 'benchmark' else ['资源 / 监督信号', '模态 / 格式', '数据划分 / 数据许可证', '规模与范围']
        scroll, table_label = '左右滚动表格可查看全部列。', '规格对比表'
        observe, act, fmt, data_license, notes_label, evidence_label = '观测', '动作 / 输出', '格式', '数据许可证', '范围与来源备注', '一手证据'
        not_recorded = '未记录'
    else:
        prefix = ''
        title = 'Compare GUI-agent benchmark protocols' if kind == 'benchmark' else 'Compare GUI-agent training datasets'
        purpose = 'Match the task setting, available observations, action interface, and evaluator to the capability you need to measure.' if kind == 'benchmark' else 'Match supervision, modalities, data format, splits, and license to the training objective you need.'
        body = f'<div class="eyebrow">SOURCE-REVIEWED COMPARISON</div><h1>{title}</h1><p class="answer-lead">{purpose}</p><p>{len(selected)} profiles are available among {total} reviewed {plural} in the catalog. Remaining entries are available in the <a href="/categories/{kind}/">full directory</a>. Missing values mean not recorded.</p>'
        body += '<p>Counts retain their units and subsets; figures are publisher-reported unless marked computed. Different resources can describe parts of the same project.</p>'
        search_label, placeholder, environment_label, every_environment = 'Search profiles', 'Name, interface, supervision, or format…', 'Environment', 'All environments'
        status = f'Showing {len(selected)} of {len(selected)} profiles.'
        columns = ['Resource / setting', 'Observations / actions', 'Evaluation', 'Scale with scope'] if kind == 'benchmark' else ['Resource / supervision', 'Modalities / format', 'Splits / data license', 'Scale with scope']
        scroll, table_label = 'Scroll the table sideways to see all columns.', 'Profile comparison table'
        observe, act, fmt, data_license, notes_label, evidence_label = 'Observe', 'Act / output', 'Format', 'Data license', 'Scope and source notes', 'Primary evidence'
        not_recorded = 'Not recorded'
    environments = sorted({env for row in selected for env in row['environments']})
    body += f'<div class="compare-controls"><div><label for="compare-query">{search_label}</label><input id="compare-query" type="search" placeholder="{placeholder}"></div><div><label for="compare-environment">{environment_label}</label><select id="compare-environment"><option value="">{every_environment}</option>' + ''.join(f'<option value="{esc(env)}">{esc(env_label(env))}</option>' for env in environments) + '</select></div></div>'
    marker = ' data-lang="zh"' if zh else ''
    body += f'<p id="compare-results" role="status" aria-live="polite"{marker}>{status}</p>'
    body += f'<p class="table-help">{scroll}</p><div class="table-scroll compare-scroll" tabindex="0" aria-label="{table_label}"><table class="coverage-table compare-table"><thead><tr>' + ''.join('<th scope="col">' + label + '</th>' for label in columns) + '</tr></thead><tbody>'
    for row in selected:
        profile = row['details'][key]
        visible_values = [' '.join(value) if isinstance(value,list) else str(value) for key,value in profile.items() if key not in {'counts','evidence_urls'}]
        text = ' '.join([row['name'], *row['environments'], *visible_values, *(count_text(count) for count in profile['counts'])])
        shown_environments = [env_label(env) for env in row['environments']] if zh else row['environments']
        body += f'<tr data-profile-row data-environments="{esc(" ".join(row["environments"]))}" data-search="{esc(text)}"><td><a class="compare-name" href="{link_for(row)}">{esc(row["name"])}</a><div>{esc(words(shown_environments, zh))}</div>'
        if kind == 'benchmark':
            body += '<p>' + esc(words(profile['focus'], zh)) + '<br>' + esc(profile['setting']) + f'</p></td><td><strong>{observe}</strong>' + esc(words(profile['observations'], zh)) + f'<strong>{act}</strong>' + esc(words(profile['actions'], zh)) + '</td><td>' + esc(profile['evaluation'] or not_recorded) + '</td>'
        else:
            license = row['licenses']['data']
            declaration = f'<a href="{safe_href(license["url"])}">{esc(words(license["declared"], zh) if isinstance(license["declared"],list) else license["declared"])}</a>' if license else not_recorded
            body += '<p>' + esc(words(profile['supervision'], zh)) + '</p></td><td>' + esc(words(profile['modalities'], zh)) + f'<strong>{fmt}</strong>' + esc(words(profile['formats'], zh)) + '</td><td>' + esc(words(profile['splits'], zh)) + f'<strong>{data_license}</strong>' + declaration + '</td>'
        # Evidence already linked as a count source in this row is not repeated; the table stays light enough to scroll.
        linked = {count.get('reference_url') or count['evidence_url'] for count in profile['counts']}
        evidence = [url for url in profile['evidence_urls'] if url not in linked]
        body += '<td>' + counts_html(profile, zh) + f'<details><summary>{notes_label}</summary>' + esc(profile['notes']) + ''.join(f'{" " if index==0 else " · "}<a href="{safe_href(url)}">{evidence_label} {index+1}</a>' for index,url in enumerate(evidence)) + '</details></td></tr>'
    other = 'datasets' if kind == 'benchmark' else 'benchmarks'
    if zh:
        body += '</tbody></table></div><p>各资源页面列有来源时间戳、内容指纹，以及分别记录的代码、数据与权重许可证。</p>'
        body += f'<p><a href="/downloads/{plural}-profiles.json">下载这些规格档案（JSON）</a> · <a href="/zh/data/">完整目录与 SQLite</a> · <a href="/zh/compare/{other}/">比较{"数据集" if kind=="benchmark" else "评测基准"}</a></p><script type="module" src="/compare.js"></script>'
        return body
    body += '</tbody></table></div><p>Use each resource page for source timestamps, content fingerprints, and separate code, data, and weight licenses.</p>'
    body += f'<p><a href="/downloads/{plural}-profiles.json">Download these profiles as JSON</a> · <a href="/data/">Complete catalog and SQLite</a> · <a href="/compare/{other}/">Compare {other}</a></p><script type="module" src="/compare.js"></script>'
    return body

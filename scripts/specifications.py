"""Evidence-linked dataset and benchmark profiles, preserving count units and scopes."""
from __future__ import annotations
import html
import json
import math
import urllib.parse

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


def words(values):
    return ', '.join(values) if values else 'Not recorded'


def count_text(count):
    value = f'{count["value"]:,}'
    return f'{PREFIXES[count["qualifier"]]}{value} {count["unit"]} — {count["population"]}' + (' (computed)' if count['basis']=='computed' else '')


def counts_html(profile):
    if not profile['counts']:
        return '<span class="unknown-value">Not recorded</span>'
    return '<ul class="measure-list">' + ''.join(f'<li>{esc(count_text(count))} <a href="{safe_href(count.get("reference_url") or count["evidence_url"])}" aria-label="Source for {esc(count["population"])}">source</a></li>' for count in profile['counts']) + '</ul>'


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


def resource_profile_html(row):
    key = PROFILE_KEYS.get(row['kind'])
    profile = row['details'].get(key) if key else None
    if not profile:
        return ''
    if row['kind'] == 'benchmark':
        facts = [('Focus', words(profile['focus'])), ('Setting', profile['setting']), ('Observations', words(profile['observations'])), ('Actions / outputs', words(profile['actions'])), ('Evaluation', profile['evaluation'] or 'Not recorded')]
    else:
        facts = [('Supervision', words(profile['supervision'])), ('Modalities', words(profile['modalities'])), ('Formats', words(profile['formats'])), ('Splits', words(profile['splits']))]
    title = 'Evaluation protocol' if row['kind'] == 'benchmark' else 'Dataset profile'
    body = f'<h2>{title}</h2><dl class="page-facts">' + ''.join(f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>' for label, value in facts) + '</dl>'
    body += '<h3>Scale and counting units</h3>' + counts_html(profile)
    body += '<p>' + esc(profile['notes']) + '</p><p><a href="/compare/' + ('benchmarks' if row['kind'] == 'benchmark' else 'datasets') + '/">Compare source-reviewed profiles</a></p>'
    return body


def comparison_body(rows, kind, link_for):
    key = PROFILE_KEYS[kind]
    selected = selected_profiles(rows, kind)
    total = sum(row['kind'] == kind and row['review_status'] == 'curated' for row in rows)
    plural = 'benchmarks' if kind == 'benchmark' else 'datasets'
    title = 'Compare GUI-agent benchmark protocols' if kind == 'benchmark' else 'Compare GUI-agent training datasets'
    purpose = 'Match the task setting, available observations, action interface, and evaluator to the capability you need to measure.' if kind == 'benchmark' else 'Match supervision, modalities, data format, splits, and license to the training objective you need.'
    body = f'<div class="eyebrow">SOURCE-REVIEWED COMPARISON</div><h1>{title}</h1><p class="answer-lead">{purpose}</p><p>{len(selected)} profiles are available among {total} reviewed {plural} in the catalog. Remaining entries are available in the <a href="/categories/{kind}/">full directory</a>. Missing values mean not recorded.</p>'
    body += '<p>Counts retain their units and subsets; figures are publisher-reported unless marked computed. Different resources can describe parts of the same project.</p>'
    from paper_library import PLATFORMS  # imported here: paper_library itself imports this module
    label = lambda env: PLATFORMS.get(env, ('Not specified' if env == 'unspecified' else env,))[0]
    environments = sorted({env for row in selected for env in row['environments']}, key=lambda env: label(env).casefold())
    body += '<div class="compare-controls"><div><label for="compare-query">Search profiles</label><input id="compare-query" type="search" placeholder="Name, interface, supervision, or format…"></div><div><label for="compare-environment">Environment</label><select id="compare-environment"><option value="">All environments</option>' + ''.join(f'<option value="{esc(env)}">{esc(label(env))}</option>' for env in environments) + '</select></div></div>'
    body += f'<p id="compare-results" role="status" aria-live="polite">Showing {len(selected)} of {len(selected)} profiles.</p>'
    columns = ['Resource / setting', 'Observations / actions', 'Evaluation', 'Scale with scope'] if kind == 'benchmark' else ['Resource / supervision', 'Modalities / format', 'Splits / data license', 'Scale with scope']
    body += '<p class="table-help compare-help">Scroll the table sideways to see all columns.</p><div class="table-scroll compare-scroll" tabindex="0" aria-label="Profile comparison table"><table class="coverage-table compare-table"><thead><tr>' + ''.join('<th scope="col">' + label + '</th>' for label in columns) + '</tr></thead><tbody>'
    for row in selected:
        profile = row['details'][key]
        visible_values = [' '.join(value) if isinstance(value,list) else str(value) for key,value in profile.items() if key not in {'counts','evidence_urls'}]
        platforms = [label(env) for env in row['environments']]
        text = ' '.join([row['name'], *row['environments'], *platforms, *visible_values, *(count_text(count) for count in profile['counts'])])
        # data-label names each cell's column for the stacked phone layout, where the header row is hidden.
        cell = lambda index: f'<td data-label="{esc(columns[index])}">'
        body += f'<tr data-profile-row data-environments="{esc(" ".join(row["environments"]))}" data-search="{esc(text)}">{cell(0)}<a href="{link_for(row)}"><strong>{esc(row["name"])}</strong></a><div>{esc(words(platforms))}</div>'
        if kind == 'benchmark':
            body += '<p>' + esc(words(profile['focus'])) + '<br>Setting: ' + esc(profile['setting']) + '</p></td>' + cell(1) + '<strong>Observe</strong><br>' + esc(words(profile['observations'])) + '<br><strong>Act / output</strong><br>' + esc(words(profile['actions'])) + '</td>' + cell(2) + esc(profile['evaluation'] or 'Not recorded') + '</td>'
        else:
            license = row['licenses']['data']
            declaration = f'<a href="{safe_href(license["url"])}">{esc(words(license["declared"]) if isinstance(license["declared"],list) else license["declared"])}</a>' if license else 'Not recorded'
            body += '<p>' + esc(words(profile['supervision'])) + '</p></td>' + cell(1) + esc(words(profile['modalities'])) + '<br><strong>Format</strong><br>' + esc(words(profile['formats'])) + '</td>' + cell(2) + esc(words(profile['splits'])) + '<br><strong>Data license</strong><br>' + declaration + '</td>'
        body += cell(3) + counts_html(profile) + '<details><summary>Scope and source notes</summary><p>' + esc(profile['notes']) + '</p><ul>' + ''.join(f'<li><a href="{safe_href(url)}">Primary evidence {index+1}</a></li>' for index,url in enumerate(profile['evidence_urls'])) + '</ul></details></td></tr>'
    body += '</tbody></table></div><p>Use each resource page for source timestamps, content fingerprints, and separate code, data, and weight licenses.</p>'
    body += f'<p><a href="/downloads/{plural}-profiles.json">Download these profiles as JSON</a> · <a href="/data/">Complete catalog and SQLite</a> · <a href="/compare/{"datasets" if kind=="benchmark" else "benchmarks"}/">Compare {"datasets" if kind=="benchmark" else "benchmarks"}</a></p><script type="module" src="/compare.js"></script>'
    return body

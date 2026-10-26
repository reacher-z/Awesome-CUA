"""How to cite the AwesomeCUA catalog itself, built from CITATION.cff."""
import html
from pathlib import Path

from citation_file import read_citation_file

CITATION_FILE = Path(__file__).resolve().parents[1] / 'CITATION.cff'
BIBTEX_PATH = '/downloads/awesomecua.bib'


def catalog_bibtex(snapshot, cff=None):
    # The README carries the same entry; only the year follows the evidence snapshot. Pinning belongs in the prose.
    cff = cff or read_citation_file(CITATION_FILE)
    repository = cff['repository-code']
    fields = [('title', cff['title']),
              ('author', ' and '.join(f"{a['family-names']}, {a['given-names']}" for a in cff['authors'])),
              ('year', snapshot[:4]), ('url', cff['url']), ('howpublished', '\\url{' + repository + '}'),
              ('note', 'Versioned data releases: ' + repository + '/releases')]
    return '@misc{awesomecua,\n' + ',\n'.join(f'  {key:<12} = {{{value}}}' for key, value in fields) + '\n}\n'


def cite_section(bibtex, repository, language='en'):
    zh = language == 'zh'
    releases = html.escape(repository + '/releases', quote=True)
    heading = '引用 AwesomeCUA' if zh else 'Cite AwesomeCUA'
    lead = (f'使用本目录时，请按以下条目引用。数据随每次扫描更新，请同时记录所用的<a href="{releases}">发布标签</a>或提交（<code>git rev-parse HEAD</code>）。'
            if zh else f'If you use the catalog, cite it as below. The data changes with every scan, so also record the <a href="{releases}">release tag</a> or commit (<code>git rev-parse HEAD</code>) you used.')
    links = (f'<a href="{BIBTEX_PATH}" download>{"下载 BibTeX" if zh else "Download BibTeX"}</a> · '
             f'<a href="{html.escape(repository, quote=True)}/blob/main/CITATION.cff">CITATION.cff</a>')
    return (f'<section class="catalog-citation" id="cite" aria-labelledby="cite-heading"><h2 id="cite-heading">{heading}</h2><p>{lead}</p>'
            f'<pre class="command-block"><code>{html.escape(bibtex.rstrip())}</code></pre><p>{links}</p></section>')

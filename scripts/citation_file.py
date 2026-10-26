"""Read the top-level facts of CITATION.cff without a YAML dependency."""
import re
from pathlib import Path

REQUIRED = ('title', 'license', 'repository-code', 'url')


def read_citation_file(path):
    # Only flat scalars and the authors list are read; CI has no YAML parser, and GitHub validates the full file.
    text = Path(path).read_text(encoding='utf-8')
    facts = {key: value.strip().strip('"') for key, value in re.findall(r'^([a-z][a-z-]*): *(\S.*)$', text, re.M)}
    block = re.search(r'^authors:\n((?:[ -] .*\n)+)', text, re.M)
    authors = [{key: value.strip().strip('"') for key, value in re.findall(r'([a-z-]+): *(.+)', item)}
               for item in re.split(r'^  - ', block[1], flags=re.M)[1:]] if block else []
    if not authors or not all(author.get('given-names') and author.get('family-names') for author in authors):
        raise ValueError('CITATION.cff must list authors with given and family names')
    missing = [key for key in REQUIRED if not facts.get(key)]
    if missing:
        raise ValueError('CITATION.cff is missing ' + ', '.join(missing))
    return {**facts, 'authors': authors}

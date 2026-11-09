"""Reconcile generated page files against the current publication manifest."""
from pathlib import Path


# /survey companions are owned by its bundle manifest, not by these global basenames.
# prepare_publication validates/reconciles them through survey_bundle before copying.
MANAGED_ROOTS = ('resources', 'categories', 'guides', 'topics', 'zh/topics', 'badges')
MANAGED_FILES = frozenset({'index.html', 'index.md', 'record.json', 'citation.bib', 'citation.csl.json',
                           'publication-citation.bib', 'publication-citation.csl.json',
                           'featured-by-awesomecua-laurel.svg', 'featured-by-awesomecua.svg', 'featured-by-awesomecua-dark.svg', 'awesomecua-featured-seal.svg'})


def reconcile_generated_pages(directory, pages):
    directory = Path(directory)
    expected = {item['path'] for item in pages}
    for name in MANAGED_ROOTS:
        root = directory / name
        if root.is_symlink():
            raise ValueError('Generated page roots must not be symbolic links: ' + name)
        if not root.exists():
            continue
        for file in root.rglob('*'):
            if file.name not in MANAGED_FILES or not file.is_file():
                continue
            page = '/' + file.parent.relative_to(directory).as_posix() + '/'
            if page not in expected:
                file.unlink()

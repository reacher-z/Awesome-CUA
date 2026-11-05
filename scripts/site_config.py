"""Public origin of the AwesomeCUA website, shared by every builder and publication script."""
from urllib.parse import urlsplit

# Canonical origin, without a trailing slash. Canonical links, Open Graph tags, sitemaps, feeds,
# structured data, llms.txt, citation URLs and schema identifiers are all built from it.
SITE = 'https://awesomecua.com'
HOST = urlsplit(SITE).hostname

# Former canonical origins. GitHub Pages redirects them to SITE with the same path and query.
# Content reviewed under one of them, such as the frozen survey bundle, stays publishable until it is rebuilt.
FORMER_SITES = ('https://awesomecua.github.io',)

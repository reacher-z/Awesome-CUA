"""Public origin and schedule wording of the AwesomeCUA website, shared by every builder and publication script."""
from urllib.parse import urlsplit

# Canonical origin, without a trailing slash. Canonical links, Open Graph tags, sitemaps, feeds,
# structured data, llms.txt, citation URLs and schema identifiers are all built from it.
SITE = 'https://awesomecua.com'
HOST = urlsplit(SITE).hostname

# Former canonical origins. GitHub Pages redirects them to SITE with the same path and query.
# Content reviewed under one of them, such as the frozen survey bundle, stays publishable until it is rebuilt.
FORMER_SITES = ('https://awesomecua.github.io',)


def scan_schedule(config):
    """Express the configured UTC slots in a short public phrase."""
    times, zone = config['scan_times_local'], config['timezone']
    minutes = {time.split(':')[1] for time in times}
    if len(times) == 24 and len(minutes) == 1:
        return f'every hour at minute {int(minutes.pop())} {zone}'
    if len(times) == 3:
        return 'at ' + ', '.join(times[:-1]) + ' and ' + times[-1] + ' ' + zone
    return 'at ' + ', '.join(times) + ' ' + zone

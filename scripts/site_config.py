"""Public origin and schedule wording of the AwesomeCUA website, shared by every builder and publication script."""
from urllib.parse import urlsplit

# Canonical origin, without a trailing slash. Canonical links, Open Graph tags, sitemaps, feeds,
# structured data, llms.txt, citation URLs and schema identifiers are all built from it.
SITE = 'https://awesomecua.com'
HOST = urlsplit(SITE).hostname

# Former canonical origins retained for publication and notification-state compatibility.
# This list does not assert HTTP redirects; a former host may serve a mirror with canonical links to SITE.
# Content reviewed under one of them, such as the frozen survey bundle, stays publishable until it is rebuilt.
FORMER_SITES = ('https://awesomecua.github.io',)


def scan_schedule(config):
    """The configured scan times as a page states them: one phrase for an hourly schedule, not 24 times in a row."""
    times, zone = config['scan_times_local'], config['timezone']
    minutes = {time.split(':')[1] for time in times}
    if len(times) == 24 and len(minutes) == 1:
        return f'every hour at minute {int(minutes.pop())} {zone}'
    return 'at ' + ', '.join(times) + ' ' + zone

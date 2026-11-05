# Security policy

## Scope

Report vulnerabilities in:

- this repository's scripts, schemas, and data pipeline (`scripts/`, `schemas/`, `data/`);
- its GitHub Actions workflows (`.github/workflows/`) and the website publication workflow (`automation/publish.yml`), including token permissions and injection through scanned metadata;
- the website at https://awesomecua.com/ (the former awesomecua.github.io address redirects there), built from this repository by `scripts/build_site.py` and the client code in `web/`. Third-party metadata is rendered into its HTML and JavaScript, so cross-site scripting and unsafe links are in scope;
- credentials or tokens exposed in the git history.

Vulnerabilities in linked papers, repositories, models, or datasets belong with their publishers. Report incorrect catalog facts through the [resource issue form](https://github.com/reacher-z/Awesome-CUA/issues/new?template=resource.yml).

Only the current `main` branch and the live website are supported.

## Reporting a vulnerability

Report privately through GitHub's private vulnerability reporting: open the repository's **Security** tab and choose **Report a vulnerability**, or go to https://github.com/reacher-z/Awesome-CUA/security/advisories/new. Do not open a public issue, pull request, or discussion about a vulnerability.

If that form is unavailable, open a [bug report](https://github.com/reacher-z/Awesome-CUA/issues/new?template=bug.yml) titled "Security contact request" and write only "Details withheld" in it. A maintainer will arrange a private channel.

## What to include

- The affected file, workflow, or page URL, and the commit you tested.
- Steps to reproduce, such as a crafted catalog record, URL, or workflow input.
- The impact you observed or expect.
- A suggested fix, if you have one.

## What to expect

The maintainer aims to acknowledge a report within 7 days and to share an assessment and remediation plan within 30 days. Fixes are published through a GitHub security advisory that credits the reporter, unless you ask not to be named.

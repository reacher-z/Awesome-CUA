#!/usr/bin/env python3
"""Check a pull request's commits and description against the repository's commit rules.

Every pull request: no commit message carries a ``Co-Authored-By: Claude`` trailer
or "Generated with Claude".
Pull requests opened by the maintainer account or a bot: every commit's author and
committer is the maintainer account or a GitHub bot; a ``GitHub <noreply@github.com>``
committer is accepted when the author passes.
Pull requests opened by the maintainer account: the description has a ``Codex review``
(or ``Independent review``) heading with text under it, or the line "independent reviewer
agent (Codex usage limit until YYYY-MM-DD)".

Failure messages name the commit SHA and the field, never a person's name.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

MAINTAINER = 'reacher-z'
MAINTAINER_EMAILS = frozenset({'reacher-z@users.noreply.github.com', '68239571+reacher-z@users.noreply.github.com'})
GITHUB_COMMITTER = ('GitHub', 'noreply@github.com')
BOT_EMAIL = re.compile(r'(\d+)\+(.+)@users\.noreply\.github\.com')
TRAILER = re.compile(r'^[ \t]*co-authored-by:[^\n]*(?:\bclaude\b|noreply@anthropic\.com)', re.I | re.M)
# The usual footer is "Generated with [Claude Code](...)": allow the link bracket.
GENERATED = re.compile(r'generated[ \t]+with[ \t]+\[?[ \t]*claude', re.I)
HEADING = re.compile(r'^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$')
CLOSING_HASHES = re.compile(r'(?:^|[ \t]+)#+$')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
FENCE_CLOSE = re.compile(r'^ {0,3}(`{3,}|~{3,})[ \t]*$')
SETEXT = re.compile(r'^ {0,3}(=+|-+)[ \t]*$')
# A comment that opens a line hides everything up to the line with `-->`, or the rest of the description.
COMMENT_BLOCK = re.compile(r'^ {0,3}<!--')
# Inside a line, closed comments are hidden and code spans are shown as written.
INLINE = re.compile(r'(`+).*?\1|<!--.*?-->')
# Markup that leaves no readable text: list and quote markers, tags, entities and escapes.
MARKUP = re.compile(r'^[ \t>]*(?:[-*+]|\d+[.)])?[ \t]|<[^>]*>|&#?\w+;|\\')
RULE = re.compile(r'^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$')
# Lines that stay what they are above a `---` underline: list items, quotes and table rows.
NOT_PARAGRAPH = re.compile(r'^ {0,3}(?:[-*+][ \t]|\d+[.)][ \t]|>|\|)')
# While Codex is unavailable an independent reviewer agent reviews instead, under either heading or as this line.
REVIEW_HEADINGS = frozenset({'codex review', 'independent review'})
SUBSTITUTE = re.compile(r'independent reviewer agent \(codex usage limit until \d{4}-\d{2}-\d{2}\)', re.I)


def is_bot_login(login, user_type=None):
    return user_type == 'Bot' or str(login or '').endswith('[bot]')


def is_maintainer(person):
    return person.get('name') == MAINTAINER and str(person.get('email') or '').lower() in MAINTAINER_EMAILS


def is_bot(person):
    name, email = str(person.get('name') or ''), str(person.get('email') or '')
    match = BOT_EMAIL.fullmatch(email)
    return name.endswith('[bot]') and bool(match) and match.group(2) == name


def short(sha):
    return str(sha or '')[:12] or 'unknown'


def message_problems(commit):
    message = commit.get('commit', {}).get('message') or ''
    problems = []
    if TRAILER.search(message):
        problems.append(f'commit {short(commit.get("sha"))}: message has a Co-Authored-By: Claude trailer')
    if GENERATED.search(message):
        problems.append(f'commit {short(commit.get("sha"))}: message contains "Generated with Claude"')
    return problems


def identity_problems(commit):
    data = commit.get('commit', {})
    author, committer = data.get('author') or {}, data.get('committer') or {}
    sha = short(commit.get('sha'))
    problems = []
    author_ok = is_maintainer(author) or is_bot(author)
    if not author_ok:
        problems.append(f'commit {sha}: author is not {MAINTAINER} or a GitHub bot')
    github = (committer.get('name'), str(committer.get('email') or '').lower()) == GITHUB_COMMITTER
    if not (is_maintainer(committer) or is_bot(committer) or github and author_ok):
        problems.append(f'commit {sha}: committer is not {MAINTAINER}, a GitHub bot, or GitHub for a passing author')
    return problems


def blocks(body):
    """(kind, level, text) per line as GitHub renders it: ATX and setext headings, fence markers, fenced code, rules
    and other lines, with HTML comments removed; code is never a heading and its comments stay."""
    tokens, fence, comment = [], None, False
    for line in (body or '').replace('\r\n', '\n').split('\n'):
        if comment:
            comment = '-->' not in line
            continue
        if fence:
            close = FENCE_CLOSE.match(line)
            if close and close.group(1)[0] == fence[0] and len(close.group(1)) >= len(fence):
                fence = None
                tokens.append(('fence', None, line))
            else:
                tokens.append(('code', None, line))
            continue
        if COMMENT_BLOCK.match(line):
            comment = '-->' not in line[line.index('<!--') + 4:]
            continue
        marker = FENCE.match(line)
        if marker and not (marker.group(1)[0] == '`' and '`' in marker.group(2)):
            fence = marker.group(1)
            tokens.append(('fence', None, line))
            continue
        line = INLINE.sub(lambda match: match.group(0) if match.group(1) else '', line)
        heading, underline = HEADING.match(line), SETEXT.match(line)
        previous = tokens[-1][2] if tokens and tokens[-1][0] == 'text' else ''
        if heading:
            tokens.append(('heading', len(heading.group(1)), CLOSING_HASHES.sub('', heading.group(2) or '')))
        elif (underline and previous.strip() and not previous.startswith(('    ', '\t'))
              and not NOT_PARAGRAPH.match(previous)):
            tokens[-1] = ('heading', 1 if underline.group(1)[0] == '=' else 2, previous.strip())
        elif RULE.match(line):
            tokens.append(('rule', None, line))
        else:
            tokens.append(('text', None, line))
    return tokens


def heading_words(text):
    """A heading as read: emphasis and code marks dropped, links unwrapped, a trailing colon ignored."""
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)
    return re.sub(r'[*_`]', '', text).strip().rstrip(':').strip().lower()


def readable(text):
    return bool(re.search(r'\w', MARKUP.sub('', text)))


def codex_review_text(body):
    """Readable text under the first review heading, up to the next heading of the same or a higher level; None without one."""
    level, collected = None, []
    for kind, depth, text in blocks(body):
        if kind == 'heading' and level is not None and depth <= level:
            break
        if kind == 'heading' and level is None and heading_words(text) in REVIEW_HEADINGS:
            level = depth
        elif level is not None and (kind == 'text' and readable(text) or kind == 'code' and text.strip()):
            # Sub-headings, rules, fence markers and empty markup are not review text.
            collected.append(text)
    return None if level is None else '\n'.join(collected).strip()


def has_substitute_line(body):
    return any(kind in ('text', 'code', 'heading') and SUBSTITUTE.search(text) for kind, _, text in blocks(body))


def check(pull_request, commits):
    author = pull_request.get('user') or {}
    login = author.get('login')
    problems = []
    for commit in commits:
        problems += message_problems(commit)
    if login == MAINTAINER or is_bot_login(login, author.get('type')):
        for commit in commits:
            problems += identity_problems(commit)
    if login == MAINTAINER:
        body = pull_request.get('body') or ''
        review = codex_review_text(body)
        if has_substitute_line(body):
            pass
        elif review is None:
            problems.append('description: no "Codex review" heading')
        elif not review:
            problems.append('description: the "Codex review" heading has no text under it')
    return problems


def read_commits(path):
    """Commits from `gh api --paginate`: one or more concatenated JSON arrays."""
    text, decoder, position, commits = Path(path).read_text(encoding='utf-8'), json.JSONDecoder(), 0, []
    while True:
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            return commits
        page, position = decoder.raw_decode(text, position)
        if not isinstance(page, list):
            raise ValueError('Expected a JSON array of pull request commits')
        commits += page


def main(argv=None):
    parser = argparse.ArgumentParser(description='Check pull request commit identities, trailers and the Codex review section.')
    parser.add_argument('--commits', required=True, help='JSON from GET /repos/{repo}/pulls/{number}/commits (paginated)')
    parser.add_argument('--event', default=os.environ.get('GITHUB_EVENT_PATH'), help='pull_request event payload (default: $GITHUB_EVENT_PATH)')
    args = parser.parse_args(argv)
    if not args.event:
        parser.error('--event or GITHUB_EVENT_PATH is required')
    pull_request = json.loads(Path(args.event).read_text(encoding='utf-8')).get('pull_request') or {}
    commits = read_commits(args.commits)
    if not commits:
        print('::error::No pull request commits were read.')
        return 1
    expected = pull_request.get('commits')
    if isinstance(expected, int) and len(commits) < expected:
        # The pull request commits API lists at most 250 commits.
        print(f'::error::Read {len(commits)} of the pull request\'s {expected} commits; split it into pull requests of at most 250 commits.')
        return 1
    problems = check(pull_request, commits)
    if problems:
        print('Commit rules: commits carry no Co-Authored-By: Claude trailer or "Generated with Claude" text; '
              f'pull requests from {MAINTAINER} or a bot have only {MAINTAINER} or bot authors and committers; '
              f'pull requests from {MAINTAINER} have a "Codex review" section in the description.')
        for problem in problems:
            print('::error::' + problem)
        return 1
    print(f'Checked {len(commits)} commits and the description.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

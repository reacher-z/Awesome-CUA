#!/usr/bin/env python3
"""Fail when a protected personal name appears in tracked files or a built website.

The protected forms are stored only as a random salt and salted SHA-256 digests of
normalized word grams, never as plaintext; docs/maintenance.md#protected-names
explains the policy.

Text is folded to lowercase ASCII after decoding accents, full-width letters, HTML
entities, JSON escapes and percent-encoding. The grams are single words, adjacent
word pairs (spaced and joined), given names written as two syllables, account
suffixes and "Family, Given" pairs; given and family fields of CFF, CSL and
schema.org objects are paired as well. As in a plain-text search, punctuation and
spacing between two words join them, so each protected family name is also checked
against the words on either side of it, across list entries and quotes, and in markup
also with each tag read as a space, so a name split across elements matches.
Initials with a family name are not matched.

Usage:
  python3 scripts/privacy_guard.py            # tracked files, plus dist/site when built
  python3 scripts/privacy_guard.py PATH...    # these files or directory trees
  python3 scripts/privacy_guard.py --omit-protected-authors   # rewrite data/papers.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import html
import multiprocessing
from operator import methodcaller
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import unicodedata
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SALT = bytes.fromhex('9b474cd8588bf6ed780d3aa8009b2e71')
# sha256(SALT + gram) of each protected normalized gram.
PROTECTED = frozenset(bytes.fromhex(value) for value in (
    '1b3c6b6d908e85739a6cc7ef5d96569261f86986403120bed49ec6d02e2a9afc',
    '6764c0398d67a3a791958608d17120d10622ee879119288dbd4fb6031ee3997c',
    '7924409998d6e2806be03b153008fc2e59fec4edf02dad8d6eda4dc650b90486',
    '798857aa234d193b762092bf23aa3c52d9acf1adbdfd90ab45eb1ef6e0c43f8c',
    '84529e82e6578f40d12832dd2c621f1f29bf353997af2bf797a69110a795a49e',
    '84c2cf4db12a0294f71aa1818c6deb4e8ffa3db42bde49151759e7079e468e7b',
    'a20b5e49d2d7c4067ebdd24c882acfe5b1fc1043269ec2dcb46a9098e23d1901',
    'b5c84bf8b9a371458539a5f6abb4c4592fafd859f22f20acfa6fc1f10f3e72e6',
    'b5f53af8b6e7b59ef29fbaf92d9f7dad940d22cf434e97eff149dc03f5c10c50',
    'b73066ccbdec28f3d8bab0dc24e14c4dbedc377b177b99cf51a26d7953eca3d3',
    'c416862463852c98ac3747c8ac231df292c6ca2d8a33700f3f4f3706dc02457b',
    'c4fea96d6006fd986281c14af25409e5bec073d0d805d5078d82d71db2a85236',
    'f5a95deb946bcfd2a340f6c0c94d61871fa53a99c3415d73db2f5a74a852e926',
))
# sha256(SALT + SURNAME_DOMAIN + word) of the protected family names, so a name split by any
# punctuation (two neighbouring list entries, a JSON array) still matches as a plain-text search would.
SURNAME_DOMAIN = b'\x00family-name\x00'
SURNAMES = frozenset(bytes.fromhex(value) for value in (
    'b1cdd22c02f0038fcec2ed54dde3deeb527e9ff270fd87f5eaa93bfeab7f5a74',
    'd555c582efe8de73c0016e3e0a4d3f20895a52cc2959777b95d872b03291f324',
))

_LETTERS = b'abcdefghijklmnopqrstuvwxyz0123456789'


def _table(first_pass):
    """Map bytes to word characters, a weak joiner (space), a comma or a break (NUL).

    The first pass keeps bytes that decoding or break detection still needs.
    """
    table = bytearray(256)
    for value in range(256):
        if value in _LETTERS:
            table[value] = value
        elif 65 <= value <= 90:
            table[value] = value + 32
        elif value in b" \t\r\x0b\x0c_'~":
            table[value] = 32
        elif value == ord(','):
            table[value] = value
        elif value in b'\n-+.':
            table[value] = value if first_pass else 32
        elif first_pass and (value in b'&#;%\\' or value >= 0x80):
            table[value] = value
    return bytes(table)


FIRST_PASS = _table(True)
FINAL_PASS = _table(False)
NEEDS_DECODING = re.compile(rb'[&%\\\x80-\xff]')
NEEDS_BREAKS = re.compile(rb'[\n.+-]')
NEEDS_WORK = re.compile(rb'[&#;%\\\x80-\xff\n.+-]')
# Line-start list markers, blank lines, spaced dashes or plus signs, and sentence-ending dots.
BREAKS = re.compile(rb'\n[ \t]*(?:[-+]+|[0-9]{1,3}\.?)[ \t]|\n[ \t]*\n|(?<=[ \t])[-+]+(?=[ \t\n])|\.+(?=[ \t\n,]|$)|^\.+')
JSON_ESCAPE = re.compile(r'\\(?:u([0-9a-fA-F]{4})|([nrtbf])|(["\\/]))')
PERCENT = re.compile(r'(?:%[0-9A-Fa-f]{2})+')
# Combining marks and invisible format characters join the letters around them.
INVISIBLE = re.compile('[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f'
                       '\u00ad\u180e\u200b-\u200f\u2060-\u2064\ufeff]+')
# Unicode spaces and punctuation (dashes, quotes, middle dots, CJK punctuation) join words like ASCII punctuation.
UNICODE_SPACE = re.compile('[\u00a0\u00b7\u1680\u2000-\u206f\u2e00-\u2e7f\u3000-\u303f\ufe10-\ufe1f\ufe30-\ufe6f]')
# The same characters as UTF-8 bytes, for words beside a family name in undecoded text.
PUNCTUATION_BYTES = re.compile(rb'\xc2[\xa0\xb7]|\xe1\x9a\x80|\xe2[\x80\x81][\x80-\xbf]|\xe2[\xb8\xb9][\x80-\xbf]'
                               rb'|\xe3\x80[\x80-\xbf]|\xef\xb8[\x90-\x9f\xb0-\xbf]|\xef\xb9[\x80-\xaf]')
WORD = re.compile(rb'[a-z0-9]+')
TAG = re.compile(rb'<[^<>]{0,4096}>')
# Beside a family name, after PUNCTUATION_BYTES: other non-ASCII bytes belong to words (letters, CJK).
WORD_BYTE = re.compile(rb'[a-z0-9\x80-\xff]')
LAST_WORD = re.compile(rb'(?<![a-z0-9\x80-\xff])([a-z0-9]+)[^a-z0-9\x80-\xff]+$')
NEXT_WORD = re.compile(rb'[^a-z0-9\x80-\xff]+([a-z0-9]+)(?![a-z0-9\x80-\xff])')
_FIELD_VALUE = rb'(?:[-_ ]?names?)?["\']?[ \t]*[:=][ \t]*["\']?([^"\'\r\n,;{}\[\]<>]{1,80})'
GIVEN_FIELD = re.compile(rb'given' + _FIELD_VALUE)
FAMILY_FIELD = re.compile(rb'(?<![a-z0-9])(?:family|sur)' + _FIELD_VALUE)
FIELD_BOUNDARY = re.compile(rb'[{}]|\n[ \t]*-[ \t]')
DIGITS = b'0123456789'
# Inputs larger than this are scanned in parallel worker processes.
PARALLEL_BYTES = 64 * 1024 * 1024


def _json_unescape(match):
    if match.group(1):
        return chr(int(match.group(1), 16))
    return ' ' if match.group(2) else match.group(3)


def _decode(segment):
    text = segment.decode('utf-8', 'replace')
    if '&' in text:
        text = html.unescape(text)
    if '\\' in text:
        text = JSON_ESCAPE.sub(_json_unescape, text)
    if '%' in text:
        text = PERCENT.sub(lambda match: unquote(match.group()), text)
    if not text.isascii():
        text = unicodedata.normalize('NFKD', text)
        text = UNICODE_SPACE.sub(' ', INVISIBLE.sub('', text))
    return text.lower().encode('utf-8', 'replace').translate(FIRST_PASS)


def raw_segments(data, translated=None):
    """Break a file into runs that may hold one name, before decoding and break detection."""
    translated = data.translate(FIRST_PASS) if translated is None else translated
    raw = set(translated.split(b'\0'))
    for name in _structured_names(data):
        raw.update(name.translate(FIRST_PASS).split(b'\0'))
    raw.discard(b'')
    return raw


def normalize(segment):
    """Decode one raw run and split it at breaks into normalized word runs."""
    if not NEEDS_WORK.search(segment):
        return {segment}
    if NEEDS_DECODING.search(segment):
        segment = _decode(segment)
    if NEEDS_BREAKS.search(segment):
        segment = BREAKS.sub(b'\0', segment)
    found = set(segment.translate(FINAL_PASS).split(b'\0'))
    found.discard(b'')
    return found


def _structured_names(data):
    """Pair each given-name field with the nearest family-name field of the same object (CFF, CSL, schema.org)."""
    if b'given' not in data and b'Given' not in data:
        return []
    lowered = data.lower()
    names = []
    position = lowered.find(b'given')
    while position >= 0:
        given = GIVEN_FIELD.match(lowered, position)
        if given and (position == 0 or not WORD_BYTE.match(lowered, position - 1)):
            nearest = None
            for family in FAMILY_FIELD.finditer(lowered, max(0, position - 400), position + 400):
                start, end = sorted((position, family.start()))
                if not FIELD_BOUNDARY.search(lowered, start, end) and (
                        nearest is None or abs(family.start() - position) < abs(nearest.start() - position)):
                    nearest = family
            if nearest is not None:
                names.append(given.group(1).strip() + b' ' + nearest.group(1).strip())
        position = lowered.find(b'given', position + 5)
    return names


def grams(segment):
    """Words, adjacent word pairs (spaced and joined), split given names, and "Family, Given" pairs."""
    if b' ' not in segment and b',' not in segment:
        return {segment, segment.rstrip(DIGITS) or segment}
    out = set()
    parts = [WORD.findall(part) for part in segment.split(b',')]
    for words in parts:
        out.update(words)
        out.update(word.rstrip(DIGITS) for word in words if word[-1] in DIGITS and not word.isdigit())
        if len(words) < 2:
            continue
        pairs = list(zip(words, words[1:]))
        joined = list(map(b''.join, pairs))
        out.update(joined)
        out.update(map(b' '.join, pairs))
        if len(words) > 2:
            # A given name written as two syllables: "ab c" and "a bc".
            out.update(map(b' '.join, zip(joined, words[2:])))
            out.update(map(b' '.join, zip(words, joined[1:])))
        if any(word[-1] in DIGITS for word in words[1:]):
            # An account suffix such as "name_name2" still identifies the person.
            for first, second in pairs:
                bare = second.rstrip(DIGITS)
                if bare and bare != second:
                    out.update((first + b' ' + bare, first + bare))
    for left, right in zip(parts, parts[1:]):
        if b'and' in left:
            left = left[len(left) - left[::-1].index(b'and'):]
        if b'and' in right:
            right = right[:right.index(b'and')]
        if len(left) == 1 and len(right) in {1, 2}:
            # One given name, possibly written as two syllables; more words mean another person.
            given = b''.join(right)
            out.update((left[0] + b' ' + given, left[0] + given))
    return out


class Matcher:
    """Check files against the digests, remembering every run and gram already checked.

    Repeated content (the same records on many pages) costs only set operations;
    each distinct gram is hashed once.
    """

    def __init__(self, protected=None, salt=None, surnames=None):
        self.protected = PROTECTED if protected is None else protected
        self.salt = SALT if salt is None else salt
        self.surnames = SURNAMES if surnames is None else surnames
        self.raw_seen, self.raw_hits = set(), set()
        self.runs_seen, self.run_hits = set(), set()
        self.hashed, self.gram_hits, self.family_names = set(), set(), set()

    def _digest(self, gram):
        return hashlib.sha256(self.salt + gram).digest()

    def _check(self, grams_found):
        """Hash grams not seen before; return whether any gram is protected."""
        new_grams = grams_found - self.hashed
        if new_grams:
            self.hashed |= new_grams
            digests = map(methodcaller('digest'), map(hashlib.sha256, map(self.salt.__add__, new_grams)))
            if not self.protected.isdisjoint(digests):
                self.gram_hits.update(gram for gram in new_grams if self._digest(gram) in self.protected)
            words = [gram for gram in new_grams if b' ' not in gram]
            prefix = self.salt + SURNAME_DOMAIN
            self.family_names.update(word for word in words if hashlib.sha256(prefix + word).digest() in self.surnames)
        return not self.gram_hits.isdisjoint(grams_found)

    def neighbours(self, translated):
        """Pair each protected family name with the words beside it, across any punctuation."""
        pairs = set()
        for name in self.family_names:
            position = translated.find(name)
            while position >= 0:
                end = position + len(name)
                before = PUNCTUATION_BYTES.sub(b' ', translated[max(0, position - 96):position])
                after = PUNCTUATION_BYTES.sub(b' ', translated[end:end + 96])
                if not WORD_BYTE.match(before[-1:]) and not WORD_BYTE.match(after[:1]):
                    previous, following = LAST_WORD.search(before), NEXT_WORD.match(after)
                    if previous:
                        pairs.update((previous.group(1) + b' ' + name, previous.group(1) + name))
                    if following:
                        pairs.update((name + b' ' + following.group(1), name + following.group(1)))
                position = translated.find(name, end)
        return bool(pairs) and self._check(pairs)

    def data(self, data):
        translated = data.translate(FIRST_PASS)
        if self._runs(data, translated) or self.neighbours(translated):
            return True
        # Markup can split a visible name across elements: read each tag as a space beside a family name too.
        if (b'</' in data or b'/>' in data) and any(name in translated for name in self.family_names):
            return self.neighbours(TAG.sub(b' ', data).translate(FIRST_PASS))
        return False

    def _runs(self, data, translated):
        raw = raw_segments(data, translated)
        fresh = raw - self.raw_seen
        if fresh:
            self.raw_seen |= fresh
            runs = {segment: normalize(segment) for segment in fresh}
            new_runs = set().union(*runs.values()) - self.runs_seen
            self.runs_seen |= new_runs
            run_grams = {run: grams(run) for run in new_runs}
            self._check(set().union(*run_grams.values()))
            if self.gram_hits:
                self.run_hits.update(run for run, found in run_grams.items() if not self.gram_hits.isdisjoint(found))
            if self.run_hits:
                self.raw_hits.update(segment for segment, found in runs.items() if not self.run_hits.isdisjoint(found))
        return not self.raw_hits.isdisjoint(raw)


def contains_protected(text, protected=None, salt=None, surnames=None):
    """Whether a string, such as an author name, URL or file body, contains a protected form."""
    data = text.encode('utf-8') if isinstance(text, str) else bytes(text)
    return Matcher(protected, salt, surnames).data(data)


def scan_files(paths, protected=None, salt=None, workers=None, surnames=None):
    """Return (path, line numbers) for each readable file with a protected form; line 0 means a multi-line form.

    Large inputs are split, in path order, across forked worker processes when the platform supports it.
    """
    paths = [Path(path) for path in paths]
    sizes = [_size(path) for path in paths]
    if workers is None:
        available = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
        # Fork only a single-threaded process; forking beside live threads can deadlock the child.
        forkable = 'fork' in multiprocessing.get_all_start_methods() and threading.active_count() == 1
        workers = min(available, 8) if sum(sizes) > PARALLEL_BYTES and forkable else 1
    if workers <= 1:
        return _scan(paths, protected, salt, surnames)
    target, chunks, current, filled = sum(sizes) / workers, [], [], 0
    for path, size in zip(paths, sizes):
        current.append(path)
        filled += size
        if filled >= target * (len(chunks) + 1) and len(chunks) < workers - 1:
            chunks.append(current)
            current = []
    chunks.append(current)
    context, readers, processes = multiprocessing.get_context('fork'), [], []
    for chunk in chunks:
        reader, writer = context.Pipe(duplex=False)
        process = context.Process(target=_worker, args=(writer, chunk, protected, salt, surnames), daemon=True)
        process.start()
        writer.close()
        readers.append(reader)
        processes.append(process)
    try:
        results = [reader.recv() for reader in readers]
    finally:
        for process in processes:
            process.join()
    errors = [result for result in results if isinstance(result, str)]
    if errors:
        raise RuntimeError('Protected-name scan worker failed: ' + errors[0])
    return [hit for result in results for hit in result]


def _worker(writer, paths, protected, salt, surnames):
    # A forked worker inherits the module; only the results cross the pipe.
    try:
        writer.send(_scan(paths, protected, salt, surnames))
    except BaseException as error:  # Report instead of leaving the parent waiting.
        writer.send(f'{type(error).__name__}: {error}')
    finally:
        writer.close()


def _size(path):
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _scan(paths, protected, salt, surnames):
    matcher, outcomes, hits = Matcher(protected, salt, surnames), {}, []
    for path in paths:
        try:
            data = path.read_bytes()
        except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
            continue
        key = hashlib.blake2b(data, digest_size=20).digest()
        if key not in outcomes:
            outcomes[key] = _lines(data, matcher) if matcher.data(data) else None
        if outcomes[key]:
            hits.append((path, outcomes[key]))
    return hits


def _lines(data, matcher):
    lines = [number for number, line in enumerate(data.split(b'\n'), 1) if matcher.data(line)]
    return lines or [0]


def protected_authors(record):
    """Whether an author of a record, or of its recorded publication edition, is a protected person."""
    names = list(record.get('authors') or [])
    edition = (record.get('details') or {}).get('publication')
    if isinstance(edition, dict):
        names += list(edition.get('authors') or [])
    # Joined as an author line would be printed, so neighbouring entries are checked as a plain-text search sees them.
    return bool(names) and contains_protected(', '.join(name for name in names if isinstance(name, str)))


def omit_protected_authors(record):
    """Return the record unchanged, or with every author list omitted when one names a protected person.

    An omission covers the whole record, so an attached publication edition lists no authors either.
    """
    from publication_metadata import authors_omitted, omit_authors
    return omit_authors(record) if authors_omitted(record) or protected_authors(record) else record


def require_clean(paths, label):
    """Raise before publication when any file names a protected person; only paths and line numbers are shown."""
    hits = scan_files(paths)
    if hits:
        lines = [f'{path}: line {", ".join(map(str, numbers[:20]))}' for path, numbers in hits]
        raise SystemExit(f'Protected personal names found in {len(hits)} {label} file(s); '
                         'see docs/maintenance.md#protected-names:\n' + '\n'.join(lines))
    return len(paths)


def tracked_files(root=ROOT):
    output = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'], capture_output=True, check=True).stdout
    return [Path(root) / name for name in output.decode('utf-8', 'surrogateescape').split('\0') if name]


def tree_files(directory):
    """Every file under a directory, skipping VCS metadata and build caches."""
    files = []
    for folder, names, filenames in os.walk(directory):
        names[:] = sorted(name for name in names if name not in {'.git', '.pipeline', '.cache', '__pycache__'})
        files.extend(Path(folder) / name for name in sorted(filenames))
    return files


def default_files(root=ROOT):
    site = Path(root) / 'dist/site'
    return tracked_files(root) + (tree_files(site) if site.is_dir() else [])


def omit_archive_authors(path=None):
    """Rewrite the arXiv archive with protected author lists omitted; return the changed record IDs."""
    from catalog import DATA, read_jsonl, write_jsonl
    path = Path(path) if path is not None else DATA / 'papers.jsonl'
    rows = read_jsonl(path)
    updated = [omit_protected_authors(row) for row in rows]
    changed = [row['id'] for row, new in zip(rows, updated) if new != row]
    if changed:
        write_jsonl(path, updated)
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('paths', nargs='*', type=Path, help='files or directory trees; default: tracked files and dist/site')
    parser.add_argument('--omit-protected-authors', action='store_true',
                        help='omit author lists naming a protected person from data/papers.jsonl, then exit')
    args = parser.parse_args(argv)
    if args.omit_protected_authors:
        changed = omit_archive_authors()
        print(f'Omitted the author lists of {len(changed)} archived record(s); run python3 scripts/catalog.py build next.')
        return 0
    files = [file for path in args.paths for file in (tree_files(path) if path.is_dir() else [path])] if args.paths else default_files()
    hits = scan_files(files)
    for path, lines in hits:
        shown = ', '.join(map(str, lines[:20])) + (' ...' if len(lines) > 20 else '')
        print(f'{path}: protected personal name on line {shown}', file=sys.stderr)
    if hits:
        print(f'Protected personal names found in {len(hits)} file(s); see docs/maintenance.md#protected-names.', file=sys.stderr)
        return 1
    print(f'No protected personal names in {len(files)} files.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

# Rebuild the English survey

This is an evidence-traced working manuscript, not a peer-reviewed publication or an independent reproduction of the cited experiments. Its research inventory is fixed at source commit `87166fe8ad9c8e832f7a90ee84b2e93c6e0e40db`, release `v2026.10.18`, and catalog SHA-256 `7f71a1683ab013e587a20086c3e357956981f517a24ae8bc8e81791108c66e4f`. Later changes to the production catalog do not change this manuscript's bibliography or inventory counts.

Python 3.11+ and the standard library are sufficient. No provider request, model endpoint, package installation, or Git-history download is needed:

```sh
python3 -S research/survey/scripts/build_article.py --output output/survey
```

Open `output/survey/index.html`. The HTML embeds its styles, enhancement script, and inventory figure. `scripts/build_site.py` publishes that article with the current site header and footer in place of its own bar, and the published `build-manifest.json` keeps the reviewed page's fingerprint as `reviewed_index_sha256`. The same directory contains BibTeX and CSL-JSON references, a compact source-reading register, public evidence ledgers, and a build manifest with file sizes and SHA-256 fingerprints. Raw papers, full source abstracts, model weights, and training data are not redistributed.

By default, the builder writes **only the output directory**. It does not update the generated files under `research/survey`. To explicitly refresh those mirrors after reviewing a manuscript change:

```sh
python3 -S research/survey/scripts/build_article.py --output output/survey --update-source
```

The production site may copy and verify a reviewed static artifact separately. This builder does not edit the site, deploy, create tags, or publish a release.

## Frozen bibliography and shallow checkouts

`fixtures/frozen-catalog-bibliography.json` contains the **70 original paper/survey records actually cited from the pinned catalog**, without changing their fields. Each entry retains its stable citation key and source-record SHA-256. The record hash is computed over UTF-8 JSON with sorted keys, compact separators, and non-ASCII characters preserved. The fixture also records the original full-catalog fingerprint and source commit. Its exact file fingerprint is pinned in the builder.

A record may instead carry `authors_omitted: true` with empty author lists, as the production catalog shows it; the history comparison and the re-export below apply that same omission to the pinned object and accept no other difference. Such a reference shows "Authors: see the paper" with a link to the cited edition.

The subset cannot recreate the full catalog's SHA-256; that fingerprint records the catalog from which the subset was exported. The reviewed fixture's own hash and per-record hashes verify the offline input. The builder additionally checks citation titles, ordered author lists, and inspected arXiv versions against the reading ledgers. It never substitutes the mutable `data/catalog.jsonl` in the current checkout.

If the pinned Git object is already available, the default build additionally compares all 70 records against `git show <pinned-commit>:data/catalog.jsonl`. If that object or Git itself is unavailable, as in a shallow checkout, the verified fixture is sufficient. The builder never fetches missing history. To skip even the local history probe:

```sh
python3 -S research/survey/scripts/build_article.py --no-history-check --output output/survey
```

The 14 new arXiv citations come from the retained official title-search metadata in `evidence/title-search.json`. Five additional references are supplied by `evidence/extra-references.json`. These inputs remain separate from the frozen catalog and do not approve new production-catalog records. The reading register deduplicates the resulting 89 cited works: 87 selected full-text-section reads, one abstract/project-page-only source, and one versioned dataset snapshot. A section read does not mean that every page was inspected.

## Maintain the snapshot deliberately

Keep changes to scientific claims, reading evidence, bibliography, and presentation reviewable. Edit the seven source fragments rather than the generated HTML. Record the actual source edition and sections read; leave missing dates or publication facts unknown. Do not replace a retained preprint's authors with those of a different proceedings edition.

To reproduce the existing bibliography fixture when the complete pinned Git object is already present:

```sh
python3 -S research/survey/scripts/build_article.py --export-frozen-bibliography /tmp/awesomecua-survey-bibliography.json
cmp research/survey/fixtures/frozen-catalog-bibliography.json /tmp/awesomecua-survey-bibliography.json
```

Export is read-only with respect to Git. It refuses to overwrite its destination with a selection whose fingerprint differs from the reviewed fixture. An intentional snapshot change therefore requires reviewing the changed selection, original records, reading editions, and counts before updating the fixture and its pin. Do not merely recalculate hashes to make an unexpected change pass.

Public evidence retains source URLs, retrieval times, fingerprints, actual reading locators, original annotations, and limitations. Full upstream text and original acquisition bodies belong in the ignored private cache. When removing private paths from a source ledger, retain an exact private backup and confirm that the cleaned JSON equals the previously exported public form. The documented 2026-10-18 cleanup did this without altering manuscript prose or citation facts.

Run the targeted offline checks after changes:

```sh
python3 -S -m unittest discover -s tests -p 'test_research_survey.py' -v
node --check research/survey/article.js
```

The tests cover offline building without the historical object, deterministic outputs, title/author/version mismatches, fixture and record tampering, public-evidence boundaries, and preservation of the generated source mirrors in output-only mode. Browser review of the assembled desktop and mobile reader remains a separate check.

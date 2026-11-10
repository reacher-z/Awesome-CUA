## Summary

<!-- What changed and why. For a resource, link the primary source, note uncertain facts, and say whether it is core or adjacent. -->

## Checklist

- [ ] Primary sources were inspected directly; reviewed entries set `editorial_reviewed` and `reviewed_sha256` from `data/primary-evidence.jsonl`
- [ ] Ran `python3 scripts/catalog.py validate`, `python3 scripts/catalog.py build --check`, `python3 scripts/run_tests.py`, `node --test tests/web.test.mjs`, and `python3 scripts/build_site.py`
- [ ] Regenerated views are committed with their sources; no generated file was edited by hand ([CONTRIBUTING](https://github.com/reacher-z/Awesome-CUA/blob/main/CONTRIBUTING.md))

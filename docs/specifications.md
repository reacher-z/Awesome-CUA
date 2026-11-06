# Dataset and benchmark specifications

The catalog retains source-reviewed profiles under `details.benchmark_protocol` and `details.dataset_profile`. These support the website's [benchmark comparison](https://awesomecua.com/compare/benchmarks/) and [dataset comparison](https://awesomecua.com/compare/datasets/), along with the corresponding JSON downloads.

One profile describes one catalog resource. It is not a benchmark run, an independently reproduced result, or necessarily a distinct project. Only curated resources can publish a profile. Missing profiles and fields remain unknown.

## Count observations

Every quantity carries a value, unit, precision qualifier, population, counting basis, and primary evidence URL. For example, OSWorld's `test_all.json` and `test_nogdrive.json` are different task populations. WorkArena's task definitions and instantiated tasks are different units. Screen2Words summaries and referenced screens are different units.

- `qualifier`: `exact`, `approximately`, `at-least`, or `more-than` preserves the source's precision.
- `basis`: `reported` means stated by the publisher; `computed` means counted from an inspected source manifest or table.
- `population`: identifies the subset, release, or artifact to which the count applies.
- `evidence_url`: must resolve to a primary receipt already retained in the resource record.
- Optional `reference_url` provides a readable original publication page when the evidence receipt is a machine-readable API response. The response URL and digest remain available for auditing.

No cross-resource or cross-unit total is computed. Package files and hosting-service size bands are not converted into sample counts. Empty counts are not zero. Duplicate unit/population pairs within a profile fail validation.

## Provenance and limitations

Profile evidence can include the resource's README, a dataset card, a published abstract, or an inspected task manifest/evaluator. Supplementary evidence has its own URL, retrieval time, digest, and supported field scope. A failed or changed supporting source revokes the editorial verification match when evidence is refreshed.

Specifications describe what the inspected sources establish. An available repository does not prove that all announced evaluation levels are implemented. A GUI grounding accuracy is not a full-task success rate; frameworks can expose different observations and tools. Keep benchmark version, task split, agent framework, evaluator, step budget, and evaluation date with any performance observation.

Data licenses remain separate from code and weight licenses. Profiles record publisher declarations and known limitations; they do not grant rights to third-party content or establish training-data quality.

## Validate and inspect

```bash
python3 scripts/catalog.py build
python3 scripts/catalog.py validate
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
```

The JSON Schema defines the profile shapes, and `scripts/specifications.py` validates evidence references and count grain. `notebooks/catalog-quality.ipynb` provides a reproducible quality profile and coverage comparison against the documented baseline.

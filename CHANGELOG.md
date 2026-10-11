# Changelog

All notable changes to this project are documented here.
Format based on Keep a Changelog; versions are SemVer.

## v0.1.1 — 2026-10-11 (round 2: audit + revision)

### Changed
- **Correctness (critical fix)**: README worked-example numbers were wrong
  ($756.0 .. $1,512.0); recomputed against the code and corrected to
  `$356.4 .. $712.8` with the derivation shown, plus a new regression test
  `test_readme_example_regression` so README and code can no longer drift.
- **Clarity**: intro paragraph tightened 49 → 38 words (still <=60, rule 16).
- **Completeness**: repro command now names every coefficient used, so the
  example is auditable without reading source.

### Verified
- self_test.py re-run after revision: all three tiers PASS
  (functional 5, error-path 4, edge 5 = 14 tests).

## v0.1.0 — 2026-10-11 (initial draft)

### Added
- `port_economics.py`: `estimate` (token/cost range with overridable
  `[estimated]` coefficients), `risk` (0-100 additive risk score + failure
  modes), `cases` (two publicly reported port experiments with source-nature
  labels, as of 2026-10-11).
- `self_test.py`: functional / error-path / edge three-tier suite.
- README, MIT LICENSE, ALIGNMENT.md (16-item audit).

# llm-port-economics

Estimate the cost of an LLM-driven large-codebase port before committing a budget. Input task size, model prices and process assumptions; output a cost range, a failure-risk score, and likely failure modes. Pure standard library, no network, no keys.

Data currency: **as of 2026-10-11**.

## Problem

Teams either refuse large ports outright (fear of six-figure LLM bills) or start them blind and stall at 60% with the budget gone. The only public anchor points are two experiments on the *same* port target — the TypeScript compiler (tsc) ported to Rust:

- **Case A**: reportedly ~$24K, completed in ~2 weeks, using a 2026-generation agentic coding model.
- **Case B**: an earlier attempt with a different model, reportedly ~$420K, did not complete.

Both figures are **self-reported by the experiment authors** (public project README and blog posts), **not independently verified**, and accurate **as of 2026-10-11**. Two data points are an anecdote, not a curve — and the interesting lesson is not "model X is smarter" but that the cost-optimal model generation *drifts*, so the baseline must be re-measured per generation. This tool makes those baseline assumptions explicit and computable.

## How it works

1. **Cost model** (`estimate`): `core_tokens = loc x tokens_per_loc`, multiplied by `passes` and an overhead range (1.5x–3.0x for re-reads, retries, context churn), priced with a blended input/output rate, then scaled by a reality multiplier (`unattended` = 1x, `human-loop` = 10x). Every coefficient is overridable and labeled `[estimated]` by default.
2. **Risk model** (`risk`): additive score 0–100 from four components — codebase size, test-coverage gap, spec gap, team-familiarity gap — plus a matched list of likely failure modes.
3. **Case database** (`cases`): prints the two reported experiments with source nature and verification status attached to each number.

## Quickstart (~2 min total)

```bash
# Step 1: cost range for a 100k-LOC port, human-in-the-loop (~5 s)
python port_economics.py estimate --loc 100000 --model workhorse --automation human-loop

# Step 2: failure risk with your coverage and spec state (~5 s)
python port_economics.py risk --loc 100000 --coverage 55 --spec-pages 4 --familiarity 6

# Step 3: the two public case studies with sourcing labels (~2 s)
python port_economics.py cases

# Full self test (~30 s)
python self_test.py
```

Reproducing the README example numbers: `python port_economics.py estimate --loc 100000 --model workhorse --automation human-loop` yields `$356.4 .. $712.8` (1.2M core tokens ×3 passes ×1.5–3.0 overhead × $6.6/Mtok blended × 10 reality multiplier) — this is the **floor**; see Limits for why real cases land higher. This figure is regression-tested in `self_test.py`.

## Why not X

| Alternative | Why not |
|---|---|
| Spreadsheet with token math | Same arithmetic, but no failure-risk model, no `[estimated]` labeling discipline, and no reproducible CLI for CI. |
| Vendor pricing calculators | Token-only and vendor-specific; they price usage, not *port projects*, and ignore overhead, passes and human-loop reality. |
| Reading case-study blog posts and extrapolating | Single-point anchoring; no way to swap assumptions and see the sensitivity. Two anecdotes are not a baseline. |
| Runtime cost dashboards (metering tools) | They measure *after* you spend. This tool estimates *before* — they complement, not substitute. |

## Minimal Fallback

No Python? Open `port_economics.py` and read `CASE_STUDIES` (20 lines) plus the formula in `estimate_cost` — the whole model is one page of arithmetic you can do by hand. `python port_economics.py cases` also works offline with zero configuration.

## Design Trade-offs

Priority order when conflicts arise: **honest labeling > arithmetic correctness > simplicity > feature count**. Concretely: intervals over point estimates; placeholder presets instead of scraped live prices (no network, no staleness bugs); a deliberately crude additive risk model over an opaque ML scoring function — you must be able to audit every number it prints.

## Limits & Second-order Effects

- Defaults (`tokens_per_loc=12`, overhead 1.5–3.0x, reality 10x) are `[estimated]` and language-dependent; a REPL-heavy language can double them.
- The two case figures are self-reported and may exclude hidden costs (review time, failed branches).
- **Second-order effects**: if this tool is widely adopted, teams may treat a "low risk" score as a substitute for human review, or anchor budgets on the interval midpoint. The floor estimate can also become a negotiating weapon ("the tool says $1K") against engineers who know it will cost 50x that. Label outputs as *baselines*, not budgets.

## FAQ

**When NOT to use this tool?** For small greenfield tasks (estimation overhead exceeds the task); for runtime spend control (use metering); for procurement contracts (the numbers are `[estimated]` baselines, not commitments); and for non-port work like feature development, where the cost model's shape does not apply.

**Are the $24K / $420K figures verified?** No. Self-reported by the authors, as of 2026-10-11. This repo treats them as reported data points and says so on every printout.

**Why is the floor so much lower than the real cases?** The floor prices tokens only. Real ports burn budget on human review, re-planning and dead branches — hence the `human-loop` reality multiplier (10x, `[estimated]`) and the explicit Limits note.

**Can I add my own model pricing?** Yes — edit `MODEL_PRESETS`. Keep prices current; the CLI stamps its own `as_of` date so stale presets are at least visible.

Confidence: **High (>=80%)** that outputs are arithmetically consistent with the inputs you provide (unit-tested). **Low (<60%)** that the default coefficients fit your specific project — they are placeholders `[estimated]`.

## [Core Assumptions]

1. Token consumption per line of ported code is roughly stable within a language family (default 12 `[estimated]`).
2. Port cost scales approximately linearly with passes and orchestration overhead; sublinear model-output pricing is ignored.
3. Failure risk decomposes additively into size, coverage, spec clarity and familiarity — interactions (e.g., huge codebase + zero coverage) are underestimated by design.
4. Self-reported public case costs are directionally informative enough to serve as calibration anchors, despite lacking independent verification.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 zhengming contributors.

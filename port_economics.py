#!/usr/bin/env python3
"""llm-port-economics — cost & risk baseline estimator for LLM-driven ports of large codebases.

Pure standard library. No network. No secrets.
All default coefficients are [estimated] placeholders meant to be overridden
by your own measurements. Data currency: 2026-10-11.
"""
from __future__ import annotations

import argparse
import json
import sys

AS_OF = "2026-10-11"

# USD per 1M tokens. These are PLACEHOLDER presets, not quotes. [estimated]
MODEL_PRESETS = {
    "flagship": {"price_in": 15.0, "price_out": 75.0},
    "workhorse": {"price_in": 3.0, "price_out": 15.0},
    "budget": {"price_in": 0.5, "price_out": 2.0},
}

# Two publicly reported experiments on the same port target (paraphrased).
# Self-reported by the experiment authors; NOT independently verified.
CASE_STUDIES = [
    {
        "id": "case-A",
        "target": "TypeScript compiler (tsc) ported to Rust",
        "model": "2026-generation agentic coding model",
        "reported_cost_usd": 24000,
        "outcome": "completed",
        "duration": "~2 weeks",
        "source_nature": "self-reported by the port author (public project README and blog post)",
        "independently_verified": False,
    },
    {
        "id": "case-B",
        "target": "same port target, earlier attempt",
        "model": "earlier-generation frontier model",
        "reported_cost_usd": 420000,
        "outcome": "did not complete",
        "duration": "not disclosed",
        "source_nature": "retrospectively reported by the author of the later experiment",
        "independently_verified": False,
    },
]


class InputError(ValueError):
    """Raised for invalid user inputs; the CLI turns this into exit code 2."""


def estimate_cost(loc, tokens_per_loc, passes, model, io_split, automation="human-loop"):
    """Floor-to-ceiling token/cost arithmetic. All coefficients overridable."""
    if loc is None or loc <= 0:
        raise InputError("--loc must be a positive integer")
    if tokens_per_loc is None or tokens_per_loc <= 0:
        raise InputError("--tokens-per-loc must be positive")
    if passes is None or passes <= 0:
        raise InputError("--passes must be positive")
    if model not in MODEL_PRESETS:
        raise InputError("unknown model preset: %r (choose from %s)"
                         % (model, ", ".join(sorted(MODEL_PRESETS))))
    if not io_split or len(io_split) != 2 or io_split[0] < 0 or io_split[1] < 0:
        raise InputError("--io-split must be two non-negative numbers (in out)")
    if io_split[0] + io_split[1] <= 0:
        raise InputError("--io-split values must sum to a positive number")
    if automation not in ("unattended", "human-loop"):
        raise InputError("--automation must be 'unattended' or 'human-loop'")

    preset = MODEL_PRESETS[model]
    core_tokens = loc * tokens_per_loc
    overhead = {"low": 1.5, "high": 3.0}  # re-reads, retries, context churn [estimated]
    tokens_low = core_tokens * passes * overhead["low"]
    tokens_high = core_tokens * passes * overhead["high"]
    in_frac, out_frac = io_split[0], io_split[1]
    total = in_frac + out_frac
    in_frac, out_frac = in_frac / total, out_frac / total
    blended = in_frac * preset["price_in"] + out_frac * preset["price_out"]
    # Human-in-the-loop ports in the public cases landed far above the raw
    # token floor; a 10x reality multiplier is a coarse calibration [estimated].
    reality = 1.0 if automation == "unattended" else 10.0
    return {
        "as_of": AS_OF,
        "loc": loc,
        "tokens_per_loc": tokens_per_loc,
        "tokens_per_loc_label": "[estimated]",
        "passes": passes,
        "model": model,
        "price_in_per_mtok": preset["price_in"],
        "price_out_per_mtok": preset["price_out"],
        "io_split": [round(in_frac, 4), round(out_frac, 4)],
        "overhead_range": [overhead["low"], overhead["high"]],
        "overhead_label": "[estimated]",
        "automation": automation,
        "reality_multiplier": reality,
        "reality_multiplier_label": "[estimated]" if reality != 1.0 else "none",
        "tokens_low": round(tokens_low),
        "tokens_high": round(tokens_high),
        "cost_low_usd": round(tokens_low / 1e6 * blended * reality, 2),
        "cost_high_usd": round(tokens_high / 1e6 * blended * reality, 2),
        "note": "floor estimate; real reported cases can land 10-100x above the unattended floor",
    }


def failure_risk(loc, coverage, spec_pages, familiarity):
    """Additive risk score 0-100 (higher = worse) plus failure-mode flags."""
    if loc is None or loc <= 0:
        raise InputError("--loc must be a positive integer")
    if not 0 <= coverage <= 100:
        raise InputError("--coverage must be within 0..100")
    if spec_pages is None or spec_pages < 0:
        raise InputError("--spec-pages must be >= 0")
    if not 0 <= familiarity <= 10:
        raise InputError("--familiarity must be within 0..10")

    size_risk = min(30.0, loc / 100_000 * 3.0)
    coverage_gap = (100 - coverage) / 100 * 40
    spec_gap = 10.0 if spec_pages >= 10 else 25.0
    familiarity_gap = (10 - familiarity) / 10 * 20
    score = round(size_risk + coverage_gap + spec_gap + familiarity_gap, 1)
    band = "low" if score < 30 else ("medium" if score <= 60 else "high")
    modes = []
    if coverage < 60:
        modes.append("behavioral regressions slip through: port compiles but diverges silently")
    if loc > 500_000:
        modes.append("context budget exhaustion: model loses cross-module invariants")
    if familiarity < 4:
        modes.append("review bottleneck: team cannot judge correctness of generated code")
    if spec_pages < 10:
        modes.append("spec vacuum: model invents semantics where the source is only implicit")
    return {
        "risk_score": score,
        "band": band,
        "components": {
            "size": round(size_risk, 1),
            "coverage_gap": round(coverage_gap, 1),
            "spec_gap": round(spec_gap, 1),
            "familiarity_gap": round(familiarity_gap, 1),
        },
        "likely_failure_modes": modes or ["no dominant failure mode flagged at these inputs"],
    }


def _load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise InputError("config file is not valid JSON: %s" % exc)
    except OSError as exc:
        raise InputError("cannot read config file: %s" % exc)
    if not isinstance(data, dict):
        raise InputError("config file must contain a JSON object")
    return data


def cmd_estimate(ns):
    cfg = _load_config(ns.config) if ns.config else {}
    def pick(key, cli_val, default):
        if cli_val is not None:
            return cli_val
        return cfg.get(key, default)
    loc = pick("loc", ns.loc, None)
    tpl = pick("tokens_per_loc", ns.tokens_per_loc, 12.0)
    passes = pick("passes", ns.passes, 3)
    model = pick("model", ns.model, "workhorse")
    io_split = pick("io_split", ns.io_split, [0.7, 0.3])
    automation = pick("automation", ns.automation, "human-loop")
    result = estimate_cost(loc, tpl, passes, model, io_split, automation)
    print(json.dumps(result, indent=2) if ns.json else _fmt_estimate(result))
    return 0


def _fmt_estimate(r):
    lines = [
        "LLM port cost estimate (as of %s)" % r["as_of"],
        "  loc=%s  tokens/loc=%s %s  passes=%s" % (r["loc"], r["tokens_per_loc"], r["tokens_per_loc_label"], r["passes"]),
        "  model=%s ($%.2f in / $%.2f out per Mtok, io split %s)"
            % (r["model"], r["price_in_per_mtok"], r["price_out_per_mtok"], "/".join(str(x) for x in r["io_split"])),
        "  tokens: %s .. %s" % ("{:,}".format(r["tokens_low"]), "{:,}".format(r["tokens_high"])),
        "  COST RANGE: $%s .. $%s  (automation=%s, reality multiplier %s %s)"
            % ("{:,}".format(r["cost_low_usd"]), "{:,}".format(r["cost_high_usd"]),
               r["automation"], r["reality_multiplier"], r["reality_multiplier_label"]),
        "  note: %s" % r["note"],
    ]
    return "\n".join(lines)


def cmd_risk(ns):
    result = failure_risk(ns.loc, ns.coverage, ns.spec_pages, ns.familiarity)
    print(json.dumps(result, indent=2) if ns.json else _fmt_risk(result))
    return 0


def _fmt_risk(r):
    lines = [
        "Port failure risk (higher = worse)",
        "  score: %s / 100   band: %s" % (r["risk_score"], r["band"]),
        "  components: %s" % ", ".join("%s=%s" % (k, v) for k, v in r["components"].items()),
        "  likely failure modes:",
    ]
    lines += ["   - %s" % m for m in r["likely_failure_modes"]]
    return "\n".join(lines)


def cmd_cases(_ns):
    ratio = CASE_STUDIES[1]["reported_cost_usd"] / CASE_STUDIES[0]["reported_cost_usd"]
    print("Publicly reported experiments on the same port target (as of %s)" % AS_OF)
    print("Both are self-reported by their authors and NOT independently verified.\n")
    for c in CASE_STUDIES:
        print("- %s: %s" % (c["id"], c["target"]))
        print("  model: %s" % c["model"])
        print("  reported cost: $%s | outcome: %s | duration: %s"
              % ("{:,}".format(c["reported_cost_usd"]), c["outcome"], c["duration"]))
        print("  source nature: %s\n" % c["source_nature"])
    print("Reported cost ratio (case-B / case-A): %.1fx" % ratio)
    print("Caveat: two data points are an anecdote, not a curve. Treat as a")
    print("starting baseline, re-measure against current model generations.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="port_economics", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("estimate", help="estimate cost range for a port task")
    e.add_argument("--loc", type=int, help="lines of code to port")
    e.add_argument("--tokens-per-loc", type=float, default=None)
    e.add_argument("--passes", type=int, default=None)
    e.add_argument("--model", default=None, choices=sorted(MODEL_PRESETS) + [None])
    e.add_argument("--io-split", type=float, nargs=2, default=None, metavar=("IN", "OUT"))
    e.add_argument("--automation", default=None, choices=["unattended", "human-loop"])
    e.add_argument("--config", default=None, help="JSON config file; CLI flags override it")
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=cmd_estimate)

    r = sub.add_parser("risk", help="score failure risk of a port task")
    r.add_argument("--loc", type=int, required=True)
    r.add_argument("--coverage", type=float, required=True, help="test coverage 0..100")
    r.add_argument("--spec-pages", type=float, default=5)
    r.add_argument("--familiarity", type=float, default=5, help="team familiarity 0..10")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_risk)

    c = sub.add_parser("cases", help="show publicly reported case studies")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_cases)
    return p


def main(argv=None):
    ns = build_parser().parse_args(argv)
    try:
        return ns.func(ns)
    except InputError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate 13-monorepo-layout.md from model.json plus the package map below.

Gate: every one of the model's components must land in exactly one package, and
every package must have a kind, a phase and a layer-legal dependency list.
Run: python3 model/build_layout.py   (exits 1 on any gap)
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PLAN = HERE.parent
D = json.load(open(HERE / "model.json"))
D = D.get("D", D)
COMPS = D["comps"]

# kind -> layer rank. A package may import only from a lower rank.
RANK = {"contracts": 0, "module": 1, "feature": 2, "service": 3, "app": 4}

# name: (kind, phase, [component ids], one-line job, [deps by package name])
PKGS = {
    "contracts": ("contracts", "P0", ["cap"], "Token buckets, ledger row, events, capability flags, Feature and Adapter ports. No I/O.", []),
    # modules: pure libraries and plugins, no sideways imports
    "metering": ("module", "P0", ["norm", "dedupe", "calc"], "Five-bucket normaliser, dedupe guard, ordered cost formula.", ["contracts"]),
    "pricebook-core": ("module", "P0", ["pb", "plife", "pplan"], "Append-only price rows, 30-day flag, stale block, plan units.", ["contracts"]),
    "stats": ("module", "P2", ["stats", "cpsc"], "Paired task-clustered bootstrap, non-inferiority test, cost per successful task.", ["contracts"]),
    "redaction": ("module", "P0", ["logp", "ret"], "Metadata-only logging policy, retention, redaction.", ["contracts"]),
    "joiner": ("module", "P0", ["joiner"], "Join gateway, hook and OTel rows on session and prompt id.", ["contracts"]),
    # features: policy and guard behaviours, each behind its own flag
    "feat-upstream": ("feature", "P0", ["p_anth", "p_oai", "p_xai", "p_gem", "p_rtr", "cat", "b_oauth"], "Send the request upstream: one file per provider, the model catalogue, and the pass-through of OAuth tokens (never stored).", ["contracts"]),
    "feat-harness-adapters": ("feature", "P0", ["a_cc", "a_cx", "a_ai", "a_sdk", "a_obs"], "Connect a harness to the gateway: one file per harness (base URL, hooks, OTel, transcripts).", ["contracts"]),
    "feat-headless-runner": ("feature", "P1", ["a_cli", "b_cc", "b_cx"], "Run a CLI agent as a backend: one file per CLI (budget, turns, schema, bare flags).", ["contracts"]),
    "feat-budgets": ("feature", "P1", ["bst", "bres", "alert"], "Virtual-key budgets, reserve then true-up, 75/90/100 alerts.", ["contracts", "metering"]),
    "feat-turn-cap": ("feature", "P1", ["tcap"], "Turn cap at P75 of own baseline.", ["contracts"]),
    "feat-loop-guard": ("feature", "P1", ["loop"], "Stop after the first repeated-failure signature.", ["contracts"]),
    "feat-sticky-model": ("feature", "P2", ["stick"], "Cache key per session, rate cap.", ["contracts"]),
    "feat-switch-pricer": ("feature", "P2", ["swp"], "Price the cache loss at a model change.", ["contracts", "metering"]),
    "feat-rules-router": ("feature", "P2", ["rules"], "Rules and atomic classifier, ship-first routing.", ["contracts"]),
    "feat-static-router": ("feature", "P2", ["srt"], "Router trained on execution-verified labels.", ["contracts"]),
    "feat-cascade": ("feature", "P2", ["casc"], "Cascade with fallback, only when acceptance beats the extra call.", ["contracts"]),
    "feat-probe": ("feature", "P2", ["probe"], "One-probe cost predictor.", ["contracts"]),
    "feat-strong-share": ("feature", "P3", ["share"], "Per-tenant strong-model ceiling.", ["contracts"]),
    "feat-cache-planner": ("feature", "P2", ["cplan"], "TTL from the observed reuse gap.", ["contracts"]),
    "feat-tier-selector": ("feature", "P3", ["tsel"], "Batch, flex, priority, reserved, small.", ["contracts"]),
    "feat-cache-hit-monitor": ("feature", "P2", ["hit"], "Hit rate per caller against its own baseline.", ["contracts"]),
    "feat-schema-deferral": ("feature", "P2", ["schema"], "Defer tool schemas above about 20 tools.", ["contracts"]),
    "feat-output-cap": ("feature", "P2", ["ocap"], "Tool-output cap, keep tracebacks.", ["contracts"]),
    "feat-observation-masking": ("feature", "P2", ["mask"], "Mask stale observations above about 10 events.", ["contracts"]),
    "feat-context-clearing": ("feature", "P2", ["clear"], "Clear at 30 to 40k, keep 5.", ["contracts"]),
    "feat-compaction-guard": ("feature", "P2", ["compact"], "Compaction last, restart at the third.", ["contracts"]),
    "feat-max-tokens": ("feature", "P1", ["mtok"], "Hard max_tokens on every call.", ["contracts"]),
    "feat-instruction-lint": ("feature", "P2", ["ilint"], "CLAUDE.md and AGENTS.md size linter.", ["contracts"]),
    "feat-prompt-lint": ("feature", "P2", ["pwl"], "Prompt-wording lint.", ["contracts"]),
    "feat-anomaly": ("feature", "P3", ["anom"], "Anomaly detector (DevX proposal).", ["contracts"]),
    # services: stateful, own a store, expose a Port
    "svc-ledger": ("service", "P0", ["led", "meta"], "Append-only ledger and metadata store.", ["contracts", "metering"]),
    "svc-pricebook": ("service", "P0", [], "Serves price rows, owns the price store.", ["contracts", "pricebook-core"]),
    "svc-signals": ("service", "P0", ["hookr", "otelr", "trans"], "Hook, OTel and transcript receivers.", ["contracts", "joiner"]),
    "svc-health": ("service", "P1", ["rl", "fb"], "Rate-limit tracker and priced fallback chain.", ["contracts"]),
    "svc-reconciler": ("service", "P1", ["rec", "canary", "planq"], "Invoice reconciler, weekly price canary, plan quota.", ["contracts", "metering"]),
    "svc-policy": ("service", "P1", [], "Runs the feature pipeline in order, applies flags.", ["contracts"]),
    "svc-insight": ("service", "P1", ["attr", "dash"], "Attribution and reports.", ["contracts"]),
    "svc-eval": ("service", "P2", ["evalh", "gold"], "Paired runs, private task set, isolated cache per arm.", ["contracts", "stats"]),
    "svc-rollout": ("service", "P2", ["shadow", "canr", "kill", "rollb"], "Shadow, canary, kill-switch, rollback.", ["contracts", "stats"]),
    "svc-tenancy": ("service", "P1", ["tenant", "pol", "audit", "authz", "secrets"], "Tenants, keys, policy-as-code, audit, roles, secrets.", ["contracts", "redaction"]),
    # apps: deployables, compose everything
    "app-gateway": ("app", "P0", ["gw", "authk", "tee", "fmode"], "The request path: async web-server proxy, key resolve, stream tee, failure mode.", ["contracts"]),
    "app-admin-api": ("app", "P1", ["api"], "Keys, budgets, policies, reports over HTTP.", ["contracts"]),
    "app-worker": ("app", "P1", [], "Reconciler, canary, evals and rollout jobs.", ["contracts"]),
    "app-cli": ("app", "P0", [], "token-economics CLI: init, replay, report, lint.", ["contracts"]),
}

# Provider and harness differences live as FILES inside the package of the capability, never as packages.
# package: {file: what differs}
FILES = {
    "feat-upstream": {"anthropic.py": "Messages API, cache_control, tiers", "openai.py": "Responses API, prompt_cache_key", "xai.py": "x-grok-conv-id, band repricing", "gemini.py": "implicit and explicit cache, storage fee", "bedrock.py": "aggregator", "openrouter.py": "aggregator", "vercel.py": "aggregator", "catalogue.py": "exact model ids, tiers, limits", "oauth.py": "forward anthropic-beta and tokens, never store"},
    "feat-harness-adapters": {"claude_code.py": "base URL, hooks, OTel, transcripts", "codex.py": "model_providers base_url, Responses wire", "openai_compat.py": "Aider and any OPENAI_API_BASE client", "sdk.py": "Agent SDK and API clients", "observe.py": "observe-only: exports, local JSONL"},
    "feat-headless-runner": {"claude_cli.py": "claude -p flags and budget", "codex_cli.py": "codex exec, user-level config"},
    "feat-cache-planner": {"anthropic.py": "explicit TTL and breakpoints", "openai.py": "prompt_cache_key", "xai.py": "conversation id header", "gemini.py": "explicit cache and storage fee"},
    "feat-cache-hit-monitor": {"anthropic.py": "cache read and write fields", "openai.py": "cached_tokens", "xai.py": "cached prompt tokens", "gemini.py": "cached content tokens"},
    "feat-sticky-model": {"anthropic.py": "cache scope per session", "openai.py": "key per session", "xai.py": "conv id per session", "gemini.py": "cache name per session"},
    "feat-tier-selector": {"anthropic.py": "batch and priority tiers", "openai.py": "batch, flex, priority", "gemini.py": "batch tier"},
    "metering": {"anthropic.py": "usage fields to five buckets", "openai.py": "usage fields to five buckets", "xai.py": "usage fields to five buckets", "gemini.py": "usage fields to five buckets"},
    "pricebook-core": {"anthropic.py": "price rows and multipliers", "openai.py": "price rows and multipliers", "xai.py": "price rows, bands", "gemini.py": "price rows, storage fee"},
}
for _n in FILES:
    assert _n in PKGS, _n


def check():
    errs = []
    seen = {}
    for n, (kind, phase, comps, job, deps) in PKGS.items():
        for c in comps:
            if c not in COMPS:
                errs.append(f"{n}: unknown component {c}")
            if c in seen:
                errs.append(f"{c} in both {seen[c]} and {n}")
            seen[c] = n
        for d in deps:
            if d not in PKGS:
                errs.append(f"{n}: unknown dep {d}")
            elif RANK[PKGS[d][0]] >= RANK[kind] and not (kind == "contracts"):
                errs.append(f"{n} ({kind}) may not import {d} ({PKGS[d][0]})")
        if kind == "module":
            for d in deps:
                if d != "contracts" and PKGS[d][0] != "module":
                    errs.append(f"{n}: modules import only modules")
    for c in COMPS:
        if c not in seen:
            errs.append(f"component {c} ({COMPS[c]['label']}) is in no package")
    return errs, seen


def pkg_dir(n):
    kind = PKGS[n][0]
    if kind == "contracts":
        return "modules/contracts"
    base = {"module": "modules", "feature": "features", "service": "services", "app": "apps"}[kind]
    short = n
    for p in ("feat-", "svc-", "app-"):
        if short.startswith(p):
            short = short[len(p):]
    return f"{base}/{short}"


def main():
    errs, seen = check()
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    kinds = ["contracts", "module", "feature", "service", "app"]
    names = {"contracts": "Contracts", "module": "Modules", "feature": "Features", "service": "Services", "app": "Apps"}
    out = []
    for k in kinds:
        rows = [(n, v) for n, v in PKGS.items() if v[0] == k]
        out.append(f"### {names[k]} ({len(rows)})\n")
        out.append("| Folder | Phase | Job | Plan components | May import |")
        out.append("|---|---|---|---|---|")
        for n, (kind, ph, comps, job, deps) in rows:
            cs = ", ".join(COMPS[c]["label"] for c in comps) or "none (new in code)"
            ds = ", ".join(pkg_dir(d).split('/')[-1] for d in deps) or "nothing"
            out.append(f"| {pkg_dir(n)} | {ph} | {job} | {cs} | {ds} |")
        out.append("")
    out.append("### Provider and harness files\n")
    out.append("| Package | File | What differs |")
    out.append("|---|---|---|")
    for n, fs in FILES.items():
        for f, w in fs.items():
            out.append(f"| {pkg_dir(n)}/src/.../providers/ | {f} | {w} |")
    out.append("")
    table = "\n".join(out)
    tmpl = (HERE / "layout_template.md").read_text()
    counts = {k: sum(1 for v in PKGS.values() if v[0] == k) for k in kinds}
    text = (tmpl.replace("__TABLES__", table)
            .replace("__NPKG__", str(len(PKGS)))
            .replace("__NCOMP__", str(len(COMPS)))
            .replace("__NMOD__", str(counts["module"]))
            .replace("__NFEAT__", str(counts["feature"]))
            .replace("__NSVC__", str(counts["service"]))
            .replace("__NAPP__", str(counts["app"])))
    (PLAN / "13-monorepo-layout.md").write_text(text)
    json.dump({n: {"kind": v[0], "phase": v[1], "dir": pkg_dir(n), "components": v[2], "deps": v[4], "files": sorted(FILES.get(n, {}))}
               for n, v in PKGS.items()}, open(HERE / "layout.json", "w"), indent=1)
    print(f"ok: {len(PKGS)} packages, {len(COMPS)} components mapped, {counts}")


if __name__ == "__main__":
    main()

"""`token-economics`: init, report, detect, prices, replay. Everything is found through entry points."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from token_economics_contracts import (
    ADAPTERS,
    NORMALISERS,
    SERVICES,
    Attempt,
    NoPriceRow,
    TokenEconomicsError,
    load,
    load_all,
)


def state_dir() -> Path:
    return Path(os.environ.get("TOKEN_ECONOMICS_STATE_DIR", "~/.token-economics")).expanduser()


def _optional(name: str, *args: object) -> Any:
    try:
        return load(SERVICES, name)(*args)
    except LookupError:
        return None


def _audit(action: str, subject: str, detail: dict[str, Any]) -> None:
    """Record an admin change in the audit log, when the tenancy service is installed."""
    log = _optional("audit", str(state_dir()))
    if log is not None:
        log.record(action, subject, detail, actor=os.environ.get("USER", "cli"))


def _issue_key(tenant: str, team: str, caller: str) -> tuple[str, str]:
    """A new virtual key as (plaintext, key id). Hashed at rest when the tenancy service is installed."""
    from token_economics_contracts import KeyInfo  # noqa: PLC0415

    state = state_dir()
    state.mkdir(parents=True, exist_ok=True)
    store = _optional("keys", str(state))
    if store is not None:
        plaintext, key_id = store.issue(
            KeyInfo(tenant=tenant, team=team, caller=caller), actor=os.environ.get("USER", "cli")
        )
        return str(plaintext), str(key_id)
    keys_path = state / "keys.json"  # P0 fallback: plaintext file
    keys = json.loads(keys_path.read_text()) if keys_path.exists() else {}
    key = "vk-" + secrets.token_urlsafe(18)
    keys[key] = {"tenant": tenant, "team": team, "caller": caller}
    keys_path.write_text(json.dumps(keys, indent=2) + "\n")
    keys_path.chmod(0o600)
    return key, ""


def cmd_init(a: argparse.Namespace) -> int:
    """Issue a virtual key and print how to point each harness at the gateway."""
    key, key_id = _issue_key(a.tenant, a.team, a.caller)
    print(f"state directory: {state_dir()}")
    print(f"virtual key for {a.caller}@{a.tenant}: {key}" + (f"  (id {key_id})" if key_id else ""))
    print("This key is shown once; only its hash is stored.\n" if key_id else "")
    print(f"1. start the gateway:  token-economics-gateway --port {a.port}")
    for name, adapter in sorted(load_all(ADAPTERS).items()):
        settings = adapter.route(f"http://127.0.0.1:{a.port}", key)
        if settings:
            print(f"\n{name}:")
            for k, v in settings.items():
                print(f"  {k}={v}")
    print("\nRequests are observed. Nothing is blocked until a policy is switched on (token-economics policy show).")
    return 0


def cmd_key(a: argparse.Namespace) -> int:
    store = _optional("keys", str(state_dir()))
    if store is None:
        print("the tenancy service is not installed")
        return 2
    if a.action == "issue":
        key, key_id = _issue_key(a.tenant, a.team, a.caller)
        print(f"{key}\nid {key_id}: shown once; only its hash is stored")
    elif a.action == "revoke":
        ok = store.revoke(a.key_id, actor=os.environ.get("USER", "cli"))
        print(
            f"revoked {a.key_id}: the gateway refuses it within a second" if ok else f"no active key with id {a.key_id}"
        )
        return 0 if ok else 1
    else:
        print("| id | tenant | team | caller | created | revoked |\n|---|---|---|---|---|---|")
        for k in store.list():
            revoked = f"{k.revoked_at:%Y-%m-%d %H:%M}" if k.revoked_at else ""
            who = f"{k.info.tenant} | {k.info.team} | {k.info.caller}"
            print(f"| {k.key_id} | {who} | {k.created_at:%Y-%m-%d %H:%M} | {revoked} |")
    return 0


# ---------------------------------------------------------------- policy file

MODES = ("off", "advisory", "enforced")


def _policy_path() -> Path:
    return state_dir() / "policy.json"


def _read_policy() -> dict[str, Any]:
    try:
        data = json.loads(_policy_path().read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_policy(policy: dict[str, Any]) -> None:
    state_dir().mkdir(parents=True, exist_ok=True)
    tmp = _policy_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(policy, indent=2) + "\n")
    tmp.replace(_policy_path())  # the gateway re-reads the file when it changes


def _section(policy: dict[str, Any], feature: str) -> dict[str, Any]:
    section: dict[str, Any] = policy.setdefault("features", {}).setdefault(feature, {})
    section.setdefault("mode", "off")
    return section


def cmd_policy(a: argparse.Namespace) -> int:
    policy = _read_policy()
    if a.action == "mode":
        before = _section(policy, a.feature)["mode"]
        _section(policy, a.feature)["mode"] = a.mode
        _write_policy(policy)
        _audit("policy_mode_changed", a.feature, {"from": before, "to": a.mode})
    elif a.action == "set":
        try:
            value = json.loads(a.value)
        except ValueError:
            value = a.value
        _section(policy, a.feature)[a.key] = value
        _write_policy(policy)
        _audit("policy_changed", a.feature, {"key": a.key})
    features = policy.get("features") or {}
    if not features:
        print("no policy: every feature is off, the gateway only observes")
        return 0
    print("| feature | mode | settings |\n|---|---|---|")
    for name, section in features.items():
        rest = {k: v for k, v in section.items() if k != "mode"}
        print(f"| {name} | {section.get('mode', 'off')} | {json.dumps(rest) if rest else ''} |")
    print("\noff: not applied. advisory: logged as would_block, nothing blocked. enforced: blocked at the gateway.")
    return 0


def cmd_budget(a: argparse.Namespace) -> int:
    policy = _read_policy()
    section = _section(policy, "budgets")
    limits: list[dict[str, Any]] = section.setdefault("limits", [])

    def same(x: dict[str, Any]) -> bool:
        return (x.get("scope"), x.get("match", "*"), x.get("window")) == (a.scope, a.match, a.window)

    if a.action == "set":
        if Decimal(a.usd) <= 0:
            print("--usd must be more than 0")
            return 2
        section["limits"] = [x for x in limits if not same(x)] + [
            {"scope": a.scope, "match": a.match, "window": a.window, "usd": str(Decimal(a.usd))}
        ]
        if a.mode:
            section["mode"] = a.mode
        _write_policy(policy)
        _audit(
            "budget_set",
            f"{a.scope}:{a.match}",
            {"window": a.window, "usd": str(Decimal(a.usd)), "mode": section["mode"]},
        )
    elif a.action == "remove":
        section["limits"] = [x for x in limits if not same(x)]
        _write_policy(policy)
        _audit("budget_removed", f"{a.scope}:{a.match}", {"window": a.window})
    print(
        f"budgets are {section['mode']}"
        + (
            ""
            if section["mode"] != "off"
            else "  (switch on with: token-economics policy mode budgets advisory|enforced)"
        )
    )
    print("| scope | match | window | limit |\n|---|---|---|---|")
    for x in section["limits"]:
        print(f"| {x['scope']} | {x.get('match', '*')} | {x['window']} | ${Decimal(str(x['usd'])):,.2f} |")
    reader = _optional("budget_status", str(state_dir()))
    status = list(reader.status()) if reader is not None else []
    if status:
        print("\n| budget | window | spent | held | limit | used |\n|---|---|---|---|---|---|")
        for s in status:
            print(
                f"| {s.scope} | {s.window} | ${s.spent_usd:,.4f} | ${s.reserved_usd:,.4f} | ${s.limit_usd:,.2f} | "
                f"{s.used_share:.0%} |"
            )
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    """The baseline from the ledger: spend per developer (mean, median, P95), cache hit per caller, failed-run share."""
    path = state_dir() / "ledger.sqlite"
    if not path.exists():
        print(f"no ledger at {path}: start the gateway and send traffic through it first")
        return 1
    since = datetime.now(UTC) - timedelta(days=a.days) if a.days else None
    rows = list(load(SERVICES, "ledger")(str(path)).rows(since=since))
    text = load(SERVICES, "baseline_markdown")(load(SERVICES, "baseline")(rows))
    _emit(text, a.md)
    return 0


def cmd_detect(a: argparse.Namespace) -> int:
    """Run the leak detectors in alert mode and print the 50-row coverage table."""
    detectors = load(SERVICES, "detectors")(
        str(Path(a.transcripts).expanduser()), str(state_dir() / "detectors"), a.prompt_check
    )
    since = datetime.now(UTC) - timedelta(days=a.days) if a.days else None
    findings, coverage = detectors.run(since)
    total = getattr(detectors, "last_total_usd", None)
    _emit(load(SERVICES, "coverage_markdown")(coverage, total), a.md)
    print(
        f"\n{len(findings)} findings. Estimates rank work; they are list-price figures from transcripts "
        "(cost_source = client) and do not predict savings."
    )
    return 0


def cmd_prices(a: argparse.Namespace) -> int:
    """List the price book, flagging rows that are unverified for 30 days or about to expire."""
    state_dir().mkdir(parents=True, exist_ok=True)
    book = load(SERVICES, "pricebook")(str(state_dir() / "pricebook.sqlite"))
    stale = {r.price_row_id for r in book.stale(datetime.now(UTC))}
    rows = [r for r in book.rows() if not a.stale or r.price_row_id in stale]
    print("| model | band from | input | output | cache read | write 5m | write 1h | confidence | stale |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r.provider, r.model, r.context_band_min)):
        print(
            f"| {r.model} | {r.context_band_min:,} | {r.input} | {r.output} | {r.cache_read} | {r.cache_write_5m} | "
            f"{r.cache_write_1h} | {r.confidence} | {'yes' if r.price_row_id in stale else ''} |"
        )
    print(f"\n{len(stale)} of {len(book.rows())} rows are stale (USD per 1M tokens).")
    return 0


def cmd_replay(a: argparse.Namespace) -> int:
    """Price a local transcript with the price book: a client-side estimate, printed, never written to the ledger."""
    adapter = load(ADAPTERS, a.harness)
    normalisers = load_all(NORMALISERS)
    state_dir().mkdir(parents=True, exist_ok=True)
    book, calc = load(SERVICES, "pricebook")(str(state_dir() / "pricebook.sqlite")), load(SERVICES, "cost")()
    now, tokens, cost, calls, skipped = (
        datetime.now(UTC),
        Counter[str](),
        Counter[str](),
        Counter[str](),
        Counter[str](),
    )
    target = Path(a.path).expanduser()
    for path in [target] if target.is_file() else sorted(target.rglob("*.jsonl")):
        for obs in adapter.replay(path):
            try:
                buckets = normalisers[obs.provider].normalise(obs.usage)
                price = book.lookup(obs.provider, obs.model, now, buckets.prompt_tokens, obs.service_tier)
            except NoPriceRow:
                skipped["no price row"] += 1
                continue
            except (TokenEconomicsError, ValueError, KeyError):
                skipped["usage rejected"] += 1
                continue
            usd = calc.cost(buckets, price, calc.active_for(obs.service_tier, obs.speed, obs.inference_geo))
            calls[obs.model] += 1
            tokens[obs.model] += buckets.total
            cost[obs.model] += int(usd * Decimal(1_000_000))  # micro-dollars, summed exactly
    print("| model | responses | tokens | est. cost (client) |\n|---|---|---|---|")
    for model in sorted(calls):
        print(f"| {model} | {calls[model]:,} | {tokens[model]:,} | ${Decimal(cost[model]) / 1_000_000:,.2f} |")
    print(f"\nPriced at today's price rows; cost_source = client. Skipped: {dict(skipped) or 'none'}.")
    return 0


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def _eval_table(result: dict[str, Any]) -> str:
    """The per-arm summary and the paired verdicts of one analysis, as markdown tables."""
    lines = [
        f"{result['name']}: baseline {result['baseline']}, bound {result['bound_pp']} pp, alpha {result['alpha']}",
        "",
        "| arm | attempts | success | total cost | CPS | failed-run waste | errors |",
        "|---|---|---|---|---|---|---|",
    ]
    for arm, s in result["arms"].items():
        cps = "n/a" if s["cps_usd"] is None else f"${Decimal(s['cps_usd']):,.4f}"
        lines.append(
            f"| {arm} | {s['attempts']} | {_pct(s['success_rate'])} | ${Decimal(s['total_cost_usd']):,.4f} | {cps} "
            f"| {_pct(s['failed_waste_share'])} | {s['errors']} |"
        )
    lines += [
        "",
        "| candidate | CPS ratio (CI) | success diff pp (CI) | adjusted p | verdict |",
        "|---|---|---|---|---|",
    ]
    for arm, c in result["comparisons"].items():
        ci, sci = c["ratio_ci"], c["success_diff_ci"]
        ratio = "n/a" if ci is None or c["ratio"] is None else f"{c['ratio']:.3f} ({ci[0]:.3f} to {ci[1]:.3f})"
        diff = "n/a" if sci is None else f"{c['success_diff'] * 100:+.1f} ({sci[0] * 100:+.1f} to {sci[1] * 100:+.1f})"
        lines.append(f"| {arm} | {ratio} | {diff} | {c['adjusted_p']:.4f} | {c['verdict']}: {c['reason']} |")
    return "\n".join(lines)


def cmd_eval(a: argparse.Namespace) -> int:
    """Run a preregistered eval spec, re-read a result folder, or run the no-op self-test."""
    harness = load(SERVICES, "eval")()
    if a.action == "selftest":
        out = harness.selftest(a.seed)
        print(_eval_table(out["analysis"]))
        print(f"\nno-op self-test: {'PASSED' if out['passed'] else 'FAILED'} ({out['verdict']}: {out['reason']})")
        return 0 if out["passed"] else 1
    if a.action == "report":
        folder = Path(a.result_dir).expanduser()
        try:
            spec = json.loads((folder / "spec.json").read_text())
            attempts = [
                Attempt.model_validate_json(line)
                for line in (folder / "attempts.jsonl").read_text().splitlines()
                if line.strip()
            ]
        except (OSError, ValueError) as exc:
            print(f"cannot read the result folder {folder}: {exc}")
            return 1
        print(_eval_table(harness.analyse(attempts, spec)))
        return 0
    try:
        folder = harness.run(
            Path(a.spec).expanduser(), Path(a.out).expanduser() if a.out else None, allow_dirty=a.allow_dirty
        )
    except (
        RuntimeError,
        ValueError,
    ) as exc:  # not preregistered, a bad spec or task file, a harness that skips the gateway
        print(f"token-economics eval: {exc}", file=sys.stderr)
        return 2
    print(f"results in {folder}\n")
    print((folder / "REPORT.md").read_text())
    return 0


def _emit(text: str, md: str | None) -> None:
    print(text)
    if md:
        Path(md).write_text(text + "\n")
        print(f"\nwrote {md}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="token-economics", description="Token Economics: price every model call")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="create a virtual key and print harness settings")
    p.add_argument("--tenant", default="default")
    p.add_argument("--team", default="")
    p.add_argument("--caller", default=os.environ.get("USER", "developer"))
    p.add_argument("--port", type=int, default=8787)
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("key", help="virtual keys: issue, list, revoke")
    ksub = p.add_subparsers(dest="action", required=True)
    k = ksub.add_parser("issue")
    k.add_argument("--tenant", default="default")
    k.add_argument("--team", default="")
    k.add_argument("--caller", required=True)
    ksub.add_parser("list")
    k = ksub.add_parser("revoke")
    k.add_argument("key_id")
    p.set_defaults(fn=cmd_key)
    p = sub.add_parser("policy", help="show or switch policy features (off, advisory, enforced)")
    psub = p.add_subparsers(dest="action")
    psub.add_parser("show")
    k = psub.add_parser("mode")
    k.add_argument("feature")
    k.add_argument("mode", choices=MODES)
    k = psub.add_parser("set", help="set one setting of a feature, e.g. policy set turn_cap default 60")
    k.add_argument("feature")
    k.add_argument("key")
    k.add_argument("value")
    p.set_defaults(fn=cmd_policy, action="show")
    p = sub.add_parser("budget", help="budgets per key, caller, team or tenant")
    bsub = p.add_subparsers(dest="action")
    bsub.add_parser("list")
    for name in ("set", "remove"):
        k = bsub.add_parser(name)
        k.add_argument("--scope", choices=["key", "caller", "team", "tenant"], required=True)
        k.add_argument("--match", default="*", help="the caller, team, tenant or key id; * for each one separately")
        k.add_argument("--window", choices=["day", "month", "total"], default="day")
        if name == "set":
            k.add_argument("--usd", required=True)
            k.add_argument("--mode", choices=MODES)
    p.set_defaults(fn=cmd_budget, action="list")
    p = sub.add_parser("report", help="baseline from the ledger")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--md")
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("detect", help="leak detectors in alert mode: the 50-row coverage table")
    p.add_argument("--transcripts", default="~/.claude/projects")
    p.add_argument("--days", type=int, default=30)
    p.add_argument(
        "--prompt-check",
        action="store_true",
        help="let a model label prompt text (off by default: no prompt text leaves this machine)",
    )
    p.add_argument("--md")
    p.set_defaults(fn=cmd_detect)
    p = sub.add_parser("prices", help="list the price book")
    p.add_argument("--stale", action="store_true", help="only rows that need verifying")
    p.set_defaults(fn=cmd_prices)
    p = sub.add_parser("replay", help="price a local transcript (client estimate, not written to the ledger)")
    p.add_argument("path")
    p.add_argument("--harness", default="claude_code")
    p.set_defaults(fn=cmd_replay)
    p = sub.add_parser("eval", help="eval harness: run a preregistered spec, re-read a result, self-test")
    esub = p.add_subparsers(dest="action", required=True)
    k = esub.add_parser("run", help="run a spec: baseline and candidate arms, paired, with a verdict each")
    k.add_argument("spec")
    k.add_argument("--out", help="result folder (default evals/results/<name>/<UTC time>; rerun into one to resume)")
    k.add_argument("--allow-dirty", action="store_true", help="run a spec that is not committed (marked as such)")
    k = esub.add_parser("report", help="re-analyse a result folder and print the table and verdicts")
    k.add_argument("result_dir")
    k = esub.add_parser("selftest", help="two identical arms must report no difference")
    k.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_eval)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return int(a.fn(a))
    except LookupError as exc:  # a package the command needs is not installed
        print(f"token-economics: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

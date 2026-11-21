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

from token_economics_contracts import ADAPTERS, NORMALISERS, SERVICES, NoPriceRow, TokenEconomicsError, load, load_all


def state_dir() -> Path:
    return Path(os.environ.get("TOKEN_ECONOMICS_STATE_DIR", "~/.token-economics")).expanduser()


def cmd_init(a: argparse.Namespace) -> int:
    """Create the state directory and a virtual key, and print how to point each harness at the gateway."""
    state = state_dir()
    state.mkdir(parents=True, exist_ok=True)
    keys_path = state / "keys.json"
    keys = json.loads(keys_path.read_text()) if keys_path.exists() else {}
    key = next((k for k, v in keys.items() if v.get("caller") == a.caller and v.get("tenant") == a.tenant), None)
    if key is None:
        key = "vk-" + secrets.token_urlsafe(18)
        keys[key] = {"tenant": a.tenant, "team": a.team, "caller": a.caller}
        keys_path.write_text(json.dumps(keys, indent=2) + "\n")
        keys_path.chmod(0o600)
    print(f"state directory: {state}\nvirtual key for {a.caller}@{a.tenant}: {key}\n")
    print(f"1. start the gateway:  token-economics-gateway --port {a.port}")
    for name, adapter in sorted(load_all(ADAPTERS).items()):
        settings = adapter.route(f"http://127.0.0.1:{a.port}", key)
        if settings:
            print(f"\n{name}:")
            for k, v in settings.items():
                print(f"  {k}={v}")
    print(
        "\nObserve mode: requests are never blocked or changed. A request without the key is attributed to 'unknown'."
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

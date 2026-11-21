"""Refuse a request when the same tool call has failed repeatedly in a row."""

from __future__ import annotations

from token_economics_contracts.types import Decision, FeatureEnv, LedgerRow, RequestContext

DEFAULT_REPEAT_FAILURES = 2  # the first repeat of the same failing call


class LoopGuard:
    name = "loop_guard"
    fail_closed = False

    def __init__(self, repeat_failures: int = DEFAULT_REPEAT_FAILURES) -> None:
        self.repeat_failures = repeat_failures

    def before(self, ctx: RequestContext) -> Decision | None:
        n = ctx.facts.trailing_repeat_failures
        if n < self.repeat_failures:
            return None
        return Decision(
            allow=False,
            feature=self.name,
            status=429,
            code="repeated_failure",
            message=(
                f"Loop guard: the same tool call has failed {n} times in a row with the same input. "
                "Change the approach before retrying."
            ),
        )

    def after(self, ctx: RequestContext, row: LedgerRow | None, status: int) -> None:
        return None


def create(env: FeatureEnv) -> LoopGuard:
    value = env.config.get("repeat_failures", DEFAULT_REPEAT_FAILURES)
    valid = isinstance(value, int) and not isinstance(value, bool) and value >= 1
    return LoopGuard(value if valid else DEFAULT_REPEAT_FAILURES)

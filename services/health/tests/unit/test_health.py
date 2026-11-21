import threading
from email.utils import formatdate

from token_economics_contracts import HealthTracker, load
from token_economics_svc_health import InMemoryHealth, open_health


class Clock:
    def __init__(self, now: float = 1_800_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def make() -> tuple[InMemoryHealth, Clock]:
    clock = Clock()
    return InMemoryHealth(clock=clock), clock


def test_counts_each_status_class_per_provider():
    # Given a tracker
    h, _ = make()
    # When responses of several kinds are recorded
    for s in (200, 200, 429, 500, 404):
        h.record("anthropic", s, {})
    h.record("openai", 200, {})
    # Then the counters add up per provider
    a = h.snapshot()["anthropic"]
    assert (a["requests"], a["ok_2xx"], a["rate_limited_429"], a["errors_5xx"], a["other"]) == (5, 2, 1, 1, 1)
    assert a["error_rate"] == 0.4 and a["last_status"] == 404
    assert h.snapshot()["openai"]["requests"] == 1


def test_old_requests_leave_the_window():
    # Given requests recorded now
    h, clock = make()
    h.record("anthropic", 500, {})
    # When more than five minutes pass
    clock.now += 301
    # Then they no longer count
    assert h.snapshot()["anthropic"]["requests"] == 0


def test_degraded_when_error_rate_high_with_enough_requests():
    # Given 5 requests with 1 failure (20%), failures not consecutive at the end
    h, _ = make()
    h.record("p", 429, {})
    for _ in range(4):
        h.record("p", 200, {})
    # Then it is degraded
    assert h.snapshot()["p"]["state"] == "degraded"
    # And fewer than 5 requests at the same rate is not
    h2, _ = make()
    h2.record("p", 500, {})
    h2.record("p", 200, {})
    assert h2.snapshot()["p"]["state"] == "healthy"


def test_three_consecutive_failures_degrade_and_a_success_resets():
    # Given three failures in a row
    h, _ = make()
    for _ in range(3):
        h.record("p", 503, {})
    assert h.snapshot()["p"]["state"] == "degraded"
    assert not h.healthy("p")
    # When a 2xx arrives
    for _ in range(30):
        h.record("p", 200, {})
    # Then consecutive failures reset and the error rate is low again
    s = h.snapshot()["p"]
    assert s["consecutive_failures"] == 0 and s["state"] == "healthy"
    assert h.healthy("p") and h.healthy("never-seen")


def test_retry_after_seconds_makes_provider_rate_limited_until_it_passes():
    # Given a 429 with Retry-After in seconds
    h, clock = make()
    h.record("p", 429, {"Retry-After": "30"})
    s = h.snapshot()["p"]
    assert s["state"] == "rate_limited" and s["retry_until"] is not None
    # When the time passes
    clock.now += 31
    # Then it is no longer rate limited
    s = h.snapshot()["p"]
    assert s["state"] != "rate_limited" and s["retry_until"] is None


def test_retry_after_http_date_on_529():
    # Given a 529 with an HTTP date 60 s ahead
    h, clock = make()
    h.record("p", 529, {"retry-after": formatdate(clock.now + 60, usegmt=True)})
    assert h.snapshot()["p"]["state"] == "rate_limited"
    clock.now += 61
    assert h.snapshot()["p"]["state"] != "rate_limited"


def test_retry_after_nonsense_is_ignored():
    h, _ = make()
    h.record("p", 429, {"retry-after": "soon"})
    assert h.snapshot()["p"]["retry_until"] is None


def test_rate_limit_headers_are_captured_case_insensitively_and_others_ignored():
    # Given a response with documented headers and an unknown one
    h, _ = make()
    h.record(
        "anthropic",
        200,
        {
            "Anthropic-RateLimit-Requests-Remaining": "49",
            "anthropic-ratelimit-tokens-remaining": "9000",
            "anthropic-ratelimit-requests-reset": "2026-01-01T00:00:00Z",
            "anthropic-ratelimit-tokens-reset": "2026-01-01T00:00:10Z",
            "x-mystery": "1",
        },
    )
    h.record("openai", 200, {"X-RateLimit-Remaining-Requests": "5", "x-ratelimit-remaining-tokens": "70"})
    snap = h.snapshot()
    assert snap["anthropic"]["limits"] == {
        "requests_remaining": "49",
        "tokens_remaining": "9000",
        "requests_reset": "2026-01-01T00:00:00Z",
        "tokens_reset": "2026-01-01T00:00:10Z",
    }
    assert snap["openai"]["limits"] == {"requests_remaining": "5", "tokens_remaining": "70"}


def test_snapshot_is_json_serialisable():
    import json

    h, _ = make()
    h.record("p", 429, {"retry-after": "5"})
    json.dumps(h.snapshot())


def test_threads_recording_together_lose_no_counts():
    # Given 8 threads each recording 250 responses
    h = InMemoryHealth()
    threads = [threading.Thread(target=lambda: [h.record("p", 200, {}) for _ in range(250)]) for _ in range(8)]
    # When they run
    [t.start() for t in threads]
    [t.join() for t in threads]
    # Then nothing is lost
    assert h.snapshot()["p"]["requests"] == 2000


def test_entry_point_resolves_to_a_health_tracker():
    assert load("token_economics.services", "health") is open_health
    assert isinstance(open_health(), HealthTracker)

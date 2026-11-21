"""A synthetic Claude Code transcript tree. All text is made up; nothing here comes from a real session."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

PROMPT_SENTINEL = "SYNTHETIC-PROMPT-TEXT-do-not-leak"
T0 = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def _ts(minutes: float) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def prompt(sid: str, minute: float, text: str = PROMPT_SENTINEL) -> dict[str, object]:
    return {
        "type": "user",
        "timestamp": _ts(minute),
        "sessionId": sid,
        "uuid": f"u-{sid}-{minute}",
        "cwd": "/work/demo",
        "message": {"role": "user", "content": text},
    }


def call(
    sid: str,
    minute: float,
    n: int,
    *,
    cache_read: int,
    cache_write: int,
    fresh: int = 10,
    out: int = 200,
    model: str = "claude-sonnet-4-6",
) -> dict[str, object]:
    return {
        "type": "assistant",
        "timestamp": _ts(minute),
        "sessionId": sid,
        "uuid": f"a-{sid}-{n}",
        "cwd": "/work/demo",
        "message": {
            "id": f"msg-{sid}-{n}",
            "role": "assistant",
            "model": model,
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "done"}],
            "usage": {
                "input_tokens": fresh,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
                "output_tokens": out,
                "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": cache_write},
            },
        },
    }


def write_session(root: Path, project: str, sid: str, entries: list[dict[str, object]]) -> None:
    folder = root / project
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{sid}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))


class Synth:
    """The builders as one fixture (test modules cannot import conftest under importlib mode)."""

    SENTINEL = PROMPT_SENTINEL
    prompt = staticmethod(prompt)
    call = staticmethod(call)
    write_session = staticmethod(write_session)


@pytest.fixture
def synth() -> type[Synth]:
    return Synth


@pytest.fixture
def transcripts(tmp_path: Path) -> Path:
    """Three sessions. `s-break` has a heavy start and a 3-hour gap after which the whole cache is rewritten."""
    root = tmp_path / "projects"
    write_session(
        root,
        "-work-demo",
        "s-break",
        [
            prompt("s-break", 0),
            call("s-break", 1, 1, cache_read=0, cache_write=80_000),
            call("s-break", 2, 2, cache_read=80_000, cache_write=500),
            prompt("s-break", 185),
            call("s-break", 186, 3, cache_read=0, cache_write=82_000),
        ],
    )
    write_session(
        root,
        "-work-demo",
        "s-small",
        [
            prompt("s-small", 10),
            call("s-small", 11, 1, cache_read=0, cache_write=20_000),
            call("s-small", 12, 2, cache_read=20_000, cache_write=300),
        ],
    )
    write_session(
        root,
        "-work-other",
        "s-other",
        [
            prompt("s-other", 30),
            call("s-other", 31, 1, cache_read=0, cache_write=18_000, model="claude-opus-4-7"),
        ],
    )
    return root

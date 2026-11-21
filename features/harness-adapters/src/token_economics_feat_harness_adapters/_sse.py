"""Server-sent-events parsing shared by both wire formats. Pure functions, never raise."""
from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator, Mapping
from typing import Any


def header(headers: Mapping[str, str], name: str) -> str:
    """Case-insensitive header lookup; "" when absent."""
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return ""


def is_sse(headers: Mapping[str, str], text: str) -> bool:
    ctype = header(headers, "content-type").lower()
    if "text/event-stream" in ctype:
        return True
    if "json" in ctype:
        return False
    return not text.lstrip().startswith("{")


def events(text: str) -> Iterator[tuple[str, Any]]:
    """Yield (event name, parsed JSON data) per SSE event. Bad JSON, comments and empty events are skipped."""
    name = ""
    data: list[str] = []
    for line in [*text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), ""]:
        if line == "":
            if data:
                with contextlib.suppress(ValueError):
                    yield name, json.loads("\n".join(data))
            name, data = "", []
        elif line.startswith(":"):
            continue
        else:
            field, _, value = line.partition(":")
            value = value.removeprefix(" ")
            if field == "event":
                name = value
            elif field == "data":
                data.append(value)


def loads_object(body: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None

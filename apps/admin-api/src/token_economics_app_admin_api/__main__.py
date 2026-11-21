"""`token-economics-admin`: serve the dashboard and the read-only API, on localhost by default."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from .app import create_app


def state_dir() -> Path:
    return Path(os.environ.get("TOKEN_ECONOMICS_STATE_DIR", "~/.token-economics")).expanduser()


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="token-economics-admin", description=__doc__)
    p.add_argument("--host", default="127.0.0.1", help="default 127.0.0.1; there is no authentication")
    p.add_argument("--port", type=int, default=8788)
    a = p.parse_args(argv)
    if a.host not in ("127.0.0.1", "localhost", "::1"):
        print(f"warning: {a.host} is not localhost and the dashboard has NO authentication", flush=True)
    print(f"dashboard: http://{a.host}:{a.port}/  (state directory {state_dir()})", flush=True)
    uvicorn.run(create_app(state_dir()), host=a.host, port=a.port, log_level="warning", server_header=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

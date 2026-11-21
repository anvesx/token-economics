"""`token-economics-gateway`: run the gateway in observe mode."""

from __future__ import annotations

import argparse

import uvicorn

from .app import create_app
from .settings import Settings


def main() -> None:
    ap = argparse.ArgumentParser(description="Token Economics gateway (observe mode: nothing is blocked or changed)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    settings = Settings()
    print(f"token-economics gateway on http://{a.host}:{a.port}  state: {settings.state_dir}")
    # no server or date header of our own: responses carry the upstream's headers only
    uvicorn.run(
        create_app(settings), host=a.host, port=a.port, log_level="warning", server_header=False, date_header=False
    )


if __name__ == "__main__":
    main()

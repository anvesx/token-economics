"""`token-economics-admin`: serve the dashboard and the API, on localhost by default."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from token_economics_contracts import SERVICES, load

from .app import create_app


def state_dir() -> Path:
    return Path(os.environ.get("TOKEN_ECONOMICS_STATE_DIR", "~/.token-economics")).expanduser()


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="token-economics-admin", description=__doc__)
    p.add_argument("--host", default="127.0.0.1", help="default 127.0.0.1; any other address needs --require-auth")
    p.add_argument("--port", type=int, default=8788)
    p.add_argument("--transcripts", type=Path, default=None, help="Claude Code transcripts, default ~/.claude/projects")
    p.add_argument(
        "--prompt-check",
        action="store_true",
        help="let a model (Sonnet, through your own Claude Code login) label prompts so tasks are split more "
        "accurately; prompt text is sent to the model; off by default. Labels already cached by the Hermes plugin "
        "are reused either way.",
    )
    p.add_argument("--require-auth", action="store_true", help="refuse every /api request without an admin token")
    p.add_argument("--issue-admin-token", metavar="NAME", help="issue an admin token for NAME, print it once, and exit")
    p.add_argument(
        "--role", choices=("viewer", "operator", "admin"), default="admin", help="role for --issue-admin-token"
    )
    a = p.parse_args(argv)
    if a.issue_admin_token:
        auth = load(SERVICES, "admin_auth")(str(state_dir()))
        plaintext, token_id = auth.issue(a.issue_admin_token, a.role, actor="cli")
        print(f"token id {token_id}; the token is shown once and cannot be recovered:\n{plaintext}")
        return 0
    if a.host not in ("127.0.0.1", "localhost", "::1") and not a.require_auth:
        # Fail closed: off localhost the API must never answer without a token, even before the first token exists.
        print(f"refusing to listen on {a.host} without --require-auth (the API would be open)", file=sys.stderr)
        return 2
    print(f"dashboard: http://{a.host}:{a.port}/  (state directory {state_dir()})", flush=True)
    uvicorn.run(
        create_app(
            state_dir(),
            transcripts_root=a.transcripts.expanduser() if a.transcripts else None,
            prompt_check=a.prompt_check,
            require_auth=a.require_auth,
        ),
        host=a.host,
        port=a.port,
        log_level="warning",
        server_header=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

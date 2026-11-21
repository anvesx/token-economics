"""Gateway settings, read from the environment."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from token_economics_contracts import KeyInfo

KEY_HEADER = "x-token-economics-key"
UNKNOWN = KeyInfo(tenant="unknown")


@dataclass(frozen=True)
class Settings:
    state_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("TOKEN_ECONOMICS_STATE_DIR", "~/.token-economics")).expanduser()
    )
    max_observed_bytes: int = 64 * 1024 * 1024  # a response body larger than this is forwarded but not observed
    upstream_timeout_s: float = 600.0

    @property
    def ledger_path(self) -> Path:
        return self.state_dir / "ledger.sqlite"

    @property
    def pricebook_path(self) -> Path:
        return self.state_dir / "pricebook.sqlite"

    @property
    def keys_path(self) -> Path:
        return self.state_dir / "keys.json"

    @property
    def rejects_path(self) -> Path:
        return self.state_dir / "rejects.jsonl"


def load_keys(path: Path) -> dict[str, KeyInfo]:
    """Virtual keys: a JSON object {"<key>": {"tenant": ..., "team": ..., "caller": ..., "agent": ...}}.

    A missing or broken file means no keys. In observe mode an unknown key is attributed to tenant "unknown"; the
    request is never blocked.
    """
    try:
        raw = json.loads(path.read_text())
        return {str(k): KeyInfo.model_validate(v) for k, v in raw.items()}
    except (OSError, ValueError):
        return {}

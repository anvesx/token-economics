from __future__ import annotations

import json
from pathlib import Path

from token_economics_app_admin_api.app import tail_jsonl


def test_tail_reads_past_one_block_and_drops_a_cut_first_line(tmp_path: Path) -> None:
    # Given a file much larger than the 64 KiB block
    path = tmp_path / "big.jsonl"
    path.write_text("".join(json.dumps({"n": i, "pad": "x" * 100}) + "\n" for i in range(3000)))
    # When / Then
    got = tail_jsonl(path, 1500)
    assert [d["n"] for d in got] == list(range(1500, 3000))

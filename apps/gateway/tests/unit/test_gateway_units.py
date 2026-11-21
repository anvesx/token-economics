import gzip
import json
import zlib
from pathlib import Path

import brotli
from token_economics_app_gateway.observer import decode_body
from token_economics_app_gateway.settings import Settings, load_keys


def test_compressed_bodies_are_decoded_for_observation_only() -> None:
    raw = b'{"usage": {"input_tokens": 1}}'
    assert decode_body(raw, "") == raw
    assert decode_body(gzip.compress(raw), "gzip") == raw
    assert decode_body(zlib.compress(raw), "deflate") == raw
    assert decode_body(brotli.compress(raw), "br") == raw


def test_an_unreadable_or_unknown_encoding_is_reported_not_guessed() -> None:
    assert decode_body(b"not gzip", "gzip") is None
    assert decode_body(b"x", "zstd") is None


def test_keys_file_maps_a_virtual_key_to_its_tenant(tmp_path: Path) -> None:
    (tmp_path / "keys.json").write_text(json.dumps({"vk-1": {"tenant": "devx", "caller": "dhruv"}}))
    keys = load_keys(Settings(state_dir=tmp_path).keys_path)
    assert keys["vk-1"].tenant == "devx" and keys["vk-1"].caller == "dhruv"


def test_a_missing_or_broken_keys_file_means_no_keys_not_a_crash(tmp_path: Path) -> None:
    assert load_keys(tmp_path / "missing.json") == {}
    (tmp_path / "keys.json").write_text("{not json")
    assert load_keys(tmp_path / "keys.json") == {}

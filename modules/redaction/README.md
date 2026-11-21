# token-economics-redaction

Metadata-only logging policy: what may be stored, and a scan that proves it.

Kind: module. Phase: P0. May import: token-economics-contracts.

Run alone: `uv run --package token-economics-redaction pytest modules/redaction`

## Usage

```python
from pathlib import Path
from token_economics_redaction import check_metadata_only, scan_for_content

check_metadata_only(record)  # raises ContentNotAllowed naming keys outside ALLOWED_FIELDS
hits = scan_for_content([Path("data")], ["a prompt from a fixture"])  # [(file, needle), ...]; must be []
```

`scan_for_content` reads raw bytes (UTF-8 and UTF-16-LE forms of each needle), so it also finds text inside SQLite files.

# key_revoked

Severity: info. Source: apps/gateway: Decision code key_revoked (HTTP 401). Owner: see `ops/alerts.json` (currently UNASSIGNED until a person is named).

State dir below is `$TOKEN_ECONOMICS_STATE_DIR`, default `~/.token-economics`.

## What it means

A request used a virtual key that was revoked, so the gateway refuses it with 401. Either a leaver or a rotated key still in use, or a key that leaked and is being tried.

## Who is affected

The holder of that key.

## First checks

```bash
uv run token-economics key list
sqlite3 ${TOKEN_ECONOMICS_STATE_DIR:-~/.token-economics}/tenancy.sqlite "select ts, actor, action, subject from audit order by ts desc limit 20"
uv run token-economics report --days 1   # any spend after revocation?
```

## Actions

1. If the key was revoked on purpose: nothing to do; tell the holder to use their new key (`uv run token-economics key issue --tenant <t> --caller <name>`).
2. If it keeps arriving from somewhere unexpected: treat it as a possible leak. Check the audit log, rotate the provider key if there is any doubt, and tell security.
3. If revoked by mistake: issue a new key. Revocation is not undone.

## Confirm recovery

No more `key_revoked` lines for the holder, or they now use a valid key and requests succeed.

## Escalation

Many refusals for one key from new addresses: page the owner and security.

Kill switches and CLI verbs: see [README.md](README.md).

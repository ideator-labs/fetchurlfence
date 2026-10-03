# AGENTS.md - FetchUrlFence

Cold-start handoff for a coding agent with no prior context.

## Claim proved

An MCP-style fetch tool without a URL/IP fence will record a fetch to cloud metadata (`169.254.169.254`). The same call behind `UrlFence` is denied with `blocked_metadata` and writes zero fetch log lines. A public fixture URL that redirects to a private IP is denied with `blocked_redirect_hop` before any log line is written.

Evidence from `bash demo.sh`:

1. PATH A: unguarded `fetch(http://169.254.169.254/latest/meta-data/)` produces 1 line in `data/fetches.log`. Reason `open`.
2. PATH B: fenced fetch of the same URL produces 0 lines. Response `ok=false`, reason `blocked_metadata`.
3. PATH C: fenced fetch of `http://8.8.8.8/redir` (fixture redirects to `http://10.0.0.5/secret`) produces 0 lines. Reason `blocked_redirect_hop`.

## Status: real vs stubbed

Real:

- `FenceDecision` + `check_url` / `check_redirect_chain` IP classification
- Fake `FetchTool` with optional fence and append-only fetch log
- Redirect fixture map (no live HTTP)
- Self-proving `demo.sh` with exit codes

Stubbed / not built:

- Live HTTP client or MCP SDK server
- DNS resolution / DNS-rebinding-safe dialer
- Hostname allowlists
- Patch for upstream `mcp-server-fetch`
- Hivemind OS or Workflow Core integration

## Data shape (with paths)

Primary type: `FenceDecision` in `src/fence.py`.

| Field | Meaning |
| --- | --- |
| `allowed` | may the fetch proceed |
| `reason` | `ok` \| `ok_hostname_unchecked` \| `blocked_metadata` \| `blocked_loopback` \| `blocked_link_local` \| `blocked_private` \| `blocked_special` \| `blocked_redirect_hop` \| `blocked_bad_url` \| `blocked_empty_chain` \| `open` (unguarded only) |
| `url` | URL under decision (blocked hop URL for redirect denials) |
| `host` | parsed hostname when present |
| `ip` | classified IP literal when present |

Side-effect oracle: `data/fetches.log` (one URL line per allowed fetch).

Redirect fixtures: `REDIRECT_FIXTURES` in `src/fetch_tool.py`.

## Repo map

| Path | Role |
| --- | --- |
| `src/fence.py` | `FenceDecision`, `check_url`, `check_redirect_chain` |
| `src/fetch_tool.py` | Fake fetch tool + redirect fixtures + log helpers |
| `src/__init__.py` | package marker |
| `demo.sh` | proof runner |
| `README.md` | short human summary |
| `AGENTS.md` | this file |
| `requirements.txt` | notes stdlib-only |
| `.gitignore` | ignores `data/`, caches |
| `LICENSE` | MIT |

## Setup / run / verify (fresh clone)

```bash
git clone https://github.com/ideator-labs/fetchurlfence.git
cd fetchurlfence
bash demo.sh
```

Needs Python 3.10+ on PATH. No pip install.

Expected pass (abridged):

```
PATH A (unguarded metadata): PASS
PATH B (fenced metadata): PASS
PATH C (fenced redirect-to-private): PASS
SUMMARY: 3 passed, 0 failed
ALL CLAIMS PASSED
```

Exit code 0.

What failure looks like:

- Wrong line counts or reasons print `FAIL` for that path and exit 1.
- Example: if fenced metadata still fetched, PATH B fails with `lines=1`.
- Example: if redirect hop was not re-checked, PATH C fails with reason other than `blocked_redirect_hop` or `lines=1`.

## Design decisions

1. **IP literals only in v0.** Avoids needing network or a resolver mock. Callers that already resolved a host can pass `http://<ip>/...`.
2. **Metadata checked before private/link-local.** `169.254.169.254` is both link-local and private in Python's `ipaddress`; the explicit metadata reason is the useful audit signal for CVE-2026-104120.
3. **Redirect chain is fenced hop-by-hop.** Mirrors the failure mode where the first URL is public and a later Location is private.
4. **No real network.** The demo never dials. That keeps CI hermetic and avoids touching live metadata endpoints.
5. **Fetch log is the oracle.** Allowed fetches append one line; denials append nothing.

## Known limits

- Non-literal hostnames return `ok_hostname_unchecked` (allowed). Do not treat that as a production allow.
- No DNS rebinding / TOCTOU defense (resolver-level dial filter is a next step).
- Does not replace network egress policy. Fence the tool *and* deny private ranges at the network when you can.
- Does not ship a patch for `modelcontextprotocol/servers`.

## Prioritized next steps (done-when)

1. **Resolver-level dial hook.** Classify the address the client actually connects to. Done-when: a unit test where DNS returns public then private (simulated) still denies connect.
2. **httpx/aiohttp wrapper.** Wrap a real client with hop re-validation on redirects. Done-when: an integration test against a local redirect server to a private listener is denied and the private listener access log stays empty.
3. **Hostname allowlist mode.** Optional allowlist for non-literal hosts. Done-when: unknown host is denied; allowlisted host with private resolved IP is still denied.
4. **Hivemind plug.** Expose UrlFence as a tool-gateway policy before fetch egress. Done-when: a Hivemind integration test shows metadata URL tool calls denied.
5. **Pair with EgressDrill.** Application fence + in-sandbox breakout probes. Done-when: a combined CI job runs both demos green.

## Working rules

- Name data shapes before adding branches.
- Keep `demo.sh` green before claiming done. Break one assertion on purpose once when changing proof logic, then restore.
- No em-dashes in docs.
- Do not fabricate source links.
- Prefer deleting code over adding layers.

## Context + checked sources

Built 2026-10-03 for Ideator Labs after CVE-2026-104120 on the official MCP reference fetch server. Sibling POCs cover auth gates and sandbox egress probes; this one fences the fetch tool's URL argument at the application layer.

- https://nvd.nist.gov/vuln/detail/CVE-2026-104120
- https://al-ice.ai/posts/2026/10/mcp-server-fetch-cve-2026-104120-ssrf-reference-server-unpatched/
- https://github.com/modelcontextprotocol/servers/pull/4890

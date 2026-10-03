# FetchUrlFence

Application-layer URL/IP fence for MCP-style fetch tools.

**Handoff for coding agents:** see [AGENTS.md](./AGENTS.md).

## What it proves

An unguarded fetch tool accepts a cloud-metadata URL. The same call behind `UrlFence` is rejected. A public URL that redirects to a private IP is also rejected before any fetch is recorded.

Run:

```bash
bash demo.sh
```

Needs Python 3.10+. No pip install.

## Limits

- IP-literal hosts only in v0. Hostname DNS resolution is not implemented, so DNS rebinding is out of scope.
- Redirect hops are local fixtures, not live HTTP.
- Does not patch `mcp-server-fetch`. It is a reusable fence you can put in front of a fetch tool.

## License

MIT. Copyright (c) Daniel Gerlag.

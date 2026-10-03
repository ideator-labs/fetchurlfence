"""Fake fetch tool with optional UrlFence. No real network I/O."""

from __future__ import annotations

from pathlib import Path

from fence import FenceDecision, check_redirect_chain, check_url

# Fixture: a "public" page that redirects to a private IP.
REDIRECT_FIXTURES: dict[str, list[str]] = {
    "http://8.8.8.8/redir": [
        "http://8.8.8.8/redir",
        "http://10.0.0.5/secret",
    ],
}


class FetchTool:
    def __init__(self, log_path: Path, fenced: bool = True):
        self.log_path = log_path
        self.fenced = fenced
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _record(self, url: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(url + "\n")

    def fetch(self, url: str) -> dict:
        chain = REDIRECT_FIXTURES.get(url, [url])

        if not self.fenced:
            # Unguarded path mirrors follow_redirects=True with no IP checks.
            final = chain[-1]
            self._record(final)
            return {
                "ok": True,
                "mode": "unguarded",
                "url": url,
                "fetched": final,
                "reason": "open",
            }

        decision: FenceDecision
        if len(chain) > 1:
            decision = check_redirect_chain(chain)
        else:
            decision = check_url(url)

        if not decision.allowed:
            return {
                "ok": False,
                "mode": "fenced",
                "url": url,
                "fetched": None,
                "reason": decision.reason,
                "blocked_url": decision.url,
                "blocked_ip": decision.ip,
            }

        self._record(decision.url)
        return {
            "ok": True,
            "mode": "fenced",
            "url": url,
            "fetched": decision.url,
            "reason": decision.reason,
        }


def clear_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def log_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]

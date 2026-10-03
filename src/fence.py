"""URL/IP fence for fetch-style tool arguments."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address, IPv4Address, IPv6Address
from typing import Iterable
from urllib.parse import urlparse


METADATA_NETS = (
    # AWS/GCP/Azure classic link-local metadata
    ip_address("169.254.169.254"),
)


@dataclass(frozen=True)
class FenceDecision:
    allowed: bool
    reason: str
    url: str
    host: str | None = None
    ip: str | None = None


def _classify_ip(addr: IPv4Address | IPv6Address) -> str | None:
    if addr in METADATA_NETS:
        return "blocked_metadata"
    if addr.is_loopback:
        return "blocked_loopback"
    if addr.is_link_local:
        return "blocked_link_local"
    if addr.is_private:
        return "blocked_private"
    if addr.is_unspecified or addr.is_multicast or addr.is_reserved:
        return "blocked_special"
    return None


def check_url(url: str) -> FenceDecision:
    """Classify a single URL. Only IP-literal hosts are classified in v0.

    Hostname resolution is intentionally out of scope for this POC so the
    demo needs no network. Callers that already resolved a host can pass an
    http://<ip>/... URL, or use check_redirect_chain with IP literals.
    """
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return FenceDecision(False, "blocked_bad_url", url)

    try:
        addr = ip_address(host)
    except ValueError:
        # Non-literal hostnames are not auto-resolved here.
        return FenceDecision(True, "ok_hostname_unchecked", url, host=host)

    blocked = _classify_ip(addr)
    if blocked:
        return FenceDecision(False, blocked, url, host=host, ip=str(addr))
    return FenceDecision(True, "ok", url, host=host, ip=str(addr))


def check_redirect_chain(urls: Iterable[str]) -> FenceDecision:
    """Fence every hop. First blocked hop wins; reason becomes blocked_redirect_hop
    when the blocking hop is not the initial URL.
    """
    urls = list(urls)
    if not urls:
        return FenceDecision(False, "blocked_empty_chain", "")

    for i, url in enumerate(urls):
        decision = check_url(url)
        if not decision.allowed:
            if i == 0:
                return decision
            return FenceDecision(
                False,
                "blocked_redirect_hop",
                url,
                host=decision.host,
                ip=decision.ip,
            )
    last = check_url(urls[-1])
    return FenceDecision(True, "ok", urls[-1], host=last.host, ip=last.ip)

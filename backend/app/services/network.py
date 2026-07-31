"""SSRF protection for outbound requests to user-provided URLs.

The guard resolves DNS once, re-checks that every resolved address is public,
and pins httpx's TCP connection to the validated literal IP — defeating
DNS-rebinding TOCTOU between a pre-check and the actual connect.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

_SCRAPER_USER_AGENT = "BrunoFreshBot/1.0"
_DEFAULT_TIMEOUT = 30.0


def _is_private_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_public_host(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    return not any(_is_private_ip(info[4][0]) for info in infos)


def _resolve_public(host: str, port: int, *, type_: int = socket.SOCK_STREAM) -> list[tuple]:
    """Resolve ``host`` to addrinfos, raising if any resolved IP is non-public.

    Returns the full filtered list (all public) so callers can pin one without a
    second DNS resolution.
    """
    try:
        infos = socket.getaddrinfo(host, port, type=type_)
    except socket.gaierror as exc:
        raise httpx.ConnectError(f"DNS resolution failed for {host}") from exc
    for info in infos:
        if _is_private_ip(info[4][0]):
            raise httpx.ConnectError(
                f"SSRF: {host} resolves to a private address ({info[4][0]})"
            )
    return infos


class _PinnedAsyncBackend:
    """anyio-style async network backend that resolves once and pins the IP.

    httpcore passes the URL hostname (string) into ``connect_tcp``; anyio then
    resolves it again internally. By overriding here we (1) resolve via our
    own ``getaddrinfo`` with SSRF filtering, and (2) hand connect_tcp a literal
    IP so httpx's downstream resolution is bypassed. TLS SNI / cert verification
    still use the original URL host (handled by httpcore on top of the raw TCP
    stream), so HTTPS keeps working.
    """

    def __init__(self) -> None:
        from httpcore._backends.anyio import AnyIOBackend
        self._inner = AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        infos = await asyncio.to_thread(_resolve_public, host, port)
        pinned_ip, pinned_port, *_ = infos[0][4]
        return await self._inner.connect_tcp(
            host=pinned_ip,
            port=pinned_port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    def __getattr__(self, name):
        return getattr(self._inner, name)


class _PinnedSyncBackend:
    """Sync twin of ``_PinnedAsyncBackend`` for ``httpx.Client``."""

    def __init__(self) -> None:
        from httpcore._backends.sync import SyncBackend
        self._inner = SyncBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        infos = _resolve_public(host, port)
        pinned_ip, pinned_port, *_ = infos[0][4]
        return self._inner.connect_tcp(
            host=pinned_ip,
            port=pinned_port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    def __getattr__(self, name):
        return getattr(self._inner, name)


class SSRFGuardedTransport(httpx.AsyncHTTPTransport):
    """Async transport whose TCP connection is pinned to an SSRF-checked IP."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # httpcore stores the resolver/network backend at this attribute.
        self._pool._network_backend = _PinnedAsyncBackend()  # type: ignore[attr-defined]


class SSRFGuardedSyncTransport(httpx.HTTPTransport):
    """Synchronous version of :class:`SSRFGuardedTransport` for ``httpx.Client``."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pool._network_backend = _PinnedSyncBackend()  # type: ignore[attr-defined]


def create_ssrf_safe_client(
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    user_agent: str = _SCRAPER_USER_AGENT,
) -> httpx.AsyncClient:
    """Return an ``httpx.AsyncClient`` that pins TCP connections to SSRF-checked
    resolved IPs, defeating DNS-rebinding between pre-check and connect.

    **Usage**: use as an async context manager::

        async with create_ssrf_safe_client() as client:
            resp = await client.get(url)
    """
    return httpx.AsyncClient(
        transport=SSRFGuardedTransport(),
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers={"User-Agent": user_agent},
    )


async def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed")

    hostname = parsed.hostname or ""
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL host")

    is_public = await asyncio.to_thread(is_public_host, hostname)
    if not is_public:
        raise HTTPException(status_code=400, detail="Private or invalid network target rejected")

    return url
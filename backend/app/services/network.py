"""SSRF protection for outbound requests to user-provided URLs.

Every such request must go through the SSRF-guarded clients/transports so that
DNS rebinding is blocked at connect time, not just at URL-validation time.
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


def _assert_public_host(host: str, port: int) -> None:
    try:
        infos = socket.getaddrinfo(host, port)
    except socket.gaierror as exc:
        raise httpx.ConnectError(f"DNS resolution failed for {host}") from exc
    for info in infos:
        if _is_private_ip(info[4][0]):
            raise httpx.ConnectError(
                f"SSRF: {host} resolves to a private address ({info[4][0]})"
            )


class SSRFGuardedTransport(httpx.AsyncHTTPTransport):
    """Custom async transport that re-validates the resolved IP immediately before
    connecting, closing the DNS-rebinding window between our pre-check and
    the actual TCP connection.
    """

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        await asyncio.to_thread(_assert_public_host, host, port)
        return await super().handle_async_request(request)


class SSRFGuardedSyncTransport(httpx.HTTPTransport):
    """Synchronous version of SSRFGuardedTransport for use with httpx.Client."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        _assert_public_host(host, port)
        return super().handle_request(request)


def create_ssrf_safe_client(
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    follow_redirects: bool = True,
    user_agent: str = _SCRAPER_USER_AGENT,
) -> httpx.AsyncClient:
    """Return an ``httpx.AsyncClient`` that validates DNS resolution at connect
    time, closing the DNS-rebinding window between pre-check and actual TCP
    connection.

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

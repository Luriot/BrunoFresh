from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException


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


class SSRFGuardedTransport(httpx.AsyncHTTPTransport):
    """Custom transport that re-validates the resolved IP immediately before
    connecting, closing the DNS-rebinding window between our pre-check and
    the actual TCP connection.
    """

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        try:
            infos = await asyncio.to_thread(socket.getaddrinfo, host, port)
        except socket.gaierror as exc:
            raise httpx.ConnectError(f"DNS resolution failed for {host}") from exc
        for info in infos:
            if _is_private_ip(info[4][0]):
                raise httpx.ConnectError(
                    f"SSRF: {host} resolves to a private address ({info[4][0]})"
                )
        return await super().handle_async_request(request)


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


async def validate_public_host_for_download(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    hostname = parsed.hostname or ""
    if not hostname:
        return False

    return await asyncio.to_thread(is_public_host, hostname)

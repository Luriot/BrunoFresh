"""Unit tests for app.services.network — no actual network calls."""
from __future__ import annotations

import pytest

from fastapi import HTTPException

from app.services.network import _is_private_ip, validate_public_http_url


# ── _is_private_ip ────────────────────────────────────────────────────────────

class TestIsPrivateIp:
    @pytest.mark.parametrize("ip", [
        "127.0.0.1",       # loopback
        "127.0.0.2",       # loopback range
        "::1",             # IPv6 loopback
        "10.0.0.1",        # RFC-1918
        "10.255.255.255",  # RFC-1918
        "192.168.0.1",     # RFC-1918
        "192.168.100.50",  # RFC-1918
        "172.16.0.1",      # RFC-1918
        "172.31.255.255",  # RFC-1918
        "169.254.0.1",     # link-local
        "169.254.169.254", # AWS metadata endpoint
        "0.0.0.0",         # unspecified
        "224.0.0.1",       # multicast
    ])
    def test_private_ips_return_true(self, ip: str):
        assert _is_private_ip(ip) is True, f"{ip!r} should be private"

    @pytest.mark.parametrize("ip", [
        "8.8.8.8",                   # Google DNS
        "1.1.1.1",                   # Cloudflare DNS
        "104.21.0.0",                # Cloudflare public
        "2001:4860:4860::8888",      # Google IPv6 DNS
    ])
    def test_public_ips_return_false(self, ip: str):
        assert _is_private_ip(ip) is False, f"{ip!r} should be public"


# ── validate_public_http_url ──────────────────────────────────────────────────

class TestValidatePublicHttpUrl:
    async def test_ftp_scheme_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            await validate_public_http_url("ftp://example.com/file.txt")
        assert exc_info.value.status_code == 400

    async def test_no_scheme_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            await validate_public_http_url("example.com/path")
        assert exc_info.value.status_code == 400

    async def test_empty_host_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            await validate_public_http_url("http:///path")
        assert exc_info.value.status_code == 400

    async def test_localhost_raises_400(self):
        """localhost resolves to 127.0.0.1 which is private."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_public_http_url("http://localhost/resource")
        assert exc_info.value.status_code == 400

    async def test_private_ip_url_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            await validate_public_http_url("http://192.168.1.1/api")
        assert exc_info.value.status_code == 400

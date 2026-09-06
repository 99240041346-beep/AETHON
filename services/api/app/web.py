from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx


class WebPolicyError(ValueError):
    pass


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise WebPolicyError("only absolute HTTP(S) URLs are allowed")
    host = parsed.hostname
    try:
        addresses = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise WebPolicyError("hostname could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise WebPolicyError("private or non-public network targets are blocked")
    return url


class WebFetcher:
    def __init__(self, timeout: float = 10.0, max_bytes: int = 1_000_000):
        self.timeout = timeout
        self.max_bytes = max_bytes

    def fetch(self, url: str) -> dict:
        validate_public_url(url)
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            response = client.get(url, headers={"User-Agent": "AETHON-Web/0.1"})
        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise WebPolicyError("redirect without location")
            validate_public_url(str(httpx.URL(url).join(location)))
            raise WebPolicyError("redirects require explicit re-validation")
        response.raise_for_status()
        content = response.content
        if len(content) > self.max_bytes:
            raise WebPolicyError("response exceeds configured size limit")
        return {
            "url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "text": response.text,
        }

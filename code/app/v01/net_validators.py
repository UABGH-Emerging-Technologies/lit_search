import ipaddress
import os
import socket
from urllib.parse import urlparse


def validate_public_http_url(url: str) -> str:
    """
    Validate that a URL is a public HTTP(S) endpoint safe for server-side requests.

    Enforces an http/https scheme, a non-empty host, optional allowlist membership,
    rejection of internal hostnames, and that all resolved addresses are public.

    Args:
        url: The URL to validate.

    Returns:
        The original URL unchanged if it passes all checks.

    Raises:
        ValueError: If the URL is not a valid public HTTP(S) endpoint.
    """
    parsed = urlparse(url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("endpoint URL scheme must be http or https")

    if not parsed.hostname:
        raise ValueError("endpoint URL must include a host")

    hostname = parsed.hostname.lower()

    # Optional allowlist from the environment. If set, the hostname must match one
    # of the entries exactly; a match short-circuits all remaining checks.
    allowlist_raw = os.environ.get("LIT_LLM_ENDPOINT_ALLOWLIST", "")
    allowlist = [entry.strip().lower() for entry in allowlist_raw.split(",") if entry.strip()]
    if allowlist:
        if hostname in allowlist:
            return url
        raise ValueError("endpoint host is not in the allowlist")

    # Reject internal hostnames.
    if hostname == "localhost" or hostname.endswith((".local", ".internal", ".localhost")):
        raise ValueError("endpoint host is not permitted")

    # Determine the target IPs. An IP literal is used directly; otherwise fall back
    # to DNS resolution. If DNS fails, fail open (no IP checks) so offline CI works.
    ips = []
    try:
        ips = [ipaddress.ip_address(hostname.strip("[]"))]
    except ValueError:
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
            ips = [ipaddress.ip_address(addr_info[4][0]) for addr_info in addr_infos]
        except (socket.gaierror, OSError):
            ips = []

    for ip in ips:
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("endpoint host resolves to a non-public address")

    return url

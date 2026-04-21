"""
Network Utilities
=================
Provides LAN-facing helpers used by the Settings API.

detect_server_ip()
    Uses the routing-table probe trick (connect to 8.8.8.8:80 without
    sending any data) to discover the machine's primary LAN IP address.
    No internet traffic is actually sent — the OS just resolves which
    local interface it would use for that route.

    Returns '127.0.0.1' as a safe fallback if detection fails (e.g. no
    network interfaces available on a stripped-down test environment).
"""

import socket
import logging

logger = logging.getLogger(__name__)


def detect_server_ip() -> str:
    """
    Detects the primary LAN IP of the current machine.

    Algorithm:
        1. Create a UDP socket (no packets sent — UDP is connectionless).
        2. 'Connect' to an external address (8.8.8.8:80) to force the OS
           to resolve which local interface to use.
        3. Read getsockname() to get that interface's IP.
        4. Close the socket immediately.

    This works correctly on:
        - Linux (LaspberryPi, Ubuntu servers)
        - macOS (development machines)
        - Windows (admin panel server)

    Returns:
        str: The primary LAN IP (e.g. '192.168.1.15') or '127.0.0.1'
             if detection fails.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        logger.debug("Detected server LAN IP: %s", ip)
        return ip
    except Exception as exc:
        logger.warning("Could not detect server LAN IP: %s — defaulting to 127.0.0.1", exc)
        return "127.0.0.1"

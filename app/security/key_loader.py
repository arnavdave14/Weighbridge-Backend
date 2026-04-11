"""
Secure Key Loader
=================
Priority chain:
  1. OS Keyring (keyring library — backed by macOS Keychain / Linux Secret Service / Windows DPAPI)
  2. Environment variable fallback (with a loud warning)
  3. Hard-fail in production if the key is still at the default placeholder.

This module is the ONLY place that reads/writes secrets. Every other module
imports from here — never from os.environ directly.

Usage:
    from app.security.key_loader import get_secret, set_secret
"""

import os
import logging
import warnings
from typing import Optional, Union

logger = logging.getLogger(__name__)

# ─── Keyring Service Name ────────────────────────────────────────────────────
# This is what appears under "Keychain Access" on macOS.
_KEYRING_SERVICE = "weighbridge-edge"

# ─── Sentinel for unset keys ─────────────────────────────────────────────────
_DEFAULT_DB_KEY    = "default_dev_key_change_me"
_DEFAULT_LOCAL_KEY = "default_local_secret_change_me"


def _try_import_keyring():
    """Returns the keyring module or None if unavailable."""
    try:
        import keyring as _keyring
        return _keyring
    except ImportError:
        return None


def get_secret(key_name: str, *, env_fallback: Optional[str] = None) -> Optional[str]:
    """
    Retrieve a secret by name.

    Args:
        key_name:     Logical name of the secret (e.g. "DB_MASTER_KEY").
        env_fallback: Name of the environment variable to fall back to.

    Returns the secret string, or None if not found anywhere.
    """
    _kr = _try_import_keyring()

    # 1. Try OS keyring first
    if _kr is not None:
        try:
            value = _kr.get_password(_KEYRING_SERVICE, key_name)
            if value:
                logger.debug("Secret '%s' loaded from OS keyring.", key_name)
                return value
        except Exception as exc:  # noqa: BLE001
            logger.warning("Keyring read failed for '%s': %s. Falling back to env.", key_name, exc)

    # 2. Fall back to environment variable
    if env_fallback:
        value = os.environ.get(env_fallback)
        if value:
            warnings.warn(
                f"Secret '{key_name}' loaded from environment variable '{env_fallback}'. "
                "Store it in the OS keyring for production use: "
                f"  python -c \"from app.security.key_loader import set_secret; set_secret('{key_name}', '<VALUE>')\"",
                stacklevel=2,
            )
            return value

    return None


def set_secret(key_name: str, value: str) -> bool:
    """
    Persist a secret into the OS keyring.

    Returns True on success, False if keyring is unavailable.
    """
    _kr = _try_import_keyring()
    if _kr is None:
        logger.error("keyring package not installed. Cannot persist secret '%s' to OS keyring.", key_name)
        return False

    try:
        _kr.set_password(_KEYRING_SERVICE, key_name, value)
        logger.info("Secret '%s' stored in OS keyring successfully.", key_name)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to store secret '%s' in OS keyring: %s", key_name, exc)
        return False


def delete_secret(key_name: str) -> bool:
    """Remove a secret from the OS keyring."""
    _kr = _try_import_keyring()
    if _kr is None:
        return False
    try:
        _kr.delete_password(_KEYRING_SERVICE, key_name)
        return True
    except Exception:  # noqa: BLE001
        return False


def load_db_master_key() -> str:
    """
    Returns the SQLCipher database master key.
    Resolution order: keyring → DB_MASTER_KEY env var → default (dev only).
    """
    key = get_secret("DB_MASTER_KEY", env_fallback="DB_MASTER_KEY")

    if not key:
        key = _DEFAULT_DB_KEY

    _assert_not_default_in_production("DB_MASTER_KEY", key, _DEFAULT_DB_KEY)
    return key


def load_local_api_secret() -> str:
    """
    Returns the X-Local-Secret token.
    Resolution order: keyring → LOCAL_API_SECRET env var → default (dev only).
    """
    key = get_secret("LOCAL_API_SECRET", env_fallback="LOCAL_API_SECRET")

    if not key:
        key = _DEFAULT_LOCAL_KEY

    _assert_not_default_in_production("LOCAL_API_SECRET", key, _DEFAULT_LOCAL_KEY)
    return key


def _assert_not_default_in_production(name: str, value: str, default: str):
    """Raise in production if secret is still at its placeholder default."""
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production" and value == default:
        raise RuntimeError(
            f"CRITICAL BOOT FAILURE: Secret '{name}' is still at the default dev placeholder. "
            "Set it via the OS keyring before deploying to production:\n"
            f"  python -c \"from app.security.key_loader import set_secret; "
            f"set_secret('{name}', '<STRONG_RANDOM_VALUE>')\""
        )

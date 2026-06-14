"""API key validation for Brevitas Systems."""
from __future__ import annotations

import hashlib
import os
import re
from typing import Optional

_KEY_PREFIX = "bvt_"
_KEY_PATTERN = re.compile(r"^bvt_[A-Za-z0-9_\-]{32,}$")

_VALIDATION_URL = os.getenv(
    "BREVITAS_VALIDATION_URL",
    "https://api.brevitas.systems/v1/auth/validate",
)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def validate_key(key: str, *, offline: bool = False) -> None:
    """Raise ValueError if the key is invalid.

    Performs format validation always; also pings the Brevitas auth endpoint
    unless offline=True or BREVITAS_OFFLINE=1 is set.
    """
    if not key or not _KEY_PATTERN.match(key):
        raise ValueError(
            f"Invalid Brevitas API key format. Keys must start with '{_KEY_PREFIX}'. "
            "Generate one at https://brevitas.systems/dashboard."
        )

    if offline or os.getenv("BREVITAS_OFFLINE") == "1":
        return

    try:
        import requests

        resp = requests.post(
            _VALIDATION_URL,
            json={"key_hash": _hash_key(key)},
            timeout=5,
        )
        if resp.status_code == 401:
            raise ValueError(
                "Brevitas API key is invalid or has been revoked. "
                "Check your key at https://brevitas.systems/dashboard."
            )
        # Any non-auth error (network, 5xx) → fall through silently so
        # users aren't blocked by transient outages.
    except ValueError:
        raise
    except Exception:
        pass


def resolve_key(api_key: Optional[str]) -> str:
    """Return the key from the argument or BREVITAS_API_KEY env var."""
    key = api_key or os.getenv("BREVITAS_API_KEY", "")
    if not key:
        raise ValueError(
            "No Brevitas API key provided. Pass api_key= to optimize() or "
            "set the BREVITAS_API_KEY environment variable. "
            "Generate a key at https://brevitas.systems/dashboard."
        )
    return key

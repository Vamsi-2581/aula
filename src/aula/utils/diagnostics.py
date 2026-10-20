"""Credential redaction for diagnostic copies, without modifying wire data."""

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SECRET_FIELDS = {
    "accesstoken",
    "refreshtoken",
    "idtoken",
    "token",
    "authorization",
    "proxyauthorization",
    "cookie",
    "cookies",
    "setcookie",
    "phpsessid",
    "csrftoken",
    "csrfptoken",
    "code",
    "codeverifier",
    "state",
    "password",
    "samlresponse",
    "samlrequest",
    "relaystate",
    "requestverificationtoken",
    "mitidauthcode",
    "sessionuuid",
    "challenge",
}


def diagnostic_url(url: object) -> str:
    """Retain destination and query names; omit credentials and all query values."""
    try:
        parts = urlsplit(str(url))
        authority = parts.netloc.rsplit("@", 1)[-1]
        query = urlencode(
            [(key, "[redacted]") for key, _ in parse_qsl(parts.query, keep_blank_values=True)]
        )
        return urlunsplit((parts.scheme, authority, parts.path, query, ""))
    except ValueError:
        return "[invalid URL]"


def redact_credentials(value: Any) -> Any:
    """Copy nested structures, replacing recognized credential fields before logging."""
    if isinstance(value, dict):
        return {
            key: "[redacted]"
            if "".join(c for c in str(key).lower() if c.isalnum()) in _SECRET_FIELDS
            else redact_credentials(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_credentials(item) for item in value]
    if isinstance(value, str) and "://" in value:
        return diagnostic_url(value)
    return value

"""Descriptor helpers shared by the adapters."""

from __future__ import annotations

import re

from . import http

_TOKEN_RE = re.compile(r"[\x21-\x7e]+")


def field(key, scope, label, *, type="string", help="", required=False, default=None,
          placeholder=None, options=None, resource=None, visible_when=None):
    """One entry of an adapter's ``fields`` descriptor, in the exact JSON shape."""
    return {
        "key": key,
        "scope": scope,
        "type": type,
        "label": label,
        "help": help,
        "required": required,
        "default": default,
        "placeholder": placeholder,
        "options": options,
        "resource": resource,
        "visible_when": visible_when,
    }


def fact(label, value, tone="neutral"):
    return {"label": label, "value": str(value), "tone": tone}


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def check_token(token):
    """The token when it is printable ASCII without spaces, else a ``FetchError``."""
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        raise http.FetchError(
            "invalid_token", "The stored token contains characters that cannot be sent in a header"
        )
    return token

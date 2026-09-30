"""A redirect guard shared by every module that sends a request off this machine.

`update.py` hands it a host-allowlist check and `integrations/http.py` a same-origin
check; neither imports the other.
"""

from __future__ import annotations

import urllib.request


class RestrictedRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only when ``check(newurl)`` accepts it (it raises otherwise)."""

    def __init__(self, check):
        super().__init__()
        self._check = check

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._check(newurl)
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )

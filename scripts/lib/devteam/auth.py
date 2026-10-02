"""``devteam auth``: sign in, sign out, license state, profile and account deletion (ADR-0029).

The CLI owns the session; the desktop app and the installers call these commands and never
talk to the identity provider themselves. Handlers return ``(payload, human)`` like every
other command, and nothing here prints on its own, so the ``--json`` contract holds.

Exit codes (a code never changes meaning once released):

====  =====================================================================================
0     success; for ``check``, the account is entitled
1     the server said no: wrong credential or code, dead session, not signed in; for
      ``check``, signed out, ``trial_expired``, ``banned`` or an invalid cached license
2     usage: bad flag, a password outside the policy, a code that is not 8 digits
3     environment: server unreachable, rate limited (``details.retry_after``), no display
      for a browser sign-in, secret store unavailable, build without an account server;
      for ``check``, an online check is required and could not be made
4     conflict: the store lock could not be taken
====  =====================================================================================

Secrets: a code or a password is read from the terminal without echo, or as one line from
stdin, in the order the command prompts; there is no flag that takes one (SR-9). Nothing
secret is written to stdout, stderr, ``--json`` or an exception (SR-18). Every rejection of
a credential or code is the same fixed text, and ``otp start`` and ``password reset`` answer
identically whether or not the address is registered (SR-10).
"""

from __future__ import annotations

import sys
import time

from . import auth_gotrue as gotrue
from . import auth_oauth as oauth
from . import auth_session as session
from . import entitlement
from .auth_gotrue import Rejected
from .errors import EXIT_ENVIRONMENT, EXIT_FINDINGS, DevteamError, EnvError, UsageError

SENT_MESSAGE = (
    "If this address can sign in, a code was sent to it. The code is valid for 10 minutes."
)
CONFIRM_ANSWER = "delete"


class EntitlementRefusal(DevteamError):
    """``check`` found the account not entitled. Carries the state at the top level.

    Exit ``1`` when the server or the local record says no, ``3`` when the answer needs an
    online check that could not be made. The body is the same shape a passing ``check``
    returns, plus the error fields, so a caller reads one schema.
    """

    def __init__(self, exit_code, message, hint, view):
        entitlement_view = view["entitlement"]
        super().__init__(
            message, hint, {"reason": entitlement_view["reason"] or entitlement_view["status"]}
        )
        self.exit_code = exit_code
        self.view = view

    def payload(self):
        body = super().payload()
        body.update(self.view)
        return body


# ── shared plumbing ───────────────────────────────────────────────────────────


def _identity(emitter, network=True):
    identity = entitlement.load_identity()
    warning = entitlement.seam_warning(identity)
    if warning:
        emitter.stderr.write(warning + "\n")
    if network and not identity.configured:
        raise EnvError(
            "this build has no account server configured",
            hint="Use a released build of dev-team-agents.",
            details={"reason": gotrue.REASON_NOT_CONFIGURED},
        )
    return identity


def _is_console():
    from . import cli

    return cli._stdin_is_console()


def _prompt(text):
    sys.stderr.write(text)
    sys.stderr.flush()


def _read_secret(prompt):
    """One secret: no echo on a terminal, one line from stdin otherwise. Never from argv."""
    if _is_console():
        import getpass

        return getpass.getpass(prompt)
    stream = sys.stdin
    line = stream.readline() if stream is not None else ""
    if line == "":
        raise UsageError(
            "expected a value on stdin",
            hint="Values are read one per line, in the order the command asks for them.",
        )
    return line.rstrip("\r\n")


def _read_optional_line(prompt):
    if _is_console():
        import getpass

        return getpass.getpass(prompt)
    line = sys.stdin.readline() if sys.stdin is not None else ""
    return line.rstrip("\r\n")


def _read_new_password(prompt="new password: "):
    first = _read_secret(prompt)
    if _is_console():
        if _read_secret("repeat the new password: ") != first:
            raise UsageError("the two passwords do not match")
    return first


def _require_session():
    meta = session.read_meta()
    if meta is None:
        raise Rejected(gotrue.REASON_NOT_SIGNED_IN, hint="Run `devteam auth login`.")
    return meta


def _account_view(meta):
    if meta is None:
        return None
    return {
        "id": meta["account_id"],
        "email": meta.get("email"),
        "display_name": meta.get("display_name"),
        "provider": meta.get("provider"),
        "signed_in_at": meta.get("signed_in_at"),
    }


def _state_view(identity, meta, result, online=None, warnings=None):
    backend, insecure = session.backend_view(meta)
    notes = list(warnings or [])
    if insecure:
        notes.append(session.insecure_warning())
    return {
        "signed_in": meta is not None,
        "account": _account_view(meta),
        "entitled": result.usable,
        "entitlement": result.to_dict(),
        "online": online or {"attempted": False, "ok": None},
        "last_online_check": meta.get("last_online_check") if meta else None,
        "secret_backend": backend,
        "secret_backend_insecure": insecure,
        "environment": identity.environment,
        "test_seam": identity.test_seam,
        "warnings": notes,
    }


def _state_human(view, headline=None):
    lines = [headline] if headline else []
    account = view["account"]
    if account:
        who = account["email"] or account["id"]
        lines.append("signed in as {}".format(who))
        if account.get("display_name"):
            lines.append("  name         {}".format(account["display_name"]))
        lines.append("  sign-in      {}".format(account.get("provider") or "unknown"))
    else:
        lines.append("not signed in")
    entitlement_view = view["entitlement"]
    state = entitlement_view["status"]
    if entitlement_view["reason"]:
        state += " ({})".format(entitlement_view["reason"])
    lines.append("  license      {}".format(state))
    if entitlement_view["expires_at"]:
        lines.append(
            "  valid until  {}".format(
                time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(entitlement_view["expires_at"]))
            )
        )
    if view["online"]["attempted"] and not view["online"]["ok"]:
        lines.append("  online check failed; using the cached license")
    if view["test_seam"]:
        lines.append("  test seam    active")
    for note in view["warnings"]:
        lines.append("warning: {}".format(note))
    return "\n".join(lines)


def _complete_login(emitter, identity, client, sess, provider, method, warnings=None):
    """Store the session, fetch the license, and describe the result."""
    meta = session.save_session(sess, provider)
    notes = list(warnings or [])
    try:
        result = session.fetch_entitlement(client, identity, sess["access_token"])
    except DevteamError as exc:
        notes.append("could not fetch the license now: {}".format(exc.message))
        result = entitlement.check(identity, meta["account_id"])
    view = _state_view(identity, meta, result, {"attempted": True, "ok": result.usable}, notes)
    view["method"] = method
    return view, _state_human(view, "signed in")


# ── sign-in flows ─────────────────────────────────────────────────────────────


def _oauth_session(emitter, identity, client, provider, link_access=None):
    if not oauth.can_open_browser():
        raise EnvError(
            "no display is available to open a browser on",
            hint="Sign in with `devteam auth login --email` instead.",
            details={"reason": "headless"},
        )
    verifier, challenge = oauth.new_pkce()
    with oauth.Listener(oauth.new_state()) as listener:
        if link_access:
            url = client.link_identity_url(
                link_access,
                provider,
                listener.redirect_to,
                challenge,
                scopes=oauth.PROVIDER_SCOPES.get(provider),
            )
        else:
            url = oauth.authorize_url(identity.supabase_url, provider, listener.redirect_to, challenge)
        emitter.line("Opening your browser to continue with {}...".format(provider))
        if not oauth.open_browser(url):
            emitter.warn("could not open a browser; open this address on this machine: {}".format(url))
        outcome = listener.wait()
    if outcome.get("failed"):
        raise Rejected("oauth_failed", "the browser sign-in did not complete")
    return client.pkce_exchange(outcome["code"], verifier)


def _swallow_rejection(call):
    """Run a request whose rejection must look like success (SR-10). Other errors propagate."""
    try:
        call()
    except Rejected:
        pass


def cmd_login(args, emitter):
    identity = _identity(emitter)
    client = gotrue.Client(identity)
    if args.google or args.github:
        provider = "google" if args.google else "github"
        sess = _oauth_session(emitter, identity, client, provider)
        return _complete_login(emitter, identity, client, sess, provider, "oauth-" + provider)
    if not args.email:
        raise UsageError("choose a sign-in method: --google, --github or --email ADDRESS")
    if args.signup and not args.password:
        raise UsageError("--signup goes with --password")
    email = gotrue.normalize_email(args.email)
    if args.password:
        return _login_password(args, emitter, identity, client, email)
    name = gotrue.normalize_display_name(args.name) if args.name else None
    _swallow_rejection(lambda: client.otp_start(email, True, name))
    emitter.line(SENT_MESSAGE)
    code = gotrue.normalize_code(_read_secret("code: "))
    sess = client.verify(email, code, "email")
    return _complete_login(emitter, identity, client, sess, "email", "email-otp")


def _login_password(args, emitter, identity, client, email):
    if args.signup:
        name = gotrue.normalize_display_name(args.name) if args.name else None
        password = gotrue.validate_new_password(_read_new_password("password: "))
        _swallow_rejection(lambda: client.sign_up(email, password, name))
        emitter.line(SENT_MESSAGE)
        code = gotrue.normalize_code(_read_secret("confirmation code: "))
        sess = client.verify(email, code, "signup")
        return _complete_login(emitter, identity, client, sess, "email", "password-signup")
    password = gotrue.normalize_password(_read_secret("password: "))
    sess = client.sign_in_password(email, password)
    return _complete_login(emitter, identity, client, sess, "email", "password")


def cmd_otp_start(args, emitter):
    identity = _identity(emitter)
    email = gotrue.normalize_email(args.email)
    name = gotrue.normalize_display_name(args.name) if args.name else None
    client = gotrue.Client(identity)
    _swallow_rejection(lambda: client.otp_start(email, True, name))
    return {"sent": True, "message": SENT_MESSAGE, "expires_in": 600}, SENT_MESSAGE


def cmd_otp_verify(args, emitter):
    identity = _identity(emitter)
    email = gotrue.normalize_email(args.email)
    code = gotrue.normalize_code(_read_secret("code: "))
    client = gotrue.Client(identity)
    sess = client.verify(email, code, "email")
    return _complete_login(emitter, identity, client, sess, "email", "email-otp")


def cmd_logout(args, emitter):
    identity = _identity(emitter, network=False)
    meta = session.read_meta()
    revoked = None
    if meta is not None and identity.configured:
        client = gotrue.Client(identity)
        try:
            client.logout(session.access_token(client), "local")
            revoked = True
        except DevteamError:
            revoked = False
    local = session.clear_local()
    payload = dict(local, signed_in=False, was_signed_in=meta is not None, server_revoked=revoked)
    if not all(local.values()):
        raise EnvError(
            "could not remove all of the local session",
            hint="Fix the permissions on the data store and run `devteam auth logout` again.",
            details=payload,
        )
    lines = ["signed out" if meta is not None else "not signed in"]
    if revoked is False:
        lines.append("the server could not be reached to revoke the session; it was removed here")
    return payload, "\n".join(lines)


# ── license state ─────────────────────────────────────────────────────────────


def _resolve(identity, offline):
    """The session, the cached license and what an online check added, if one was due."""
    meta = session.read_meta()
    result = entitlement.check(identity, meta["account_id"] if meta else None)
    online = {"attempted": False, "ok": None}
    if offline or not identity.configured or not session.should_refresh(result, meta):
        return meta, result, online
    online["attempted"] = True
    client = gotrue.Client(identity)
    try:
        result = session.sync_entitlement(client, identity)
        online["ok"] = result.status != entitlement.STATUS_INVALID
    except Rejected as exc:
        online.update(ok=False, reason=exc.reason)
        if exc.reason in (gotrue.REASON_SESSION_EXPIRED, gotrue.REASON_NOT_SIGNED_IN):
            session.clear_local()
            meta = None
            result = entitlement.EntitlementResult(
                status=entitlement.STATUS_SIGNED_OUT, reason="session_expired"
            )
    except DevteamError as exc:
        online.update(ok=False, reason=exc.details.get("reason", "error"))
        session.note_failed_attempt()
    return meta, result, online


def cmd_status(args, emitter):
    identity = _identity(emitter, network=False)
    meta, result, online = _resolve(identity, args.offline)
    view = _state_view(identity, meta, result, online)
    view["offline"] = bool(args.offline)
    return view, _state_human(view)


_REFUSALS = {
    entitlement.STATUS_SIGNED_OUT: (EXIT_FINDINGS, "you are not signed in", "Run `devteam auth login`."),
    entitlement.STATUS_TRIAL_EXPIRED: (
        EXIT_FINDINGS,
        "the trial for this account has ended",
        "Run `devteam auth status` for details.",
    ),
    entitlement.STATUS_BANNED: (
        EXIT_FINDINGS,
        "this account is blocked",
        "Run `devteam auth status` for details.",
    ),
    entitlement.STATUS_INVALID: (
        EXIT_FINDINGS,
        "the stored license is not valid",
        "Sign in again with `devteam auth login`.",
    ),
    entitlement.STATUS_NEEDS_ONLINE_CHECK: (
        EXIT_ENVIRONMENT,
        "an online license check is required",
        "Connect to the internet and run `devteam auth check`, or sign in again.",
    ),
}


def cmd_check(args, emitter):
    """Exit 0 when entitled; 1 when not; 3 when an online check is needed and could not be made.

    The body, success or failure, always carries ``entitled``, ``entitlement`` and the rest
    of the ``status`` shape, so the gate and the installers parse one schema (SR-42).
    """
    identity = _identity(emitter, network=False)
    meta, result, online = _resolve(identity, args.offline)
    view = _state_view(identity, meta, result, online)
    view["offline"] = bool(args.offline)
    if result.usable:
        return view, _state_human(view)
    code, message, hint = _REFUSALS.get(result.status, _REFUSALS[entitlement.STATUS_INVALID])
    if result.status == entitlement.STATUS_INVALID and online.get("ok") is False:
        code, message, hint = _REFUSALS[entitlement.STATUS_NEEDS_ONLINE_CHECK]
    raise EntitlementRefusal(code, message, hint, view)


# ── passwords ─────────────────────────────────────────────────────────────────


def _revoke_others(client, access_token):
    try:
        client.logout(access_token, "others")
        return True
    except DevteamError:
        return False


def cmd_password_reset(args, emitter):
    identity = _identity(emitter)
    client = gotrue.Client(identity)
    email = gotrue.normalize_email(args.email)
    if not args.finish:
        _swallow_rejection(lambda: client.recover(email))
        emitter.line(SENT_MESSAGE)
        if args.send_code:
            return {"sent": True, "message": SENT_MESSAGE, "expires_in": 600}, None
    code = gotrue.normalize_code(_read_secret("recovery code: "))
    password = gotrue.validate_new_password(_read_new_password())
    sess = client.verify(email, code, "recovery")
    try:
        client.update_user(sess["access_token"], {"password": password})
    except Rejected:
        raise Rejected("password_rejected", "the password was not accepted") from None
    others = _revoke_others(client, sess["access_token"])
    warnings = [] if others else ["other sessions could not be revoked; sign out elsewhere"]
    view, human = _complete_login(
        emitter, identity, client, sess, "email", "password-reset", warnings
    )
    view["other_sessions_revoked"] = others
    return view, human


def cmd_password_change(args, emitter):
    identity = _identity(emitter)
    meta = _require_session()
    if not meta.get("email"):
        raise Rejected(
            gotrue.REASON_REJECTED,
            "this account has no email address to change a password for",
            hint="Use `devteam auth password reset` with the address you sign in with.",
        )
    current = gotrue.normalize_password(_read_secret("current password: "))
    new = gotrue.validate_new_password(_read_new_password())
    client = gotrue.Client(identity)
    # A fresh sign-in with the current password: the server's secure-password-change rule
    # wants a recent authentication, and this proves the caller knows the old one.
    fresh = client.sign_in_password(meta["email"], current)
    if fresh["user"]["id"] != meta["account_id"]:
        raise Rejected(gotrue.REASON_INVALID_CREDENTIALS)
    try:
        client.update_user(fresh["access_token"], {"password": new})
    except Rejected:
        raise Rejected("password_rejected", "the password was not accepted") from None
    others = _revoke_others(client, fresh["access_token"])
    session.save_session(fresh, meta.get("provider") or "email")
    payload = {"changed": True, "other_sessions_revoked": others}
    return payload, "password changed" + ("" if others else "\nwarning: other sessions could not be revoked")


# ── profile ───────────────────────────────────────────────────────────────────


def _identities(user):
    out = []
    for item in user.get("identities") or []:
        if not isinstance(item, dict):
            continue
        data = item.get("identity_data") if isinstance(item.get("identity_data"), dict) else {}
        out.append(
            {
                "id": item.get("identity_id") or item.get("id"),
                "provider": item.get("provider"),
                "email": data.get("email") if isinstance(data.get("email"), str) else None,
            }
        )
    return out


def _profile_view(client, access, meta):
    user = client.get_user(access)
    try:
        profile = client.profile_get(access, user["id"])
    except DevteamError:
        profile = {}
    meta_name = (user.get("user_metadata") or {}).get("display_name") if isinstance(user.get("user_metadata"), dict) else None
    name = profile.get("display_name") or meta_name
    if user["id"] == meta["account_id"]:
        fields = {}
        if user.get("email") and user["email"] != meta.get("email"):
            fields["email"] = user["email"]
        if name != meta.get("display_name"):
            fields["display_name"] = name
        if fields:
            session.update_meta(**fields)
    return {
        "id": user["id"],
        "email": user.get("email"),
        "display_name": name,
        "signup_method": profile.get("signup_method") or meta.get("provider"),
        "created_at": profile.get("created_at") or user.get("created_at"),
        "identities": _identities(user),
        "pending_email": user.get("new_email") if isinstance(user.get("new_email"), str) else None,
    }


def _profile_human(account):
    lines = ["account {}".format(account["id"]), "  email         {}".format(account["email"])]
    lines.append("  display name  {}".format(account["display_name"] or "(not set)"))
    lines.append("  sign-up       {}".format(account["signup_method"]))
    if account["pending_email"]:
        lines.append("  pending email {}".format(account["pending_email"]))
    lines.append("  identities")
    for item in account["identities"]:
        lines.append("    {}  {}".format(item["provider"], item["email"] or ""))
    return "\n".join(lines)


def _signed_in_client(emitter):
    identity = _identity(emitter)
    meta = _require_session()
    client = gotrue.Client(identity)
    return identity, meta, client, session.access_token(client)


def cmd_profile_show(args, emitter):
    _identity_, meta, client, access = _signed_in_client(emitter)
    account = _profile_view(client, access, meta)
    return {"account": account}, _profile_human(account)


def cmd_profile_update(args, emitter):
    _identity_, meta, client, access = _signed_in_client(emitter)
    name = gotrue.normalize_display_name(args.name)
    client.profile_set_name(access, meta["account_id"], name)
    session.update_meta(display_name=name)
    return {"display_name": name}, "display name set to {}".format(name)


def cmd_profile_identities(args, emitter):
    _identity_, meta, client, access = _signed_in_client(emitter)
    items = _identities(client.get_user(access))
    lines = ["{}  {}".format(item["provider"], item["email"] or "") for item in items]
    return {"identities": items}, "\n".join(lines)


def cmd_profile_email(args, emitter):
    identity, meta, client, access = _signed_in_client(emitter)
    new_email = gotrue.normalize_email(args.new)
    if not args.confirm:
        client.update_user(access, {"email": new_email})
        message = "A code was sent to {} and to your current address. Run again with --confirm.".format(
            new_email
        )
        return {"sent": True, "pending_email": new_email, "message": message}, message
    first = gotrue.normalize_code(_read_secret("code sent to the new address: "))
    second_text = _read_optional_line("code sent to the current address (empty to skip): ").strip()
    fresh = client.verify_pending(new_email, first, "email_change")
    if second_text and meta.get("email"):
        second = gotrue.normalize_code(second_text)
        fresh = client.verify_pending(meta["email"], second, "email_change") or fresh
    if fresh and fresh["user"]["id"] == meta["account_id"]:
        session.save_session(fresh, meta.get("provider") or "email")
        access = fresh["access_token"]
    user = client.get_user(access)
    confirmed = user.get("email") == new_email
    if confirmed:
        session.update_meta(email=new_email)
    payload = {"confirmed": confirmed, "email": user.get("email")}
    human = "email changed to {}".format(new_email) if confirmed else (
        "waiting for the other address: run again with --confirm and its code"
    )
    return payload, human


def _provider_arg(args):
    return "google" if args.google else "github"


def cmd_profile_link(args, emitter):
    identity, meta, client, access = _signed_in_client(emitter)
    provider = _provider_arg(args)
    sess = _oauth_session(emitter, identity, client, provider, link_access=access)
    if sess["user"]["id"] != meta["account_id"]:
        raise Rejected(gotrue.REASON_REJECTED)
    session.save_session(sess, meta.get("provider") or provider)
    items = _identities(client.get_user(sess["access_token"]))
    return {"linked": provider, "identities": items}, "{} linked".format(provider)


def cmd_profile_unlink(args, emitter):
    _identity_, meta, client, access = _signed_in_client(emitter)
    provider = _provider_arg(args)
    items = _identities(client.get_user(access))
    match = next((item for item in items if item["provider"] == provider), None)
    if match is None:
        raise UsageError("{} is not linked to this account".format(provider))
    if len(items) <= 1:
        raise Rejected(
            "last_identity",
            "that is the only way to sign in to this account, so it cannot be unlinked",
            hint="Link another sign-in method first.",
        )
    client.unlink_identity(access, match["id"])
    return {"unlinked": provider}, "{} unlinked".format(provider)


# ── delete ────────────────────────────────────────────────────────────────────


def cmd_delete(args, emitter):
    """Delete the account after a fresh email code (SR-37).

    A refreshed access token keeps its original authentication time, so it cannot pass the
    server's freshness check. The CLI therefore signs in again with an email code, and uses
    that session's access token for the call. Stages: ``--send-code`` only sends the code;
    ``--yes`` on a non-interactive stdin reads the code and does not send one (sending a new
    code would invalidate the one the user holds); a terminal does both, after asking the
    user to type the address.
    """
    interactive = _is_console()
    if not (args.yes or args.send_code or interactive):
        raise UsageError(
            "deleting an account needs an explicit confirmation",
            hint="Run in a terminal, or pass --send-code and then --yes with the code on stdin.",
        )
    identity = _identity(emitter)
    meta = _require_session()
    email = meta.get("email")
    if not email:
        raise Rejected(
            gotrue.REASON_REJECTED,
            "this account has no email address to confirm a deletion with",
        )
    client = gotrue.Client(identity)
    if interactive and not args.yes and not args.send_code:
        _prompt("This permanently deletes the account {} and its license.\n".format(email))
        _prompt("Type the email address to confirm: ")
        if sys.stdin.readline().strip().lower() != email.lower():
            raise UsageError("the address did not match; nothing was deleted")
    if args.send_code or interactive:
        client.otp_start(email, False)
        emitter.line("A confirmation code was sent to {}.".format(email))
        if args.send_code:
            return {"sent": True, "message": "A confirmation code was sent."}, None
    code = gotrue.normalize_code(_read_secret("confirmation code: "))
    fresh = client.verify(email, code, "email")
    if fresh["user"]["id"] != meta["account_id"]:
        raise Rejected(gotrue.REASON_INVALID_CODE)
    client.delete_account(fresh["access_token"])
    local = session.clear_local()
    payload = dict(local, deleted=True, signed_in=False)
    return payload, "account deleted; this machine is signed out"


# ── parser ────────────────────────────────────────────────────────────────────


def register(sub, leaf):
    """Attach ``auth`` and its subcommands to the CLI parser."""
    auth = leaf(sub, "auth", help="sign in, license state, profile and account deletion")
    top = auth.add_subparsers(dest="auth_cmd")

    login = leaf(top, "login", help="sign in with Google, GitHub, an email code or a password")
    methods = login.add_mutually_exclusive_group()
    methods.add_argument("--google", action="store_true", help="continue with Google in your browser")
    methods.add_argument("--github", action="store_true", help="continue with GitHub in your browser")
    methods.add_argument("--email", metavar="ADDRESS", help="sign in with an 8-digit code sent to this address")
    login.add_argument(
        "--password",
        action="store_true",
        help="with --email: use the account password (read from the terminal or stdin) instead of a code",
    )
    login.add_argument("--signup", action="store_true", help="with --password: create the account")
    login.add_argument("--name", help="display name for a new account")
    login.set_defaults(func=cmd_login)

    leaf(top, "logout", help="sign out; removes the session and the cached license").set_defaults(
        func=cmd_logout
    )

    for name, handler, text in (
        ("status", cmd_status, "report the session and the license state"),
        ("check", cmd_check, "exit 0 only when the account is entitled (for the gate and installers)"),
    ):
        node = leaf(top, name, help=text)
        node.add_argument(
            "--offline", action="store_true", help="read the cached license only; never use the network"
        )
        node.set_defaults(func=handler)

    otp = leaf(top, "otp", help="email code sign-in in two steps").add_subparsers(dest="auth_otp_cmd")
    otp_start = leaf(otp, "start", help="send a sign-in code to an address")
    otp_start.add_argument("--email", required=True, metavar="ADDRESS")
    otp_start.add_argument("--name", help="display name for a new account")
    otp_start.set_defaults(func=cmd_otp_start)
    otp_verify = leaf(otp, "verify", help="read the code from stdin and sign in")
    otp_verify.add_argument("--email", required=True, metavar="ADDRESS")
    otp_verify.set_defaults(func=cmd_otp_verify)

    password = leaf(top, "password", help="reset or change the password").add_subparsers(
        dest="auth_password_cmd"
    )
    reset = leaf(password, "reset", help="reset a forgotten password with an emailed code")
    reset.add_argument("--email", required=True, metavar="ADDRESS")
    stage = reset.add_mutually_exclusive_group()
    stage.add_argument("--send-code", action="store_true", help="only send the recovery code")
    stage.add_argument(
        "--finish",
        action="store_true",
        help="read the code and then the new password from stdin; sends nothing",
    )
    reset.set_defaults(func=cmd_password_reset)
    leaf(password, "change", help="change the password (current, then new, from stdin)").set_defaults(
        func=cmd_password_change
    )

    profile = leaf(top, "profile", help="show or edit the account profile")
    profile.set_defaults(func=cmd_profile_show)
    profile_sub = profile.add_subparsers(dest="auth_profile_cmd")
    leaf(profile_sub, "show", help="the account, its sign-in methods and its display name").set_defaults(
        func=cmd_profile_show
    )
    update = leaf(profile_sub, "update", help="change the display name")
    update.add_argument("--name", required=True)
    update.set_defaults(func=cmd_profile_update)
    leaf(profile_sub, "identities", help="list the linked sign-in methods").set_defaults(
        func=cmd_profile_identities
    )
    email = leaf(profile_sub, "email", help="change the email address (needs a confirmation code)")
    email.add_argument("--new", required=True, metavar="ADDRESS")
    email.add_argument(
        "--confirm", action="store_true", help="read the confirmation code(s) from stdin and finish"
    )
    email.set_defaults(func=cmd_profile_email)
    for name, handler, text in (
        ("link", cmd_profile_link, "link Google or GitHub to this account"),
        ("unlink", cmd_profile_unlink, "unlink Google or GitHub (never the last sign-in method)"),
    ):
        node = leaf(profile_sub, name, help=text)
        group = node.add_mutually_exclusive_group(required=True)
        group.add_argument("--google", action="store_true")
        group.add_argument("--github", action="store_true")
        node.set_defaults(func=handler)

    delete = leaf(top, "delete", help="permanently delete the account (needs a fresh email code)")
    delete.add_argument("--yes", action="store_true", help="confirm; without a terminal the code is read from stdin")
    delete.add_argument("--send-code", action="store_true", help="only send the confirmation code")
    delete.set_defaults(func=cmd_delete)
    return auth

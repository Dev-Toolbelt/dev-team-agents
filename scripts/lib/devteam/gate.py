"""The account gate: which commands need an entitled account, and what happens when it is not (ADR-0029 SR-30).

The exempt list is an **allowlist** matched on the parsed command path, so a subcommand added
later is gated by default. A user must always be able to sign in, diagnose, take their data
and leave, so those paths are never gated.

``gate_mode`` comes from the compiled ``auth-config.json``: ``warn`` (the default when the
key is absent) prints a one-line notice on stderr and lets the command run; ``enforce``
refuses with the exit code ``devteam auth check`` uses (1 not entitled, 3 an online check is
needed and impossible). A value that is neither is read as ``enforce``: a typo must not open
the gate. stdout and the ``--json`` document are never touched in ``warn``.

The check is :func:`auth.cmd_check` itself, called in-process, so the gate, ``auth check`` and
the installers (which shell out to ``auth check --json``) share one decision.
"""

from __future__ import annotations

import argparse
import time

from . import auth, entitlement, jsonio
from . import auth_session as session

MODE_WARN = "warn"
MODE_ENFORCE = "enforce"

#: Command-path prefixes that are never gated.
EXEMPT = frozenset(
    {
        ("auth",),
        ("version",),
        ("path",),
        ("compat",),
        ("doctor",),
        ("unbind",),
        ("uninstall",),
        ("export",),
        ("quarantine", "restore"),
    }
)

#: Allowed while blocked so hook fixes reach a blocked user, but only the core-store part:
#: the project sync it would run is withheld.
CORE_SELF_UPDATE = ("update",)


def is_exempt(command_path):
    path = tuple(command_path)
    return any(path[: len(prefix)] == prefix for prefix in EXEMPT)


def gate_mode(config_path=None):
    config = jsonio.read_json(config_path or entitlement._CONFIG_PATH)
    value = config.get("gate_mode", MODE_WARN) if isinstance(config, dict) else MODE_WARN
    return value if value in (MODE_WARN, MODE_ENFORCE) else MODE_ENFORCE


def apply(command_path, args, emitter, config_path=None):
    """Gate one parsed command. Returns nothing; raises the refusal in ``enforce``."""
    path = tuple(command_path)
    if is_exempt(path):
        return
    mode = gate_mode(config_path)
    try:
        auth.cmd_check(argparse.Namespace(offline=False), emitter)
        return
    except auth.EntitlementRefusal as refusal:
        refused = refusal
    label = "devteam {}".format(" ".join(path))
    if mode == MODE_WARN:
        emitter.warn(
            "{}: {}. This will be required in an upcoming release - {}".format(
                label, refused.message, _remedy(refused)
            )
        )
        return
    if path == CORE_SELF_UPDATE:
        args.no_sync = True
        emitter.warn("{}: {}; updating the core only, projects are not synced".format(label, refused.message))
        return
    raise auth.EntitlementRefusal(
        refused.exit_code,
        "{} is blocked: {}".format(label, refused.message),
        _remedy(refused) + " `doctor`, `unbind` and `uninstall` always work.",
        refused.view,
    )


def _remedy(refusal):
    return refusal.hint or "Run `devteam auth login`."



def banner_line(local_now=None):
    """One informational line for the session-start banner; ``""`` when nothing can be said.

    Offline and read-only by construction: it reads the cached session and entitlement and
    evaluates them with the pure :func:`entitlement.evaluate`, never :func:`entitlement.check`
    (which advances a file) and never the network. It cannot raise, because the hook that
    prints it must never fail a session.
    """
    try:
        identity = entitlement.load_identity()
        meta = session.read_meta()
        now = time.time() if local_now is None else local_now
        result = entitlement.evaluate(
            entitlement.read_cache(), identity, meta["account_id"] if meta else None, now
        )
        status = result.status
        if status == entitlement.STATUS_ACTIVE:
            return "signed in"
        if status == entitlement.STATUS_TRIAL:
            days = max(0, -(-int(result.trial_ends_at - result.effective_now) // 86400))
            return "trial ends in {} day{}".format(days, "" if days == 1 else "s")
        if status == entitlement.STATUS_SIGNED_OUT:
            return "signed out (run `devteam auth login`)"
        if status == entitlement.STATUS_TRIAL_EXPIRED:
            return "trial ended (run `devteam auth status`)"
        if status == entitlement.STATUS_BANNED:
            return "blocked (run `devteam auth status`)"
        return "license needs a check (run `devteam auth check`)"
    except Exception:  # noqa: BLE001 - a banner must never fail a session
        return ""

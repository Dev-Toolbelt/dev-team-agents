"""The account gate: which commands need an entitled account, and what happens when it is not (ADR-0029 SR-30).

The exempt list is an **allowlist** matched on the parsed command path, so a subcommand added
later is gated by default. A user must always be able to sign in, diagnose, take their data
and leave, so those paths are never gated; neither is the hook plumbing (``tasks``), which a
PreToolUse hook runs on every tool call and which must never wait on a lock or the network.

``gate_mode`` is :attr:`entitlement.Identity.gate_mode`: ``warn`` prints a notice on stderr
(only when stderr is a terminal) and lets the command run;
``enforce`` refuses with the exit code ``devteam auth check`` uses (1 not entitled, 3 an
online check is needed and impossible). A value that is neither is read as ``enforce``; an
unreadable config falls back to :data:`entitlement.DEFAULT_GATE_MODE`, the mode this release
ships. In ``warn`` *nothing* the check raises stops the command, including a broken config.
stdout and the ``--json`` document are never touched in ``warn``.

A refusal carries ``details.gate = "account"`` so a client can tell it from the exit 1 that
``doctor`` or ``cred check`` use for findings.

The check is :func:`auth.cmd_check` itself, called in-process, so the gate, ``auth check`` and
the installers (which shell out to ``auth check --json``) share one decision.
"""

from __future__ import annotations

import argparse
import time

from . import auth, entitlement
from . import auth_session as session
from .errors import DevteamError, EnvError

MODE_WARN = entitlement.GATE_WARN
MODE_ENFORCE = entitlement.GATE_ENFORCE

#: The gate's verdict, read by the handler that needs it (``update``).
ALLOWED = "allowed"
CORE_ONLY = "core-only"

GATE_MARKER = "account"

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
        ("tasks",),
    }
)

#: Allowed while blocked so hook fixes reach a blocked user, but only the core-store part:
#: the project sync it would run is withheld (ADR-0029 section 3).
CORE_SELF_UPDATE = ("update",)


def is_exempt(command_path):
    path = tuple(command_path)
    return any(path[: len(prefix)] == prefix for prefix in EXEMPT)


def gate_mode(config_path=None):
    return entitlement.gate_mode_of(entitlement.read_config(config_path))


def _marked(exc):
    exc.details = dict(exc.details or {}, gate=GATE_MARKER)
    return exc


def apply(command_path, args, emitter, config_path=None):
    """Gate one parsed command. Returns :data:`ALLOWED` or :data:`CORE_ONLY`; raises in ``enforce``."""
    path = tuple(command_path)
    if is_exempt(path):
        return ALLOWED
    mode = gate_mode(config_path)
    label = "devteam {}".format(" ".join(path))
    try:
        auth.cmd_check(argparse.Namespace(offline=False), emitter)
        return ALLOWED
    except auth.EntitlementRefusal as refusal:
        refused = refusal
    except DevteamError as exc:
        if mode == MODE_WARN:
            _notice(emitter, "{}: the account check could not run ({})".format(label, exc.message))
            return ALLOWED
        if path == CORE_SELF_UPDATE:
            emitter.warn("{}: the account check could not run; updating the core only".format(label))
            return CORE_ONLY
        raise _marked(
            EnvError(
                "{} is blocked: the account check could not run ({})".format(label, exc.message),
                hint=(exc.hint or "Reinstall the CLI.") + " `doctor`, `unbind` and `uninstall` always work.",
                details=dict(exc.details or {}),
            )
        ) from None
    if mode == MODE_WARN:
        _notice(
            emitter,
            "{}: {}. This will be required in an upcoming release - {}".format(
                label, refused.message, _remedy(refused)
            ),
        )
        return ALLOWED
    if path == CORE_SELF_UPDATE:
        emitter.warn("{}: {}; updating the core only, projects are not synced".format(label, refused.message))
        return CORE_ONLY
    raise _marked(
        auth.EntitlementRefusal(
            refused.exit_code,
            "{} is blocked: {}".format(label, refused.message),
            _remedy(refused) + " `doctor`, `unbind` and `uninstall` always work.",
            refused.view,
        )
    )


def _notice(emitter, message):
    """The warn-mode notice, shown only to a person at a terminal.

    A script, a CI job, a hook or the desktop app (which renders its own banner) captures
    stderr, and a line on every command there is noise; writing a "shown today" marker would
    make a read-only command write to the store. So the rule is the terminal, not a clock.
    """
    stream = getattr(emitter, "stderr", None)
    isatty = getattr(stream, "isatty", None)
    try:
        interactive = bool(isatty and isatty())
    except (OSError, ValueError):
        interactive = False
    if interactive:
        emitter.warn(message)


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

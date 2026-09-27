"""Exit codes and the exception hierarchy that maps onto them.

The contract is part of the CLI's public surface: the Electron app and any CI
script reads it, so a code never changes meaning once released.

    0  success
    1  findings — the command ran and reported a problem it did not fix
    2  usage error — bad arguments, unknown subcommand
    3  environment error — no store, no version, unreadable directory
    4  conflict — lock timeout, identity collision, refusing to overwrite
"""

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_ENVIRONMENT = 3
EXIT_CONFLICT = 4


class DevteamError(Exception):
    """Base class. ``exit_code`` is what the CLI returns to the shell."""

    exit_code = EXIT_FINDINGS

    def __init__(self, message, hint=None, details=None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.details = details or {}

    def payload(self):
        """The ``--json`` body for a failed command."""
        body = {"ok": False, "error": self.message, "exit_code": self.exit_code}
        if self.hint:
            body["hint"] = self.hint
        if self.details:
            body["details"] = self.details
        return body


class UsageError(DevteamError):
    exit_code = EXIT_USAGE


class EnvError(DevteamError):
    """Environment is not in a state where the command can run."""

    exit_code = EXIT_ENVIRONMENT


class ConflictError(DevteamError):
    """Two things claim the same resource, or a lock could not be taken."""

    exit_code = EXIT_CONFLICT

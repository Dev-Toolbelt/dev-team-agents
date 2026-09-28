"""What a client must understand to talk to this store (ADR-0011).

ADR-0011 makes the desktop app a **client of the CLI**: every screen invokes
``devteam <command> --json`` and renders the result, and nothing about bind,
preferences or credentials is reimplemented in the app. It also states the rule that
keeps that arrangement safe:

    Compatibility is declared, not assumed. The app states ``minFrameworkVersion``
    and the framework states ``minAppVersion``. When the store is ahead of the app,
    the app degrades to read-only and says so, instead of writing a structure it
    does not understand.

This module is the framework's half of that. It declares ``min_app_version``, and it
**surfaces the schema numbers that already exist** rather than inventing a second
versioning scheme beside them: `project.json` has a `schema` and a `layout`, the
registry has a `schema`, the bind manifest has one, the credential reference layer has
one. Those are the shapes a writer has to understand. A client that finds a number
higher than it knows has its answer without guessing from a release version.

``min_app_version`` is ``None`` on purpose until an app is released. It means "no
minimum is asserted yet", which is the truth — asserting a version for software that
does not exist would be a number nobody could act on. The field exists now, before the
first app, precisely so the first app can rely on reading it.
"""

from __future__ import annotations

from . import bind, creds, project, registry

#: Bumped when a released app version stops being able to write this store safely.
#: ``None`` while no app has been released; see the module docstring.
MIN_APP_VERSION = None

#: The `--json` output shape as a whole. ADR-0011 makes it public API — "changing an
#: output shape is a breaking change" — so a client can pin against this rather than
#: inferring compatibility from the framework's release version, which moves for
#: reasons that have nothing to do with the contract.
JSON_CONTRACT_VERSION = 1


def store_schemas():
    """The shape numbers a client must understand before it writes anything.

    Read from the modules that own them, never copied: a second copy is a number that
    goes stale silently, and this one would go stale in the direction that tells a
    client it is safe to write when it is not.
    """
    return {
        "project": project.SCHEMA,
        "project_layout": project.CURRENT_LAYOUT,
        "registry": registry.SCHEMA,
        "bind_manifest": bind.MANIFEST_SCHEMA,
        "credentials": creds.SCHEMA,
    }


def describe():
    """Everything a client needs to decide whether it can write to this store."""
    return {
        "json_contract": JSON_CONTRACT_VERSION,
        "min_app_version": MIN_APP_VERSION,
        "store_schemas": store_schemas(),
    }


def unsupported_by(client_schemas):
    """Which shapes this store is ahead of, for a client that states what it knows.

    Returns ``{name: {"store": n, "client": m}}`` for every shape the store carries a
    higher number for. Empty means the client understands every shape and may write.

    A name the client does not mention at all counts as unsupported: silence is not a
    claim of support, and treating it as one is how a client writes a structure it has
    never seen. A name the client knows and the store does not is not reported — an
    older store is readable by a newer client, which is the direction that works.
    """
    if not isinstance(client_schemas, dict):
        raise TypeError("client_schemas must be a mapping of shape name to integer")
    behind = {}
    for name, store_version in store_schemas().items():
        claimed = client_schemas.get(name)
        if not isinstance(claimed, int) or isinstance(claimed, bool):
            behind[name] = {"store": store_version, "client": None}
        elif claimed < store_version:
            behind[name] = {"store": store_version, "client": claimed}
    return behind

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

This module also carries the **write gate**: the declaration seam a caller uses to say
what it understands (``--client-schemas``, ``DEVTEAM_CLIENT_SCHEMAS``), and the
classification of every command as mutating or read-only that decides when the
declaration is checked. ``devteam compat`` answers "may I write?"; the gate is what
enforces that answer against a caller that identified itself — a declared client is
refused whether or not it ever ran ``compat``, which is the half of the v4 spec's
complaint this module does close. Correct the word before it invites the wrong
expectation: the gate binds a caller that declares **truthfully**. A caller that merely
declares is self-bound, not bound — the two bypasses below are exactly the gap between
those.

**It closes neither of the other two, and both are worth stating as plainly as the one
it does close.**

The first is the spec's own sentence, worth quoting exactly: *nothing on the framework
side refuses a client that never asks.* A caller that declares nothing is still not
refused, and that is deliberate rather than pending. An anonymous invocation is
indistinguishable from a human at a terminal: there is no signal to separate the two,
and inventing one would either break ordinary CLI use or be bypassable by omitting a
flag.

The second has no name in the spec, because the declaration seam did not exist when it
was written: a caller can declare ``{"project": 999, "registry": 999, ...}`` — every
shape at or above the number the store carries — and ``gate()`` passes it unconditionally,
truthfully declared or not. This costs the caller nothing: the declaration is a file it
both names and writes, so inflating it takes no more privilege than writing any other
file it already controls. Like the credential scope check elsewhere in this codebase,
the write gate is **hygiene and auditability, not a sandbox** — it holds a caller to what
it says about itself, and has no way to check whether what it says is true. **Do not
attempt to close this one.** There is no signal in this seam, or in any seam the CLI has,
that authenticates a caller or distinguishes a truthful declaration from an invented one;
manufacturing one here would only relocate the trust assumption somewhere less visible,
not remove it.

So the gate binds — self-binds, per the correction above — the callers that declare, and
the residue — an undeclared client writes exactly as a human does — is accepted,
recorded, and left to the client to honour. Anything claiming this module refuses *every*
client that never asks is wrong; what it refuses is every **declared** client that may
not write, and only for as long as what it declared was true.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

from . import bind, creds, integrations, plugins, project, registry
from .errors import ConflictError, EnvError, UsageError

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
        "plugin_settings": plugins.SCHEMA,
        "integrations": integrations.SCHEMA,
        "integration_settings": integrations.SETTINGS_SCHEMA,
    }


def _example_declaration():
    """A syntactically valid declaration, always at the store's real numbers.

    Used only to build hint text. A hand-typed literal goes stale the moment a shape's
    schema number moves — which already happened once: a `--client` usage hint quoted
    ``{"registry": 3}`` long after ``registry.SCHEMA`` became ``1``, and stayed that way
    because nothing tied the string to the number. Deriving it from ``store_schemas()``
    costs one dict lookup and cannot drift again.
    """
    return json.dumps(store_schemas())


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


# ── the declaration seam ──────────────────────────────────────────────────────

#: Names a JSON file holding the same object ``devteam compat --client-file`` accepts.
#: An environment variable exists beside the flag because a client invokes many
#: commands per session and exporting once is the difference between a gate that is
#: honoured and a gate that is honoured on the calls somebody remembered.
CLIENT_SCHEMAS_ENV = "DEVTEAM_CLIENT_SCHEMAS"


class ClientDeclaration:
    """What a caller says it understands, and where it said it.

    ``origin`` is carried so a refusal can name the flag or the variable the caller
    actually used — a client that set the environment variable in a wrapper script
    three layers up needs to be told *that*, not the flag it never passed.
    """

    __slots__ = ("schemas", "origin", "source")

    def __init__(self, schemas, origin, source):
        self.schemas = schemas
        self.origin = origin
        self.source = source

    def __repr__(self):  # pragma: no cover - diagnostics only
        return "ClientDeclaration({!r}, {!r}, {!r})".format(self.schemas, self.origin, self.source)


def parse_client_schemas(raw, source):
    """Text -> the mapping ``unsupported_by`` takes. Raises ``UsageError`` on anything else.

    The one parser for a client declaration: ``devteam compat --client/--client-file``
    and the global ``--client-schemas``/``DEVTEAM_CLIENT_SCHEMAS`` seam all come through
    here, so the two can never disagree about what a valid declaration is — and a second
    parser is exactly how one of them would end up accepting something the other
    refuses.

    Every rejection names ``source`` — the seam and path that carried the declaration,
    or ``--client`` for inline JSON. **Nothing here may fall back to "no declaration"**:
    that is the fail-open case, and it turns a corrupt file into an ungated write.

    ``json.loads`` has two failure modes that are **not** ``JSONDecodeError``, and both
    escaped as a traceback with an empty stdout under ``--json`` before they were caught
    here: ``RecursionError`` on deeply nested input, and — via ``Path.read_text`` in
    ``load_client_schemas`` — ``UnicodeDecodeError``. A traceback is not a document, and
    it exits 1, which this CLI defines as "ran and reported a problem it did not fix": a
    client branching on ``$?`` reads a crash as a finding. Every path out of this
    function raises ``UsageError`` (exit 2, a malformed question) instead.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(
            "{} is not valid JSON: {}".format(source, exc),
            hint="Pass a JSON object, e.g. {}.".format(_example_declaration()),
        )
    except RecursionError as exc:
        # Deeply nested input exhausts the parser's stack. Raised *after* the stack has
        # unwound out of `json`, so building the error here is safe.
        raise UsageError(
            "{} is nested too deeply to parse as JSON: {}".format(source, exc),
            hint="A declaration is a flat object mapping shape names to integers.",
        )
    except ValueError as exc:
        # Anything else `json` classifies as a value problem. `JSONDecodeError` is a
        # `ValueError` too and is handled above; this is the residue, caught so it
        # cannot become the next traceback.
        raise UsageError(
            "{} could not be parsed as JSON: {}".format(source, exc),
            hint="Pass a JSON object, e.g. {}.".format(_example_declaration()),
        )
    if not isinstance(parsed, dict):
        raise UsageError(
            "{} is not a JSON object: got {}".format(source, type(parsed).__name__),
            hint="A declaration maps each shape name to an integer schema version.",
        )
    # `unsupported_by` treats an *absent* key as silence — a client honestly saying "I
    # don't know this shape" — and that is a legitimate answer, not a mistake. A
    # *present* value of the wrong type (a string, a float, `true`) is a different
    # thing: the client meant to claim something and got the claim wrong. Catching it
    # here keeps `unsupported_by` lenient for other callers while giving this boundary
    # a message that names the exact key and its type.
    #
    # The *value* itself must never appear in that message. `DEVTEAM_CLIENT_SCHEMAS` is
    # ambient and inherited, and this function is the one place a caller-named,
    # caller-controlled path (or a stale wrapper's stray env var) has its content read
    # and echoed toward `--json` output, a CI log, and the desktop app's error screen. A
    # layout-1 credentials file is a JSON object of string values — exactly the shape
    # that trips this branch on every key — so printing `value` here is a one-string
    # read primitive against any UTF-8 JSON file this process can open. The key name and
    # the type it got wrong are enough for a caller to fix its declaration; the value
    # never needs to leave the process.
    for name, value in parsed.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise UsageError(
                "{}: the value for '{}' is not an integer: got {}".format(
                    source, name, type(value).__name__
                ),
                hint="Each shape maps to a plain integer schema version, or is left out "
                "entirely to mean \"unknown\".",
            )
    return parsed


#: The size cap for a declaration file, in bytes. A well-formed declaration is a flat
#: object mapping today's five shape names to small integers — a few hundred bytes even
#: pretty-printed with generous whitespace. 4 KiB is an order of magnitude of headroom
#: above that for a hand-edited or future file, while still being small enough to refuse
#: promptly, by name, before anything that could stress this process's memory: an
#: oversized file, or a character device such as `/dev/zero` that never raises EOF.
MAX_DECLARATION_BYTES = 4096


def load_client_schemas(path, source=None):
    """Read a declaration file and parse it. ``UsageError`` naming the file on failure.

    A missing or unreadable file is a usage error, never silence — see
    ``parse_client_schemas``.

    ``source`` is the **label** every message uses, and it names the seam as well as the
    path: ``--client-file /nope/x.json``, not ``/nope/x.json``. That attribution is the
    thing this module argues for elsewhere and it was lost once already, when the two
    parsers were merged into this one — a client whose wrapper exported
    ``DEVTEAM_CLIENT_SCHEMAS`` three layers up has to be told which seam is at fault, not
    handed a path it never typed. It defaults to the bare path for a caller that has no
    seam to name.

    Two properties the plain ``Path(path).read_text()`` this used to be did not have,
    reproduced by a security review before either was closed here:

    * **The path must name a regular file.** ``stat()`` never opens anything, so the
      check happens before this function calls ``open()`` at all. Skipping it meant a
      FIFO blocked the read indefinitely — ``open()`` in read mode waits for a writer to
      connect no matter how small the eventual read is — and a character device like
      ``/dev/zero`` read without end, growing this process's heap for as long as
      anything kept consuming it.
    * **The read is capped, not trusted to ``st_size``.** A size read from ``stat()``
      and a size read moments later by ``read()`` can disagree — the file can grow
      between the two calls — so the cap is enforced against what was actually read, in
      bytes, before it is decoded or handed to ``json.loads``.
    """
    label = str(path) if source is None else source
    path = Path(path)
    try:
        file_stat = path.stat()
    except OSError as exc:
        raise UsageError(
            "{} could not be read: {}".format(label, exc),
            hint="Pass a path to a readable JSON file naming the shapes this client "
            "understands.",
        )
    if not stat.S_ISREG(file_stat.st_mode):
        raise UsageError(
            "{} is not a regular file".format(label),
            hint="Pass a path to a regular JSON file, not a pipe, socket, or device.",
        )
    try:
        with open(str(path), "rb") as handle:
            # One byte past the cap, so an oversized file is *detected* rather than
            # silently truncated into something that parses as valid JSON with the
            # wrong content.
            raw_bytes = handle.read(MAX_DECLARATION_BYTES + 1)
    except OSError as exc:
        raise UsageError(
            "{} could not be read: {}".format(label, exc),
            hint="Pass a path to a readable JSON file naming the shapes this client "
            "understands.",
        )
    if len(raw_bytes) > MAX_DECLARATION_BYTES:
        raise UsageError(
            "{} is larger than the {}-byte limit for a declaration".format(
                label, MAX_DECLARATION_BYTES
            ),
            hint="A declaration is a flat object mapping a handful of shape names to "
            "integers; it is expected to be well under {} bytes.".format(
                MAX_DECLARATION_BYTES
            ),
        )
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        # It is a `ValueError`, not an `OSError`, so the original `except OSError` let
        # it through to the shell as a traceback. See `parse_client_schemas` for why
        # every exit from here is a `UsageError`.
        raise UsageError(
            "{} is not valid UTF-8 text: {}".format(label, exc),
            hint="A declaration file is UTF-8 JSON; this one is not decodable as text.",
        )
    return parse_client_schemas(raw, label)


def client_declaration(flag_value=None, environ=None):
    """Resolve the declaration seam, or ``None`` when the caller declared nothing.

    **Precedence: the flag wins over the environment variable.** The flag is on the
    invocation in front of you; the variable is ambient, inherited, and the thing most
    likely to be stale — a wrapper that exported it once should never be able to
    override what this call says about itself. The variable is read only when the flag
    is absent.

    An empty or whitespace-only **variable** is treated as *unset*, not as an empty
    declaration: ``export DEVTEAM_CLIENT_SCHEMAS=`` is how a shell says "no value", and
    reading it as ``{}`` would refuse every write in that session with a message about a
    file whose name is the empty string.

    **An empty flag is the opposite case and is a usage error.** The asymmetry is the
    point: an absent variable and an empty one are indistinguishable to a shell, but
    ``--client-schemas ""`` is a caller that passed a value and got it wrong — almost
    always ``--client-schemas "$SCHEMAS"`` with an unset variable, which is the ordinary
    idiom a client wrapper would use. Testing the flag for mere truthiness let that case
    fall through to the environment and return ``None``: the anonymous, ungated path, and
    exactly the fail-open this module's docstring forbids. The declaration a caller
    *meant* to make must never be downgraded to silence.
    """
    environ = environ if environ is not None else {}
    if flag_value is not None:
        text = str(flag_value)
        if not text.strip():
            raise UsageError(
                "--client-schemas was given an empty value",
                hint="Pass the path to a declaration file, or omit the flag entirely to "
                "run as an undeclared caller. An empty value is not treated as 'no "
                "declaration' — that would silently drop the gate.",
            )
        return ClientDeclaration(
            load_client_schemas(text, source="--client-schemas {}".format(text)),
            "--client-schemas",
            text,
        )
    from_env = (environ.get(CLIENT_SCHEMAS_ENV) or "").strip()
    if from_env:
        return ClientDeclaration(
            load_client_schemas(
                from_env, source="{} {}".format(CLIENT_SCHEMAS_ENV, from_env)
            ),
            CLIENT_SCHEMAS_ENV,
            from_env,
        )
    return None


# ── which commands write ──────────────────────────────────────────────────────

#: Commands that create, change or remove durable state — the ones a declared client
#: must be able to understand before it is allowed to run them. Keyed by the same path
#: tuple ``tests/test_json_contract.py`` discovers from ``cli.build_parser()``, with the
#: reason beside each entry because several were judgment calls and a bare list invites
#: the next person to re-decide them from the name alone.
MUTATING = {
    ("store", "install"): "writes a new version into the core store",
    ("store", "use"): "rewrites the `current` pointer every bound project resolves through",
    ("store", "gc"): "removes installed versions with --apply; classified by what the "
    "command can do, not by which flag this invocation passed",
    ("bind",): "writes project.json, the registry entry, the manifest and every artifact",
    ("unbind",): "removes artifacts and rewrites the registry entry",
    ("sync",): "rebuilds artifacts and rewrites the manifest",
    ("pin",): "writes the pin into the registry entry",
    ("update",): "installs a version, moves `current`, and syncs every unpinned project",
    ("migrate",): "converts a v2 install: writes identity, quarantines the vendored tree. "
    "Previews without --apply, but the classification is per command, not per flag",
    ("prefs", "set"): "writes a preference layer and re-materialises resolved/preferences.json",
    ("prefs", "unset"): "drops a key from a layer and re-materialises the same file",
    ("plugin", "enable"): "writes plugin-settings/<name>.json, and may run a config-output "
    "action to seed it",
    ("plugin", "disable"): "rewrites plugin-settings/<name>.json",
    ("plugin", "config", "set"): "writes a value into plugin-settings/<name>.json",
    ("plugin", "config", "unset"): "drops a key from plugin-settings/<name>.json",
    ("plugin", "run"): "runs a script the manifest declares, and most actions write "
    "(graph output, caches). Classified per command, not per action",
    ("integration", "connect"): "writes data/integrations/<name>.json, a credential reference and "
    "its value, and the machine-local test result; then calls the integration's API",
    ("integration", "disconnect"): "removes the token's reference and value, and the test result",
    ("integration", "test"): "writes the machine-local test result after calling the API",
    ("integration", "config", "set"): "writes a field into data/integrations/<name>.json or "
    "integration-settings/<name>.json",
    ("integration", "config", "unset"): "drops a field from data/integrations/<name>.json or "
    "integration-settings/<name>.json",
    ("cred", "set"): "writes a credential reference and a value into a secret backend",
    ("cred", "unset"): "removes a reference, and the value with --forget-value",
    ("cred", "local", "init"): "creates .dev-team-agents/credentials.local.json from the "
    "canonical template (ADR-0024)",
    ("cred", "local", "patch"): "rewrites .dev-team-agents/credentials.local.json (ADR-0024)",
    ("cred", "import"): "writes references, stores values, and quarantines the v2 file",
    ("notifications", "ack"): "writes notifications-seen.json in each project's machine-local "
    "state directory",
    ("tasks", "record"): "writes a session's task record in the project's machine-local "
    "state directory (hook-only)",
    ("tasks", "mark"): "rewrites a session's task record in the machine-local state "
    "directory (hook-only)",
    ("tasks", "review-open"): "opens or joins a review window in a session's task record "
    "in the machine-local state directory (hook-only)",
    ("tasks", "review-result"): "records a review agent's result in a session's task record "
    "in the machine-local state directory (hook-only)",
    ("upgrade",): "relocates this project's memory into the store",
    ("export",): "creates an archive — durable state outside the store, and a restorable "
    "copy of shapes the declaring client just said it cannot read, which `import` on the "
    "far end will trust",
    ("import",): "replaces the data store",
    ("uninstall",): "removes the core, and the data store with --purge",
    ("skills", "install"): "writes a skill into a provider's global skill directory, and "
    "quarantines the one it replaces with --replace (ADR-0020)",
    ("skills", "remove"): "moves a global skill into the store's quarantine, or unlinks a "
    "symlinked one (ADR-0020)",
    ("doctor",): "repairs what it finds — it rewrites the directory pointers, relocates a "
    "moved registry entry, and reassigns identity with --reassign-identity. Read the "
    "actions it returns, not the word 'diagnose', before reclassifying this one",
}

#: Commands that only read. A declared client is never refused one of these: ADR-0011's
#: rule is that an incompatible client **degrades to read-only**, so read-only is
#: precisely what must keep working — including `compat` itself, or a client that has
#: fallen behind could not ask how far behind it is.
READ_ONLY = {
    ("path",): "resolves store locations; creates nothing",
    ("version",): "reports installed versions and the compat block",
    ("compat",): "the question itself — gating it would leave an incompatible client no "
    "way to learn why it is incompatible",
    ("store", "list"): "lists installed versions",
    ("list",): "lists bound projects",
    ("prefs", "list"): "reads the resolved cascade",
    ("prefs", "get"): "reads one key",
    ("plugin", "list"): "reads manifests and settings; runs only the cheap status scripts",
    ("plugin", "show"): "reads one manifest and its settings",
    ("plugin", "config", "get"): "reads the effective config",
    ("integration", "list"): "reads integration config, bindings and the last test result; "
    "never a token",
    ("integration", "show"): "reads one integration's config, binding and last test result",
    ("integration", "config", "get"): "reads the effective fields",
    ("integration", "resources"): "reads from the integration's API with the stored token "
    "(an audited read, like `cred get`); writes no shape",
    ("cred", "list"): "reference layer only — never a value",
    ("cred", "get"): "reads one value. It appends an audit line, so it is not literally "
    "side-effect-free — but that line is the framework's own record *about* the caller, "
    "in append-only text, and not one of the shapes `store_schemas()` declares. A client "
    "cannot corrupt it by misunderstanding project.SCHEMA. Gating it would turn a write "
    "gate into a read denial and stop a behind-but-entitled client from reading a secret "
    "— the opposite of 'degrade to read-only'. It also refuses --json by design "
    "(ADR-0010), and leaving it ungated is what keeps that refusal the answer a client "
    "gets on this command",
    ("cred", "check"): "reports references with no value or an insecure backend",
    ("cred", "local", "show"): "reads credentials.local.json with every secret replaced by a "
    "marker; never a value (ADR-0024)",
    ("notifications", "list"): "reads each project's queue and seen marks",
    ("notifications", "watch"): "stats each project's queue and streams new records; writes "
    "nothing — acknowledging is `notifications ack`",
    ("tasks", "list"): "reads each project's session records; writes nothing",
    ("tasks", "watch"): "stats each project's session records and streams snapshots; "
    "writes nothing",
    ("cred", "backends"): "probes which secret stores this machine offers",
    ("catalog",): "read-only browse — asserted to create nothing, machine id included",
    ("catalog", "agents"): "read-only browse",
    ("catalog", "skills"): "read-only browse",
    ("catalog", "commands"): "read-only browse",
    ("catalog", "show"): "read-only browse",
    ("skills", "list"): "reads the providers' global skill directories; creates nothing",
    ("skills", "show"): "reads one global skill; creates nothing",
}


#: Read-only commands whose **answer** depends on a machine-local record, so they cannot
#: be answered on a store that still keeps those records at the pre-ADR-0013 paths.
#:
#: This exists because ``store.adopt_machine_layout()`` is a mutation of `registry` and
#: `bind_manifest` — precisely the shapes an incompatible client declared it cannot read
#: — so it must not run on that caller's behalf. Skipping it leaves the store in the old
#: shape, and ``paths.registry_file()`` resolves only the split path: a command that
#: reads the registry then answers as though nothing were bound. `devteam list` did
#: exactly that — exit 0, ``projects: []``, no error anywhere — which is the same silent
#: failure mode as the stranded ``state-dir`` pointer that made ``state_get`` return an
#: empty string for every key.
#:
#: Membership was **measured**, not reasoned about: every read-only command was run
#: against a pre-split store with the relocation suppressed and compared byte for byte
#: against its answer on the same store after relocation. `list` was the only one that
#: differed; `path`, `version`, `compat`, `store list`, `prefs list/get`, `cred
#: list/check/backends` and every `catalog` leaf were identical, because they resolve
#: through the project's own pointers or the core store rather than the registry.
#: ``tests/test_client_gate.py`` re-runs that comparison over the whole read-only table,
#: so a command that starts reading the registry cannot quietly join the wrong side.
NEEDS_MACHINE_LAYOUT = {
    ("list",): "reads the registry, which resolves only at the post-split path — on a "
    "pre-split store it reports every bound project as unbound, with exit 0",
    ("notifications", "list"): "finds each project's queue through the registry — on a "
    "pre-split store it would report no notifications at all, with exit 0",
    ("notifications", "watch"): "the same registry walk as `notifications list`, repeated "
    "for as long as it runs",
    ("tasks", "list"): "finds each project's session records through the registry — on a "
    "pre-split store it would report an empty board, with exit 0",
    ("tasks", "watch"): "the same registry walk as `tasks list`, repeated for as long as "
    "it runs",
}


def classify(command_path):
    """``"mutating"``, ``"read-only"``, or ``None`` for a command nobody classified.

    ``None`` is not a verdict — it is the signal that the tables above have fallen
    behind ``cli.build_parser()``, which ``tests/test_client_gate.py`` fails on by
    walking the real parser. ``is_mutating`` is what decides at runtime, and it fails
    closed.
    """
    command_path = tuple(command_path)
    if command_path in MUTATING:
        return "mutating"
    if command_path in READ_ONLY:
        return "read-only"
    return None


def is_mutating(command_path):
    """Does this command need a declared client to be compatible before it runs?

    **An unclassified command counts as mutating.** A new command that nobody put in a
    table must not slip past the gate because of that omission — the omission is the
    likeliest mistake, and defaulting to read-only would make it a silent one. The cost
    of failing closed is borne only by a client that declared *and* is behind; a
    compatible client and a human are unaffected either way.
    """
    return classify(command_path) != "read-only"


def render_unsupported(unsupported):
    """``"name (store=N, client=M)"`` for each blocking shape, sorted, for a message.

    A shape the client never mentioned renders ``client=(not declared)`` rather than
    ``None``: silence is the most common reason a gate trips, and a client reading
    ``client=None`` will spend its time looking for the key it set to null.
    """
    return ", ".join(
        "{} (store={}, client={})".format(
            name,
            unsupported[name]["store"],
            "(not declared)" if unsupported[name]["client"] is None else unsupported[name]["client"],
        )
        for name in sorted(unsupported)
    )


def refusal(command_path, declaration, unsupported):
    """The error a gated command is refused with, before it touches anything.

    Exit **4** (conflict), not 1 and not 2. `devteam compat` exits 1 for an incompatible
    client because there it is a *finding*: the question ran and answered. Here nothing
    ran — the command was declined — and exit 1 in this CLI always means "ran and
    reported a problem it did not fix". `2` is reserved for a malformed question, which
    is what a broken declaration file already raises above; this invocation is
    well-formed. `3` says the environment cannot support the command, and the
    environment is fine — the client is the party that is behind. `4` already covers
    "two things disagree about a resource, so the write is refused", which is exactly
    this.

    ``details`` carries the machine-readable comparison so a client branches on data
    rather than on the wording of a sentence.
    """
    command = " ".join(command_path)
    return ConflictError(
        "{} would write to this store, and the client declared via {} does not "
        "understand {} shape(s) it uses: {}".format(
            command,
            declaration.origin,
            len(unsupported),
            render_unsupported(unsupported),
        ),
        hint=(
            "Upgrade the client, or run `devteam compat --client-file {}` for the full "
            "comparison. Read-only commands still work. Dropping the declaration is not "
            "a fix — it only hides the mismatch.".format(declaration.source)
        ),
        details={
            "command": command,
            "declared_by": declaration.origin,
            "declaration_source": declaration.source,
            "client_schemas": declaration.schemas,
            "store_schemas": store_schemas(),
            "unsupported": unsupported,
            "may_write": False,
        },
    )


def migration_required(command_path, declaration, unsupported):
    """The error for a read-only command that cannot answer without the relocation.

    Exit **3** (environment), not 4. Nothing is being refused *as a write*: this caller
    is entitled to read, and ADR-0011 says an incompatible client degrades to read-only.
    What has happened is that the store is in a shape this command cannot read, and the
    one thing that would fix it — ``store.adopt_machine_layout()`` — is a write to the
    very shapes the caller just declared it does not understand. So the environment is
    the party that is not ready, which is what 3 means, and the action is on the
    environment rather than on the client.

    A clear refusal beats a wrong answer: returning ``projects: []`` with exit 0 would
    tell a client that nothing is bound, and a client acting on that would offer to bind
    a project that is already bound.
    """
    command = " ".join(command_path)
    return EnvError(
        "{} cannot answer on this store: it still keeps machine-local records at the "
        "pre-split paths, and bringing them up to the current layout would write the {} "
        "shape(s) the client declared via {} does not understand: {}".format(
            command,
            len(unsupported),
            declaration.origin,
            render_unsupported(unsupported),
        ),
        hint=(
            "Run any devteam command from a terminal without a client declaration to "
            "perform the one-time migration, then retry. Upgrading the client works too. "
            "`devteam compat`, `devteam version` and `devteam path` answer either way."
        ),
        details={
            "command": command,
            "declared_by": declaration.origin,
            "declaration_source": declaration.source,
            "client_schemas": declaration.schemas,
            "store_schemas": store_schemas(),
            "unsupported": unsupported,
            "may_write": False,
            "machine_layout_pending": True,
        },
    )


def gate(command_path, declaration):
    """Raise :func:`refusal` when a declared client may not run this command.

    The whole gate, in one place: classification, the comparison (delegated to
    ``unsupported_by`` — never re-implemented here, or "silence is unsupported" would
    have a second definition to keep in step), and the refusal. Returns the unsupported
    mapping, empty when the command may proceed.
    """
    if declaration is None:
        return {}
    if not is_mutating(command_path):
        return {}
    unsupported = unsupported_by(declaration.schemas)
    if unsupported:
        raise refusal(command_path, declaration, unsupported)
    return unsupported

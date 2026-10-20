# new-adr.sh treats --help as a title

**Origin:** /devteam:learn consolidation, ADR-0041 and ADR-0042 work | 2026-10-19
**Tags:** new-adr.sh, --help, adr, adr number, title, docs/development/adrs, adr index, bash, argument parsing, create file

> `bash scripts/new-adr.sh --help` does not print help. It creates the next numbered ADR with the title "--help".

---

## What it is

`scripts/new-adr.sh` takes its first argument as the ADR title. It does not parse flags. It has no help output.

## How it works

1. The script assigns the next ADR number.
2. It writes `<number>-<title>.md` under the ADR directory.
3. It appends an index row to `<adr-dir>/README.md`.

## Gotchas

- `--help` becomes a real ADR. During the ADR-0041 and ADR-0042 work, it created `docs/development/adrs/0041-help.md`, which was then removed by hand.
- The script has no flag parsing for `--help`. Only `--dir` and `--list` are special, so any other first argument is taken as the title.

## Safe check

1. List existing ADRs without writing anything: `bash scripts/new-adr.sh --list`.
2. Run the script only with a real title, in quotes.

## References

- `skills/shared/adr/SKILL.md` — § Check Before Creating

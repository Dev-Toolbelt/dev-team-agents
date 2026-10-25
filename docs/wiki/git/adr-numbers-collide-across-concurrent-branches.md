# ADR Numbers Collide Across Concurrent Branches

**Origin:** context-delivery branch rebased onto main twice | 2026-10-25
**Tags:** adr number, adr collision, concurrent branches, renumber, git mv, adr index, rebase, new-adr.sh

> Read this first: `new-adr.sh` numbers from the checkout it runs in, so two open branches can each create the same ADR number. A blanket search-and-replace of that number also rewrites references that already belong to main.

---

## What it is
Each branch takes the next free ADR number from its own tree. When another branch merges first, the later branch's ADR files and their references carry a number that main already uses.

## How it works
1. The branch creates ADR-0046 to ADR-0050 while main is at ADR-0045.
2. Main lands ADR-0046 and then ADR-0047. The branch rebases and must move to 0048 to 0052.
3. Find only the lines the branch added: `git diff main -- <file>`, or any line absent verbatim from `git show main:<file>`.
4. Replace the ADR number on those lines only.
5. Move the ADR files with `git mv` in descending order (highest number first), so no move overwrites a file that has not moved yet.
6. Update the ADR index row and the ADR's title and header to the new number.
7. Run `git grep` for the old number and confirm each remaining hit belongs to main.

## Gotchas
- A `sed` across the whole file rewrites main's references. In this case ADR-0047 (third-party skills) was already cited in `CLAUDE.md`, `CHANGELOG.md`, `bind.py` and `providers.py`.
- Moving in ascending order overwrites the next file. Move the highest number first.
- Both branches add a row to `docs/development/adrs/README.md`, so a rebase conflicts there. Keep main's row and re-add the branch rows with the new numbers.
- Check the number before creating an ADR (`skills/shared/adr/SKILL.md` § Check Before Creating). That check does not see an unmerged branch, so it does not prevent a collision.

## References
- `skills/shared/adr/SKILL.md` § File Location, § ADR Index
- `docs/development/adrs/README.md`

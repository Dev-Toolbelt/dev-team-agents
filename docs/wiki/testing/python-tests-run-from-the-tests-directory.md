# Python Tests Run From tests/, Not as a Package

**Origin:** task-board audit fix pass | 2026-10-20
**Tags:** python tests, unittest, pytest, tests directory, devteam_support, python3 -m unittest, __init__.py, import error

> Read this first: run the Python suite from `tests/` with `cd tests && python3 -m unittest <module>`. `python3 -m unittest tests.test_x` fails to import `devteam_support`.

---

## What it is

`tests/` has no `__init__.py`, so it is not an importable package. Its modules import `devteam_support` by its bare name, which resolves only when `tests/` is the working directory.

## How it works

```bash
cd tests && python3 -m unittest test_tasks
```

## Gotchas

- `python3 -m unittest tests.test_x` raises an import error for `devteam_support`.
- pytest is not installed in the default `python3`. `python3 -m pytest` fails with `No module named pytest`.

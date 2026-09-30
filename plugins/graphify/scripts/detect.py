#!/usr/bin/env python3
"""Propose graphify targetPaths and manifestPaths from the project's stack.

Deterministic port of the graphify-setup skill's Step 4 heuristics. Reads the
project root (DEVTEAM_PROJECT_ROOT, else cwd), never writes a file, and prints
one JSON object: {"targetPaths": [...], "manifestPaths": [...]}.
"""

import json
import os
import sys
from pathlib import Path

MANIFESTS = {
    "package.json": "node",
    "composer.json": "php",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "setup.py": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "Gemfile": "ruby",
    "pom.xml": "java",
    "build.gradle": "java",
}

LOCK_FILES = (
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.lock",
    "Gemfile.lock",
    "poetry.lock",
)

STACK_PATHS = {
    "node": ("src", "lib", "app", "routes", "components", "pages", "services", "api"),
    "php-laravel": ("app", "routes", "config", "database/migrations", "tests"),
    "php": ("src", "lib", "app"),
    "python": ("src", "app"),
    "go": ("cmd", "internal", "pkg", "api"),
    "rust": ("src",),
    "ruby": ("app", "lib", "config"),
    "java": ("src/main", "src/test"),
}

UNKNOWN_NAMES = (
    "src", "lib", "app", "source", "sources", "core", "server", "client",
    "backend", "frontend", "cmd", "internal", "pkg", "api",
)

EXCLUDED = {
    "node_modules", "vendor", "dist", "build", "coverage", "__pycache__", "target",
    "graphify-out", "graphify-src", "venv", "env",
}


def is_excluded(name):
    return name.startswith(".") or name in EXCLUDED


def top_level_dirs(root):
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return []
    return [e for e in entries if (root / e).is_dir() and not is_excluded(e)]


def is_laravel(root):
    if (root / "artisan").is_file():
        return True
    try:
        return "laravel/framework" in (root / "composer.json").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def detect(root):
    manifests = [m for m in MANIFESTS if (root / m).is_file()]
    stacks = []
    for manifest in manifests:
        stack = MANIFESTS[manifest]
        if stack == "php" and is_laravel(root):
            stack = "php-laravel"
        if stack not in stacks:
            stacks.append(stack)

    targets = []

    def add(path):
        if path not in targets and (root / path).is_dir():
            targets.append(path)

    for stack in stacks:
        for path in STACK_PATHS[stack]:
            add(path)
        if stack == "python":
            for name in top_level_dirs(root):
                if (root / name / "__init__.py").is_file():
                    add(name)

    if not stacks:
        for name in UNKNOWN_NAMES:
            add(name)

    manifest_paths = list(manifests)
    for lock in LOCK_FILES:
        if (root / lock).is_file():
            manifest_paths.append(lock)

    return {"targetPaths": targets, "manifestPaths": manifest_paths}


def main():
    root = Path(os.environ.get("DEVTEAM_PROJECT_ROOT") or os.getcwd())
    json.dump(detect(root), sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

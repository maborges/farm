#!/usr/bin/env python3
"""Map source changes to the container images they affect."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


COMPONENTS = ("backend", "web", "campo", "agro")
DOCKERFILES = {
    "backend": "Dockerfile.backend",
    "web": "Dockerfile.web",
    "campo": "Dockerfile.campo",
    "agro": "Dockerfile.agro",
}
SHARED_FRONTEND_PATHS = (
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
)


def affected_components(paths: list[str]) -> set[str]:
    normalized = {Path(path).as_posix().lstrip("./") for path in paths}
    result: set[str] = set()

    if any(
        path == "Dockerfile.backend"
        or path.startswith("services/api/")
        or path.startswith("scripts/")
        for path in normalized
    ):
        result.add("backend")

    if any(path in SHARED_FRONTEND_PATHS or path.startswith("packages/") for path in normalized):
        result.update(("web", "campo", "agro"))

    component_paths = {
        "web": ("Dockerfile.web", "apps/web/"),
        "campo": ("Dockerfile.campo", "apps/campo/"),
        "agro": ("Dockerfile.agro", "apps/agro/"),
    }
    for component, prefixes in component_paths.items():
        if any(path == prefix or path.startswith(prefix) for path in normalized for prefix in prefixes):
            result.add(component)

    return result


def changed_paths(base: str, head: str) -> list[str]:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", base) or not re.fullmatch(
        r"[0-9a-fA-F]{40}", head
    ):
        raise ValueError("base e head devem ser SHA completos de 40 caracteres")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRTD", base, head],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--all", action="store_true", help="mark all image components affected")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    try:
        components = set(COMPONENTS) if args.all else affected_components(changed_paths(args.base, args.head))
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"Unable to determine affected images: {exc}", file=sys.stderr)
        return 2

    matrix = {
        "include": [
            {"component": item, "dockerfile": DOCKERFILES[item]}
            for item in COMPONENTS
            if item in components
        ]
    }
    values = {component: str(component in components).lower() for component in COMPONENTS}
    values["any"] = str(bool(components)).lower()
    values["matrix"] = json.dumps(matrix, separators=(",", ":"))

    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            for key, value in values.items():
                output.write(f"{key}={value}\n")
    else:
        print(json.dumps({"components": sorted(components), "matrix": matrix}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

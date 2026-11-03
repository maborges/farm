#!/usr/bin/env python3
"""Write a minimal immutable release manifest from a registry digest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from release_manifest import validate_image, write_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", choices=("backend", "web", "campo", "agro"), required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = f"{args.image}@{args.digest}"
    manifest = {"schema_version": 1, "commit": args.commit, "images": {args.component: reference}}
    from release_manifest import validate_manifest

    validate_manifest(manifest)
    write_json_atomic(args.output, manifest)
    print(f"Release manifest written for {args.component} at {args.commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

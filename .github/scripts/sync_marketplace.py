#!/usr/bin/env python3
"""Generate the external-plugin entries of .claude-plugin/marketplace.json
from every <plugin>/upstream.json, which is the single source of truth.

Each upstream.json entry:
    {"name": "<claude-code plugin name>", "description": "...",
     "repo": "owner/name", "ref": "main", "sha": "<optional 40-char pin>",
     "skills": ["dir-a", "dir-b"]}

becomes a Claude Code plugin entry with an external GitHub source. Local
plugins (and their order) in marketplace.json are left untouched; generated
entries are replaced in place (matched by name) or appended.

The same upstream.json is used by build_site.py to bundle these skills into
the plugin's OpenCode URL (e.g. /opt-tools/skills), so both harnesses always
serve the same repo/ref/sha.

Usage:
    python .github/scripts/sync_marketplace.py          # rewrite marketplace.json
    python .github/scripts/sync_marketplace.py --check  # exit 1 if out of date
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
REQUIRED = ("name", "repo", "skills")


def load_upstreams() -> list[dict]:
    entries = []
    for path in sorted(REPO_ROOT.glob("*/upstream.json")):
        for i, up in enumerate(json.loads(path.read_text(encoding="utf-8"))):
            missing = [k for k in REQUIRED if not up.get(k)]
            if missing:
                sys.exit(f"ERROR: {path.relative_to(REPO_ROOT)}[{i}] missing {missing}")
            entries.append(up)
    return entries


def to_marketplace_entry(up: dict) -> dict:
    source = {"source": "github", "repo": up["repo"]}
    if up.get("ref"):
        source["ref"] = up["ref"]
    if up.get("sha"):
        source["sha"] = up["sha"]
    description = up.get("description", "").strip()
    suffix = f"(from {up['repo']})"
    if suffix not in description:
        description = f"{description} {suffix}".strip()
    return {
        "name": up["name"],
        "description": description,
        "source": source,
        "skills": [f"./{s}" for s in up["skills"]],
    }


def render(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="don't write; exit 1 if marketplace.json is out of date")
    args = parser.parse_args()

    current_text = MARKETPLACE.read_text(encoding="utf-8")
    data = json.loads(current_text)
    plugins = data.setdefault("plugins", [])
    local_names = {p["name"] for p in plugins if isinstance(p.get("source"), str)}

    for up in load_upstreams():
        entry = to_marketplace_entry(up)
        if entry["name"] in local_names:
            sys.exit(f"ERROR: '{entry['name']}' is already a local plugin in marketplace.json")
        idx = next((i for i, p in enumerate(plugins) if p.get("name") == entry["name"]), None)
        if idx is None:
            plugins.append(entry)
        else:
            plugins[idx] = entry

    new_text = render(data)
    if new_text == current_text:
        print("marketplace.json is up to date.")
        return
    if args.check:
        print("ERROR: .claude-plugin/marketplace.json is out of sync with */upstream.json.\n"
              "Run: python .github/scripts/sync_marketplace.py", file=sys.stderr)
        sys.exit(1)
    MARKETPLACE.write_text(new_text, encoding="utf-8")
    print("Updated .claude-plugin/marketplace.json")


if __name__ == "__main__":
    main()

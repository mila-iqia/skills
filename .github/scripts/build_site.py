#!/usr/bin/env python3
"""Build the static skills site served by GitHub Pages.

For every plugin folder that has a ``skills/`` directory, this copies the
local skills into ``_site/<plugin>/skills/``, adds the skills listed in the
optional ``<plugin>/upstream.json`` (fetched from their upstream git repos,
never committed here), and writes a generated ``index.json`` in the format
OpenCode expects for ``skills``:

    {"skills": [{"name", "description", "files", "version"}]}

``version`` is a hash of the skill's contents, so OpenCode re-downloads a
skill only when it actually changed.

upstream.json format (also used by sync_marketplace.py for Claude Code):
    [{"name": "plugin-name", "description": "...", "repo": "owner/name",
      "ref": "main", "sha": "<optional pin>", "skills": ["dir-a", "dir-b"]}]

Usage: python .github/scripts/build_site.py [--out _site]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IGNORED_NAMES = {"__pycache__", ".DS_Store"}
LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def copy_skill(src: Path, dst: Path) -> None:
    shutil.copytree(
        src,
        dst,
        ignore=lambda _dir, names: [
            n for n in names if n in IGNORED_NAMES or n.startswith(".")
        ],
    )


def skill_files(skill_dir: Path) -> list[str]:
    files = sorted(
        p.relative_to(skill_dir).as_posix()
        for p in skill_dir.rglob("*")
        if p.is_file()
    )
    # SKILL.md first, for readability.
    return sorted(files, key=lambda f: (f != "SKILL.md", f))


def skill_version(skill_dir: Path, files: list[str]) -> str:
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode() + b"\0")
        h.update((skill_dir / rel).read_bytes() + b"\0")
    return h.hexdigest()[:12]


def frontmatter_description(skill_md: Path) -> str:
    """Extract `description` from SKILL.md YAML frontmatter (no PyYAML needed).

    Handles plain, quoted and block-scalar (>, >-, |, |-) values.
    """
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    try:
        end = lines.index("---", 1)
    except ValueError:
        return ""
    fm = lines[1:end]
    for i, line in enumerate(fm):
        if not line.startswith("description:"):
            continue
        value = line[len("description:"):].strip()
        if value[:1] in (">", "|"):
            block = []
            for nxt in fm[i + 1:]:
                if nxt.strip() and not nxt[:1].isspace():
                    break
                block.append(nxt.strip())
            sep = "\n" if value[0] == "|" else " "
            return sep.join(b for b in block if b).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return ""


def fetch_upstream(entry: dict, workdir: Path) -> Path:
    repo, ref, sha = entry["repo"], entry.get("ref", "main"), entry.get("sha")
    url = f"https://github.com/{repo}.git"
    dest = workdir / repo.replace("/", "__")
    if sha:
        # Pinned: fetch exactly that commit (same as the Claude Code entry).
        git = ["git", "-C", str(dest)]
        dest.mkdir(parents=True)
        subprocess.run(git + ["init", "--quiet"], check=True)
        subprocess.run(git + ["fetch", "--quiet", "--depth", "1", url, sha], check=True)
        subprocess.run(git + ["checkout", "--quiet", "FETCH_HEAD"], check=True)
    else:
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", ref, url, str(dest)],
            check=True,
        )
    head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    print(f"  fetched {repo}@{sha or ref} -> {head}")
    return dest


def build_plugin(plugin: Path, out: Path, workdir: Path) -> int:
    site_skills = out / plugin.name / "skills"
    site_skills.mkdir(parents=True)


    # 1. Local skills.
    local = plugin / "skills"
    if local.is_dir():
        for skill in sorted((plugin / "skills").iterdir()):
            if (skill / "SKILL.md").is_file():
                copy_skill(skill, site_skills / skill.name)

    # 2. Upstream skills (fetched at build time, not committed).
    upstream_file = plugin / "upstream.json"
    if upstream_file.is_file():
        for entry in json.loads(upstream_file.read_text()):
            clone = fetch_upstream(entry, workdir)
            license_file = next(
                (clone / n for n in LICENSE_NAMES if (clone / n).is_file()), None
            )
            for name in entry["skills"]:
                src = clone / name
                if not (src / "SKILL.md").is_file():
                    fail(f"{entry['repo']}: '{name}/SKILL.md' not found upstream")
                dst = site_skills / name
                if dst.exists():
                    fail(f"{plugin.name}: skill '{name}' is defined twice")
                copy_skill(src, dst)
                if license_file and not (dst / license_file.name).exists():
                    shutil.copy2(license_file, dst / license_file.name)

    # 3. Generated index.json.
    skills = []
    for skill in sorted(p for p in site_skills.iterdir() if p.is_dir()):
        files = skill_files(skill)
        skills.append({
            "name": skill.name,
            "description": frontmatter_description(skill / "SKILL.md"),
            "files": files,
            "version": skill_version(skill, files),
        })
    (site_skills / "index.json").write_text(
        json.dumps({"skills": skills}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  {plugin.name}: {len(skills)} skills -> {site_skills / 'index.json'}")
    return len(skills)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO_ROOT / "_site"))
    args = parser.parse_args()

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / ".nojekyll").touch()

    plugins = sorted(
    p for p in REPO_ROOT.iterdir()
    if ((p / ".claude-plugin" / "plugin.json").is_file() and (p / "skills").is_dir())
    or (p / "upstream.json").is_file()
    )
    with tempfile.TemporaryDirectory() as tmp:
        for plugin in plugins:
            print(f"Building {plugin.name}")
            build_plugin(plugin, out, Path(tmp))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the static skills site served by GitHub Pages.

``.claude-plugin/marketplace.json`` is the single source of truth: every plugin
listed there gets ``_site/<plugin-name>/skills/`` with its skills and a
generated ``index.json`` in the format OpenCode expects for ``skills``:

    {"skills": [{"name", "description", "files", "version"}]}

``version`` is a hash of the skill's contents, so OpenCode re-downloads a
skill only when it actually changed.

Plugin sources:
- local (``"source": "./<dir>"``): skills are copied from this repo.
- external (``"source": {"source": "github", "repo": "owner/name", ...}``,
  or ``"url"`` / ``"git-subdir"``): the repo is fetched at build time at the
  same ``ref`` / ``sha`` Claude Code uses, and never committed here.

Which skills are published follows Claude Code: the plugin's ``skills`` list
(paths relative to the plugin root) if present, otherwise every folder with a
``SKILL.md`` under the plugin's ``skills/`` directory.

To add or remove an external plugin, edit marketplace.json only.

Usage:
    python .github/scripts/build_site.py [--out _site]
    python .github/scripts/build_site.py --only pytorch-opt-skills
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
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
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


def git_url(source: dict) -> str:
    kind = source.get("source")
    if kind == "github":
        return f"https://github.com/{source['repo']}.git"
    if kind in ("url", "git-subdir"):
        return source["url"]
    fail(f"unsupported plugin source type: {kind!r} (expected github, url or git-subdir)")


def fetch_external(name: str, source: dict, workdir: Path) -> Path:
    """Clone an external plugin source and return the plugin root."""
    url, ref, sha = git_url(source), source.get("ref"), source.get("sha")
    dest = workdir / name
    git = ["git", "-C", str(dest)]
    dest.mkdir(parents=True)
    subprocess.run(git + ["init", "--quiet"], check=True)
    # Pinned sha wins (same as Claude Code); otherwise follow ref, or the default branch.
    subprocess.run(git + ["fetch", "--quiet", "--depth", "1", url, sha or ref or "HEAD"],
                   check=True)
    subprocess.run(git + ["checkout", "--quiet", "FETCH_HEAD"], check=True)
    head = subprocess.run(git + ["rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    print(f"  fetched {url}@{sha or ref or 'HEAD'} -> {head}")
    root = dest / source.get("path", "")
    if not root.is_dir():
        fail(f"{name}: path '{source.get('path')}' not found in {url}")
    return root


def find_license(root: Path, stop: Path) -> Path | None:
    """Closest license file from the plugin root up to the repo root."""
    for d in [root, *root.parents]:
        for n in LICENSE_NAMES:
            if (d / n).is_file():
                return d / n
        if d == stop:
            break
    return None


def plugin_skill_dirs(plugin: dict, root: Path) -> list[Path]:
    if plugin.get("skills"):
        dirs = [(root / s).resolve() for s in plugin["skills"]]
        for d in dirs:
            if not (d / "SKILL.md").is_file():
                fail(f"{plugin['name']}: '{d.relative_to(root.resolve())}/SKILL.md' not found")
        return dirs
    skills_root = root / "skills"
    if not skills_root.is_dir():
        fail(f"{plugin['name']}: no 'skills' list and no skills/ directory")
    return sorted(d for d in skills_root.iterdir() if (d / "SKILL.md").is_file())


def build_plugin(plugin: dict, out: Path, workdir: Path) -> int:
    name, source = plugin["name"], plugin["source"]
    site_skills = out / name / "skills"
    site_skills.mkdir(parents=True)

    if isinstance(source, str):
        root = (REPO_ROOT / source).resolve()
        license_file = None  # local skills are covered by this repo's LICENSE
    else:
        root = fetch_external(name, source, workdir)
        license_file = find_license(root, workdir / name)

    # 1. Copy skills.
    for src in plugin_skill_dirs(plugin, root):
        dst = site_skills / src.name
        if dst.exists():
            fail(f"{name}: skill '{src.name}' is defined twice")
        copy_skill(src, dst)
        if license_file and not (dst / license_file.name).exists():
            shutil.copy2(license_file, dst / license_file.name)

    # 2. Generated index.json.
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
    print(f"  {name}: {len(skills)} skills -> {site_skills / 'index.json'}")
    return len(skills)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO_ROOT / "_site"))
    parser.add_argument("--only", nargs="+", metavar="PLUGIN",
                        help="build only these plugins (default: all)")
    args = parser.parse_args()

    plugins = json.loads(MARKETPLACE.read_text(encoding="utf-8"))["plugins"]
    names = [p["name"] for p in plugins]
    if len(set(names)) != len(names):
        fail("duplicate plugin names in marketplace.json")
    if args.only:
        unknown = set(args.only) - set(names)
        if unknown:
            fail(f"not in marketplace.json: {sorted(unknown)}")
        plugins = [p for p in plugins if p["name"] in args.only]

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / ".nojekyll").touch()

    with tempfile.TemporaryDirectory() as tmp:
        for plugin in plugins:
            print(f"Building {plugin['name']}")
            build_plugin(plugin, out, Path(tmp))


if __name__ == "__main__":
    main()

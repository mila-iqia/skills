#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Read-only access to the annotations (highlights, comments, area selections) in a local Zotero library.

Zotero keeps annotations in its SQLite database (``zotero.sqlite`` in the data directory), not in
the PDFs. Zotero holds a lock on that file while it runs, and the newest annotations sit in the
write-ahead log, so every read copies the database and its WAL into a temporary directory and
queries the copy. The library is never written.

The data directory comes from ``$ZOTERO_DATA_DIR``, else the ``extensions.zotero.dataDir`` pref of a
Zotero profile, else ``~/Zotero``. Run ``zotero_reader.py check`` to see what was found.

Commands::

    zotero_reader.py check                             # data dir, database, annotation count
    zotero_reader.py papers [QUERY]                    # papers with annotations (title/key filter)
    zotero_reader.py show QUERY [--since T] [--json]   # annotations of matching papers
    zotero_reader.py recent [--days N] [--json]        # latest annotations across the library
    zotero_reader.py watch [QUERY] [--interval S]      # print annotations as they are made, one per line
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ANNOTATION_TYPES = {1: "highlight", 2: "note", 3: "image", 4: "ink", 5: "underline", 6: "text"}

PROFILE_ROOTS = [
    Path.home() / ".zotero" / "zotero",                                     # Linux
    Path.home() / "Library" / "Application Support" / "Zotero" / "Profiles",  # macOS
    Path(os.environ.get("APPDATA", "")) / "Zotero" / "Zotero" / "Profiles",  # Windows
]

# Annotations with their attachment, the attachment's parent item (absent for standalone PDFs) and
# the title of whichever of the two names the paper.
QUERY = """
SELECT
    ann_item.key AS annotation_key,
    a.type, a.color, a.pageLabel, a.position, a.sortIndex, a.text, a.comment,
    ann_item.dateAdded, ann_item.dateModified,
    paper.key AS paper_key,
    att_item.key AS attachment_key,
    att.path AS attachment_path,
    (SELECT v.value FROM itemData d
        JOIN fields f ON f.fieldID = d.fieldID AND f.fieldName = 'title'
        JOIN itemDataValues v ON v.valueID = d.valueID
        WHERE d.itemID = paper.itemID) AS title,
    (SELECT group_concat(t.name, ', ') FROM itemTags it JOIN tags t ON t.tagID = it.tagID
        WHERE it.itemID = a.itemID) AS tags
FROM itemAnnotations a
JOIN items ann_item ON ann_item.itemID = a.itemID
JOIN itemAttachments att ON att.itemID = a.parentItemID
JOIN items att_item ON att_item.itemID = att.itemID
JOIN items paper ON paper.itemID = COALESCE(att.parentItemID, att.itemID)
WHERE ann_item.itemID NOT IN (SELECT itemID FROM deletedItems)
"""


def find_data_dir() -> tuple[Path, str]:
    """The Zotero data directory and a description of where that answer came from."""
    if env := os.environ.get("ZOTERO_DATA_DIR"):
        return Path(env).expanduser(), "$ZOTERO_DATA_DIR"
    for root in PROFILE_ROOTS:
        for prefs in sorted(root.glob("*/prefs.js")) if root.is_dir() else []:
            m = re.search(r'user_pref\("extensions\.zotero\.dataDir",\s*"([^"]+)"\)', prefs.read_text())
            if m:
                return Path(m.group(1)), f"dataDir pref in {prefs}"
    return Path.home() / "Zotero", "default location"


def db_files(data_dir: Path) -> list[Path]:
    return [data_dir / "zotero.sqlite", data_dir / "zotero.sqlite-wal"]


def snapshot(data_dir: Path, tmp: Path) -> sqlite3.Connection:
    """Copy the database and its WAL (which holds the newest annotations) and open the copy."""
    db, wal = db_files(data_dir)
    if not db.is_file():
        sys.exit(f"No Zotero database at {db}. Set ZOTERO_DATA_DIR to the Zotero data directory.")
    for name in ("zotero.sqlite", "zotero.sqlite-wal", "zotero.sqlite-shm"):
        (tmp / name).unlink(missing_ok=True)
    shutil.copy2(db, tmp / db.name)
    if wal.is_file():
        shutil.copy2(wal, tmp / wal.name)
    conn = sqlite3.connect(tmp / db.name)
    conn.row_factory = sqlite3.Row
    return conn


def pdf_path(data_dir: Path, attachment_key: str, path: str | None) -> str | None:
    """Where the annotated file is: stored files live under storage/<key>/, linked ones anywhere."""
    if not path:
        return None
    if path.startswith("storage:"):
        return str(data_dir / "storage" / attachment_key / path.removeprefix("storage:"))
    return path


def load_annotations(conn: sqlite3.Connection, data_dir: Path, where: str = "", params: tuple = ()) -> list[dict]:
    rows = conn.execute(f"{QUERY} {where} ORDER BY paper.key, att_item.key, a.sortIndex", params)
    out = []
    for row in rows:
        ann = dict(row)
        ann["type"] = ANNOTATION_TYPES.get(ann["type"], str(ann["type"]))
        # 1-based page in the file, for reading the page itself; pageLabel is the printed number.
        ann["page"] = json.loads(ann.pop("position") or "{}").get("pageIndex", -1) + 1 or None
        ann["pdf"] = pdf_path(data_dir, ann["attachment_key"], ann.pop("attachment_path"))
        if ann["type"] in ("image", "ink"):
            # Zotero renders these to a PNG cache when the PDF is opened.
            image = data_dir / "cache" / "library" / f"{ann['annotation_key']}.png"
            ann["image"] = str(image) if image.is_file() else None
        out.append(ann)
    return out


def paper_filter(query: str | None) -> tuple[str, tuple]:
    """Match an item key exactly or a case-insensitive substring of the title."""
    if not query:
        return "", ()
    return "AND (paper.key = ? OR att_item.key = ? OR title LIKE ?)", (query, query, f"%{query}%")


def print_annotations(anns: list[dict]) -> None:
    current = None
    for ann in anns:
        if ann["paper_key"] != current:
            current = ann["paper_key"]
            print(f"\n## {ann['title'] or '(untitled)'}  [{ann['paper_key']}]")
            print(f"pdf: {ann['pdf']}")
        print(f"\n- p.{ann['pageLabel'] or '?'} (pdf page {ann['page']}) {ann['type']} {ann['color'] or ''}"
              f" ({ann['dateModified']} UTC)")
        if ann["text"]:
            print("  > " + " ".join(ann["text"].split()))
        if ann["comment"]:
            print("  comment: " + ann["comment"].strip())
        if ann["tags"]:
            print("  tags: " + ann["tags"])
        if "image" in ann:
            print(f"  image: {ann['image'] or 'not cached (open the PDF in Zotero to render it)'}")


def one_line(ann: dict, event: str) -> str:
    """A self-contained single line, so each watch event can be read on its own."""
    parts = [f"{event} {ann['type']} p.{ann['pageLabel'] or '?'} (pdf page {ann['page']})",
             f"in [{ann['paper_key']}] {ann['title'] or '(untitled)'}"]
    if ann["text"]:
        parts.append(f"text: {' '.join(ann['text'].split())!r}")
    if ann["comment"]:
        parts.append(f"comment: {' '.join(ann['comment'].split())!r}")
    if ann.get("image"):
        parts.append(f"image: {ann['image']}")
    parts.append(f"pdf: {ann['pdf']}")
    return " | ".join(parts)


def emit(anns: list[dict], as_json: bool) -> None:
    if as_json:
        print(json.dumps(anns, indent=2))
    else:
        print_annotations(anns)


def cmd_check(conn: sqlite3.Connection, data_dir: Path, source: str, args: argparse.Namespace) -> None:
    n = conn.execute("SELECT count(*) FROM itemAnnotations").fetchone()[0]
    print(f"data dir: {data_dir}  (from {source})")
    print(f"database: {data_dir / 'zotero.sqlite'}")
    print(f"annotations: {n}")


def cmd_papers(conn: sqlite3.Connection, data_dir: Path, source: str, args: argparse.Namespace) -> None:
    counts: dict[str, list] = {}
    for ann in load_annotations(conn, data_dir, *paper_filter(args.query)):
        entry = counts.setdefault(ann["paper_key"], [ann["title"], 0, ann["dateModified"]])
        entry[1] += 1
        entry[2] = max(entry[2], ann["dateModified"])
    for key, (title, n, last) in sorted(counts.items(), key=lambda kv: kv[1][2], reverse=True):
        print(f"{key}  {n:3d} annotations  last {last}  {title}")


def cmd_show(conn: sqlite3.Connection, data_dir: Path, source: str, args: argparse.Namespace) -> None:
    where, params = paper_filter(args.query)
    if args.since:
        where, params = where + " AND ann_item.dateModified >= ?", params + (args.since,)
    anns = load_annotations(conn, data_dir, where, params)
    if not anns:
        sys.exit(f"No annotations on a paper matching {args.query!r}. Try `papers` to list them.")
    emit(anns, args.json)


def cmd_recent(conn: sqlite3.Connection, data_dir: Path, source: str, args: argparse.Namespace) -> None:
    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d %H:%M:%S")
    emit(load_annotations(conn, data_dir, "AND ann_item.dateModified >= ?", (since,)), args.json)


def watch(data_dir: Path, tmp: Path, query: str | None, interval: float) -> None:
    """Print a line for each annotation added or edited from now on, until killed.

    Zotero saves a highlight as soon as it is made and the comment typed into it later, so one
    highlight with a comment usually shows up as NEW and then UPDATED.
    """
    seen: dict[str, str] = {}
    stamps = None
    first = True
    while True:
        current = [f.stat().st_mtime_ns if f.is_file() else 0 for f in db_files(data_dir)]
        if current != stamps:
            stamps = current
            conn = snapshot(data_dir, tmp)
            try:
                anns = load_annotations(conn, data_dir, *paper_filter(query))
            finally:
                conn.close()
            for ann in anns:
                key, modified = ann["annotation_key"], ann["dateModified"]
                if not first and seen.get(key) != modified:
                    print(one_line(ann, "NEW" if key not in seen else "UPDATED"), flush=True)
                seen[key] = modified
            if first:
                print(f"watching {len(seen)} existing annotations in {data_dir}", flush=True)
                first = False
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="show the data dir and database found").set_defaults(fn=cmd_check)
    p = sub.add_parser("papers", help="list papers that have annotations")
    p.add_argument("query", nargs="?", help="item key or title substring")
    p.set_defaults(fn=cmd_papers)
    p = sub.add_parser("show", help="annotations of the papers matching QUERY")
    p.add_argument("query", help="item key or title substring")
    p.add_argument("--since", help="only annotations modified at or after this UTC time, e.g. '2026-10-26 15:30'")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("recent", help="annotations added or changed in the last N days")
    p.add_argument("--days", type=float, default=7)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_recent)
    p = sub.add_parser("watch", help="print annotations as they are made, one line each, until killed")
    p.add_argument("query", nargs="?", help="only this paper (item key or title substring)")
    p.add_argument("--interval", type=float, default=3, help="seconds between checks")
    args = parser.parse_args()

    data_dir, source = find_data_dir()
    with tempfile.TemporaryDirectory(prefix="zotero-snapshot-") as tmp:
        if args.command == "watch":
            try:
                watch(data_dir, Path(tmp), args.query, args.interval)
            except KeyboardInterrupt:
                pass
            return
        conn = snapshot(data_dir, Path(tmp))
        try:
            args.fn(conn, data_dir, source, args)
        finally:
            conn.close()


if __name__ == "__main__":
    main()

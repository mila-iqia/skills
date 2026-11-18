#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Reply to a Zotero annotation's comment by appending an answer to it, through the Zotero Web API.

The reply is appended after the user's comment, separated by a blank line and a ``— 🤖 Claude:``
marker, so the question and its answer stay together in one comment. Zotero's sync brings it to the
desktop app within seconds.

This goes through the Web API (api.zotero.org), never the local database: writing ``zotero.sqlite``
can corrupt the library or be undone by sync, and Zotero's local HTTP API (port 23119) is read-only.
The write is conditional on the annotation's version (``If-Unmodified-Since-Version``), so an edit
the user synced in the meantime is never overwritten: on a conflict the comment is re-read and the
reply appended to its latest text.

Needs ``ZOTERO_API_KEY``: a key with write access, from https://www.zotero.org/settings/keys/new.
The user ID is looked up from the key. The annotation must already be synced to zotero.org.

Usage::

    zotero_reply.py ANNOTATION_KEY "answer text"     # append a reply
    zotero_reply.py ANNOTATION_KEY - < answer.txt    # reply text from stdin
    zotero_reply.py ANNOTATION_KEY "..." --dry-run   # print the new comment, write nothing
    zotero_reply.py ANNOTATION_KEY "..." --group ID  # annotation in a group library
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.zotero.org"
MARKER = "— 🤖 Claude:"
ATTEMPTS = 3


def call(method: str, url: str, key: str, body: dict | None = None, version: int | None = None) -> tuple[int, dict | None]:
    """One Web API request; returns the status and the decoded JSON body (None when empty)."""
    headers = {"Zotero-API-Key": key, "Zotero-API-Version": "3", "Content-Type": "application/json"}
    if version is not None:
        headers["If-Unmodified-Since-Version"] = str(version)
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode()
            return response.status, json.loads(text) if text else None
    except urllib.error.HTTPError as error:
        return error.code, None


def library_url(key: str, group: str | None) -> str:
    if group:
        return f"{API}/groups/{group}"
    status, info = call("GET", f"{API}/keys/current", key)
    if status != 200 or not info:
        sys.exit(f"error: could not look up the API key (HTTP {status}); is ZOTERO_API_KEY valid?")
    if not info.get("access", {}).get("user", {}).get("write"):
        sys.exit("error: this API key has no write access to the personal library")
    return f"{API}/users/{info['userID']}"


def with_reply(comment: str | None, reply: str) -> str:
    comment = (comment or "").rstrip()
    reply = f"{MARKER} {reply.strip()}"
    return f"{comment}\n\n{reply}" if comment else reply


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("annotation", help="annotation key, as printed by zotero_reader.py show --json")
    parser.add_argument("text", help="the reply; '-' reads it from stdin")
    parser.add_argument("--group", help="group library ID, when the annotation is not in the personal library")
    parser.add_argument("--dry-run", action="store_true", help="print the new comment and write nothing")
    args = parser.parse_args()

    key = os.environ.get("ZOTERO_API_KEY")
    if not key:
        sys.exit("error: ZOTERO_API_KEY is not set (create a key with write access at https://www.zotero.org/settings/keys/new)")
    reply = sys.stdin.read() if args.text == "-" else args.text
    if not reply.strip():
        sys.exit("error: empty reply")
    item_url = f"{library_url(key, args.group)}/items/{args.annotation}"

    for _ in range(ATTEMPTS):
        status, item = call("GET", item_url, key)
        if status == 404 or not item:
            sys.exit(f"error: annotation {args.annotation} not found on zotero.org (HTTP {status}): "
                     "not synced yet, sync disabled, or in a group library (--group)")
        if item["data"].get("itemType") != "annotation":
            sys.exit(f"error: {args.annotation} is a {item['data'].get('itemType')}, not an annotation")
        comment = with_reply(item["data"].get("annotationComment"), reply)
        if args.dry_run:
            print(comment)
            return
        status, _ = call("PATCH", item_url, key, {"annotationComment": comment}, version=item["version"])
        if status == 204:
            print(f"replied to {args.annotation}")
            return
        if status != 412:  # 412: the annotation changed since it was read; re-read and retry
            sys.exit(f"error: update of {args.annotation} failed (HTTP {status})")
    sys.exit(f"error: {args.annotation} kept changing while replying; try again once the user stops editing it")


if __name__ == "__main__":
    main()

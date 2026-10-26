---
name: zotero-reading-buddy
description: >-
  Act as the user's reading buddy for papers they read in Zotero: they highlight
  passages they don't understand (often with a question in the comment) and you
  help them understand, interactively, grounded in the paper itself. Reads
  highlights, comments and area selections from the local Zotero database, and
  can watch for new ones live while the user reads. Use when the user asks what
  they highlighted or annotated, asks for help with a paper they are reading in
  Zotero, says "reading buddy", "help me read", "explain my highlights", or wants
  their reading notes reviewed. Read-only: never modifies the Zotero library.
---

# Zotero reading buddy

The user reads papers in Zotero and highlights what they don't understand, often
typing a question into the highlight's comment. Your job is to help them
understand the paper: explain the passages they flagged, answer their questions,
and check that the explanation landed, as a knowledgeable colleague reading
alongside them would.

## Tool

`scripts/zotero_reader.py`, next to this file (at
`$CLAUDE_PLUGIN_ROOT/skills/zotero-reading-buddy/scripts/` when that is set).
Standard library only; run it with `uv run --script` (or `python3`).

```bash
zotero_reader.py papers [QUERY]                    # papers with annotations, most recently annotated first
zotero_reader.py show QUERY [--since T] [--json]   # annotations of the matching paper(s), in reading order
zotero_reader.py recent [--days N] [--json]        # annotations added/changed in the last N days (default 7)
zotero_reader.py watch [QUERY] [--interval S]      # one line per new/edited annotation, until killed
zotero_reader.py check                             # which data dir and database are used
```

`QUERY` is a Zotero item key (e.g. `NYY8TDXS`, as printed by `papers`) or a
case-insensitive substring of the title. Use the key once you know it. `--since`
takes a UTC time such as `'2026-10-26 15:30'`.

Every annotation comes with the PDF's path and its **pdf page** (1-based page in
the file; `p.` is the printed page label, which can differ). Area selections
(`image`) and drawings (`ink`) have no text: read the PNG at the `image` path to
see what was selected, usually a figure or an equation.

## Starting a session

1. Find the paper: `papers` (the one being read is usually the most recently
   annotated), then `show <key>`.
2. Read the paper before explaining anything: the abstract and introduction, and
   the full pages the annotations are on (read the PDF with the page range). A
   highlight is a fragment; the sentence before it, the definition two
   paragraphs up, or the figure it refers to is usually what makes it make sense.
3. Go through the annotations in reading order, as below.
4. If the user is still reading, ask which mode they want (next section): batch
   (they annotate a stretch, then ask for answers) or live (you react to each
   highlight as it is made). Batch is the default if they don't say.

## Helping with an annotation

- **A comment is the user talking to you.** Answer its question directly, first.
- **A highlight without a comment** still means "I don't get this": explain it
  briefly, then ask whether that was the sticking point.
- **Ground it in the paper.** Use the paper's own notation and equations, and
  point to where things are defined ("eq. 3 on p.4 defines …"). If the
  explanation depends on an earlier section, a figure, or a cited paper, read
  that rather than guessing what it says.
- **Explain, then check.** Give the intuition, then the precise version (a small
  derivation, a toy example, or how it differs from what the user may already
  know). End with one short question that tests understanding, or ask what is
  still unclear. Don't lecture through every highlight at once: take them one or
  two at a time and let the user steer.
- **Be honest about the paper.** If a passage is vague, hand-wavy or wrong, say
  so; the confusion is not always the reader's fault.
- Related highlights (same page, same concept) can be answered together.

## Batch or live mode

**Batch mode** (the default): the user keeps reading and annotating
undisturbed, then says they're ready. Note the UTC time of the last annotation
you discussed, and when they come back fetch only the new ones with
`show <key> --since '<that time>'`, then answer them in reading order. Nothing
runs in the background.

**Live mode**: you react to each highlight as it is made. Some readers like
this, but it can feel like being interrupted mid-thought; if the user says so,
stop the watcher and switch to batch. Run `watch` in the background (in Claude
Code, with the Monitor tool, so that each output line arrives as a
notification), restricted to the paper being read:

```bash
uv run --script <scripts>/zotero_reader.py watch <paper key>
```

It prints one self-contained line per annotation added or edited, with the
text, the comment, the pdf page and the PDF path. Zotero saves a highlight as
soon as it is made, and saves its comment while it is being typed, so one
highlight can arrive as `NEW` followed by several `UPDATED` lines with a
partial comment ("Maybe only in the case where"). Answer only once the comment
reads as a complete question. A lone `NEW` highlight with no comment may get
one shortly, so give it a moment too. Stop the watcher when the session ends.

## How it reads the database safely

Annotations live in Zotero's SQLite database (`zotero.sqlite`), not in the PDFs.
Zotero locks the database while it runs, and the newest annotations sit in the
write-ahead log until Zotero checkpoints it, so the script copies **both** files
to a temporary directory and queries the copy. That works while Zotero is open
and never writes to the library. Don't open `zotero.sqlite` directly, and never
write to it: a direct read can miss the latest highlights, and a write can
corrupt the library or be overwritten by sync.

The data directory is found from `$ZOTERO_DATA_DIR`, the
`extensions.zotero.dataDir` pref of a Zotero profile, or `~/Zotero`; `check`
says which. If an image annotation's PNG isn't cached yet, opening the PDF in
Zotero renders it.

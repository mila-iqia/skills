---
name: mila-paperoni
description: >-
  Query and manage the Mila Paperoni publication database via its REST API at
  https://paperoni.mila.quebec. Use when the user wants to search for papers,
  look up an author's publications, filter by venue or date, add missing papers,
  populate a paper entry from an external link (arXiv, DOI, etc.), or claim papers
  to their Mila profile with their @mila.quebec email. Also use when the user asks
  about the Paperoni API, authentication/token setup, which identity a token
  belongs to, or how to submit a paper suggestion.
---

# Paperoni

Paperoni is Mila's scientific publication database, available at **https://paperoni.mila.quebec**. It indexes papers by Mila researchers and supports search, filtering, and community-driven additions.

## Authentication

All write endpoints and some advanced features require a Bearer token.

### Getting your token

1. Open **https://paperoni.mila.quebec/token** in your browser.
2. Sign in with your Google account when prompted.
3. After the OAuth flow completes the page shows your token — copy it.

Your identity in Paperoni **is** the email account you signed in with — the token
itself is opaque and carries no readable identity. Call `GET /api/v1/me` to read it
back programmatically.

### Storing the token

Store it in one of two places (Claude will use whichever is set):

```bash
# Option A – environment variable (good for one-off scripts)
export PAPERONI_TOKEN="<your-token>"

# Option B – config file (persisted across sessions)
mkdir -p ~/.config/paperoni
# paste the token, then press Ctrl-D (avoids putting it in shell history)
cat > ~/.config/paperoni/token
chmod 600 ~/.config/paperoni/token
```

### Using the token in API calls

Send it as a Bearer token in every authenticated request:

```
Authorization: Bearer <your-token>
```

---

## Endpoints (user-facing)

Base URL: `https://paperoni.mila.quebec`

### `GET /api/v1/me` — Who am I?

Returns the identity the Bearer token resolves to: the account's email, its display
name when one is set, and the capabilities granted to it. Requires authentication but
**no capability** — any valid token gets a `200`.

Use it to:

- confirm a stored token is valid before a batch of writes;
- read back the email that identifies you, e.g. the `@mila.quebec` address to put on
  your papers when claiming them;
- see which roles a token actually holds, before debugging a `403`;
- tell a bad token apart from an under-privileged one. `/me` asks for no capability, so
  it isolates token validity on its own: `401 {"detail":"Authentication required"}` (no
  header sent), `401 {"detail":"Malformed authorization"}` (header garbled) and
  `401 {"detail":"Invalid user"}` (token revoked or unknown) all mean the token is the
  problem. A valid token gets `200` here, and fails only later with
  `403 {"detail":"validate capability required"}` on a route needing a role it lacks.

**Response** — `email` is always present; `name` is nullable.

```json
{
  "email": "jane.doe@mila.quebec",
  "name": "Jane Doe",
  "capabilities": ["search", "user", "validate", "admin"]
}
```

Capability names are plain strings — `search`, `user`, `validate`, `admin` and
`user_management` are the ones in use, and a token may carry others (`dev`, for
instance). A service or automation token may also resolve to something that is not a
`@mila.quebec` address — if `/me` returns such an identifier, do not use it as the author
email when claiming papers.

**Example**

```bash
curl -H "Authorization: Bearer $PAPERONI_TOKEN" \
  "https://paperoni.mila.quebec/api/v1/me"
```


---

### `GET /api/v1/search` — Search papers

Returns a paginated list of papers matching the given filters.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `title` | string | Full-text search on the paper title |
| `author` | string | Author name. Prefix with `=` for an exact match (e.g. `=Yoshua Bengio`). A `@mila.quebec` email also works and is the reliable way to find one researcher's papers |
| `institution` | string | Institution name of an author |
| `venue` | string | Venue name (conference, journal, etc.) |
| `topic` | string[] | Topic tags — all supplied topics must match |
| `start_date` | date | Earliest publication date, `YYYY-MM-DD` |
| `end_date` | date | Latest publication date, `YYYY-MM-DD` |
| `status` | string[] | Release status filter. Prefix with `-` or `~` to exclude |
| `flags` | string[] | Flag filter. Prefix with `-` or `~` to exclude |
| `paper_id` | integer | Retrieve by numeric paper ID |
| `expand_links` | boolean | Resolve metadata link tokens to actual URLs (default: `false`) |
| `limit` | integer | Max papers to return (default: `100`) |
| `offset` | integer | Pagination offset (default: `0`) |

**Response**

```json
{
  "results": [ /* array of Paper objects */ ],
  "total": 42,
  "count": 10,
  "next_offset": 10   /* null when no more pages */
}
```

**Example — find recent NeurIPS papers by Yoshua Bengio**

```bash
curl "https://paperoni.mila.quebec/api/v1/search?author=%3DYoshua+Bengio&venue=NeurIPS&start_date=2023-01-01"
```

OR, using the researcher's email address:

```bash
curl "https://paperoni.mila.quebec/api/v1/search?author=yoshua.bengio@mila.quebec&venue=NeurIPS&start_date=2023-01-01"
```

---

### `GET /api/v1/paper/{paper_id}` — Get a single paper

Returns the full record for one paper.

**Path parameter:** `paper_id` (string or integer)

**Query parameter:** `latest_edit` (boolean, default `false`) — return the most recent pending edit rather than the accepted version.

**Example**

```bash
curl "https://paperoni.mila.quebec/api/v1/paper/12345"
```

---

### `POST /api/v1/populate` — Pre-fill a paper from external links

Given one or more external links (arXiv URL, DOI, Semantic Scholar URL, etc.), the server fetches metadata and returns a merged `Paper` object. **This does not write anything to the database** — it is a helper for building a well-formed Paper before submitting it via `/api/v1/suggest`.

**Request body**

```json
{
  "papers": [
    {
      "title": "",
      "links": [
        { "type": "arxiv", "link": "https://arxiv.org/abs/2301.00001" }
      ]
    }
  ],
  "comment": "optional note"
}
```

**Response**

```json
{
  "success": true,
  "message": "...",
  "paper": { /* merged Paper object */ }
}
```

**Tip:** use `/api/v1/populate` to let the server auto-fill `title`, `abstract`, `authors`, `releases`, and `topics` from an arXiv or DOI link, then pass the result to `/api/v1/suggest`.

**Author emails in harvested metadata are not trustworthy.** arXiv, DOI and Semantic
Scholar carry either no email or a personal/institutional one. Never copy a personal
address into the record. Set `authors[].author.email` only where you are sure of the
person's `@mila.quebec` address and it is already recorded in Paperoni — see the
**Claiming papers** section — and otherwise leave it `null`. Claiming is not part of
ingesting a paper; it is a separate, conservative step.

---

### `POST /api/v1/suggest` — Suggest adding or editing a paper

> ⚠️ **Always search first.** Before calling this endpoint, use `/api/v1/search` (by title, DOI link, or author) to confirm the paper is not already in the database. Duplicate submissions create review burden for validators.

Submits one or more papers for inclusion. The submission enters a pending queue and must be approved by a validator before appearing in search results.

**Editing an existing paper.** Set `id` to the paper's ID; it also works for the ID of a
pending paper, if you need to correct a previous suggestion. An edit **replaces** the
paper rather than merging into it: the payload is taken as the paper's new whole contents,
so whatever you omit — `abstract`, `releases`, `topics`, `links`, co-authors — is gone
once a validator accepts the edit. Fetch the current record from `/api/v1/paper/{paper_id}`,
change what you need, and submit the complete object back. The server-set fields that come
with it (`score`, `version`, `key`, `info`) are accepted on re-submission, so the fetched
record needs no scrubbing. Never submit a stub.

**Requesting a deletion.** Set the paper's `id`, add `"mark:delete"` to `flags`, and say
why in `comment`. When a validator approves that suggestion the paper is deleted instead of
updated; rejecting it leaves the paper untouched. This is the only submission where a
partial record is correct — it is acted on as a removal, so it cannot clobber the paper the
way a partial edit would. `title` is still required by the schema: send the paper's current
title, or the request fails with a `500`.

```bash
curl -sf -X POST "https://paperoni.mila.quebec/api/v1/suggest" \
  -H "Authorization: Bearer $PAPERONI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"papers": [{"id": "'"$PAPER_ID"'", "title": "'"$TITLE"'", "flags": ["mark:delete"]}],
       "comment": "Duplicate of <other paper id>: same DOI"}'
```

Deletion is permanent and nothing in the API restores a paper, so request it only for a
clear duplicate or a record that plainly does not belong. Wrong *metadata* is an edit, not
a deletion. The `comment` is stored on the suggestion alongside your identity in
`info.comments` and is the only context a validator gets, so name the duplicate's ID or
state the reason rather than writing "remove this".

To watch for deletions awaiting review, including your own:

```bash
curl -s -H "Authorization: Bearer $PAPERONI_TOKEN" \
  "https://paperoni.mila.quebec/api/v1/pending/list?flags=mark%3Adelete&limit=20"
```

**Request body**

```json
{
  "papers": [ /* one or more Paper objects (see schema below) */ ],
  "comment": "optional note for the validator"
}
```

**Response**

```json
{
  "success": true,
  "message": "...",
  "count": 1,
  "ids": ["<pending-paper-id>"]
}
```

The `id` returned is the pending suggestion's, which is also the paper's own ID: a new
paper keeps that ID once approved, and an edit is filed under the ID it targets, so the
same ID comes back either way. Multiple edits to one paper share a single queue entry.
IDs are commonly opaque hex strings rather than the integers the schema admits.

**Typical workflow for adding a missing paper**

```bash
# 1. Check it doesn't already exist
curl "https://paperoni.mila.quebec/api/v1/search?title=Attention+Is+All+You+Need"

# 2. Populate metadata from an external link (returns a pre-filled Paper)
curl -s -X POST "https://paperoni.mila.quebec/api/v1/populate" \
  -H "Authorization: Bearer $PAPERONI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "papers": [{"title": "", "links": [{"type": "arxiv", "link": "https://arxiv.org/abs/1706.03762"}]}]
  }'

# 3. Submit the populated paper for review
curl -X POST "https://paperoni.mila.quebec/api/v1/suggest" \
  -H "Authorization: Bearer $PAPERONI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "papers": [ /* paste the paper object from step 2 */ ],
    "comment": "Missing paper from NeurIPS 2017"
  }'
```

---

## Claiming papers

**Claiming** a paper means attaching your `@mila.quebec` email to it as an author —
`authors[].author.email` — so Paperoni knows the paper is yours.

This is not decoration: **author lookups run on the `@mila.quebec` address.** A paper
that stores no email, or only a personal one (`@gmail.com`, a former institution's
domain, an advisor's shared address), will not come back when someone searches for that
person. The `@mila.quebec` address is the key the lookup uses; a personal email is never
used for it, so it does not just fail to help — it leaves a record that someone has to
clean up later.

**Rules**

- **Your own papers: claim freely.** Your address comes from `GET /api/v1/me`, so it
  cannot be guessed wrong. This applies both to papers you add and to edits you suggest.
- **Other people's papers: don't fill in emails wholesale.** A wrong address is worse
  than a missing one. Add a co-author's address only when all three hold:
  1. they are an **obvious** Mila author — Mila on the paper itself, or a researcher you
     know to be at Mila;
  2. that address **already exists in Paperoni attached to that person** (check below);
  3. you are adding **at most 5** addresses to that one paper. Stop at 5. Papers with a
     hundred authors are not a to-do list: sweeping them produces a wall of unverifiable
     edits, buries the validator, and is wrong more often than it is right.
- **Never construct an address from a name.** It is not reliably
  `firstname.lastname@mila.quebec` — some carry numeric suffixes, some differ entirely.
  A constructed address that happens to exist belongs to whoever holds it. If it is not
  already in the database, treat it as unknown and leave `email` null.
- **Never a personal address** (`@gmail.com`, a former institution) for anyone. Personal
  addresses are not used for lookup, so they buy nothing and leave a record to clean up.
- Leave `display_name` and `author.name` exactly as printed — the claim lives in the
  `email` field alone. Don't "correct" a name to match an address.
- External collaborators with no Mila address: leave their `email` null.

**Checking an address exists before using it**

Never attach an email you have not confirmed is already in Paperoni for that person:

```bash
EMAIL=jane.doe@mila.quebec
curl -s -H "Authorization: Bearer $PAPERONI_TOKEN" \
  "https://paperoni.mila.quebec/api/v1/search?author=$EMAIL&limit=5" |
jq -c --arg e "$EMAIL" \
  '{total, names: [.results[].authors[] | select(.author.email == $e) | .display_name] | unique}'
```

Use the address only if `total` is above zero **and** `names` includes the person you are
about to attach it to. `total: 0` means the address is wrong or has never been recorded —
either way, leave the field null and let that person claim their own work. This catches
exactly the near-miss that pattern-matching produces: someone recorded as
`jane.doe2@mila.quebec` returns `0` for the `jane.doe@mila.quebec` you guessed — and that
guessed address may itself exist and belong to a different person entirely.

**Claiming via the API**

Fetch the record, change the one email, send the record back whole (an edit replaces —
see `/api/v1/suggest`).

```bash
PAPER_ID=6a12f3c0d4e5f6a7b8c9d0e1   # ids are usually hex strings, not integers

# 1. Full current record. Take /paper/{id} as the base for the edit, not a search hit.
#    -sf makes curl fail on an error response instead of silently handing jq an error
#    body. What comes back can be fed straight in again as-is: the server-set fields it
#    carries (score, version, key, info) are accepted.
curl -sf -H "Authorization: Bearer $PAPERONI_TOKEN" \
  "https://paperoni.mila.quebec/api/v1/paper/$PAPER_ID" > paper.json

# 2. Set the email for one author only; other authors are left exactly as they were
jq '(.authors[] | select(.author.name == "Jane Doe") | .author.email)
    = "jane.doe@mila.quebec"' paper.json > claim.json

# 3. Submit that record back, untouched apart from step 2
jq -n --slurpfile p claim.json \
  '{papers: [$p[0]], comment: "Claim: attaching my Mila email"}' |
curl -sf -X POST "https://paperoni.mila.quebec/api/v1/suggest" \
  -H "Authorization: Bearer $PAPERONI_TOKEN" \
  -H "Content-Type: application/json" \
  -d @-
```

Edits go through the same pending queue as new papers and need a validator.
Batch-claiming your *own* papers is this loop repeated over the papers you wrote,
re-fetching each record rather than editing one template. It is not a template for
filling in co-authors.

**Claiming in the browser**

**https://paperoni.mila.quebec/my-papers** is the interface for reviewing and claiming
your own papers one at a time. Point a user there when they want to see their own list
and click through it themselves; use the API when automating or batch-claiming.

**Claiming on someone else's behalf**

A token is not limited to your own record. You may edit anybody's paper, including
attaching a colleague's `@mila.quebec` address to work they have not claimed yet — useful
when onboarding someone. It is also the easiest way to attach the wrong address to
another person's entire publication record, so every check above applies in full, and the
5-per-paper cap applies to you exactly as it would to anyone else. Two points specific to
claiming for someone else:

- Use **the author's** address, never your own — the submitter is not the person being
  claimed.
- Say so in `comment` ("claiming on behalf of …") so the validator knows why the submitter
  isn't an author on the paper.

For anything beyond a handful of papers, point the person at `/my-papers` and let them
claim their own list: they can confirm each entry, and you cannot. Bulk-rewriting a whole
group's catalogue is not a task to automate on other people's behalf.

**Verify a claim landed** — search by the address once the edit is accepted:

```bash
curl "https://paperoni.mila.quebec/api/v1/search?author=jane.doe@mila.quebec"
```

Pending edits are not in search results; check them with `latest_edit=true` on
`/api/v1/paper/{paper_id}`.

---

## Paper JSON schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Paper",
  "type": "object",
  "required": ["title"],
  "properties": {
    "id":       { "anyOf": [{"type": "integer"}, {"type": "string"}], "description": "Internal database ID (set by server, omit on submission)" },
    "version":  { "type": "string", "format": "date-time", "description": "Timestamp of the last accepted version (set by server)" },
    "key":      { "type": "string", "default": "n/a" },
    "score":    { "type": "number", "default": 0.0, "description": "Relevance score (set by server on search results)" },
    "title":    { "type": "string" },
    "abstract": { "type": "string" },
    "flags":    { "type": "array", "items": {"type": "string"}, "uniqueItems": true },
    "info":     { "type": "object", "additionalProperties": true, "description": "Arbitrary extra metadata" },
    "authors": {
      "type": "array",
      "items": {
        "title": "PaperAuthor",
        "type": "object",
        "required": ["author", "display_name"],
        "properties": {
          "display_name": { "type": "string" },
          "author": {
            "title": "Author",
            "type": "object",
            "required": ["name"],
            "properties": {
              "name":    { "type": "string" },
              "email":   { "type": "string" },
              "aliases": { "type": "array", "items": {"type": "string"} },
              "links":   { "$ref": "#/$defs/LinkArray" }
            }
          },
          "affiliations": {
            "type": "array",
            "items": {
              "title": "Institution",
              "type": "object",
              "required": ["name"],
              "properties": {
                "name":     { "type": "string" },
                "category": { "enum": ["industry", "academia", "unknown"], "default": "unknown" },
                "country":  { "type": "string" },
                "aliases":  { "type": "array", "items": {"type": "string"} }
              }
            }
          }
        }
      }
    },
    "releases": {
      "type": "array",
      "items": {
        "title": "Release",
        "type": "object",
        "required": ["venue", "status"],
        "properties": {
          "status": { "type": "string" },
          "pages":  { "type": "string" },
          "peer_review_status": {
            "enum": ["peer-reviewed", "preprint", "workshop", "other", "unknown"],
            "default": "unknown"
          },
          "venue": {
            "title": "Venue",
            "type": "object",
            "required": ["type", "name", "series", "date", "date_precision"],
            "properties": {
              "type": {
                "enum": [
                  "journal", "conference", "workshop", "symposium", "book",
                  "review", "news", "study", "meta_analysis", "editorial",
                  "letters_and_comments", "case_report", "clinical_trial",
                  "unknown", "challenge", "forum", "track", "tutorials",
                  "seminar", "preprint", "dataset"
                ]
              },
              "name":           { "type": "string" },
              "series":         { "type": "string", "description": "Canonical series name, e.g. \"NeurIPS\"" },
              "short_name":     { "type": "string" },
              "date":           { "type": "string", "format": "date" },
              "date_precision": { "enum": [0, 1, 2, 3], "description": "0=unknown, 1=year, 2=month, 3=day" },
              "volume":         { "type": "string" },
              "publisher":      { "type": "string" },
              "aliases":        { "type": "array", "items": {"type": "string"} },
              "links":          { "$ref": "#/$defs/LinkArray" },
              "open":           { "type": "boolean", "default": false },
              "peer_reviewed":  { "type": "boolean", "default": false }
            }
          }
        }
      }
    },
    "topics": {
      "type": "array",
      "items": {
        "title": "Topic",
        "type": "object",
        "required": ["name"],
        "properties": {
          "name": { "type": "string" }
        }
      }
    },
    "links": { "$ref": "#/$defs/LinkArray" }
  },
  "$defs": {
    "Link": {
      "title": "Link",
      "type": "object",
      "required": ["type", "link"],
      "properties": {
        "type": { "type": "string", "description": "e.g. \"arxiv\", \"doi\", \"html\", \"pdf\", \"semanticscholar\"" },
        "link": { "type": "string" }
      }
    },
    "LinkArray": {
      "type": "array",
      "items": { "$ref": "#/$defs/Link" }
    }
  }
}
```

---

## Common link types

| `type` value | Meaning |
|---|---|
| `arxiv` | arXiv abstract URL or arXiv ID |
| `doi` | DOI URL or bare DOI string |
| `pdf` | Direct PDF URL |
| `html` | Publisher/proceedings page |
| `semanticscholar` | Semantic Scholar paper URL |

---

## Pagination pattern

```python
import os, requests

token = os.environ.get("PAPERONI_TOKEN") or open(os.path.expanduser("~/.config/paperoni/token")).read().strip()
headers = {"Authorization": f"Bearer {token}"}
base = "https://paperoni.mila.quebec/api/v1/search"

offset, limit = 0, 100
while True:
    r = requests.get(base, headers=headers, params={"author": "Yoshua Bengio", "limit": limit, "offset": offset})
    r.raise_for_status()
    data = r.json()
    for paper in data["results"]:
        print(paper["title"])
    if data.get("next_offset") is None:
        break
    offset = data["next_offset"]
```

---

## What this skill does NOT cover

- **Endpoints that mutate the collection directly** (`POST /api/v1/delete`,
  `/api/v1/pending/decide`, `/api/v1/set_flag`, `/api/v1/focuses`, `/api/v1/work/*`) —
  these require validator or admin roles and are outside the scope of regular user
  workflows. Taking a paper out of the database as a regular user means **requesting** it
  with the `mark:delete` flag described under `/api/v1/suggest`; never call
  `/api/v1/delete` yourself. `GET /api/v1/pending/list` is the one exception — it is
  read-only and available to any authenticated token, which makes it how you check on a
  suggestion you filed.
- The web UI at https://paperoni.mila.quebec — for browsing without code. Its
  `/my-papers` page is the hands-on way for a user to claim their own papers, but the
  claiming workflow itself (see the **Claiming papers** section) is covered here.

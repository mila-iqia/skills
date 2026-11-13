---
name: mila-paperoni
description: >-
  Query and manage the Mila Paperoni publication database via its REST API at
  https://paperoni.mila.quebec. Use when the user wants to search for papers,
  look up an author's publications, filter by venue or date, add missing papers,
  or populate a paper entry from an external link (arXiv, DOI, etc.). Also use
  when the user asks about the Paperoni API, authentication/token setup, or how
  to submit a paper suggestion.
---

# Paperoni

Paperoni is Mila's scientific publication database, available at **https://paperoni.mila.quebec**. It indexes papers by Mila researchers and supports search, filtering, and community-driven additions.

## Authentication

All write endpoints and some advanced features require a Bearer token.

### Getting your token

1. Open **https://paperoni.mila.quebec/token** in your browser.
2. Sign in with your Google account when prompted.
3. After the OAuth flow completes the page shows your token — copy it.

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

### `GET /api/v1/search` — Search papers

Returns a paginated list of papers matching the given filters.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `title` | string | Full-text search on the paper title |
| `author` | string | Author name. Prefix with `=` for an exact match (e.g. `=Yoshua Bengio`) |
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

---

### `POST /api/v1/suggest` — Suggest adding or editing a paper

> ⚠️ **Always search first.** Before calling this endpoint, use `/api/v1/search` (by title, DOI link, or author) to confirm the paper is not already in the database. Duplicate submissions create review burden for validators.

Submits one or more papers for inclusion. The submission enters a pending queue and must be approved by a validator before appearing in search results.

Use an existing paper's ID to edit it. It also works for the ID of a pending paper, if you need to correct a previous suggestion.

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

- **Admin / validation endpoints** (`/api/v1/pending/*`, `/api/v1/set_flag`, `/api/v1/focuses`, `/api/v1/work/*`) — these require validator or admin roles and are outside the scope of regular user workflows.
- The web UI at https://paperoni.mila.quebec — for browsing without code.

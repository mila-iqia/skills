---
name: mila-sarc
description: Fetch job, user, cluster and usage data over HTTP from the SARC API at sarc.mila.quebec. Use when asked about Mila/DRAC compute usage, slurm jobs, GPU/RGU utilization, waste, or Mila researchers — including first-person questions like "how many jobs did I run last week" or "how much GPU am I wasting".
---

# Fetching data from the SARC API

SARC serves a JSON API over HTTPS at **`https://sarc.mila.quebec`**. Everything
below is plain HTTP — curl, `requests`, or any client will do; there is nothing
to install.

Two families of endpoints matter:

| Prefix | What it gives you | Response |
| --- | --- | --- |
| `/v0/…` | Raw records: slurm jobs, job series (jobs + computed usage/waste/RGU columns), users, clusters, GPU→RGU table, health checks | JSON |
| `/dash/metrics/…` | Pre-aggregated dashboard data: job counts, RGU usage, metric distributions, per-user/per-cluster rollups | JSON |

`https://sarc.mila.quebec/dash/metrics` itself is the human-facing dashboard
(HTML) — worth opening in a browser to see what the JSON endpoints feed.

The parameters below are enough to query the API directly — go ahead and call it.
If a call fails in a way this document doesn't explain, fetch
`https://sarc.mila.quebec/openapi.json` (public, no token; interactive at
`/docs`) — it's the authoritative description of what the server accepts.

## Authentication

Every endpoint except `/v0/health/list`, `/docs` and `/openapi.json` requires a
bearer token:

```
Authorization: Bearer $SARC_TOKEN
```

Three environment variables carry everything you need. **Check them first** — an
unset `SARC_TOKEN` is the single most common reason requests come back
`401 {"detail":"Authentication required"}`:

```bash
test -n "$SARC_TOKEN" && echo "token: set" || echo "token: MISSING"
echo "user: ${SARC_USERNAME:-unset}  admin: ${SARC_IS_ADMIN:-0}"
```

If `SARC_TOKEN` is empty, stop and give the user the snippet below to paste into
their `~/.bashrc` (`~/.zshrc` works the same). Fill `SARC_USERNAME` in with your
best guess from the conversation if you have one (usually firstname.lastname@mila.quebec)
— otherwise leave the placeholder. Don't try to work around a missing token.

```bash
# --- SARC ---------------------------------------------------------------
# API token. Open https://sarc.mila.quebec/token in a browser, sign in with
# your Mila Google account, and copy the "refresh_token" value from the JSON
# page you land on. It is long-lived: treat it like a password, and never
# commit it.
export SARC_TOKEN='paste-the-refresh_token-value-here'

# Your @mila.quebec address — how SARC identifies you.
export SARC_USERNAME='your_email@mila.quebec'

# 1 if your SARC account has the admin capability, 0 otherwise.
# Leave it at 0 if you don't know; you'd know if you had it.
export SARC_IS_ADMIN=0
# ------------------------------------------------------------------------
```

Then tell them: **the agent must be restarted.** It inherited its environment at
launch, so editing a startup file (or exporting in another terminal) does not
reach the running process. Open a new shell and relaunch. On fish, the same three
values go in `~/.config/fish/config.fish` as `set -gx SARC_TOKEN '…'` etc.

### Admin or not

`SARC_IS_ADMIN` (default `0`) tells you which half of the API to aim at:

- **`0`** — use `/dash/metrics/*`. It works for any token and is automatically
  scoped to its owner's own jobs, which is exactly what a non-admin can see.
- **`1`** — the `/v0` endpoints are open to you too, with cross-user filters
  (`email=`, `as_user=`).

Treat it as a hint, not a guarantee: don't probe capabilities before querying,
just hit the endpoint you want and let the API answer.

If `SARC_IS_ADMIN` was wrong, you'll see **501** on `/v0/job/query`,
`/v0/job/count`, `/v0/job/series` or `/v0/user/query`, or **403** on
`/v0/job/id/{id}`, `/v0/user/id/{id}`, `/v0/user/email/{email}` and `as_user` —
all of them admin-only. Neither code is a bug in your request, and neither is
worth a retry with different parameters: switch to `/dash/metrics/*`, or say
what's out of reach.

## "How many jobs did *I* run?" — knowing who the user is

Questions phrased in the first person ("my jobs", "how much GPU did I waste last
week") need the user's **`@mila.quebec` email** — that's how SARC identifies
people, and it's what `SARC_USERNAME` holds despite the name.

If it's unset, **ask straight away**. Don't go hunting for it — no `git config`,
no scanning files, no directory lookups. Mention once that it belongs in `SARC_USERNAME` alongside the token, and takes effect on the next restart.

Then query: `/dash/metrics/*` is already scoped to the token's owner, so a plain
call answers "my jobs" without passing the address anywhere. The address is for
asking about *someone else* — `as_user=<address>` on `/dash/metrics/*`, or
`email=<address>` on the `/v0` job endpoints (both admin-only).

Do **not** put an email in `cluster_user`: that parameter takes the login name on
the cluster, which is a different string, and a mismatch silently returns zero
rows rather than an error.

## Timeframes

**When the user doesn't give one — or says something vague like "lately",
"recently", "these days" — use the last two weeks.** Don't ask, and don't fall
back on the server defaults (`/dash` defaults to a single day, `/v0` to all of
history). Work the dates out from today's date; no need to shell out to `date`.

- `/dash/metrics/*` take plain dates and `end` is exclusive, so the last two
  weeks *including today* is `start=<today − 14 days>&end=<tomorrow>`.
- `/v0` job filters take timezone-aware datetimes: `start=<today − 14 days>T00:00:00Z`,
  and leave `end` off to run up to now.

Say which window you used when you answer ("over the last two weeks, Aug 5–19")
so the user can redirect you in one turn if they meant something else.

## Quick start

```bash
# Clusters (cheap, but only run this as a sanity check if you suspect something is wrong)
curl -sf -H "Authorization: Bearer $SARC_TOKEN" \
  https://sarc.mila.quebec/v0/cluster/list

# [admin] Usage/waste rows for mila jobs in July (datetimes MUST be tz-aware)
curl -sfG -H "Authorization: Bearer $SARC_TOKEN" \
  https://sarc.mila.quebec/v0/job/series \
  --data-urlencode 'cluster_name=mila' \
  --data-urlencode 'start=2026-07-01T00:00:00Z' \
  --data-urlencode 'end=2026-08-01T00:00:00Z' \
  --data-urlencode 'extra_fields=rgu,gpu_sm_occupancy_mean' \
  --data-urlencode 'limit=100'

# [admin] One page of jobs, with the user object and per-job statistics attached
curl -sfG -H "Authorization: Bearer $SARC_TOKEN" \
  https://sarc.mila.quebec/v0/job/query \
  --data-urlencode 'cluster_name=mila' \
  --data-urlencode 'job_state=COMPLETED' \
  --data-urlencode 'extra_fields=sarc_user,statistics' \
  --data-urlencode 'limit=100'

# A GPU-usage rollup per user, no pagination needed (any token)
curl -sfG -H "Authorization: Bearer $SARC_TOKEN" \
  https://sarc.mila.quebec/dash/metrics/rgu_by_user \
  --data-urlencode 'start=2026-08-01' --data-urlencode 'end=2026-08-15'

# "How many jobs did I run lately?" — no timeframe given, so the last two weeks,
# by day. Already scoped to the token owner, so no identity needed; an admin
# adds as_user=$SARC_USERNAME to scope it to that person instead.
curl -sfG -H "Authorization: Bearer $SARC_TOKEN" \
  https://sarc.mila.quebec/dash/metrics/job_counts \
  --data-urlencode 'start=2026-08-05' --data-urlencode 'end=2026-08-20' \
  --data-urlencode 'period=d'
```

In Python (any HTTP client works; `requests` shown):

```python
import os
import requests

BASE = "https://sarc.mila.quebec"
HEADERS = {"Authorization": f"Bearer {os.environ['SARC_TOKEN']}"}


def paginate(path, **params):
    """Yield every record from a cursor-paginated /v0 endpoint."""
    cursor = None
    session = requests.Session()
    while True:
        q = {**params, "limit": 100}
        if cursor is not None:
            q["cursor"] = cursor
        r = session.get(f"{BASE}{path}", params=q, headers=HEADERS, timeout=120)
        r.raise_for_status()
        page = r.json()
        yield from page["results"]
        cursor = page["cursor"]
        if cursor is False:      # note: False, not None — check identity
            return


jobs = list(paginate("/v0/job/query", cluster_name="mila",
                     start="2026-08-01T00:00:00Z", extra_fields="sarc_user"))
```

Repeated parameters (`job_id`, `clusters`, `job_states`) are sent as repeated
query keys — with `requests`, pass a list: `params={"job_id": [123, 456]}`.

## `/v0` endpoints

| Endpoint | Notes |
| --- | --- |
| `GET /v0/job/query` | Filtered, paginated slurm jobs → `{results, cursor}` |
| `GET /v0/job/count` | Same filters, returns a bare integer. **Slow — avoid**, see *Practical notes* |
| `GET /v0/job/id/{id}` | One job by **SARC database id** (not the slurm `job_id`) |
| `GET /v0/job/series` | Jobs enriched with computed cost/waste/RGU/metric columns |
| `GET /v0/user/query` | Paginated users; filters `display_name` (substring, case-insensitive), `email`, `member_type`, `supervisor` (a user id), `start`/`end` |
| `GET /v0/user/id/{id}`, `GET /v0/user/email/{email}` | Single user |
| `GET /v0/cluster/list` | `[{id, name, domain, start_date, billing_is_gpu}]` |
| `GET /v0/gpu/rgu` | `[{name, rgu, drac_rgu}]` — GPU model → RGU weight |
| `POST /v0/gpu/rgu` | Admin only; writes the RGU table. **Mutating — confirm with the user first** |
| `GET /v0/health/list` | Health-check states; no auth required |

`member_type` is one of `master`, `master pro`, `phd`, `postdoc`, `professor`,
`staff`, `intern`.

### Job filters (shared by `query`, `count`, `series`)

`cluster_name`, `job_id` (repeatable: `job_id=1&job_id=2`), `job_state`,
`email`, `sarc_user_id`, `cluster_user`, `start`, `end`.

- **`start`/`end` must be timezone-aware ISO-8601** (`2026-07-01T00:00:00Z` or
  `2026-07-01T00:00:00-04:00`). A naive datetime is a 422.
- The window is *overlap*, not containment: `end` filters on `submit_time < end`,
  `start` keeps jobs that are still running or ended after `start`.
- `job_state` is one of the slurm states: `COMPLETED`, `RUNNING`, `PENDING`,
  `FAILED`, `CANCELLED`, `TIMEOUT`, `OUT_OF_MEMORY`, `PREEMPTED`, `NODE_FAIL`, …
- `cluster_user` is the username on the cluster; `email` and `sarc_user_id`
  identify the person in SARC.
- An unknown `cluster_name` is a 404, so a typo fails loudly rather than
  silently returning nothing.
- Sending `job_id=` (empty) means "the empty list", which matches no job. Omit
  the parameter entirely when you don't want to filter on it.

### Pagination

`/job/query`, `/job/series` and `/user/query` return
`{"results": [...], "cursor": <str|int|false>}`.

- `limit` is **1–100** (default 100); values above 100 are a 422.
- Pass the returned `cursor` back verbatim to get the next page.
- **`cursor === false` means "no more results"** — that's the loop's stop
  condition. In Python, test `if cursor is False`, since `0` and `""` are falsy
  but are valid cursors.
- Jobs and series are ordered by `submit_time` descending; users by id.

### `extra_fields`

Comma-separated, on `/job/query`, `/job/id/{id}` and `/job/series`. These fields
are `null` unless requested (they cost extra joins):

- Jobs (`/job/query`, `/job/id/{id}`): `cluster_name`, `sarc_user`, `statistics`.
  (`cluster_name` is added automatically when you filter on it; `sarc_user` when
  you filter on `email` or `sarc_user_id`.)
- Series (`/job/series`): `cluster_name`, `sarc_user` (→ `display_name`,
  `member_type`, `email`), `supervisors`, `rgu` (→ `gpu_type_rgu`,
  `gpu_type_rgu_drac`, `requested_rgu`, `requested_rgu_drac`, `allocated_rgu`,
  `allocated_rgu_drac`), and the four per-metric columns
  `gpu_sm_occupancy_mean`, `gpu_sm_occupancy_max`, `gpu_utilization_mean`,
  `gpu_memory_max` (each requested by name).

`statistics` exists on `/job/query` only. On `/job/series`, ask for the four named
metric columns instead; use `/job/query` when you need the full per-job
distribution.

An unknown name is a 422, and the error message tells you the valid set.

### Job vs. job series

Use `/v0/job/query` for raw slurm records: identity, requested vs. allocated
cpu/mem/gpu, timestamps, state, nodes, and with `extra_fields=statistics`, a
metric-name → `{mean, std, q05, q25, median, q75, max}` map.

Use `/v0/job/series` when the question is about **usage, waste or RGU** — it adds
precomputed columns and saves you the arithmetic. Always present:
`requested_cpu_cost`, `requested_cpu_waste`, `allocated_cpu_cost`,
`allocated_cpu_waste`, `cpu_overbilling_cost`, the same five for gpu
(`requested_gpu_cost`, …, `gpu_overbilling_cost`), and `usage_metric` (SARC's
default single measure of GPU usage — mean GPU SM occupancy). The metric and RGU
columns listed above require `extra_fields`.

Units: the `cpu_*` costs/wastes are **CPU-seconds**; the `gpu_*` ones are
**RGU-seconds** derived from raw GPU counts (count-based, not billing-based).
`requested_rgu`/`allocated_rgu` are per-job RGU *counts*, not integrated over
time. The id field is `job_db_id` (not `id`).

## `/dash/metrics` endpoints

Aggregated data behind the dashboard — much cheaper than paginating millions of
jobs when you want a trend or a rollup, and the only usage data available to a
non-admin token. Results are automatically scoped to the caller's own jobs;
admins see everything and can add `as_user=<mila email>` to scope a query to one
person (403 for a non-admin, 404 for an unknown email — never a silent fallback
to the full view).

| Endpoint | Returns |
| --- | --- |
| `/dash/metrics/job_counts` | `{period_start, period_end, count}` per bucket, empty buckets included as 0 |
| `/dash/metrics/rgu_usage` | `rgu_allocated` / `rgu_used` / `rgu_wasted` RGU·h per bucket, plus `metric_means` |
| `/dash/metrics/rgu_by_cluster` | `{periods, series}` — RGU·h per bucket, one series per cluster |
| `/dash/metrics/rgu_by_user` | Requested vs. used RGU·h per user (no time axis), descending |
| `/dash/metrics/metric_trend` | Per-bucket averages of a metric's per-job mean and max; empty buckets are `null`, not 0 |
| `/dash/metrics/metric_distribution` | `{primary: {values, weights}}` — 50 bins, weighted by in-window RGU-seconds |
| `/dash/metrics/metric_comparison` | 100×100 heatmap `{x, y, z}` of two metrics |
| `/dash/metrics/job_times_vs_limit` | `elapsed_vs_limit` + `wait_vs_limit` 100×100 grids and `total_jobs` |
| `/dash/metrics/jobs` | Paginated sortable job table → `{total, jobs}` |

Common parameters: `start`/`end` (plain **dates**, `YYYY-MM-DD` — not datetimes),
`period` (`h`/`d`/`w`/`m` for calendar buckets, or `N<unit>` like `12h`, `2w` for
fixed-width ones), `clusters` (repeatable), `cluster_user`, `job_states`
(repeatable), `metric`, and `focus_start`/`focus_end` to narrow the window to
sub-day precision. An unknown cluster name is a 404; a malformed `period` is a 400.

Endpoint-specific: `rgu_usage` takes `min_usage` (default 0.15, the threshold
`rgu_wasted` is measured against) and `whole=true` (collapse the range into a
single bucket — *not* the same as summing the per-bucket rows, since each job is
then averaged once instead of once per bucket). `job_counts` takes
`submitted=true` (see below). `metric_comparison` takes `metric2`.
`jobs` takes `limit` ≤ 500, `offset`, `include_total`, `sort_dir` and `sort_by`
(one of `cluster`, `job_id`, `submit_time`, `start_time`, `user`, `job_state`,
`elapsed`, `requested_gpu`, `allocated_gpu`, `billing`, `gpu_type`,
`gpu_type_rgu`, `rgu`, `rgu_hours`, `waste`, `gpu_utilization_mean`,
`gpu_sm_occupancy_mean`, `gpu_memory_max`) — an unrecognized `sort_by` silently
falls back to `rgu_hours` rather than erroring.

`metric` must be one of: `gpu_sm_occupancy` (default), `gpu_utilization`,
`gpu_utilization_fp16`, `gpu_utilization_fp32`, `gpu_utilization_fp64`,
`gpu_memory`, `system_memory` — all normalized to [0, 1]. `metric_distribution`,
`metric_comparison` and `metric_trend` reject anything else with a 400; the RGU
endpoints don't validate it and just find no measurements, so a typo there reads
as "everything unmeasured".

### The window: running-in-window and pro-rated

This is the thing to get right when comparing `/dash` numbers to `/v0` ones.

- Most endpoints select the jobs that **ran** in the window (overlap), not the
  ones submitted in it, and charge each job **only for the time it spent inside**
  the window/bucket. A job crossing a bucket boundary is split across buckets.
- Two exceptions select on `submit_time` instead: `job_times_vs_limit`, and
  `job_counts?submitted=true`. Those counts add up to a number of distinct jobs;
  the default (running) counts do **not** — a job spanning three buckets counts
  once in each, which reads as occupancy.
- Counts are never pro-rated (a count isn't an integral); RGU·h and `elapsed`
  are. In `/dash/metrics/jobs`, `elapsed` is the in-window slice and
  `elapsed_total` the job's full runtime.
- RGU figures use the DRAC RGU weighting.
- The RGU endpoints, `metric_distribution`, `metric_comparison` and
  `/metrics/jobs` cover **GPU jobs only**. `metric_trend` applies no GPU filter,
  so `system_memory` there also covers CPU-only jobs — the two cover different
  populations, and their numbers won't line up.

**Watch the date handling**: `start`/`end` are interpreted at 00:00 UTC and the
range is **half-open — `end` is exclusive**. `start=2026-08-01&end=2026-08-02` is
one day; `start=2026-08-01&end=2026-08-01` is an empty window. The two are sorted
server-side, so passing them backwards is harmless. Omitting them gives you
*yesterday* (a single day), not all of history — always pass an explicit range
(see *Timeframes*).

## Errors

| Code | Meaning |
| --- | --- |
| 401 `Authentication required` | `SARC_TOKEN` missing, empty, or malformed header |
| 307 (on `/dash/…`) | Same thing — unauthenticated requests redirect to the login page. Send the bearer header (and don't follow the redirect) |
| 400 (`/dash` only) | Unknown `metric`, or malformed `period` |
| 403 | Token is valid but lacks the capability, the email isn't in the SARC user database, or `as_user` was used by a non-admin |
| 404 | Unknown cluster name, no such job/user id, or unknown `as_user` email |
| 422 | Bad parameter: naive datetime, `limit > 100`, non-integer `job_id`, unknown `extra_fields` — the `detail` field says which |
| 501 | Non-admin token on an `/v0` query endpoint (see *Admin or not*) |

Error bodies are `{"detail": "..."}`; read it before retrying, it usually names
the offending parameter.

## Troubleshooting

**GPU utilization reads as zero (or missing) for a job that clearly used its
GPUs** — e.g. the job's own epilog reported real usage. The GPU metrics come from
a monitoring daemon (DCGM) running on the compute node, and anyone with access to
that node can turn it off: the user themselves, or another user sharing it. While
it's off, nothing is recorded for *any* job on that node, so SARC has no
measurement to report, and the job's own epilog — which measures independently —
will disagree. This is a known issue as of 2026-08-19 and a fix is being worked
on; when you hit it, say so rather than reporting the job as idle or wasteful.

Note that unmeasured is not the same as unused: the API reports a missing
measurement as `null`, not `0`. Charts and summaries that render `null` as an
empty bar make it *look* like zero usage.

**A query returns nothing for someone who definitely ran jobs** — check you
filtered on `email=` and not `cluster_user=` (see *knowing who the user is*), and
that `start` and `end` aren't the same date, which is an empty window.

**`/dash` numbers don't match `/v0` ones, or don't add up across buckets** —
that's expected; see *The window: running-in-window and pro-rated*.

## Practical notes

- **Avoid `/v0/job/count`** — it is disproportionately slow and will often stall a
  request for minutes. Don't use it as a sizing check before paginating; just
  paginate, or answer from `/dash/metrics/*`.
- `/dash/metrics/*` and `/v0/job/series` are the fast paths. Prefer
  `/dash/metrics/*` whenever an aggregate answers the question — one call instead
  of paginating thousands of jobs.
- Set a generous client timeout (60–120 s) anyway; wide `/v0` queries move a lot
  of rows.
- `elapsed_time` is in seconds. `requested_*`/`allocated_*` come straight from
  slurm's TRES accounting as scraped from `sacct` (memory in MB).
- Timestamps come back as ISO-8601 UTC.
- Never print the token itself into logs, files, or command output.
- The only mutating endpoint is `POST /v0/gpu/rgu`; everything else is read-only.

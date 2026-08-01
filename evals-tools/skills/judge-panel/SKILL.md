---
name: judge-panel
description: Triage a large corpus (experiment logs, model outputs, datasets, papers) with a cheap deterministic detector first, then an LLM judge only on the shortlist. Use when the user wants to label, filter, or grade more items than fit in a context window, or asks to "find the interesting/broken/valid ones" in bulk.
---

Run the two-stage "cheap detector → expensive judge" pipeline. Don't send the full corpus to a model: the detector costs zero LLM tokens and shrinks the problem; the judge is expensive and only sees the shortlist.

## Stage 0 — Refuse the one-stage temptation

If the corpus is larger than the threshold (default ~200 items; adjust for item size and budget), do NOT loop an LLM over every item. First propose a deterministic detector and show the user its shrink ratio (e.g. "12,000 rows → 340 candidates") before any model call.

## Stage 1 — Deterministic detector (zero LLM tokens)

Build the cheapest filter that optimizes for recall: false positives are acceptable (the judge removes them), missed true positives are the failure mode to design against.

- **Text corpora**: keyword/regex families for the target signal, plus a noise-list for known boilerplate. Count matches per item, rank, cut at a threshold.
- **Experiment logs**: exit codes, metric deltas beyond a band, NaN/inf, wall-clock outliers (e.g. >3x median).
- **Model outputs**: length outliers, refusal markers, format-validity checks (does it parse?), exact-duplicate hashes.

Write the detector as a standalone script the user can rerun (Python stdlib preferred). Report: items scanned, candidates kept, shrink ratio.

## Stage 2 — LLM judge (shortlist only)

Send ONLY the candidates to the judge, batched. The judge prompt must contain:

1. The decision the labels will feed (judges drift without a consumer).
2. A closed three-way verdict set. Default names `accept` / `watch` / `reject`, with each verdict defined relative to the task in the prompt itself (e.g. for broken-run triage: `accept` = confirmed broken, `watch` = suspicious, `reject` = healthy). Two-way verdicts hide uncertainty; open-ended verdicts don't aggregate.
3. A one-line justification per verdict, so a human can spot-check without rereading the item.

Pick the judge by price, not prestige: start with the cheapest model tier available in the user's setup and only escalate if calibration fails.

## Calibration — before trusting the judge

Sample 20 candidates with a fixed, reported seed. Judge them with both the cheap model and the strongest model available. If they disagree on more than 3 of 20 (a default strictness knob — tighten for high-stakes labels), replace the judge with the next-cheapest model that is more expensive than the current one (by the per-token price list of the user's provider) and repeat. Record the final agreement number in the report.

## Optional Stage 3 — Panel for high-stakes labels

When a wrong verdict is costly, replace the single judge with 3 cheap-model votes:

- A majority verdict (2 of 3 or 3 of 3) stands.
- No majority — including three-way splits — escalates the item to one strong-model tiebreak.

Report the escalation rate (share of items that had no majority) alongside the verdict counts; a high rate means the cheap models are below the task and the panel should move up a tier.

## Output contract

Deliver three artifacts, always:
1. The detector script (rerunnable).
2. A verdict table: item id · verdict · one-line justification.
3. A run summary: corpus size → shortlist size → verdict counts → calibration agreement (n/20, seed) → token savings, computed as judge-tokens spent vs the one-stage baseline of judging every item.

## Example

`/judge-panel find broken runs in results/*.jsonl` → detector flags exit!=0, NaN losses, wall-clock >3x median → 8,400 runs shrink to 120 candidates → judge labels each `accept`/`watch`/`reject` with justification → summary reports 19/20 calibration agreement (seed 42) and ~98% fewer judge tokens than one-stage labeling of all 8,400 runs.

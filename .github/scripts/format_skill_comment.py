#!/usr/bin/env python3
"""Format a single PR comment summarizing docmetrics results for all evaluated skills.

Exits with code 1 if any skill failed to improve over the baseline (no-docs) score.

Usage:
    python format_skill_comment.py --results-dir /tmp/skill-results

Results directory layout:
    <results-dir>/
        <slug>/              # skill path with "/" replaced by "__", leading "./" stripped
            current.json     # docmetrics JSON output using the current SKILL.md
            base.json        # optional: same format using the base-branch SKILL.md
"""
import argparse
import json
import sys
from pathlib import Path


def fmt_score(result: dict) -> str:
    pct = round(result["score"] * 100)
    n_cand = result.get("num_candidates", 1)
    total = result["num_questions"] * n_cand
    if n_cand > 1:
        std_pp = round(result.get("score_std", 0) * 100)
        return f"{pct}% ±{std_pp}pp ({result['correct_answers']}/{total})"
    return f"{pct}% ({result['correct_answers']}/{total})"


def fmt_delta(a: dict, b: dict) -> str:
    delta = round((b["score"] - a["score"]) * 100)
    return f"+{delta}pp" if delta >= 0 else f"{delta}pp"


def answer_cell(answers: list, i: int, n_candidates: int) -> str:
    """Render one per-question cell. Handles both single- and multi-candidate shapes."""
    if i >= len(answers):
        return "❓"
    a = answers[i]
    if "pass_rate" in a:
        # multi-candidate: a["selected"] is a list; count non-null-and-correct runs
        passed = sum(1 for s in a["selected"] if s is not None and s == a["expected"])
        return f"{passed}/{n_candidates}"
    # single-candidate
    correct = a.get("correct")
    return "✅" if correct is True else "❌" if correct is False else "❓"


def answer_pass_rate(answers: list, i: int) -> float | None:
    """Per-question pass fraction in [0, 1], or None if missing."""
    if i >= len(answers):
        return None
    a = answers[i]
    if "pass_rate" in a:
        return a["pass_rate"]
    if a.get("correct") is True:
        return 1.0
    if a.get("correct") is False:
        return 0.0
    return None


def delta_arrow(before: float | None, after: float | None) -> str:
    if before is None or after is None or before == after:
        return ""
    return "↑" if after > before else "↓"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    args = parser.parse_args()

    skill_dirs = sorted(d for d in args.results_dir.iterdir() if d.is_dir())

    if not skill_dirs:
        print("<!-- skill-ci -->\n## Skill CI\n\nNo skills were evaluated.")
        return 0

    # Load all results
    skills = []
    for skill_dir in skill_dirs:
        skill_name = skill_dir.name.replace("__", "/")
        current_data = json.loads((skill_dir / "current.json").read_text())
        base_data = (
            json.loads((skill_dir / "base.json").read_text())
            if (skill_dir / "base.json").exists()
            else None
        )
        skills.append(
            {
                "name": skill_name,
                "baseline": current_data["without_docs"],
                "current": current_data["with_docs"],
                "base": base_data["with_docs"] if base_data else None,
                "questions": current_data.get("questions", []),
                "baseline_answers": current_data["without_docs"].get("answers", []),
                "current_answers": current_data["with_docs"].get("answers", []),
            }
        )

    has_any_base = any(s["base"] is not None for s in skills)

    lines = ["<!-- skill-ci -->", "## Skill CI", ""]

    # Summary table
    if has_any_base:
        lines += [
            "| Skill | Baseline | Before | After | Δ (before→after) | |",
            "|---|:---:|:---:|:---:|:---:|:---:|",
        ]
    else:
        lines += [
            "| Skill | Baseline | With skill | Δ | |",
            "|---|:---:|:---:|:---:|:---:|",
        ]

    failed = []
    warnings = []

    for s in skills:
        improved = s["current"]["score"] > s["baseline"]["score"]
        status = "✅" if improved else "❌"
        if not improved:
            failed.append(s["name"])
        if s["base"] is not None and s["current"]["score"] < s["base"]["score"]:
            warnings.append((s["name"], fmt_delta(s["base"], s["current"])))

        if has_any_base:
            before = fmt_score(s["base"]) if s["base"] else "—"
            delta = fmt_delta(s["base"], s["current"]) if s["base"] else "—"
            lines.append(
                f"| `{s['name']}` | {fmt_score(s['baseline'])} | {before}"
                f" | {fmt_score(s['current'])} | {delta} | {status} |"
            )
        else:
            lines.append(
                f"| `{s['name']}` | {fmt_score(s['baseline'])}"
                f" | {fmt_score(s['current'])} | {fmt_delta(s['baseline'], s['current'])} | {status} |"
            )

    lines.append("")

    # Per-question collapsible sections
    for s in skills:
        if not s["questions"]:
            continue
        n_cand_base = s["baseline"].get("num_candidates", 1)
        n_cand_cur = s["current"].get("num_candidates", 1)
        multi = n_cand_base > 1 or n_cand_cur > 1

        lines.append("<details>")
        lines.append(
            f"<summary><code>{s['name']}</code> — per-question results</summary>"
        )
        lines.append("")
        if multi:
            lines.append("| Question | Baseline | With skill | Δ |")
            lines.append("|---|:---:|:---:|:---:|")
        else:
            lines.append("| Question | Baseline | With skill |")
            lines.append("|---|:---:|:---:|")
        for i, q in enumerate(s["questions"]):
            text = q["question"]
            if len(text) > 80:
                text = text[:79] + "…"
            b_cell = answer_cell(s["baseline_answers"], i, n_cand_base)
            c_cell = answer_cell(s["current_answers"], i, n_cand_cur)
            if multi:
                arrow = delta_arrow(
                    answer_pass_rate(s["baseline_answers"], i),
                    answer_pass_rate(s["current_answers"], i),
                )
                lines.append(f"| {text} | {b_cell} | {c_cell} | {arrow} |")
            else:
                lines.append(f"| {text} | {b_cell} | {c_cell} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Footer
    if warnings:
        for skill_name, delta in warnings:
            lines.append(
                f"> ⚠️ `{skill_name}` score decreased vs base branch ({delta})."
                " Scores may be unreliable."
            )
    if failed:
        failed_list = ", ".join(f"`{s}`" for s in failed)
        lines.append(
            f"> ❌ The following skills did not improve the LLM score: {failed_list}"
        )
    elif not warnings:
        lines.append("> ✅ All skills improved the LLM score.")

    lines.append(">")
    lines.append(
        "> _Note: docmetrics scores may be unreliable. This check is informational._"
    )

    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

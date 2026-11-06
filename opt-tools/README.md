# Opt Tools — Experiment & Resource Optimization Skills

This plugin groups skills that help speed up experiment workloads on Slurm
clusters without changing or compromising their results, and turn the findings
into a report for Mila's IDT team.

## Skills overview

| Skill | Trigger phrases | Description |
|-------|----------------|-------------|
| `optimization-target` | "Speed up my experiments", "improve GPU utilization / SM occupancy", "pack jobs", "how many experiments per allocation", "samples/tokens per second", "optimization report for IDT" | Guides optimizing individual experiments and packing multiple experiments into one allocation, keeping results identical, maintaining `optimization-report.md`, and submitting it to a write-only GCS drop bucket for the IDT team |

## Usage

Start a Claude Code session at the repo root, then describe what you want in
plain language:

```
These training experiments are too slow — help me speed them up without changing the results.
```

```
How many of these jobs can I pack into a single GPU allocation?
```

Claude will detect the matching skill and follow its workflow automatically.

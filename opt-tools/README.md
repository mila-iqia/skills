# Opt Tools — Experiment & Resource Optimization Skills

This plugin groups skills that help speed up experiment workloads on Slurm
clusters without changing or compromising their results, and turn the findings
into a report for Mila's IDT team.

## Skills overview

| Skill | Trigger phrases | Description |
|-------|----------------|-------------|
| `optimization-target` | "Speed up my experiments", "improve GPU utilization / SM occupancy", "pack jobs", "how many experiments per allocation", "samples/tokens per second", "optimization report for IDT" | Guides optimizing individual experiments and packing multiple experiments into one allocation, keeping results identical, maintaining `optimization-report.md`, and submitting it to a write-only GCS drop bucket for the IDT team |

### Upstream skills (OpenCode)

When this plugin is loaded in OpenCode from
`https://mila-iqia.github.io/skills/opt-tools/skills`, it also includes these
skills from [srygaard/optimization-skills](https://github.com/srygaard/optimization-skills) (MIT).
They are declared in [`upstream.json`](upstream.json) and fetched when the site is built; they are not copied into this repo.
The same file generates the `pytorch-opt-skills` entry in `.claude-plugin/marketplace.json`, so Claude Code and OpenCode use the same version.
In Claude Code, install them separately with `/plugin install pytorch-opt-skills@mila-skills`.

| Skill | Use it when |
|-------|-------------|
| `pytorch-compile` | Compiling is slow, recompiles keep happening, the compiled model is slower than eager, or you hit a mode or CUDA-graph error |
| `pytorch-dataloader` | The GPU waits on `next()`: utilization is low or bursty, workers or storage need tuning, or a DDP rank lags behind |
| `pytorch-profiler` / `pytorch-profiler-full` | You need to see what a training step is made of: idle gaps, host syncs, hotspots, all-reduce time that isn't overlapped with compute |

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

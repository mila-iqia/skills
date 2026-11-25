# Pytorch Opt Skills

## Upstream skills

This plugin is loaded in OpenCode from
`https://mila-iqia.github.io/skills/pytorch-opt-skills/skills`. It includes
skills from [srygaard/optimization-skills](https://github.com/srygaard/optimization-skills).
They are declared in [`upstream.json`](upstream.json) and fetched when the site is built; they are not copied into this repo.
The same file generates the `pytorch-opt-skills` entry in `.claude-plugin/marketplace.json`, so Claude Code and OpenCode use the same version.

| Skill | Use it when |
|-------|-------------|
| `pytorch-compile` | Compiling is slow, recompiles keep happening, the compiled model is slower than eager, or you hit a mode or CUDA-graph error |
| `pytorch-dataloader` | The GPU waits on `next()`: utilization is low or bursty, workers or storage need tuning, or a DDP rank lags behind |
| [pytorch-ddp](pytorch-ddp/SKILL.md) | multi-GPU or multi-node scaling falls short: choosing DDP / FSDP / HSDP knobs, `no_sync` or comm hooks, NCCL bandwidth, a slow rank, outgrowing DDP |
| `pytorch-profiler` / `pytorch-profiler-full` | You need to see what a training step is made of: idle gaps, host syncs, hotspots, all-reduce time that isn't overlapped with compute |
| [vibecheck](vibecheck/SKILL.md) | measurable, prioritized cleanup of a Python ML research repo before open-sourcing it: leaked secrets and internal references in git history, a missing LICENSE or README, dependencies, dead code, complexity and duplication |
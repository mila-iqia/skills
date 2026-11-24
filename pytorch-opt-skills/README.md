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
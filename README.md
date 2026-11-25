# Mila Skills Marketplace

A collection of Claude Code skills for (and by) Mila researchers, distributed as a plugin marketplace.

> 🚧 **Work in progress.** This marketplace is actively being built. Skills may change, and coverage is still limited. Researchers are welcome to contribute — see [CONTRIBUTING.md](CONTRIBUTING.md) to add your own skills or improve existing ones.

## Setup (one-time)

### Option A — interactive (recommended)

In any Claude Code session:
```
/plugin marketplace add mila-iqia/skills
```

### Option B — manual

Add to `~/.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": {
    "mila-skills": {
      "source": {
        "source": "github",
        "repo": "mila-iqia/skills"
      }
    }
  }
}
```

## Installing skills

Browse available plugins, then install the ones you want:

```
/plugin install example-tools@mila-skills
```

Installed skills appear immediately as slash commands (e.g. `/example-skill`).

### Using the skills with OpenCode

The skills of every plugin in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) are published to GitHub Pages at
`https://mila-iqia.github.io/skills/<plugin>/skills`, together with a generated `index.json`.
To load them, add the URLs you want to `opencode.json`:

```json
{
  "skills": [
    "https://mila-iqia.github.io/skills/opt-tools/skills",
    "https://mila-iqia.github.io/skills/mila-tools/skills",
    "https://mila-iqia.github.io/skills/pytorch-opt-skills/skills"
  ]
}
```

External plugins (such as `pytorch-opt-skills`) are fetched from their repository when the site is built
(see [`.github/workflows/pages.yml`](.github/workflows/pages.yml)), which happens on every push to `master` and once a week.
Each skill's `version` is a hash of its content, so OpenCode only re-downloads skills that changed.

## Available plugins

| Plugin | Description |
|---|---|
| `example-tools` | Example plugin demonstrating the structure |
| `mila-tools` | Skills for Mila users: cluster account and local setup, SSH connection, running jobs, and the SARC and Paperoni data APIs |
| `opt-tools` | Skills for optimizing experiment code and compute resource usage on Slurm clusters |
| `pytorch-opt-skills` | PyTorch optimization Skills (torch.compile, DataLoader, profiler) |

`pytorch-opt-skills` is an external plugin that points to
[srygaard/optimization-skills](https://github.com/srygaard/optimization-skills). Its skills are not copied into this repo.
Its skills are not copied into this repo. Its entry in `marketplace.json` is described in [`.claude/marketplace.json`](.claude/marketplace.json) and generated.

See [CONTRIBUTING.md](CONTRIBUTING.md#referencing-skills-from-another-repository).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on adding skills or new topic groups.

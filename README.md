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

## Available plugins

| Plugin | Description |
|---|---|
| `example-tools` | Example plugin demonstrating the structure |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on adding skills or new topic groups.

# Mila Skills Marketplace

A collection of Claude Code skills for Mila researchers, distributed as a plugin marketplace.

## Setup (one-time)

### Option A — interactive (recommended)

In any Claude Code session:
```
/plugin marketplace add mila-umontreal/skills
```

### Option B — manual

Add to `~/.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": {
    "mila-skills": {
      "source": {
        "source": "github",
        "repo": "mila-umontreal/skills"
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

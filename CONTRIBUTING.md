# Contributing Skills

## Adding a skill to an existing plugin

1. Create a directory under the relevant plugin's `skills/` folder:
   ```
   <plugin-name>/skills/<your-skill-name>/
   ```
2. Add a `SKILL.md` file with frontmatter and instructions:
   ```markdown
   ---
   name: your-skill-name
   description: One-line description of when and why to use this skill.
   ---

   Instructions for Claude go here...
   ```
3. Update the plugin's version in `<plugin-name>/.claude-plugin/plugin.json`.
4. Open a PR.

## Adding a new plugin (topic group)

1. Create a new directory at the repo root for your topic:
   ```
   <topic>-tools/
   ├── .claude-plugin/
   │   └── plugin.json
   └── skills/
       └── <skill-name>/
           └── SKILL.md
   ```
2. Write the `plugin.json` manifest:
   ```json
   {
     "name": "<topic>-tools",
     "version": "1.0.0",
     "description": "Brief description of this skill group"
   }
   ```
3. Add an entry to `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "<topic>-tools",
     "source": "./<topic>-tools",
     "description": "Brief description"
   }
   ```
4. Open a PR.

## Skill file reference

Key frontmatter fields for `SKILL.md`:

| Field | Description |
|---|---|
| `name` | Slash command name (e.g. `my-skill` → `/my-skill`) |
| `description` | When Claude should suggest/use this skill |
| `disable-model-invocation: true` | Manual invocation only (not auto-triggered) |
| `allowed-tools` | Tools available without asking (e.g. `Read, Grep`) |
| `argument-hint` | Shown in autocomplete (e.g. `[file] [format]`) |

Use `$ARGUMENTS` in the body to access arguments passed to the skill.

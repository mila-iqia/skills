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
3. Add a `quiz.yaml` file with multiple-choice questions that test the skill (see [Quiz requirement](#quiz-requirement)).
4. Update the plugin's version in `<plugin-name>/.claude-plugin/plugin.json`.
5. Open a PR.

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

## Referencing skills from another repository

To include skills from another repository without copying them, add an external plugin entry to `.claude-plugin/marketplace.json`:

```json
{
  "name": "pytorch-opt-skills",
  "description": "PyTorch optimization Skills (torch.compile, DataLoader, profiler)",
  "source": {
    "source": "github",
    "repo": "srygaard/optimization-skills",
    "ref": "main"
  },
  "skills": ["./pytorch-compile", "./pytorch-dataloader"]
}
```

- `name`: the name of the Claude Code plugin (`/plugin install <name>@mila-skills`) and of its OpenCode URL (`https://mila-iqia.github.io/skills/<name>/skills`).
- `source`: a `github` source (`repo`), or a `url` or `git-subdir` source as described in the [Claude Code docs](https://code.claude.com/docs/en/plugin-marketplaces). Add `"sha": "<40-character commit SHA>"` to pin a version; otherwise both harnesses follow `ref`.
- `skills` (optional): folders, relative to the plugin root, that each contain a `SKILL.md`. Without it, every skill under the plugin's `skills/` directory is used.

To remove external skills, delete the entry (or the paths in `skills`). That one file drives both harnesses:
- **Claude Code** reads `marketplace.json` directly.
- **OpenCode**: `build_site.py` (run by `pages.yml`) fetches the skills and publishes them with a generated `index.json`. On a PR, `marketplace-check.yml` runs the same build to check that the repo, ref and skills exist.

To check locally: `python .github/scripts/build_site.py --only <name>`.

External skills don't need a `quiz.yaml`, because they are not stored in this repo.

## Quiz requirement

Every skill must include a `quiz.yaml` alongside its `SKILL.md`. CI uses [docmetrics](https://github.com/mila-iqia/docmetrics) to verify that the skill content actually helps an LLM answer the questions — if the score doesn't improve when the skill is provided as context, the PR fails.

**What makes a good quiz question:**

Questions should test the *knowledge the skill provides*, not describe what the skill does. Ask about specific facts, configurations, or procedures documented in the skill — things a user couldn't answer without having read it.

For example, a skill about the Mila Slurm cluster might have:
```yaml
- question: "Which Slurm partition should you use on the Mila cluster for short jobs with up to 4 GPUs?"
  options:
    A: "main"
    B: "long"
    C: "short-unkillable"
    D: "cpu_jobs"
  answer: C
```

That's a good question because the answer is a concrete fact from the skill's content. A bad version would be "What does this skill help you do?" — that's describing the skill, not testing the knowledge inside it.

**Rules:**
- 3–5 questions is sufficient
- Each question needs 4 options and a correct answer letter
- Prefer specific facts over abstract descriptions

**Format:**
```yaml
- question: "..."
  options:
    A: "..."
    B: "..."
    C: "..."
    D: "..."
  answer: B
```

See [`example-tools/skills/example-skill/quiz.yaml`](example-tools/skills/example-skill/quiz.yaml) for a working example.

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

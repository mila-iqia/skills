---
name: mila-mcp
description: >-
  Use this skill when the user asks about the Mila Docs MCP server, connecting
  an AI assistant to Mila documentation, or configuring MCP in their editor.
  Trigger phrases include: "How do I set up the Mila MCP", "Mila MCP server",
  "mila-docs MCP", "How do I connect Claude to Mila docs",
  "How do I connect Cursor to Mila docs", "MCP configuration",
  "claude mcp add mila", "Algolia MCP", "How do I search Mila docs from my
  editor", "How do I give my AI assistant access to Mila documentation".
version: 1.0.0
argument-hint: <claude-code|cursor>
---

# Mila Docs MCP Server

This skill guides users through configuring the Mila Docs MCP server so that
their AI assistant (Claude Code or Cursor) can search the full Mila technical
documentation directly from their editor.

## Base policies

At the start of each response, use the Skill tool with `skill: "mila-base"` to
load and apply all shared policies before proceeding with the workflow below.

## Reference documentation

Primary source: **https://docs.mila.quebec/ai/mcp/**

## Discover documentation

Use the WebSearch tool with this query to find the current URL of the primary
source above:

    site:docs.mila.quebec "__skill-mila-mcp"

Use the URL from the search result in the WebFetch steps below. If the search
returns no results, fall back to the hardcoded URL in "Reference documentation".

## Workflow

### Step 1: Fetch the documentation

Use the WebFetch tool to fetch **https://docs.mila.quebec/ai/mcp/** and extract:
- The MCP server endpoint URL
- The configuration instructions for each supported client

### Step 2: Identify the user's editor

Determine which client the user is configuring:

- **Claude Code** — they mention `claude`, `claude mcp add`, or Claude Code CLI.
- **Cursor** — they mention Cursor or `mcp.json`.

If unclear, ask: "Are you using Claude Code or Cursor?"

### Step 3a: Configure Claude Code

Run the following command in the local terminal to register the MCP server:

```bash
claude mcp add --transport http mila-docs https://558773LESW.algolia.net/mcp/1/3_N8rKyLQhaxUEpt0FMx6A/mcp
```

Key points:
- This adds the server to the user's global Claude Code config. To restrict it
  to a single project, append `--scope project`.
- The endpoint is the official public Mila Docs MCP server; the API key is
  intentionally embedded in the URL and shared in the official docs. No
  personal credentials are required.
- The endpoint is subject to Algolia's standard rate limits. If you receive
  `429 Too Many Requests` errors, reduce query frequency or contact the Mila
  IDT team.
- After running the command, start a new Claude Code session and verify that
  `mila-docs` appears in the list of available tools.

### Step 3b: Configure Cursor

Add the following JSON to the global config (`~/.cursor/mcp.json`) or to the
project-level config (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "mila-docs": {
      "url": "https://558773LESW.algolia.net/mcp/1/3_N8rKyLQhaxUEpt0FMx6A/mcp"
    }
  }
}
```

Key points:
- If the file does not exist, create it with the content above.
- If it already exists, merge the `"mila-docs"` entry into the existing
  `"mcpServers"` object.
- The endpoint is the official public Mila Docs MCP server; the API key is
  intentionally embedded in the URL and shared in the official docs. No
  personal credentials are required.
- The endpoint is subject to Algolia's standard rate limits. If you receive
  `429 Too Many Requests` errors, reduce query frequency or contact the Mila
  IDT team.
- Restart Cursor after saving the file.
- Verify that `mila-docs` is listed and active in the MCP settings panel.

### Step 4: Verify the connection

After configuration, ask the AI assistant a Mila-specific question such as:

> "How do I submit a batch job on the Mila cluster?"

The assistant should pull up-to-date answers from the Mila documentation via
the MCP search tool. If no results are returned, double-check the endpoint URL
and restart the client.

### Step 5: Point to further resources

Once the MCP server is configured, the user can ask natural-language questions
about the Mila cluster without leaving their editor. For deeper workflows:
- Running jobs: see the **mila-run-jobs** skill.
- Connecting to the cluster: see the **mila-connect-cluster** skill.

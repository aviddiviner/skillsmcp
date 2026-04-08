# skillsmcp

MCP server that exposes [Agent Skills](https://agentskills.io) to AI agents via the [Model Context Protocol](https://modelcontextprotocol.io).

Agent Skills are reusable, portable instruction sets that guide AI coding agents. This server makes them discoverable and activatable as MCP tools, following the [progressive disclosure](https://agentskills.io/specification#progressive-disclosure) pattern from the Agent Skills specification.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — fast Python package manager

Install with Homebrew:

```
brew install uv
```

## Install

```
uv tool install git+https://github.com/aviddiviner/skillsmcp.git
```

This installs `skillsmcp` as a command on your PATH. To update later:

```
uv tool upgrade skillsmcp
```

## Configure

### Zed

Add to your settings (`~/.config/zed/settings.json`):

```json
{
  "context_servers": {
    "skillsmcp": {
      "command": "uvx",
      "args": ["skillsmcp"]
    }
  }
}
```

### Claude Desktop

Add to your Claude config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "skillsmcp": {
      "command": "uvx",
      "args": ["skillsmcp"]
    }
  }
}
```

### Other MCP Clients

Any client that supports MCP's stdio transport can use this server. Run it directly:

```
uvx skillsmcp
```

## Tools

The server exposes three MCP tools:

| Tool | Description |
|------|-------------|
| `list_skills` | Discover all available skills with names and descriptions |
| `activate_skill` | Load a skill's full instructions by name |
| `read_skill_file` | Read supporting files from a skill's directory |

All tools accept an optional `project_roots` parameter — a list of project directories to scan for project-level skills. User-level skills (`~/.agents/skills/`, `~/.claude/skills/`) are always included. When `project_roots` is not provided, the server falls back to its working directory.

## Adding Skills

Skills are directories containing a `SKILL.md` file with YAML frontmatter:

```
~/.agents/skills/
└── my-skill/
    ├── SKILL.md
    ├── scripts/
    │   └── helper.py
    └── references/
        └── REFERENCE.md
```

Example `SKILL.md`:

```markdown
---
name: my-skill
description: A short description of what this skill does and when to use it.
---

# My Skill

Instructions for the AI agent go here...
```

### Skill Directories

The server scans the following directories in precedence order (first-found wins for name collisions):

1. **Project-level** (highest priority):
   - `<project>/.agents/skills/`
   - `<project>/.claude/skills/`
2. **User-level**:
   - `~/.agents/skills/`
   - `~/.claude/skills/`

Project-level skills override user-level skills with the same name.

## Development

```
git clone https://github.com/aviddiviner/skillsmcp.git
cd skillsmcp

# Install in development mode
uv sync

# Run the server directly
uv run skillsmcp
```

## Learn More

- [Agent Skills specification](https://agentskills.io) — the full format spec
- [Example skills](https://github.com/anthropics/skills) — official skill examples
- [skills.sh](https://skills.sh) — browse and install community skills
- [FastMCP](https://gofastmcp.com) — the Python MCP framework powering this server

## License

MIT

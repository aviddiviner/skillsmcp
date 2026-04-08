"""MCP server that exposes Agent Skills via tools."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastmcp import FastMCP

from skillsmcp.skills import (
    SkillInfo,
    discover_skills,
    list_skill_files,
    parse_skill_frontmatter,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("Agent Skills")


def _build_skill_roots(project_roots: list[str] | None = None) -> list[Path]:
    """Build the ordered list of skill directories to scan.

    Project-level roots (from the caller or CWD) come first so they take
    precedence, followed by user-level roots that are always included.
    """
    roots: list[Path] = []

    # Project-level: prefer explicit roots from the caller, fall back to CWD
    if project_roots:
        for root in project_roots:
            p = Path(root)
            roots.append(p / ".agents" / "skills")
            roots.append(p / ".claude" / "skills")
    else:
        cwd = Path.cwd()
        roots.append(cwd / ".agents" / "skills")
        roots.append(cwd / ".claude" / "skills")

    # User-level: always included
    home = Path.home()
    roots.append(home / ".agents" / "skills")
    roots.append(home / ".claude" / "skills")

    return roots


def _get_skills_catalog(project_roots: list[str] | None = None) -> dict[str, SkillInfo]:
    """Discover all skills from the configured roots."""
    return discover_skills(_build_skill_roots(project_roots))


@mcp.tool()
def list_skills(project_roots: list[str] | None = None) -> str:
    """List all available agent skills with their names and descriptions.

    Scans project-level and user-level skill directories for SKILL.md files.
    Returns a JSON array of objects with name, description, and path for each skill.

    Args:
        project_roots: Optional list of project root directories to scan for
            project-level skills. When provided, each root is checked for
            .agents/skills/ and .claude/skills/ subdirectories. User-level
            skill directories (~/.agents/skills/, ~/.claude/skills/) are
            always included. If not provided, falls back to the server's
            working directory.
    """
    catalog = _get_skills_catalog(project_roots)

    results: list[dict[str, str]] = []
    for name, info in sorted(catalog.items()):
        results.append(
            {
                "name": info.name,
                "description": info.description,
                "path": str(info.path),
            }
        )

    if not results:
        return json.dumps(
            {
                "skills": [],
                "message": "No skills found. Create SKILL.md files in ~/.agents/skills/<skill-name>/ or .agents/skills/<skill-name>/ in your project.",
            },
            indent=2,
        )

    return json.dumps({"skills": results, "count": len(results)}, indent=2)


@mcp.tool()
def activate_skill(name: str, project_roots: list[str] | None = None) -> str:
    """Activate a skill by name, loading its full instructions and listing supporting files.

    Args:
        name: The name of the skill to activate (as returned by list_skills).
        project_roots: Optional list of project root directories to scan.
            Same behavior as in list_skills.

    Returns:
        The skill's markdown instructions with a listing of any supporting files.
    """
    catalog = _get_skills_catalog(project_roots)

    if name not in catalog:
        available = sorted(catalog.keys())
        return json.dumps(
            {
                "error": f"Skill '{name}' not found.",
                "available_skills": available,
            },
            indent=2,
        )

    info = catalog[name]

    try:
        _metadata, body = parse_skill_frontmatter(info.path)
    except Exception as e:
        logger.warning("Failed to parse skill file %s: %s", info.path, e)
        return json.dumps({"error": f"Failed to read skill '{name}': {e}"}, indent=2)

    supporting_files = list_skill_files(info.base_dir)

    result: dict[str, object] = {
        "name": info.name,
        "description": info.description,
        "instructions": body.strip(),
    }

    if supporting_files:
        result["supporting_files"] = supporting_files

    return json.dumps(result, indent=2)


@mcp.tool()
def read_skill_file(
    skill_name: str, file_path: str, project_roots: list[str] | None = None
) -> str:
    """Read a supporting file from a skill's directory.

    Args:
        skill_name: The name of the skill that owns the file.
        file_path: Path to the file relative to the skill directory (e.g. "scripts/extract.py").
        project_roots: Optional list of project root directories to scan.
            Same behavior as in list_skills.

    Returns:
        The contents of the requested file.
    """
    catalog = _get_skills_catalog(project_roots)

    if skill_name not in catalog:
        available = sorted(catalog.keys())
        return json.dumps(
            {
                "error": f"Skill '{skill_name}' not found.",
                "available_skills": available,
            },
            indent=2,
        )

    info = catalog[skill_name]
    skill_dir = info.base_dir

    # Resolve the requested path and ensure it stays within the skill directory
    try:
        requested = (skill_dir / file_path).resolve()
        skill_dir_resolved = skill_dir.resolve()

        if (
            not str(requested).startswith(str(skill_dir_resolved) + "/")
            and requested != skill_dir_resolved
        ):
            return json.dumps(
                {
                    "error": "Access denied: path traversal outside skill directory is not allowed."
                },
                indent=2,
            )
    except Exception as e:
        return json.dumps({"error": f"Invalid path: {e}"}, indent=2)

    if not requested.is_file():
        available = list_skill_files(skill_dir)
        return json.dumps(
            {
                "error": f"File '{file_path}' not found in skill '{skill_name}'.",
                "available_files": available,
            },
            indent=2,
        )

    try:
        content = requested.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return json.dumps(
            {
                "error": f"File '{file_path}' appears to be binary and cannot be read as text."
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to read file: {e}"}, indent=2)

    return json.dumps(
        {
            "skill_name": skill_name,
            "file_path": file_path,
            "content": content,
        },
        indent=2,
    )


def main() -> None:
    """Entry point: create and run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()

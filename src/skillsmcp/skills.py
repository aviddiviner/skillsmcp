"""Skill discovery and parsing logic for Agent Skills."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

SKILL_FILENAME = "SKILL.md"


@dataclass
class SkillInfo:
    """Metadata about a discovered agent skill."""

    name: str
    description: str
    path: Path  # Full path to the SKILL.md file
    base_dir: Path  # Parent directory containing SKILL.md and supporting files


def parse_skill_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter and body content from a SKILL.md file.

    Frontmatter is delimited by ``---`` lines at the start of the file.

    Returns:
        A tuple of (metadata_dict, body_content). If no valid frontmatter is
        found, metadata_dict will be empty and body_content will be the full
        file text.
    """
    text = path.read_text(encoding="utf-8")

    # Frontmatter must start with a ``---`` line
    if not text.startswith("---"):
        return {}, text.strip()

    # Find the closing ``---``
    end_index = text.find("\n---", 3)
    if end_index == -1:
        return {}, text.strip()

    frontmatter_raw = text[3:end_index].strip()
    body = text[end_index + 4:].strip()  # skip past the closing ---\n

    try:
        metadata = yaml.safe_load(frontmatter_raw)
        if not isinstance(metadata, dict):
            logger.warning("Frontmatter in %s did not parse as a mapping, skipping", path)
            return {}, text.strip()
    except yaml.YAMLError as exc:
        logger.warning("Malformed YAML frontmatter in %s: %s", path, exc)
        return {}, text.strip()

    # Normalise values to strings
    cleaned: dict[str, str] = {}
    for key, value in metadata.items():
        cleaned[str(key)] = str(value) if value is not None else ""

    return cleaned, body


def list_skill_files(skill_dir: Path) -> list[str]:
    """List all files in a skill directory, relative to that directory.

    The SKILL.md file itself is excluded from the listing.
    Hidden files/directories (starting with ``.'') are also excluded.
    """
    files: list[str] = []

    if not skill_dir.is_dir():
        return files

    for child in sorted(skill_dir.rglob("*")):
        if not child.is_file():
            continue

        relative = child.relative_to(skill_dir)

        # Skip SKILL.md itself
        if relative.name == SKILL_FILENAME and relative.parent == Path("."):
            continue

        # Skip hidden files/directories
        if any(part.startswith(".") for part in relative.parts):
            continue

        files.append(str(relative))

    return files


def _skill_roots() -> list[Path]:
    """Return the default ordered list of skill root directories to scan.

    Precedence (first-found wins):
      1. <cwd>/.agents/skills/
      2. <cwd>/.claude/skills/
      3. ~/.agents/skills/
      4. ~/.claude/skills/
    """
    cwd = Path.cwd()
    home = Path.home()

    return [
        cwd / ".agents" / "skills",
        cwd / ".claude" / "skills",
        home / ".agents" / "skills",
        home / ".claude" / "skills",
    ]


def discover_skills(roots: list[Path] | None = None) -> dict[str, SkillInfo]:
    """Scan *roots* for SKILL.md files and return a dict keyed by skill name.

    Each immediate sub-directory of a root that contains a ``SKILL.md`` is
    treated as a skill.  The skill's ``name`` comes from the frontmatter (with
    a fallback to the directory name), and the first skill found for a given
    name wins (so project-level skills shadow user-level ones).

    Args:
        roots: Directories to scan.  If ``None``, the default set from
            :func:`_skill_roots` is used.

    Returns:
        A dict mapping skill name → :class:`SkillInfo`.
    """
    if roots is None:
        roots = _skill_roots()

    skills: dict[str, SkillInfo] = {}

    for root in roots:
        if not root.is_dir():
            logger.debug("Skill root does not exist, skipping: %s", root)
            continue

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue

            skill_file = child / SKILL_FILENAME
            if not skill_file.is_file():
                logger.debug("No %s in %s, skipping", SKILL_FILENAME, child)
                continue

            try:
                metadata, _body = parse_skill_frontmatter(skill_file)
            except OSError as exc:
                logger.warning("Could not read %s: %s", skill_file, exc)
                continue

            # Determine the skill name: prefer frontmatter, fall back to dir name
            name = metadata.get("name", "").strip() or child.name
            description = metadata.get("description", "").strip()

            if name in skills:
                logger.debug(
                    "Skill %r already discovered at %s; ignoring duplicate at %s",
                    name,
                    skills[name].path,
                    skill_file,
                )
                continue

            skills[name] = SkillInfo(
                name=name,
                description=description,
                path=skill_file,
                base_dir=child,
            )
            logger.debug("Discovered skill %r at %s", name, skill_file)

    return skills

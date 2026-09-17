#!/usr/bin/env python3
"""Install the skills in this repo into a coding agent's skills directory.

DEPRECATED: superseded by `hive skills install` in the Hivekit CLI, which ships
these skills as package data. This script still works but is unmaintained.

A "skill" is just a folder containing a SKILL.md (plus any supporting files).
Installing means copying that folder into the agent's skills directory. Some
agents share a directory (Gemini CLI and Antigravity both read
~/.gemini/config/skills), so destinations are de-duplicated before copying.

Usage:
    python3 install.py                 # interactive: pick which agents
    python3 install.py --all           # install for every supported agent
    python3 install.py claude codex    # install for the named agents
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILLS_DIR = REPO_ROOT / "skills"

# key -> (display name, skills directory for that agent)
TARGETS: dict[str, tuple[str, Path]] = {
    "gemini": ("Gemini CLI", Path("~/.gemini/config/skills")),
    "antigravity": ("Antigravity", Path("~/.gemini/config/skills")),
    "claude": ("Claude Code", Path("~/.claude/skills")),
    "codex": ("OpenAI Codex", Path("~/.agents/skills")),
}

# Preserve the ordering the user listed the agents in for the interactive menu.
MENU_ORDER = ["gemini", "antigravity", "claude", "codex"]


def discover_skills() -> list[Path]:
    """Return every skill folder in the repo (a subdir of skills/ with a SKILL.md)."""
    if not SKILLS_DIR.is_dir():
        sys.exit(f"error: no skills/ directory found at {SKILLS_DIR}")
    skills = sorted(p for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file())
    if not skills:
        sys.exit(f"error: no skills (folders containing SKILL.md) found in {SKILLS_DIR}")
    return skills


def resolve_on_conflict(src: Path, dest: Path) -> bool:
    """Decide what to do when `dest` (a skill folder) already exists.

    Called only when the destination skill folder is already present. Return
    True to proceed with copying (the caller will remove `dest` first), or
    False to skip this skill and leave the existing copy untouched.

    Strategy: always overwrite. This keeps re-running the installer idempotent
    and guarantees the destination gets the latest version of the skill; any
    local edits to an installed copy are replaced.
    """
    return True


def install_skill(src: Path, dest_dir: Path) -> str:
    """Copy one skill folder into a destination skills directory.

    Returns a short status word: "installed", "updated", or "skipped".
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    updating = dest.exists()
    if updating:
        if not resolve_on_conflict(src, dest):
            return "skipped"
        shutil.rmtree(dest)

    shutil.copytree(src, dest)
    return "updated" if updating else "installed"


def choose_targets_interactively() -> list[str]:
    """Show a numbered menu and return the selected agent keys."""
    print("Which agents do you want to install the skills for?\n")
    for i, key in enumerate(MENU_ORDER, start=1):
        name, path = TARGETS[key]
        print(f"  {i}) {name:<14} ({path})")
    print("  a) all of the above\n")

    raw = input("Enter numbers (e.g. 1 3), or 'a' for all: ").strip().lower()
    if raw in ("a", "all"):
        return MENU_ORDER

    chosen: list[str] = []
    for token in raw.replace(",", " ").split():
        if not token.isdigit() or not (1 <= int(token) <= len(MENU_ORDER)):
            sys.exit(f"error: '{token}' is not a valid choice")
        key = MENU_ORDER[int(token) - 1]
        if key not in chosen:
            chosen.append(key)
    if not chosen:
        sys.exit("error: no agents selected")
    return chosen


def parse_args(argv: list[str]) -> list[str]:
    parser = argparse.ArgumentParser(
        description="Install this repo's skills into a coding agent's skills directory."
    )
    parser.add_argument(
        "agents",
        nargs="*",
        metavar="AGENT",
        help="agents to install for: " + ", ".join(TARGETS),
    )
    parser.add_argument(
        "--all", action="store_true", help="install for every supported agent"
    )
    args = parser.parse_args(argv)

    if args.all:
        return list(TARGETS)
    if args.agents:
        # de-dup while preserving order, validating each name
        seen: list[str] = []
        for a in args.agents:
            if a not in TARGETS:
                sys.exit(f"error: unknown agent '{a}' (choose from: {', '.join(TARGETS)})")
            if a not in seen:
                seen.append(a)
        return seen
    return choose_targets_interactively()


def main(argv: list[str]) -> None:
    print(
        "warning: install.py is deprecated. Use `hive skills install` instead.",
        file=sys.stderr,
    )
    agent_keys = parse_args(argv)
    skills = discover_skills()

    # Collapse agents that share a destination so we copy each skill once per path.
    dests: dict[Path, list[str]] = {}
    for key in agent_keys:
        _, path = TARGETS[key]
        dests.setdefault(path.expanduser(), []).append(TARGETS[key][0])

    print(f"\nInstalling {len(skills)} skill(s): {', '.join(s.name for s in skills)}\n")
    for dest_dir, names in dests.items():
        print(f"→ {' + '.join(names)}  ({dest_dir})")
        for skill in skills:
            status = install_skill(skill, dest_dir)
            print(f"    {status:>9}  {skill.name}")
    print("\nDone.")


if __name__ == "__main__":
    main(sys.argv[1:])

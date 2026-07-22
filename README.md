# Hive Experiment Setup

A coding-agent skill for setting up [Hive](https://hiverge.ai) (Hiverge) code-evolution experiments.

**`hive-setup`** builds an experiment from scratch: it writes `evaluate.py` (the scorer) and `hive.yaml` (the config), and bootstraps a baseline program to evolve when one doesn't exist yet. It works from a finished implementation, bare scaffolding, or just an idea.

## Install

The skill is a plain `SKILL.md` folder, so it runs on any coding agent that reads a skills directory — Claude Code, OpenAI Codex, and Gemini CLI / Antigravity. Clone this repo and run the installer, which copies the skill into your agent's skills directory:

```sh
python3 install.py          # interactive: pick which agents to install for
python3 install.py --all    # install for every supported agent
python3 install.py claude   # install for specific agents (claude, codex, gemini, antigravity)
```

The installer is pure stdlib, so no dependencies are needed. It's idempotent, so re-run it any time to update to the latest skill. Supported destinations:

| Agent | Skills directory |
| --- | --- |
| Gemini CLI / Antigravity | `~/.gemini/config/skills` |
| Claude Code | `~/.claude/skills` |
| OpenAI Codex | `~/.agents/skills` |

## Usage

Once installed, ask your agent to set up a Hive experiment — for example:

- "Set up a Hive experiment to optimize the `solve()` function in this file."
- "Use Hive to evolve this kernel to make it faster."
- "Help me write a hive.yaml and evaluate.py for this problem."

Agents that support semantic skill matching (such as Claude Code) trigger it automatically when your request fits; otherwise invoke it by name or reference it in your prompt.

## What you'll need

The skill assumes you have the Hivekit CLI installed and authenticated (`hive login`). It produces the files; you launch an experiment with `hive create exp -c hive.yaml`.

## Layout

```
install.py                        # cross-platform installer (python3 install.py)
skills/
  hive-setup/
    SKILL.md
    references/configuration.md   # full hive.yaml field reference
```

## License

[Apache 2.0](LICENSE).

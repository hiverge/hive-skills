# Hive Experiment Setup

> **Deprecated:** this standalone repo is deprecated. We now ship these skills
> as part of `hivekit`.

A coding-agent skill for setting up [Hive](https://hiverge.ai) (Hiverge) code-evolution experiments.

## Install

The skill ships with the Hive CLI:

```sh
uv pip install hivekit       # install the CLI itself
hive skills install          # interactive
hive skills install --all    # all supported coding assistants
hive skills install AGENT    # selected agents (claude, codex, gemini, antigravity)
```

See the [CLI reference](https://docs.hiverge.ai/gettingstarted/cli/reference) for the full command and target directories.

## License

[Apache 2.0](LICENSE).

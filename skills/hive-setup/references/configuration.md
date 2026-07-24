# Hive `hive.yaml` configuration reference

Full field reference for the experiment config passed via `hive create exp -c hive.yaml`.
Source: https://docs.hiverge.ai/gettingstarted/cli/configuration

## Contents
- [Top-level fields](#top-level-fields)
- [`repo`](#repo)
- [`runtime`](#runtime)
- [`sandbox`](#sandbox)
- [`sandbox.resources`](#sandboxresources)
- [`sandbox.services[]`](#sandboxservices)
- [`prompt`](#prompt)
- [Evaluator output contract](#evaluator-output-contract)
- [Full example](#full-example)
- [CLI cheat-sheet](#cli-cheat-sheet)

## Top-level fields
| Field | Type | Default | Notes |
|---|---|---|---|
| `apiversion` | string | `v1alpha1` | Schema version |
| `experiment_name` | string | required | Valid DNS label; trailing `-` appends a random unique suffix |
| `coordinator_config_name` | string | `default-coordinator-config` | |
| `log_level` | string | `WARNING` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |

## `repo`
| Field | Type | Default | Notes |
|---|---|---|---|
| `source` | string | — | A remote git URL (`https://`, `ssh://`, or `git@`) **or** a local directory path (absolute is recommended so it works from anywhere — uploaded directly, so uncommitted changes work). If omitted (`null`), no source is uploaded — the base image must already contain the code at `workdir`. |
| `files` | list[string] | `[]` | Files/dirs to include from `source`. Empty = everything. Patterns applied in order; `!`-prefix excludes; globs (`*`, `?`, `[…]`) supported. Hidden files and symlinks skipped. |
| `branch` | string | `main` | Branch to use when cloning a remote source |
| `evaluation_script` | string | `evaluation.py` | Path relative to repo root; run as `python <path>` |
| `target_code` | list[string] | required | Files/ranges the agents may rewrite |
| `additional_context` | list[string] | `[]` | Supporting files agents read but don't edit |
| `github_token` | string | — | For private repos (avoid; prefer the variable form) |
| `github_token_variable` | string | — | Env var name holding the token; mutually exclusive with `github_token` |

**`target_code` / file list syntax:** `main.py` (whole file), `main.py:1-50` (line range), `main.py:1-10&21-30` (multiple ranges).

**Supported file extensions for `target_code` and `additional_context`:** `.py`, `.pyi`, `.cpp`, `.cxx`, `.cc`, `.c++`, `.hpp`, `.hxx`, `.hh`, `.h++`, `.c`, `.h`, `.cu`, `.cuh`, `.pyx`, `.pxd`, `.go`, `.rs`, `.mk`, `Makefile`, `GNUmakefile`, `.cmake`, `CMakeLists.txt`.

**`repo.files` example:**
```yaml
repo:
  files:
    - src              # include the src directory
    - "*.py"           # include top-level Python files
    - "!src/secrets"   # exclude a subdirectory
```

## `runtime`
| Field | Type | Default | Notes |
|---|---|---|---|
| `num_agents` | integer | `1` | Parallel agents |
| `max_runtime_seconds` | integer | `-1` | `-1` = unlimited |
| `max_iterations` | integer | `-1` | Per agent; `-1` = unlimited |
| `stochastic_evaluator` | bool | `false` | If the evaluator is fundamentally stochastic |

## `sandbox`
| Field | Type | Default | Notes |
|---|---|---|---|
| `base_image` | string | required | e.g. `python:3.12-slim` |
| `workdir` | string | `/app` | |
| `setup_script` | string | `null` | Shell commands run once at sandbox creation, from repo root. Omit or set to `null` if none needed |
| `evaluation_timeout` | integer | `60` | Seconds before an evaluation is killed |
| `envs` | list | — | Entries with `name`/`value` |
| `services` | list | — | Sidecar containers |

## `sandbox.resources`
| Field | Type | Default | Notes |
|---|---|---|---|
| `cpu` | string | `"1"` | |
| `memory` | string | `"2Gi"` | |
| `shmsize` | string | — | e.g. `"1Gi"` |
| `accelerators` | string | — | `<accelerator-name>:<num-gpus>`, e.g. `a100-80gb:8` |

Available accelerators: `a100-80gb`, `a100-40gb`, `h100`, `h200`, `b200`, `a10`, `t4`, `l4`, `l40s`.
Tip: allocate resources and timeouts with headroom — resource exhaustion counts as a failed evaluation.

## `sandbox.services[]`
Sidecar containers (e.g. a database or queue the evaluator needs).
| Field | Type | Notes |
|---|---|---|
| `name` | string | required |
| `image` | string | required |
| `ports` | list | each entry: `port` (+ optional `protocol`: TCP/UDP) |
| `envs` | list | `name`/`value` entries |
| `command` | list | container entrypoint |
| `args` | list | arguments |
| `resources.cpu` | string | `"1"` |
| `resources.memory` | string | `"2Gi"` |

## `prompt`
Optional — omit for defaults. Steers the agents' search.
| Field | Type | Default | Notes |
|---|---|---|---|
| `context` | string | — | Experiment-specific guidance, multi-line |
| `ideas` | list[string] | — | Distinct directions; one randomly sampled and injected each iteration |

## Evaluator output contract
`evaluate.py` must print a JSON object on the **final line** of stdout.

On success:
```json
{"status": "success", "result": {"fitness": 0.85, "feedback_message": "..."}}
```
On failure (incorrect candidate, error, timeout, build failure):
```json
{"status": "failed", "error": "Output did not match the expected result"}
```

| Field | Type | Notes |
|---|---|---|
| `status` | string | `"success"` or `"failed"` |
| `result.fitness` | number or object | Required when success. Number (higher is better), or object of named numbers for multi-objective (e.g. `{"speedup": 2.48, "accuracy": 0.94}`). Hive maximizes it; negate to minimize. |
| `result.feedback_message` | string (optional) | Surfaced to the agents |
| `error` | string | Required when failed; describes what went wrong |

## Full example
```yaml
apiversion: v1alpha1
experiment_name: my-experiment-
coordinator_config_name: default-coordinator-config
log_level: WARNING

repo:
  source: https://github.com/your-org/your-repo.git
  branch: main
  evaluation_script: evaluate.py
  target_code:
    - main.py:1-50
  additional_context:
    - utils.py:10-30
  github_token_variable: GITHUB_TOKEN

runtime:
  num_agents: 10
  max_runtime_seconds: 3600
  max_iterations: 100

sandbox:
  base_image: python:3.12-slim
  workdir: /app
  evaluation_timeout: 600
  setup_script: |
    pip install -r requirements.txt
  resources:
    cpu: "2"
    memory: "4Gi"
    shmsize: "1Gi"
    accelerators: a100-80gb:8
  envs:
    - name: DATABASE_URL
      value: postgres://localhost/mydb
  services:
    - name: redis
      image: redis:7-alpine
      ports:
        - port: 6379
          protocol: TCP
      resources:
        cpu: "500m"
        memory: "512Mi"

prompt:
  context: "Focus on optimizing the data pipeline for throughput."
  ideas:
    - "Try batching database writes"
    - "Consider async I/O for network calls"
```

## CLI cheat-sheet
- `hive init` — set up `~/.hive/config.yaml` (org ID)
- `hive login` / `hive logout` — authenticate / clear credentials
- `hive create exp -c hive.yaml [key.path=value ...]` — launch; inline dot-notation overrides the YAML; `~key.path` removes a key (restores default)
- `hive list exp` — table of experiments (NAME, AGENTS ready/total, STATUS, AGE)
- `hive get exp <name>` — detailed spec + status
- `hive logs <name> --source {all,coordinator,sandbox} [--worker N] [--no-follow]` — stream logs (live by default; `--source` defaults to `all`; `--worker` selects a sandbox worker)
- `hive stop exp <name> [...] [-y]` — stop one or more running experiments
- `hive dashboard [--no-browser]` — open the dashboard
- `hive list image` / `hive push image <local> hive:<short>:<tag> [--sync-config hive.yaml]` / `hive delete image <image> [--all]` — manage custom base images (`--sync-config` pins the pushed image's digest into the config)

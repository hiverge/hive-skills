---
name: hive-setup
description: Set up a Hive (Hiverge) code-evolution experiment by writing the two files it needs — evaluate.py (scores a candidate, prints fitness as JSON) and hive.yaml (experiment config) — plus, when no working algorithm exists yet, the initial baseline program for Hive to evolve from. Works whether the user has a finished implementation, only problem-definition scaffolding, or just an idea for an algorithm or mathematical problem to optimize. Use when the user wants to run, configure, or launch a Hive experiment, evolve/optimize code with Hive, write a Hive evaluator or hive.yaml, bootstrap a starting solution for Hive, or mentions Hive/Hiverge, "hive create exp", or AI-driven code optimization against a metric.
---

# Hive Experiment Setup Assistant

Hive (by Hiverge) is an AI-powered code-evolution platform. You point it at some target code and an evaluation metric, and a swarm of agents iteratively rewrites the target to maximize that metric. Your job in this skill is to produce everything a Hive experiment needs to run:

1. **`evaluate.py`** — a script that scores a candidate version of the code and prints the score as JSON.
2. **`hive.yaml`** — the experiment config: what code to evolve, how to build the sandbox, how many agents, etc.
3. **A baseline implementation to evolve** — *only when one doesn't already exist*. Hive evolves an existing program; it can't start from an empty file. If there's no working algorithm yet, you also write a simple seed — anything from a naive baseline to a trivial dummy — for the agents to improve on (see Step 2).

So this skill handles three starting points along one spectrum:
- **Finished implementation** — a working algorithm already lives in the repo; you wrap it in an evaluator and config. (Skip Step 2's bootstrapping.)
- **Scaffolding only** — the repo defines the problem (interfaces, data, a `solve()` stub, a reference/checker) but has no real algorithm; you fill in a baseline that satisfies the interface.
- **Just an idea** — no repo yet; you stand up a minimal project (the target file, any harness, `requirements.txt`) around the user's described problem.

Assume the user already has the Hivekit CLI installed and authenticated (`hive login`). Your deliverables are the files above; they launch with `hive create exp -c hive.yaml`.

**Resolve questions first, then write everything in one pass.** Clarify the metric, target, and correctness gate in Step 1 — those questions are cheap and shape every artifact. Once you have answers, produce all files (baseline if needed, `evaluate.py`, `hive.yaml`) without pausing, then present the summary (Step 5).

**This is collaborative — work with the user, don't just hand them an answer.** Good setup depends on judgment calls only the user can make: surface your assumptions, check the decisions that matter, let them steer, and **ask whenever you're unsure — don't guess.** A wrong assumption about the metric, correctness check, target, or environment wastes real compute before anyone notices it's measuring the wrong thing; a clarifying question is far cheaper.

For the full configuration field reference, read `references/configuration.md` — pull it in whenever you're unsure about a field name, default, or syntax.

If the evaluation splits into independent pieces that can be scored in parallel — slices of a dataset, several benchmarks — or the workload wants many single-GPU sandboxes instead of one multi-GPU one, read `references/multi-evaluator.md` before writing `evaluate.py` and `hive.yaml`; it changes the shape of both.


## Step 1 — Understand the task

**Start with the docs, yourself.** Before exploring source code (or delegating any exploration, if your agent supports subtasks), read `README.md`, `CONTRIBUTING.md`, and any project documentation directly. Summarize what you learn before moving on — many of the questions below should be answerable from the docs alone. Don't hand off "figure out the build" or "explore the codebase" until you have read and understood the project docs yourself.

### What to evolve

0. **Starting point** — does a working implementation already exist, or are you bootstrapping one? Look at the repo: is there real algorithm code in the target, or just stubs/interfaces/`NotImplementedError`/a problem spec? If it's the latter (or there's no repo at all), you'll write the baseline in Step 2 before wrapping it. When in doubt, ask the user whether they have a starting solution or want you to create one.
1. **Target code — and the scope of evolution.** First settle *how wide* the search should be: is this one algorithm/heuristic/kernel in a single or a few distinct, well-defined files (name those paths, ideally down to functions or line ranges), or a general whole-codebase optimization where the win could come from anywhere (leave the target open and fence off what must stay fixed)? Ask if it's ambiguous — see the `target_code` note in Step 4 for how each case is expressed. Either way, everything outside the target stays frozen, so the target should cover the algorithm and not the test harness. **Target code in place** — don't extract parts of the code into a new file for the experiment. Target them where they already live so agents see each value next to the logic it affects.
2. **Metric** — what "better" means. Throughput, latency, accuracy, compression ratio, etc. Hive *maximizes* fitness, so a quantity you want to minimize (like runtime) must be negated or inverted (see Step 3).
3. **Correctness** — how to tell a candidate is *valid*. This is what stops the optimizer from cheating.
4. **Test inputs** — how evaluation inputs are produced (generated, loaded from a fixture, a benchmark dataset).

### Environment and build

Getting this right matters — the sandbox must match the environment the user actually runs in, or improvements Hive finds won't transfer.

5. **Environment** — language, runtime version, dependencies, and whether a GPU is needed. Also note any **large data** the evaluator needs (datasets, model weights — order of GBs): these shouldn't be uploaded with the code; plan to download them in `setup_script` (see Step 4).
6. **Build instructions** — use what the docs prescribe (toolchain, base image, package manager). If the docs say "use conda" or "use this base image," do that — don't improvise an alternative. Only consult `CMakeLists.txt`, `Makefile`, or `build.sh` to fill gaps the docs leave. These directly feed your `setup_script`, `base_image`, and Dockerfile in Step 4.

Ask about anything you can't infer from the repo, or if it's unclear which part of the codebase the user wants to optimize.

Capture this analysis as you go — the findings here (what the target does, the metric, correctness constraints) become the `prompt.context` you write in Step 4, the agents' primary steer.


## Step 2 — Establish a baseline to evolve (only if one doesn't exist)

Hive improves an existing program — it needs a valid starting point in `target_code`, not a blank file. If Step 1 found a working implementation, skip ahead to Step 3. Otherwise, write the seed yourself.

**Do not try to make the seed good, and do not iterate on it.** This is the easy trap: writing an initial program, seeing it perform poorly, and trying to improve it. **Stop at the first version that produces `"status": "success"` from `evaluate.py`.** That's the only bar. A low score, a zero score, getting stuck, being slow, producing bad output — none of these are problems to fix. Making it good is *Hive's entire job*; every improvement you hand-write is wasted effort, headroom taken away from the search, and a more biased starting point. A trivial program that does essentially nothing (returns a constant, the input unchanged, an empty result) is often *ideal*, as long as `evaluate.py` completes with `"status": "success"` and a fitness value.

Beyond "make it run," a few things to get right:

- **How trivial it can be depends on the correctness gate.** Under a *hard gate* (wrong output ⇒ `status: "failed"`) the seed must actually be correct, just slow (a naive exact method); under a *graded* signal (partial credit, a smoothly-improving error) a do-nothing placeholder that scores low but doesn't fail is ideal. Hive doesn't need a non-zero starting score to make progress, so don't waste time trying to give the optimizer "something to work with."
- **Complete on the evaluated path.** It must satisfy the interface the rest of the codebase and your evaluator expect — same signature, return type, and invariants — with no `NotImplementedError` or `pass` on the path the evaluator exercises. "Dummy" means trivial logic, not a stub that crashes.
- **Plain and readable.** Clear, idiomatic code with no premature optimization. This is what the agents read first, so it doubles as a specification of intent — obvious code evolves better than clever code.
- **Functionally and structurally minimal.** The seed's *shape* biases the search as much as its logic. Helper layouts, a sketched-out approach, or an elaborate scaffold quietly anchor agents to one template and steer them away from directions you didn't anticipate. Commit to as little structure as the interface allows — a single trivial function beats a tidy multi-module skeleton.
- **Honest.** Don't hardcode the expected outputs, special-case the test inputs, or short-circuit the scored work — that's the reward-hacking the evaluator is meant to catch, and seeding it teaches the agents the wrong lesson. A trivial-but-genuine attempt (a constant, a greedy first guess) is fine; a lookup table keyed to the test cases is not.

**When there's no repo at all (just an idea):** stand up a minimal project around the problem — the target file with the baseline implementation, any small harness or data the evaluator needs, and a `requirements.txt`. Keep the structure flat and obvious. Decide with the user where it should live and whether it'll be a local path or a git repo (this feeds `repo.source` in Step 4).

**When the repo is scaffolding:** respect the interfaces already defined (function names, dataclasses, the checker/reference). Implement the missing algorithm to fit them rather than reshaping the scaffold — the scaffold usually encodes how the candidate will be scored.


## Step 3 — Write `evaluate.py`

The evaluator is run as `python3 evaluate.py` from the repo root. It must print a **JSON object on the final line** of stdout. On success:

```json
{"status": "success", "result": {"fitness": 0.85, "feedback_message": "throughput +23% vs baseline"}}
```

When the candidate is invalid (fails correctness, errors, times out, build fails), report the failure explicitly instead:

```json
{"status": "failed", "error": "Output did not match the expected result"}
```

Contract:
- `status` — `"success"` or `"failed"`.
- `result.fitness` — required on success: a number (higher is better), **or** an object mapping names to numbers for multi-objective runs, e.g. `{"speedup": 2.48, "accuracy": 0.94}`. Hive maximizes it, so a quantity you want to minimize (runtime, error rate) must be negated or inverted into a speedup-style score.
- `result.feedback_message` — optional string passed back to the agents; a good place to explain *why* a candidate scored as it did.
- `error` — required on failure: a short description of what went wrong, surfaced to the agents so they can avoid the same mistake.

### Enforce correctness explicitly

Never assume a candidate's output is correct. Always check it against a reference or invariants *before* scoring performance, and return a failure on incorrect results regardless of how fast they are.

### Guard against reward hacking

The Hive will exploit any shortcut that inflates the score — caching results, short-circuiting logic, hardcoding outputs, mutating global state, reading the reference answer, or exiting early. Build validation checks into your evaluator.

### Determinism

Where possible, make the evaluator deterministic — the same code should always produce the same fitness — since unnecessary noise makes genuine improvements harder to distinguish. But if it's *fundamentally* non-deterministic (timing measurements, randomized algorithms), don't force determinism by averaging or fixing seeds. Instead set `runtime.stochastic_evaluator` to true to use the Hive's built-in mechanisms for handling noisy evaluations.

### Give the optimizer a smooth gradient

Evolution works best with a graded signal, not pass/fail. Aim for a metric that improves *incrementally* as the code gets better — e.g. average runtime across a spread of inputs from easy to hard, so progress on harder cases nudges the score up. A single all-or-nothing test gives the agents almost no feedback to learn from.

### Keep evaluations fast

Faster evaluation means faster iteration, so target well under the `sandbox.evaluation_timeout` on baseline code — with headroom, since better solutions sometimes use more time/memory and resource exhaustion counts as a failure.

If a single evaluation is unavoidably slow because it grinds through independent pieces — dataset slices, a suite of benchmarks, many test scenarios — you can split it across sandboxes to run them concurrently instead of serially. That's a **multi-evaluator**: `repo.evaluation_arguments` runs `evaluate.py` once per argument set, and a separate `aggregation_script` you also write combines the per-piece results into the final fitness. It changes the shape of both `evaluate.py` (it must take arguments selecting its piece) and `hive.yaml`, so decide before writing either — read `references/multi-evaluator.md` if you're going this route.

### Single vs. multi-objective fitness

Use a single scalar when there's one main metric of interest or when multiple criteria are positively correlated (e.g. runtime across different input sizes) — a single number gives agents a single clear goal. Use the dict form (`{"speedup": 2.48, "accuracy": 0.94}`) when goals genuinely compete (speed vs. accuracy, size vs. quality). Multi-objective mode explores the Pareto frontier and also encourages more diverse solutions, since agents can improve along different axes.

### Template A — pure Python target

```python
import json

def make_inputs():
    # Generate or load a spread of test cases, easy -> hard. Seed any randomness.
    ...

def reference(x):
    # Known-correct (possibly pre-computed) result, for the correctness gate.
    ...

def main():
    inputs = make_inputs()
    total_score = 0.0
    for x in inputs:
        result = candidate(x)            # the function under optimization
        if result != reference(x):       # correctness gate
            print(json.dumps({"status": "failed", "error": "Incorrect result"}))
            return
        total_score += score_one(x, result)

    fitness = total_score / len(inputs)
    print(json.dumps({
        "status": "success",
        "result": {"fitness": fitness, "feedback_message": f"mean score {fitness:.4f}"},
    }))

if __name__ == "__main__":
    main()
```

**`evaluate.py` is always Python** — Hive runs it as `python3 evaluate.py`. To evaluate code in another language (C/C++/Rust/Go/CUDA/etc.), drive it from this Python script with `subprocess`: compile the candidate (treat a build failure as a failed run — `{"status": "failed", "error": "build failed: ..."}`), then run the resulting binary and parse its output. The target the agents evolve can be in any language; only the evaluator that scores it must be Python. Keep the evaluator modular — small helpers are easier to get right than one big block.

### Template B — compiled target (C/C++/CUDA) driven via `subprocess`

Same shape as A — make inputs, gate on correctness, score — but the candidate is a binary the evaluator builds and runs. Build *incrementally* (only the edited target; reuse cached objects — see Step 4's prebuilt-image notes) and treat a build failure as a failed run.

```python
import json, subprocess, time

def build():
    # Incremental rebuild of just the target. Reuse the warm build dir baked into the image.
    # Build only what's needed (no tests/examples). Returns (ok, log).
    r = subprocess.run(["cmake", "--build", "build", "--target", "solver"],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stderr

def run_case(x):
    # Invoke the compiled binary on one input; parse stdout into a result.
    r = subprocess.run(["build/solver"], input=x.stdin, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return parse_output(r.stdout)

def main():
    ok, log = build()
    if not ok:
        print(json.dumps({"status": "failed", "error": f"build failed: {log}"}))
        return

    total_score = 0.0
    inputs = make_inputs()
    for x in inputs:
        try:
            result = run_case(x)
        except (subprocess.TimeoutExpired, RuntimeError) as e:
            print(json.dumps({"status": "failed", "error": f"run failed: {e}"}))
            return
        if result != reference(x):              # correctness gate
            print(json.dumps({"status": "failed", "error": "Incorrect result"}))
            return
        total_score += score_one(x, result)

    fitness = total_score / len(inputs)
    print(json.dumps({
        "status": "success",
        "result": {"fitness": fitness, "feedback_message": f"mean score {fitness:.4f}"},
    }))

if __name__ == "__main__":
    main()
```


## Step 4 — Write `hive.yaml`

### How the sandbox is built

At sandbox creation, in order:
1. **Starts from `base_image`**.
2. **Adds `repo` at `workdir` (default `/app`)** (filtered by `repo.files`).
3. **Runs `setup_script` once**, from `workdir`.

### Choosing an image strategy

Pick one strategy before writing the config. The decision is simple:

| Question | Answer | Strategy |
|----------|--------|----------|
| Is the target interpreted (Python, JS)? | Yes | **A — Stock image** |
| Is it compiled, but builds in seconds? | Yes | **A — Stock image** |
| Does a full build take minutes? | Yes | **B — Prebuilt image** |

**Strategy A — Stock image.** Use a stock `base_image` (`python:3.14-slim`, `gcc`, `rust`, `nvidia/cuda`), install deps in `setup_script`, and let `evaluate.py` handle any per-candidate compilation (Template B from Step 3). This covers both interpreted targets and small compiled targets. For the skill's own seeded experiments, `repo.source` should usually be a **local directory** (so uncommitted seed/evaluator files upload directly) — unless those files already live in a repo and the user only needs the `hive.yaml`.

**Strategy B — Prebuilt image.** Bake the codebase and heavy dependencies into a custom Docker image. **Don't assume this image exists.** Unless the user says they have one, building it is part of your job: confirm they want this route, write the `Dockerfile`, and set `base_image` to `hive:<remote-tag>:<version>`.

**Example A — stock image (Python / quick-compiled).** For quick builds, swap the base image for a toolchain (e.g. `gcc`) and let `evaluate.py` compile per run:

```yaml
apiversion: v1alpha1
experiment_name: my-exp-          # trailing '-' appends a unique suffix; keep it

repo:
  source: /absolute/path/to/directory          # git URL or an absolute local path
  branch: main                                 # only for a remote git URL; omit for a local path
  evaluation_script: evaluate.py
  target_code:
    - path/to/target.py           # whole file, or target.py:10-50 for a line range

runtime:
  num_sandboxes: 10               # parallel sandboxes; see guidance below
  max_runtime_seconds: 3600       # -1 = unlimited

sandbox:
  base_image: python:3.14-slim
  setup_script: |
    pip install -r requirements.txt   # runs once at sandbox creation, from repo root
  evaluation_timeout: 600           # seconds; must exceed baseline evaluate.py runtime
  resources:
    cpu: "1"
    memory: "4Gi"
    shmsize: "1Gi"
    # accelerators: a100-80gb:1     # only if a GPU is needed; format <name>:<count>

prompt:
  context: |
    <your onboarding document — see "Writing prompt.context" below>
```

**Example B — prebuilt image (compiled, e.g. C++/CUDA).** The codebase is pre-compiled in the image. No `setup_script`; only `repo.files` entries are overlaid each run — set this to **only `evaluate.py`** (everything else is already in the image):

```yaml
apiversion: v1alpha1
experiment_name: my-cpp-exp-

repo:
  source: /absolute/path/to/directory
  files:                            # overlay only the files from source that are different from the prebuilt image
    - evaluate.py
  evaluation_script: evaluate.py
  target_code:
    - src/solver.cpp

runtime:
  num_sandboxes: 10
  max_runtime_seconds: 3600

sandbox:
  base_image: hive:my-cpp-exp:v1    # pushed via: docker build -t my-cpp-exp . && hive push image my-cpp-exp hive:my-cpp-exp:v1
  workdir: /app                     # where the code was baked in
  # no setup_script: dependencies + build are already in the image
  evaluation_timeout: 600           # evaluate.py recompiles the candidate; leave headroom
  resources:
    cpu: "1"
    memory: "8Gi"
    accelerators: a100-80gb:1       # if the kernel needs a GPU

prompt:
  context: |
    <your onboarding document — see "Writing prompt.context" below>
```

Two things keep this fast:
- **Make the per-evaluation rebuild incremental, not from scratch.** Bake the heavy, stable build (third-party libs, the object files for everything *except* the target) into the image's layers, and configure the in-evaluator build to reuse those cached objects (a warm build directory, `ccache`, an unchanged `make`/CMake graph) so only the one edited translation unit recompiles and relinks — seconds, not a full rebuild.
- **Build as little as possible.** Compile only what the evaluation actually exercises. Skip tests, examples, benchmarks, docs, and unrelated targets (`cmake --build . --target solver`, `BUILD_TESTING=OFF`, etc.) — every target you build is time paid on every candidate for no benefit.

### Writing `prompt.context`

This is the agents' primary steer. Write it as an onboarding document — imagine getting a new PhD student up to speed so they can start contributing:

- **Describe the problem, not the solution.** Do NOT suggest optimization approaches, likely bottlenecks, or directions to explore — that biases the Hive and narrows its search.
- **Never describe the current code.** This context is fixed while the target evolves every iteration, so anything about how the present implementation works is stale and misleading at once.
- **Distill useful background from the repo's README or design docs** into this prose — agents get context only here, never as markdown files; `repo.additional_context` is for code files only.

### Key field notes

Field-level details (types, defaults, full syntax) are in `references/configuration.md`. These are the choices that matter most:

- **`target_code`** — decide the **scope of evolution** here; it's a real choice, not a formality.
  - *Bounded scope* — the thing being optimized is one algorithm, heuristic, or kernel living in a single file or a few distinct, well-defined ones. **List those paths explicitly** (narrow to line ranges where the file mixes the algorithm with harness/plumbing). This is the common case, and a tight target concentrates the search on the code that actually moves the metric.
  - *Whole-codebase scope* — the user wants the system optimized end-to-end and the wins could come from anywhere, with no single obvious hot file. **Leave `target_code` empty**, which lets the Hive evolve any file except the evaluation script, and use `!`-prefixed entries to fence off what must stay fixed (`["!fixed.py"]` = evolve everything but `fixed.py`). Fence off anything correctness depends on — reference implementations, checkers, fixtures, test harnesses — otherwise the agents can weaken the very code that's meant to catch them.
  - **If it's unclear which of the two the user wants, ask.** Getting this wrong is expensive in opposite directions: too narrow and the Hive can't reach the improvement; too broad and the search dilutes across files that don't matter.
- **`setup_script`** — the most common source of failures. Runs from repo root; must install everything `evaluate.py` imports. Omit only if the base image already has every dependency.
- **Large data (GBs)** — if data is public, download in `setup_script` (curl/wget/`huggingface-cli`), not via `source`/`repo.files`. Multi-GB uploads are slow and may fail.
- **Never put secrets in a Hive file.** API keys, tokens, and passwords must never appear in `hive.yaml`, `setup_script`, `evaluate.py`, or anything under `repo`/`repo.files` — these are committed, shared, and baked into sandboxes, so a credential there is a leak. This is a hard rule. If access to a resource needs a credential (e.g. a gated or private Hugging Face model, a private dataset), **do not** authenticate from `setup_script`. Instead fetch it *locally*, where you already hold the credential, and make the resulting artifact available without the secret — ship it in the repo if small enough, or bake it into a prebuilt image (Strategy B) / upload it to storage the sandbox can read without a per-user secret if large. If you find yourself needing a token to make the experiment run, stop and flag it to the user rather than embedding it.
- **`evaluation_timeout`** — must comfortably exceed baseline `evaluate.py` runtime.
- **`repo.additional_context`** — files the agents can *read* but not edit. Agents see only `target_code` plus what you list here; if the target calls an API they can't see, they'll hallucinate its signature. Include the interfaces the target depends on (imports, called functions, input shapes) — but be minimal: narrow to relevant files or line ranges (`file.py:1-50`). The test: *would the target be ambiguous without this file?* **Code files only — no `.md` or prose docs.**

### Choosing `num_sandboxes`, `max_runtime_seconds` and hardware — ask if unsure

These drive cost and feasibility, so **when unsure about sandbox count, runtime, GPU type, or memory, ask the user** rather than guessing.
- Start around 5–10 sandboxes for a typical CPU experiment; scale up (toward 20–30) for harder search spaces. More sandboxes = more parallel exploration but more cost. With a multi-evaluator, size it as (sub-evaluations) × (parallel attempts), or the pieces just serialize.
- **Always set `max_runtime_seconds`** — default to 1–2 hours (3600–7200) for a first run. Never leave it unset (infinite) unless the user explicitly asks for an open-ended experiment; an uncapped run burns budget silently if the metric plateaus.
- Only request `accelerators` when the workload genuinely needs a GPU (ML training/inference, CUDA kernels). Available: `a100-80gb`, `a100-40gb`, `h100`, `h200`, `b200`, `a10`, `t4`, `l4`, `l40s`.
- **Prefer many small GPU sandboxes over one large allocation.** A request like `a100-80gb:8` schedules far more slowly than eight separate `a100-80gb:1` sandboxes, so if the evaluation can be split into independent pieces, do that instead of asking for one big multi-GPU box — see `references/multi-evaluator.md`. Only request multiple GPUs in a single sandbox when one evaluation genuinely needs them together (a model that doesn't fit on one card, multi-GPU communication being the thing under optimization).

### Validate the configuration

After writing `hive.yaml`, you **must** run `hive create exp -c hive.yaml --dry-run` to confirm the config is valid. Fix any errors before moving on.


## Step 5 — Wrap up

Once all files are written, conclude with a summary and offer next steps. Use this template:

---

**Summary of what was created:**

- `evaluate.py` — <metric chosen, how fitness is computed, and what correctness checks gate it>
- `hive.yaml` — <key config choices: image strategy, num_sandboxes, timeout, target>
- <any other files: Dockerfile, baseline implementation, requirements.txt, etc.>

**Choices made:**

- <non-obvious decisions the agent made autonomously — e.g. image strategy, timeout value, fitness formulation, resource sizing>

**If using a custom image, also include:**

```
# Build and push the image:
docker build -t <local-tag> .
hive push image <local-tag> hive:<remote-tag>:<version>

# Iterating without rebuilding: edit files locally and add them to
# repo.files in hive.yaml — Hive overlays them onto the container each
# run, so changes take effect immediately without a rebuild + re-push.
```

**Recommended before launching — validate the evaluator in a real sandbox**

`hive shell` builds the same sandbox this config describes and drops you into it, so you can check the evaluator against the real environment before spending compute:

```
hive shell -c /absolute/path/to/hive.yaml --max-duration 600

# inside the sandbox:
python3 evaluate.py    # want "status": "success" on the last line, well under evaluation_timeout
```

**How to launch the Hive experiment**

Once the evaluator checks out, run

```
hive create exp -c /absolute/path/to/hive.yaml
```

Other useful commands:
- `hive dashboard` — watch progress and fitness over time
- `hive stop exp <name>` — stop the run

---

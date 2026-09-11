# Multi-evaluator experiments

Splitting one evaluation into several sub-evaluators that run concurrently, with an aggregation script combining their results.
Source: https://docs.hiverge.ai/gettingstarted/cli/configuration#multi-evaluator

## When to use it

By default a single evaluator produces the fitness. Setting `repo.evaluation_arguments` splits the evaluation into several sub-evaluators that run **concurrently across sandboxes**, with `repo.aggregation_script` combining their results into the experiment's fitness. Reach for it when:

- **The objective decomposes into independent pieces** — slices of a dataset, several benchmarks, a suite of test scenarios — that can be scored in parallel.
- **You want many small GPU sandboxes instead of one big one.** A single large allocation such as `a100-80gb:8` is far slower to schedule than eight separate `a100-80gb:1` sandboxes. Splitting the evaluation across many single-GPU sandboxes provisions much faster than requesting one multi-GPU sandbox — often the main reason to reach for a multi-evaluator at all.

If the evaluation is one indivisible measurement, stay with a single evaluator.

## Configuration

```yaml
repo:
  evaluation_script: evaluator.py
  evaluation_arguments:
    - '0'                 # runs: evaluator.py 0
    - ['--slice', '1']    # runs: evaluator.py --slice 1
  aggregation_script: aggregator.py
  target_code:
    - main.py

runtime:
  num_sandboxes: 2        # one sandbox per sub-evaluation (2) x parallel attempts (1)
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `repo.evaluation_arguments` | list | `[]` | One entry per sub-evaluator, passed to `evaluation_script` as that run's command-line arguments. A single value = one argument; a list = several. Requires `aggregation_script`. |
| `repo.aggregation_script` | string | `null` | Combines the per-evaluator results into the final result. Only valid together with `evaluation_arguments`. |

## How it works

1. For each entry in `evaluation_arguments`, the Hive runs `evaluation_script` with those arguments. Each sub-evaluator emits the usual final-line JSON — `{"status": "success", "result": {"fitness": ...}}` or `{"status": "failed", "error": ...}`.
2. `aggregation_script` receives **one argument: the path to a JSON file** holding the list of per-evaluator results, in `evaluation_arguments` order. **Failed evaluators appear in that list too**, so the aggregator must check every `status` field.
3. The aggregation script's own output follows the same contract as `evaluation_script`, and its `fitness` becomes the experiment's fitness.

That file holds a JSON **array of the sub-evaluators' output objects, verbatim** — same shape each one printed, in `evaluation_arguments` order, successes and failures mixed together:

```json
[
  {"status": "success", "result": {"fitness": 0.91, "feedback_message": "slice 0: 910/1000 solved"}},
  {"status": "failed", "error": "run failed: timeout after 30s"},
  {"status": "success", "result": {"fitness": 0.44, "feedback_message": "slice 2: 440/1000 solved"}}
]
```

**Sizing:** set `runtime.num_sandboxes` ≈ (number of sub-evaluations) × (number of parallel attempts). Under-provision and the sub-evaluators serialize, wasting the whole point of the split.

## Aggregation script template

**Preferred — floor the failed pieces** (when the metric has a natural worst case; see the notes below):

```python
# aggregator.py
import json
import sys

FLOOR = 0.0   # the worst attainable per-piece score, e.g. 0 accuracy / 0 items solved

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        results = json.load(f)          # one entry per evaluator, in order

    # Failed evaluators are included; score them at the floor rather than
    # discarding the whole evaluation, so partial progress still registers.
    scores = [r["result"]["fitness"] if r["status"] == "success" else FLOOR
              for r in results]

    # Default: concatenate each piece's own message (or error). Summarize more
    # cleverly if that serves the agents better — see the notes below.
    messages = "; ".join(
        f"[{i}] " + (r["result"].get("feedback_message", "ok") if r["status"] == "success"
                     else f"FAILED: {r['error']}")
        for i, r in enumerate(results)
    )

    # Arithmetic mean suits absolute, same-unit scores; use a geometric mean for
    # ratios spanning orders of magnitude (and then a positive floor, never 0).
    fitness = sum(scores) / len(scores)
    print(json.dumps({"status": "success", "result": {
        "fitness": fitness,
        "feedback_message": messages,
    }}))
```

**Fallback — fail the whole evaluation** (when no honest floor exists):

```python
    # Failed evaluators are included, so handle them explicitly.
    if any(r["status"] != "success" for r in results):
        print(json.dumps({"status": "failed", "error": "an evaluation failed"}))
        sys.exit(0)

    fitness = sum(r["result"]["fitness"] for r in results) / len(results)
    print(json.dumps({"status": "success", "result": {"fitness": fitness}}))
```

Notes on writing the aggregator:

- **Decide what a partial failure means — prefer a floor over failing everything.** If the metric has a natural worst-case value for a piece that didn't complete, substitute that floor and keep aggregating: accuracy `0.0` on a slice that errored, the baseline (un-improved) runtime for a timed slice that timed out, zero items solved for a benchmark that crashed. That preserves the gradient — a candidate that nails nine slices and dies on the tenth still scores above one that dies on all ten, which is exactly the signal the search needs. Failing the whole evaluation (as in the template above) is the fallback for when no such floor exists.
- **The floor must be genuinely the worst attainable value, not merely a low one.** Failing a piece has to score *no better* than the laziest honest attempt at it, or you've built a shortcut: if bailing out scores higher than a slow-but-correct run, agents will learn to bail out. When you can't identify a value with that property — the objective is a ratio, the pieces aren't comparable, correctness is all-or-nothing — fail the whole evaluation instead.
- **Pick the mean that matches the pieces.** Use an **arithmetic mean** for absolute quantities in the same units (accuracy, items solved, seconds saved). Use a **geometric mean** when the per-piece values span orders of magnitude — typically ratios like per-slice speedups or tolerances/accuracies — where one slice going 20× would otherwise swamp regressions everywhere else. Prefer a mean over a sum so fitness stays comparable if the number of pieces changes.
- **Exit 0 even when reporting `"failed"`** — same contract as the evaluator; a non-zero exit is a crashed aggregator, not a failed candidate.
- **Set `feedback_message` — the aggregator is the only place that sees every sub-result.** Concatenating each piece's `feedback_message` (or its `error`, when it failed) tagged by index is a fine default and needs no logic. Do something smarter where it earns its keep: name the pieces instead of indexing them, call out just the worst or the regressed ones when there are many, or add a per-piece breakdown that shows where the score was lost. What matters is that the agents can tell *which* slice or benchmark held them back.

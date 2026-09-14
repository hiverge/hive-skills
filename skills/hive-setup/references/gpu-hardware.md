# Provider and hardware selection

How to pick `provider`, and how to size `sandbox.resources` so sandboxes fit onto real machines without stranding GPUs.


## Choosing a provider

`provider` is a **top-level** field in `hive.yaml` (sibling of `experiment_name`, `repo`, `runtime`, `sandbox`), and takes `aws` or `modal`.

Apply these rules in order. Only the first depends on something you can't read off the config — ask that one question, then derive the rest and report the outcome rather than asking again:

1. **CPU-sensitive/heavy measurement ⇒ `aws`.** Ask the user whether the score their evaluator computes depends on CPU performance: e.g., wall-clock timing that includes host-side work. If so, use AWS as they have more stable and superior CPU performance.
2. **Otherwise, any GPU ⇒ `modal`.** Modal allocates one GPU per container with an independent CPU request, so it provisions much faster than waiting for a free slice of a whole AWS GPU instance, and you're billed per container rather than for the GPUs a partly-filled machine leaves idle. The gap is widest on the premium accelerators (`a100-40gb`, `a100-80gb`, `h100`, `h200`, `b200`), which on AWS live almost exclusively on 8-GPU machines (see the catalog below).
3. **No GPU ⇒ `aws`.**


## Fitting sandboxes onto GPU machines

Each sandbox takes one GPU, and Kubernetes holds back **about 2 vCPU per machine** for system components. So a tier of `V` vCPU and `G` GPUs has `V - 2` vCPU to give out, fits `floor((V - 2) / cpu)` sandboxes, and is fully used only when `cpu` is at or below its per-GPU budget of `(V - 2) / G`.

GPU machines are sold only in discrete tiers, so accelerator, `cpu` and `num_sandboxes` have to be chosen *together*. AWS publishes the most flexible range of GPU sizes, so treat the catalog below as the proxy for what a sandbox shape can land on — **including on Modal**, which rents from the same clouds and so can't obtain a shape no provider sells.

Exceed a tier's per-GPU budget and the sandbox spills onto a larger tier, where something sits idle:

- **vCPU idle.** The tier that takes the sandbox hands it more cores than it asked for, so you pay for cores nothing uses — and you wait longer for a rarer machine. e.g., `l4:1` with `cpu: "16"` exceeds the 14 available on a `g6.4xlarge`, so it lands on a `g6.8xlarge` and uses 16 of that machine's 30.
- **GPUs idle.** vCPU runs out before the cards do, so fewer sandboxes fit than the machine has GPUs. e.g., `l4:1` with `cpu: "64"` lands on a `g6.24xlarge` — 94 vCPU available, 4 L4s — where one sandbox fits and 3 GPUs are paid for and unused. Similarly, ask for 3 sandboxes on a 4-GPU machine and the fourth GPU has nothing to run, so round `num_sandboxes` up to a multiple of what fits on one machine.

The two providers fail differently. On AWS an ill-fitting request still runs — you just pay for the idle hardware. On Modal a container whose CPU-per-GPU ratio would leave the host's remaining GPUs unusable (e.g., `l4:1` with `cpu: "64"`) may never be scheduled at all, so the experiment fails to even start.


### GPU instance catalog

AWS sizes, used as the proxy for both providers (see above). Source: [Specifications for Amazon EC2 accelerated computing instances](https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html), whose performance-specifications table gives the vCPU count, accelerator count and accelerator model of every size (retrieved 2026-09-14). Availability changes by region and over time; treat this as the shape of the fleet rather than a guarantee that a given size is schedulable today.

| Accelerator | Family | Sizes (vCPU / GPUs) |
|---|---|---|
| `t4` | g4dn | 4/1, 8/1, 16/1, 32/1, 64/1, 48/4, 96/8 |
| `a10` | g5 (A10G) | 4/1, 8/1, 16/1, 32/1, 64/1, 48/4, 96/4, 192/8 |
| `l4` | g6, gr6 | 4/1, 8/1, 16/1, 32/1, 64/1, 48/4, 96/4, 192/8 |
| `l40s` | g6e | 4/1, 8/1, 16/1, 32/1, 64/1, 48/4, 96/4, 192/8 |
| `a100-40gb` | p4d | 96/8 |
| `a100-80gb` | p4de | 96/8 |
| `h100` | p5 | 16/1, 192/8 |
| `h200` | p5e, p5en | 192/8 |
| `b200` | p6-b200 | 192/8 |


### Warning the user

If the user asks to change `cpu`, the accelerator, or `num_sandboxes` in a way that wastes hardware, warn them before applying it — don't accept it silently, and don't quietly substitute your own numbers either; they may know something you don't about the workload. Tell them, concretely:

- which machine the new request lands on, and how many sandboxes fit on it once the ~2 vCPU reserve is taken out;
- how many GPUs that leaves idle, or which larger machine tier it spills onto — or, on `modal`, that a CPU-per-GPU ratio no host can satisfy may mean the sandbox never provisions, so the experiment stalls rather than costing more;
- the nearest values that would fit cleanly, and that a smaller `cpu` is both **cheaper** and **quicker to schedule** — it fits the same sandboxes onto fewer machines, and needs a smaller free slice to land on.

Then ask whether to reduce `cpu`, raise `num_sandboxes` to fill the machine, or keep the request as it is. If they confirm it, apply it and note the trade-off in the Step 5 summary.

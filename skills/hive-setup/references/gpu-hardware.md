# Provider and hardware selection

How to pick `provider`, and how to size `sandbox.resources` so sandboxes fit onto real machines without stranding GPUs.


## Choosing a provider

`provider` is a **top-level** field in `hive.yaml` (sibling of `experiment_name`, `repo`, `runtime`, `sandbox`), and takes `aws` or `modal`.

Apply these rules in order — the outcome is a derivation, not a user preference, so set the field and report it rather than asking:

1. **Premium GPU ⇒ `modal`.** If `accelerators` names `a100-40gb`, `a100-80gb`, `h100`, `h200`, `b200`, schedule on Modal. On AWS these live almost exclusively on 8-GPU instances (see the catalog below), so a sandbox has to wait for a whole 8-GPU machine and then shares it with — at best — seven siblings. Modal allocates a single premium GPU per container with an independent CPU request, so it schedules faster and wastes nothing.
2. **Any GPU with a modest CPU need (< 8 vCPU) ⇒ `modal`.** Small single-GPU sandboxes are exactly what Modal's per-container GPU allocation is good at, and they schedule far faster there than while waiting for a slice of a GPU instance.
3. **Otherwise ⇒ `aws`.** CPU-only experiments, and CPU-heavy (≥ 8 vCPU) sandboxes on the smaller GPUs (`t4`, `l4`, `a10`, `l40s`), which have generous 1-GPU instance sizes.


## Fitting sandboxes onto AWS GPU machines

Hive runs sandboxes on Kubernetes, so a machine can't hand its full vCPU count to sandboxes — **about 2 vCPU per machine** stays reserved for the system components. A machine of `V` vCPU therefore has `V - 2` to give out, and fits `floor((V - 2) / cpu)` sandboxes.

AWS sells GPU machines only in discrete tiers (see the catalog below), so accelerator, `cpu`, and `num_sandboxes` have to be chosen *together*, aiming at a combination that fills whole machines with as little waste as possible. Three ways a request misses:

- **It spills into the next tier up.** Ask for exactly a tier's vCPU count and the reserve no longer fits: `l4:1` with `cpu: "16"` can't go on a `g6.4xlarge` (16 vCPU, only 14 available), so it lands on a `g6.8xlarge` (32 vCPU) — twice the machine for 2 extra vCPU, at a higher price and with less capacity to schedule against.
- **It strands GPUs.** Each sandbox takes one GPU, so a 4-GPU machine is only fully used if 4 sandboxes fit on it — and vCPU is what decides how many fit. Ask for too much `cpu` and you run out of vCPU before you run out of GPUs, leaving idle GPUs you're still paying for.
- **It leaves a machine half empty.** `num_sandboxes` matters just as much: ask for 3 sandboxes on a 4-GPU machine and the fourth GPU has nothing to run. Round `num_sandboxes` up to a multiple of what fits on one machine — those extra sandboxes come on hardware you're already paying for, so they buy more parallel exploration for close to nothing.


### AWS GPU instance catalog

Sources: AWS instance-type pages for 
- [G4dn](https://aws.amazon.com/ec2/instance-types/g4/)
- [G5](https://aws.amazon.com/ec2/instance-types/g5/)
- [G6](https://aws.amazon.com/ec2/instance-types/g6/)
- [G6e](https://aws.amazon.com/ec2/instance-types/g6e/)
- [P4](https://aws.amazon.com/ec2/instance-types/p4/)
- [P5](https://aws.amazon.com/ec2/instance-types/p5/)
- [P6](https://aws.amazon.com/ec2/instance-types/p6/)
(retrieved 2026-09-14). Availability changes by region and over time; treat this as the shape of the fleet rather than a guarantee that a given size is schedulable today.

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
- how many GPUs that leaves idle, or which larger machine tier it spills onto;
- the nearest values that would fit cleanly, and that a smaller `cpu` is both **cheaper** and **quicker to schedule** — it fits the same sandboxes onto fewer machines, and needs a smaller free slice to land on;
- that `provider: modal` sidesteps the whole question for single-GPU sandboxes.

Then ask whether to reduce `cpu`, raise `num_sandboxes` to fill the machine, or keep the request as it is. If they confirm it, apply it and note the trade-off in the Step 5 summary.

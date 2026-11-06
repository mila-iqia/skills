---
name: optimization-target
description: >-
  Optimize experiment code and compute usage on Slurm clusters so that many
  experiments finish as quickly as possible without changing or compromising
  their results. Use when asked to speed up, profile, or scale experiment or
  training code, improve GPU utilization or SM occupancy (SMO), pack multiple
  experiments into one job allocation, tune throughput (samples/tokens per
  second), or write the optimization report for Mila's IDT team.
---

# Code and resource optimization

The context is that we want to run many experiments using this code on clusters to which this user has access, and which use Slurm to allocate resources. We want all of these experiments to finish as quickly as possible, without changing or compromising their results. This entails finding ways to accelerate individual experiments and/or packing experiments when possible.

Furthermore, we want to produce a report about our findings and optimizations which can be sent to Mila's IDT team.

## Invariants

The optimization of the codebase should have **no impact on the results of the experiment**. Given the same seed and hyperparameters, final artifacts such as model weights and training/validation/test error should be the same, either bit-for-bit or within a margin of tolerance. While working, fidelity of intermediate artifacts such as batch loss is a good proxy.

If the algorithm is non-deterministic, or if some changes can improve performance significantly but would influence the RNG or introduce minor numerical deviations, this is likely OK as long as your changes preserve the intent and semantics of the experiment: if not precisely, you must compute qualitatively the same thing. Nonetheless, ask the user if you should proceed.

## About hyperparameter optimization

It is possible that the best way to maximize resource utilization is to change certain hyperparameters (notably increasing the batch size). Tread carefully! Changing hyperparameter optimization changes experimental results. Raise this point to the user early and ask them what the acceptable hyperparameter ranges are.

## Metrics/KPIs

The metric to optimize depends on the kind of experiment we're running. Walltime is the simplest, and the most direct representation of what we wish to achieve. However, it can take a long time, which makes it hard to iterate on. Ideally we want to optimize a good proxy for it such as throughput, for instance the number of training samples or tokens per second.

## Optimization budget

Take note that your optimization work uses the same resource budget as the experiments. Spending a lot of time iterating on minor performance gains may be unproductive unless a large enough volume of experiments is planned to make up for it.

## Job packing

If an experiment requires significantly less resources than the minimum or usual GPU allocations on the cluster, it would be a great idea to pack them: run multiple experiments in parallel in the same job allocation. You can check experimentally how the time to run N experiments in a given allocation scales to determine the optimal N, or at least a good N.

## Optimization report

You should maintain a report in `optimization-report.md`, unless otherwise specified. Update it regularly as you work, even if some claims are as-of-yet unverified. Do not write anything private or confidential in that file. The report should only describe the essentials, although more details can be written in an annex at the end at your discretion.

The IDT team is interested in this report and may ask for it, especially if we call on their expertise to further optimize the code. They may not have access to the codebase or the data. In that light, when it is possible, please include in your report:

* **Skill version**: v1.0
* **The user's username**
* **Summary of the codebase**
  * What it does. Training a model? LLM inference? Running a RL environment? What datasets? CPU-bound or GPU-bound?
  * The software stack (pytorch, huggingface, hydra, etc. and also Mila tools like cluv)
  * On which clusters experiments were run, which GPU types
* **Issues**
  * Problems that you flagged in the code
  * Fixes you made and the gains obtained
  * Changes or fixes rejected by the user, and why
* **SMO feedback** (optional)
  * If the user's experiments were flagged as "wasteful" by the IDT team, that means SMO was under a certain threshold, because SMO is the proxy they use to identify wastage. That is not a perfect proxy and some workloads may legitimately have low SMO and that's okay, but the IDT team cannot tell from their dashboard. So they would like some feedback.
  * You can measure SMO with [milalib](https://github.com/mila-iqia/milalib) (`uvx milalib monitor -i 10 -m sm_occupancy` to probe every 10s), but keep in mind that we currently have a time resolution of ~30 seconds on profiling metrics.
  * If SMO was low prior to optimization: why was it low?
  * If SMO is *still* low after your efforts: is that to be expected with this workload?
* **Feedback**
  * Anything you learned while working that would be useful to optimize other codebases, similar or not (or to avoid wasting their time)

## Sending the report to the IDT team

Ask for the user's permission before sending a report. Tell them where to read the report prior to sending.

Upload the report on a shared **write-only** Google Cloud Storage drop bucket. DROPDIR is the drop directory; the user would have received it in communications about their cluster usage. If you were not given that directory and the user doesn't know it or doesn't provide it, no need to perform the upload.

```bash
curl --data-binary @optimization-report.md \
  "https://storage.googleapis.com/upload/storage/v1/b/idt-report-drop/o?uploadType=media&name=${DROPDIR}/optimization-report-${USER}-$(date +%Y%m%d)-$(uuidgen | cut -d- -f1).md"
```

Don't persevere if it doesn't work, just say it failed.

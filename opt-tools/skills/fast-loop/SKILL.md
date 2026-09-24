---
name: fast-loop
description: Build a fast performance check for experiment code. Use when the user wants to quickly measure resource usage (GPU/CPU) of the steady-state part of an experiment, or wants to set up a tight iteration loop to optimize code performance.
---

# Objective

The objective is to produce a *fast check* for the experiment code in this repo. The objective is to get a reliable reading of the code's resource usage during its steady state -- the part of the code that will be running for most of the experiment's time -- and to get that reading *as fast as possible*. The faster we can evaluate, the faster we can tweak and experiment.

Proceed as follows:

1. Mock the data
2. Identify the "hot spots"
3. Create or configure a script to run the hot spot(s)
4. Document the script

## Mock the data

The experiment likely processes some sort of dataset. This dataset may be long to load or not accessible, and we are mainly interested in computational efficiency, which is why we'd rather mock the data.

First, though, try to understand whether mocking the data may intrinsically misrepresent the computation, e.g. if it is conditional on specific properties of the data. If so, you may want to use a subset of real data.

Then, verify what the expected data format is: the structure, the numeric ranges, using the documentation, the code, any priors you may have, or the Internet (the dataset may be known, available on HuggingFace, etc).

Lastly, write a function to generate fake data that has the expected format. If the parameters of the data can vary, e.g. image size depending on the dataset, make that configurable.

## Identify the hot spots

It should be relatively obvious where the bulk of the experiment is: a training loop, possibly a validation loop, or repeated inference on an LLM, and so on. Identify each such part and think about how to run them minimally so we can evaluate their performance and extrapolate on a full run, as fast as possible.

## Create or configure a script

We want a command that gives us a performance metric *as soon as possible*. This means minimizing set up time and only running the hot spot for a few seconds or a few minutes, depending. Try to see if command line arguments to that purpose can be easily added to the main script, or write a separate script.

The performance metrics we are interested in are:

* GPU metrics, if relevant:
  * gpu_util
  * sm_occupancy
  * mem_util
* CPU metrics, especially for CPU-bound workloads
  * cpu_util
  * ram_util

These may be obtained using `milalib` (on the Mila cluster). This command will stream a JSON object per line, one for each metric, every second:

```bash
uvx milalib monitor -i 1 -m sm_occupancy -m gpu_util -m cpu_util -m ram_util
```

Alternatively, `milalib` may be used directly from Python (it is pip/uv-installable):

```python
import asyncio

from milalib.monitor.poll import MetricRequest
from milalib.monitor.stream import stream_metrics


async def main():
    request = MetricRequest(metrics=["sm_occupancy"])
    async for m in stream_metrics(request, interval=0.1):
        print(m.timestamp, m.device, m.name, m.value)


asyncio.run(main())
```

Here's a tip: print the metrics to file descriptor 4. That way, you can easily use redirections to get them, and ignore whatever the script prints to stdout or stderr.

## Document the script

Properly document the script to use to run the hot spot in OPTLOOP.md. Also tell the user about it and be transparent about any of the choices you made.

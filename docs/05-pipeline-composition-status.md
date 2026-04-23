---
title: "Pipeline command — composing commands without any glue code"
status: publish
categories: [Architecture, Projects]
tags: [pipeline, composition, cqrs]
author: Softreck
date: 2026-04-22
---

## What this module does

The `pipeline` command chains other commands into a sequence. You hand it a list of steps; it runs them in order; each step can reference the previous step's output via the sentinel string `"$previous.output"`, which the engine rewrites at runtime into a `data:<mime>;base64,<bytes>` URI.

A step can also carry an `agent_node` — a full agent definition with `role`, `goal`, `tools`, `backend`, and `backend_config`. When the pipeline sees `agent_node`, it dispatches to `execute_agent()` instead of the command registry, and the agent's JSON output becomes the next step's `$previous.output`.

This is the tiniest possible "DSL for Command pipelines" — one sentinel, one substitution rule, plus optional agent nodes — but it covers every composition case we've needed so far. The canonical example from the design doc works verbatim:

```json
{
  "meta": {
    "steps": [
      {"command": "converttojson", "request": {"input_uri": "file:///data/products.csv", "meta": {"mode": "csv"}}},
      {"command": "render",        "request": {"input_uri": "$previous.output", "meta": {"title": "Products"}}}
    ]
  }
}
```

You get back HTML. No intermediate storage, no temp files, no per-pipeline glue code.

## Status — April 2026

The implementation is ~50 lines and it's exercised by the smoke test. What works:

- **Sequential execution** of arbitrary commands from the registry.
- **`$previous.output` substitution** anywhere in a step's request body, including nested inside `meta`. We recurse through dicts and lists.
- **Agent nodes inside steps.** A step can include `agent_node` (with `backend`, `backend_config`, `role`, `goal`, `tools`). The pipeline dispatches to `execute_agent()`, and the agent's JSON output becomes the next step's `$previous.output` after being base64-encoded as a `data:` URI.
- **Trace in the response.** The final `meta` includes a `pipeline_trace` array with each step's command name, output mime, and meta — so callers can see what happened between input and output without having to instrument each command. Agent steps include `agent_trace` and `agent_ok` in their meta.
- **Errors bubble up.** If step 3 fails, the pipeline fails; the trace up to step 2 is lost because we return the error instead. We might change this, but for now it keeps the happy-path response shape simple.

What's deliberately not in:

- **No parallelism.** Steps run sequentially. We thought about `parallel_steps` but decided we'd wait for a real use case; the current model is easier to reason about, and "the pipeline is slow because step 4 waits for step 3" has never been the bottleneck yet.
- **No conditionals.** No "if step 2 returned rows > 0, run step 3". The moment we need this we'll reach for a real workflow engine (Temporal, Argo), not grow our own.
- **No loops.** Same reasoning.
- **No access to specific fields of the previous output.** `$previous.output` is the whole payload; you can't say `$previous.meta.row_count`. We could add this but haven't needed to.

## Why the data: URI trick works so well

We kept coming back to the same design question: how does step N read step N-1's output? The obvious answers all have problems. Temp files mean we need a shared volume and a cleanup story. In-memory blob IDs mean the engine becomes stateful. Passing bytes in-band to the next command means each command needs a "received bytes from previous" code path in addition to the URI path.

The `data:` URI dodges all of it. Step N always reads a URI. It doesn't care whether the URI is `http://`, `file://`, or `data:`. The `data:` protocol handler already exists because users want to send inline payloads anyway. So the pipeline engine becomes: "render the previous response as a `data:` URI and do string substitution on step N's request." That's it.

The one wart is that it serializes the payload through base64 twice — once into the `data:` URI, and once more when the next command returns its own base64-encoded payload. For multi-megabyte payloads this matters. We think the right fix is a pipeline-local URI scheme (`prev:0`, `prev:1`) that the registry can resolve to in-memory buffers, but we haven't written it because the current overhead is irrelevant for our test payloads.

## Risks

- **The `data:` URIs can get large.** For a 10 MB intermediate result, the `data:` URI is ~13.5 MB of string. This is fine for small payloads, painful for big ones. The `prev:` fix above would solve it.
- **No circuit breakers.** A pipeline with ten `fetch` steps hitting ten different hosts will try all of them serially; if the third host is slow, steps 4-10 sit in a queue. We have per-request timeouts on HTTP but not per-pipeline wall-clock budgets.

## How you can extend it

If you want a conditional step, subclass `PipelineCommand` and add a `when` field per step; the substitution engine is already written and separate. If you want parallelism, the trickiest part is deciding whether `$previous.output` refers to "all predecessors" or "the last successful one". We think the honest answer is: don't build this, use a real workflow engine. But the hooks are all here if you want to try.

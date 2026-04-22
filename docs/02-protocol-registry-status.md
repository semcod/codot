---
title: "Protocol registry — where every URI scheme becomes a plugin"
status: publish
categories: [Architecture, Projects]
tags: [protocols, plugins, python]
author: Softreck
date: 2026-04-22
---

## What this module does

The **protocol registry** is the first thing every Command or Query touches. Before any conversion, validation, or rendering happens, something has to read bytes from a URI — and because our whole design rests on "the URI is the identity of the resource", we can't afford to hardwire any specific fetcher into the command layer.

So we put a registry in front. Every scheme (`http`, `https`, `file`, `data`, one day `s3`, `ftp`, `sqlite`) is a class with two things: a `scheme` attribute and an async `fetch(uri)` method that returns a `FetchResult` (bytes + mime + extras). Commands call `get_registry().fetch(uri)` and let the registry pick the right handler.

## Status — April 2026

The registry is production-shape for the four schemes it ships with. What's in:

- **`http` / `https`** — `httpx.AsyncClient` with follow-redirects, configurable timeout (`FETCH_TIMEOUT_SECONDS`, default 15s), configurable size cap (`FETCH_MAX_BYTES`, default 50 MiB). Returns status code and response headers in `extra` for callers that care.
- **`file://`** — resolves the URI path and refuses anything not under `ALLOWED_LOCAL_ROOTS`. This is deliberately stricter than a typical file handler: it treats "outside the root" as a `PermissionError`, not a "not found", so the API surfaces a 403 rather than a 404. The reason is policy — we want the fetch layer itself to be a defence-in-depth layer, not just a convenience wrapper.
- **`data:`** — RFC 2397 compliant. Handles both percent-encoded and base64-encoded data URIs. This one turned out to matter more than expected, because the pipeline command substitutes `"$previous.output"` with a `data:` URI at every step.

## What's missing

- **`s3://`** — we have the signature nailed down but haven't wired up boto3. The wrinkle isn't the fetch; it's credentials. We want them injected at registry-construction time, not read from env inside the protocol class. This is a two-hour job once we decide on the injection shape.
- **`ftp://`** and **`sftp://`** — trivial with `aioftp`/`asyncssh`, blocked only by "nobody asked for them yet".
- **`sqlite://`**, **`postgres://`** — these are more interesting because "fetch bytes from a database URI" is a different shape than "fetch bytes from a file". We think the right move is to return a query result as JSON bytes (`application/json`), with the SQL in the URI fragment. No code yet.
- **`redis://`, `kafka://`** — same category as the DB protocols. Probably worth doing only once we have real use cases asking for them.

## Why it's designed this way

Two small decisions that pay off disproportionately:

1. **`fetch` returns bytes, not parsed data.** Every caller decodes to the shape it needs. This is the difference between a protocol layer that's useful for one command and a protocol layer that's useful for all of them. The `converttojson` command decodes as UTF-8, the `converttobase64` command doesn't decode at all, and neither command has to know anything about HTTP or files.
2. **The `FetchResult.extra` dict is free-form.** HTTP headers go there. File size and absolute path go there. When we add S3, ETags will go there. No one consumes it today except the query `from-url` for debugging, but it's the right shape for observability once we add tracing.

## Risks

The main thing we're watching is **streaming**. The registry currently buffers the whole resource into memory before returning. For a 10 MB CSV that's fine; for a 500 MB dataset it's wrong. We have `FETCH_MAX_BYTES` as a guardrail so we fail loudly instead of OOMing, but the real fix is moving to streamed `FetchResult` objects. That's a larger refactor because the downstream commands would all have to grow a streaming path. We're deferring it until we have a caller that actually needs it.

## How you can extend it

If you want to add a new scheme today, the whole contract is:

```python
class MyProtocol:
    scheme = "myproto"

    async def fetch(self, uri: str) -> FetchResult:
        content = ...  # bytes
        return FetchResult(content=content, mime="...", source_uri=uri, extra={...})
```

Register it in `protocols/__init__.py::register_default_protocols`, restart the container, and you're done. The command layer doesn't need any changes.

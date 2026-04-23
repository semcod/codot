---
title: "Policy engine — access control where the URL is the resource"
status: publish
categories: [Architecture, Security, Projects]
tags: [rbac, abac, policy, security]
author: Softreck
date: 2026-04-22
---

## What this module does

Every Command and Query in the platform goes through the **policy engine** before it runs. The engine answers a single question: given this user, this action name, this input URI, and this optional schema URI — allow or deny?

Because our whole architecture treats URLs as the identity of resources, the policy engine has an easier time than most: it doesn't need to know what's behind a URL, only whether the caller is allowed to poke at URLs matching a particular glob. This is a lot less complex than true ABAC, and it covers 90% of what we actually need.

## Status — April 2026

The engine is simple, fast, and tested. What's in:

- **RBAC with glob patterns.** Rules live in a YAML file keyed by role. Each rule lists `allowed_commands`, `allowed_queries`, `allowed_uris`, and `allowed_schemas` as shell-style globs (`*` matches anything, `?` matches one). First matching rule wins.
- **Enforcement in one place.** The FastAPI dispatcher calls `policy.can_execute_command(...)` or `policy.can_execute_query(...)` immediately after auth, before the command handler runs. That's the only enforcement point; there is no second-guessing inside handlers.
- **Denials carry a reason.** `PolicyDecision.deny("no rule matched role=user command=converttojson uri=file:///data/products.csv")` — the reason goes into the 403 response body and the API log. This has saved us a lot of "why is this failing?" time in smoke tests.
- **Three demo roles with wildly different reach:** `admin` gets everything (including `agent_run`); `analyst` gets all commands/queries plus `agent_run` but only against `http(s)://` and the mounted `/data`, `/schemas` roots; `user` is locked to a specific public prefix.

What isn't in:

- **Attribute-based rules.** No "only during business hours", no "only the user's own tenant". The hooks are there (the `User` object has a `claims` dict) but we haven't needed it yet. When we do, the right move is either Oso or a small evaluator that understands a handful of attribute comparisons. We're not going to drag in OPA for this.
- **Hot reload.** The YAML is read once at startup. We want file-watch reload, but it's low priority because `make restart` is fast.
- **Per-tenant scoping.** A realistic SaaS deployment would want `tenant_id` in the token, and URIs scoped like `https://api/tenants/{tenant_id}/...`. The policy engine can express this today with globs, but we haven't written the wiring.

## What we learned

Two non-obvious things:

1. **Matching on URIs is better than matching on resource types.** Early drafts had rules like "analyst can read CSV" or "user cannot write to database". The URI-matching variant is both more specific ("user cannot read `file:///data/internal/*`") and more general ("analyst can read any `http://` but no `file://` outside `/data`"). The former requires classifying resources; the latter just requires knowing where they live.
2. **Policy denials as user-friendly text is worth the effort.** Returning `"no matching rule for role=user command=converttojson uri=file:///data/products.csv"` in the response body means frontend developers and curl users know exactly what to fix. A terse "forbidden" would make this project unusable.

## Risks

- **Glob patterns can't express negation cleanly.** If you want "analyst can read everything except `file:///data/secrets/*`", you need to reorder rules carefully. This has bitten us once. We're considering adding a `denied_uris` field that always takes precedence, but the YAML gets messier fast.
- **The "first matching rule wins" semantics means rule order matters.** That's fine for a six-rule file but scales poorly. If we cross thirty rules we'll add explicit priorities or move to a real rule engine.
- **Decisions are not audited.** Denials are logged but not stored anywhere queryable. For any deployment where "who tried to access what?" matters, we'd need to emit policy decisions as structured events and put them somewhere searchable.

## How you can extend it

To add a role:

```yaml
- role: editor
  allowed_commands: ["fetch", "converttojson", "render", "agent_run"]
  allowed_queries:  ["*"]
  allowed_uris:     ["http://cms/*", "file:///data/editorial/*"]
  allowed_schemas:  ["http://schemas/editorial-*"]
```

Mint a JWT with `"role": "editor"` and that's it. No code change. Note that `agent_run` must be listed in `allowed_commands` for a role to execute agents through the pipeline or the `/agents/{id}/run` endpoint.

To add attribute-based logic (not yet in): subclass `PolicyEngine`, override `can_execute_command` to consult `user.claims` or request context, and swap the instance via `reload_engine` at startup.

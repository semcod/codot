---
title: "Frontend playground — poking at commands from the browser"
status: publish
categories: [Frontend, Projects]
tags: [html, javascript, playground]
author: Softreck
date: 2026-04-22
---

## What this module does

The **playground** is the small static HTML/JS app that ships with the platform so you can see commands and queries work without writing any client code. It's deliberately not a product UI — it's a tool for developers and for us during development.

Everything it does, you can do with curl. Nothing is client-side magic. The playground reads the `/catalog` endpoint to populate dropdowns, stores the JWT in `sessionStorage`, and posts JSON bodies to `/commands/{name}` and `/queries/{name}`. The response is shown twice: as a JSON envelope (so you can see the `meta` and the `mime`) and as a decoded preview (HTML gets rendered in a sandboxed iframe, images get `<img>` tags, text gets a `<pre>`, binaries get a size notice).

## Status — April 2026

It works and it's small enough to understand in one sitting. What's in:

- **Login flow** with three canned users (admin/alice/bob) hardcoded in the form placeholder so nobody has to dig through docs on first use.
- **Catalog-driven dropdowns.** If you add a new command to the backend, it shows up in the playground's dropdown automatically — no frontend rebuild.
- **Three preset buttons** that fill in the form with working examples: CSV → JSON, render posts, and the full `fetch → json → render` pipeline. These double as smoke tests for anyone evaluating the project.
- **Inline payload decoding.** The response envelope carries a base64-encoded payload; the UI decodes it and picks a renderer based on the `mime`. HTML goes into a sandboxed iframe, so a command that returns malformed HTML can't break the playground.
- **Query runner** for `from-url` and `introspect`.

What isn't in:

- **No pipeline builder.** You write the steps as JSON in a textarea. A drag-and-drop builder would be delightful but isn't the point of this codebase. If someone wants one, the JSON shape is stable; a builder can sit on top without changing the API.
- **No history.** Every request forgets the previous one. This is fine for a playground; it would be annoying as a real UI.
- **No schema-aware form generation.** In principle we could fetch the `schema_uri` and render a form matching the schema. We wrote this as an experiment and it was too fiddly to ship — form UX for arbitrary JSON Schemas is a product in itself.

## What we'd do differently

Nothing, so far. The playground was originally going to be a React app with proper state management and a routing layer. We tried that first and threw it away after a day because it was taking longer to set up than the backend did to write. The three-file vanilla JS version (`api.js`, `app.js`, plus a bit of CSS) does everything we need and loads instantly.

The one pattern we will keep using: **have the backend expose a `/catalog` endpoint that the frontend reads on boot**. It means the frontend doesn't encode knowledge of the backend's command list, and adding commands never breaks the UI. This kept biting us every time we tried to ship a typed client.

## Risks

- **`sessionStorage` for the JWT is fine for a playground, not fine for anything else.** A real deployment should use httpOnly cookies. The playground deliberately avoids cookies so you can run it from `file://` during development, but nobody should copy this pattern to a production UI.
- **CORS is currently wide open** (`allow_origins=["*"]`) because the playground might run from a different port during development. Tighten this in any deployment.

## How you can extend it

If you want to add a UI for a specific command (say, you want a PDF-signing flow), just build a new HTML page that hits `/commands/signpdf` with the shape you need. The playground isn't opinionated — it lives in `frontend/html/` and anything next to it is served by the same nginx.

# codot is CQRS-URL Platform


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.3-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.30-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-2.0h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $0.3000 (2 commits)
- 👤 **Human dev:** ~$200 (2.0h @ $100/h, 30min dedup)

Generated on 2026-04-22 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---

Commands and Queries as **URL-addressable resources**. Operate on arbitrary data over pluggable protocols (`http://`, `https://`, `file://`, `data:`, …), with runtime JSON-Schema validation and policy-based access control — no DTOs, no codegen, no per-command type churn.

This is the reference implementation of the design discussed in the accompanying articles:

- CQRS decoupled from data models (bytes + Struct envelope)
- Command/Query as a URL resource (`PUT /commands/converttojson`)
- Required schemas at runtime (JSON Schema at `schema_uri`)
- Controlling who can do what on which URI (policy engine with URL globs)

## Quick start

```bash
# 1. Build and run everything
make build
make up

# 2. Issue a token (admin)
make token

# 3. Open the playground
#    → http://localhost:8000
#
#    Sign in with admin/admin, alice/alice (analyst), or bob/bob (user).
#    Hit one of the preset buttons: CSV → JSON, render posts, pipeline.

# 4. Smoke-test the API
make test
```

## Endpoints

| Method | Path                          | Purpose                                   |
|--------|-------------------------------|-------------------------------------------|
| GET    | `/health`                     | liveness probe                            |
| GET    | `/catalog`                    | public catalog of commands/queries/protocols |
| POST   | `/auth/token`                 | issue a dev JWT                           |
| GET    | `/auth/me`                    | current principal                         |
| GET    | `/commands`                   | list commands (auth)                      |
| PUT    | `/commands/{name}`            | run a command                             |
| GET    | `/queries`                    | list queries (auth)                       |
| POST   | `/queries/{name}`             | run a query                               |
| GET    | `/docs`                       | OpenAPI / Swagger UI                      |

## Bundled commands

| Name            | Purpose                                                                 |
|-----------------|-------------------------------------------------------------------------|
| `fetch`         | read a resource from any protocol and return its raw bytes (base64)    |
| `converttojson` | fetch + transform CSV/text/XML to JSON (+ optional schema validation)   |
| `converttoxml`  | fetch JSON/CSV and emit XML                                             |
| `converttocsv`  | fetch JSON list-of-objects and emit CSV                                 |
| `converttobase64` | base64-encode any resource (useful for PDFs, images)                  |
| `render`        | Jinja2 template → HTML page (data from URI or inline)                   |
| `pipeline`      | chain other commands; use `"$previous.output"` as a URI reference       |

Adding your own command is three steps: subclass `Command`, register it, optionally add a policy rule.

## Bundled queries

| Name         | Purpose                                                 |
|--------------|---------------------------------------------------------|
| `from-url`   | fetch one or more URIs and return them in a list        |
| `introspect` | list commands, queries, protocols                       |

## Protocols

| Scheme          | Notes                                                   |
|-----------------|---------------------------------------------------------|
| `http`, `https` | standard fetch via httpx, size-limited                  |
| `file://`       | local reads limited to `ALLOWED_LOCAL_ROOTS` (default: `/data`, `/schemas`) |
| `data:`         | RFC 2397 inline payloads, base64 or percent-encoded     |

Adding a new protocol (e.g. `s3://`, `ftp://`, `sqlite://`) is a matter of writing a class with a `scheme` attribute and an async `fetch(uri)` method, then registering it in `protocols/__init__.py`.

## Policy

Policies are loaded from `api/policy/rules.yaml` at startup. Each rule matches by role and lists glob patterns of allowed command/query names, URIs and schema URIs. Reload without rebuild: edit the file and restart the container (`make restart`).

Three built-in roles:

- **admin** — everything
- **analyst** — all commands/queries, all `http(s)://` and `file:///data`, `file:///schemas`
- **user** — only `fetch`, `converttojson`, `converttobase64`, `render` and public queries, only against `http://cqrs-data/*`, `https://public-*`, `file:///data/public/*`, `data:*`

See also: `api/policy/__init__.py` (the engine), `api/auth/__init__.py` (JWT issuance), `api/main.py` (enforcement point).

## Layout

```
.
├── api/                 FastAPI service
│   ├── commands/        one file per command
│   ├── queries/         one file per query
│   ├── protocols/       pluggable URI fetchers
│   ├── policy/          RBAC engine + rules.yaml
│   ├── validators/      JSON Schema over arbitrary URIs
│   ├── auth/            JWT issuance + FastAPI dependencies
│   ├── models.py        envelope (CommandRequest/Response)
│   ├── config.py        env-based settings
│   └── main.py          HTTP layer
├── frontend/            nginx + static playground (HTML/CSS/JS)
├── schemas/             JSON Schemas served at http://schemas/
├── sample-data/         demo data served at http://cqrs-data/
├── tests/
│   ├── smoke.sh         curl-based end-to-end tests
│   ├── test_policy.py   pytest unit tests
│   └── test_protocols.py
├── articles/            status articles (Markdown, for WordPress)
├── docker-compose.yml
└── Makefile
```

## Adding a command

1. Create `api/commands/my_thing.py`:

```python
from . import Command
from models import CommandRequest, CommandResponse

class MyThingCommand(Command):
    name = "mything"
    description = "Short sentence."
    input_hint = {"input_uri": "...", "meta.foo": "..."}

    async def execute(self, request: CommandRequest) -> CommandResponse:
        # ... do work, return CommandResponse(payload_b64=..., mime=..., meta=...)
```

2. Register it in `api/commands/__init__.py::register_default_commands`.
3. Optionally add an entry in `rules.yaml` if you want non-admins to call it.

That's the whole loop.

## Environment

Copy `.env.example` → `.env` and adjust. Key variables:

- `JWT_SECRET` — must be ≥ 32 chars in production
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default 60
- `ALLOWED_LOCAL_ROOTS` — comma list, default `/data,/schemas`
- `FETCH_MAX_BYTES` — size cap for fetched resources (default 50 MiB)

## License

Licensed under Apache-2.0.

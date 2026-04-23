# TODO

## Protocols & Fetch Layer
- [ ] Add `s3://` protocol (boto3, inject credentials at registry-construction time)
- [ ] Add `ftp://` / `sftp://` protocols (`aioftp` / `asyncssh`)
- [ ] Add `sqlite://` and `postgres://` protocols (return query result as JSON bytes)
- [ ] Add `redis://` and `kafka://` protocols once use-cases emerge
- [ ] Move from buffered to **streaming `FetchResult`** for resources > `FETCH_MAX_BYTES`

## Write-Side Commands
- [ ] Implement `store` command (persist bytes to URI-backed storage)
- [ ] Implement `publish` command (enqueue / notify)
- [ ] Implement `enqueue` command (push to a queue)
- [ ] Lock down policy engine for **mutating commands** before shipping writes

## Error & Observability
- [ ] Typed error taxonomy (`error_code` strings in JSON body) instead of generic 400/403/404
- [ ] Per-pipeline wall-clock budget / circuit breakers
- [ ] Pipeline trace retention on partial failure (today trace up to N-1 is lost on step N error)

## Agents & MCP
- [ ] Wire `memory_uri` to a real persistent store (Redis, Postgres, S3)
- [ ] Hook real LiteLLM / OpenAI backend for goal-driven agents that choose their own tools
- [ ] Integrate real-world MCP servers (filesystem, GitHub, databases)
- [ ] Swarm / branching: conditional steps and parallel agent execution in pipelines
- [ ] `$previous.field` selector (e.g. `$previous.meta.row_count`) instead of whole payload only

## Workflow Editor (Frontend)
- [ ] Backend endpoints: `POST /v1/workflows`, `GET /v1/workflows/:id`, `POST /v1/workflows/run`
- [ ] Node palette (Fetch, HTTP, Command, Render, Agent)
- [ ] Side-panel form for `schema_uri`, `mime_type`, `backend_config`
- [ ] Live validation: `input` must point to existing `id`

## Infra & Scaling
- [ ] Queue in front of long-running commands (stateless service is fine for 50 MB PDF, not for heavy ETL)
- [ ] Horizontal scaling story (load balancer + multiple API replicas)

## Testing
- [x] Fix `api/test_all_agents.py` strict-mode async decorators and absolute MCP server paths
- [ ] Add CI workflow that runs `pytest` + `make test` on every PR

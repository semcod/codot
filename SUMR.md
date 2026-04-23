# codot is CQRS-URL Platform

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Dependencies](#dependencies)
- [Call Graph](#call-graph)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `codot`
- **version**: `0.1.7`
- **python_requires**: `>=3.8`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Makefile, app.doql.less, goal.yaml, .env.example, docker-compose.yml, project/(5 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: codot;
  version: 0.1.7;
}

dependencies {
  runtime: "fastapi>=0.115.0, uvicorn[standard]>=0.32.0, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60, pydantic>=2.9.0, httpx>=0.27.0, PyJWT>=2.9.0, passlib>=1.7.4, jsonschema>=4.23.0, PyYAML>=6.0.2, jinja2>=3.1.4, python-multipart>=0.0.12, xmltodict>=0.13.0";
  dev: "pytest>=7.0.0, pytest-asyncio>=0.21.0, httpx>=0.27.0, goal>=2.1.0, costs>=0.1.20, pfix>=0.1.60";
}

entity[name="PipelineStep"] {
  command: string!;
  request: CommandRequest!;
  agent_node: AgentNode | None;
}

entity[name="AgentNode"] {
  id: string!;
  role: string!;
  goal: string!;
  tools: list[str]!;
  backend: AgentCommunicationBackend!;
  backend_config: dict[str, Any]!;
  memory_uri: str | None;
  input: str | None;
  inputs: list[str]!;
  description: str | None;
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

workflow[name="build"] {
  trigger: manual;
  step-1: run cmd=docker compose build;
}

workflow[name="up"] {
  trigger: manual;
  step-1: run cmd=docker compose up -d;
  step-2: run cmd=echo "";
  step-3: run cmd=echo "Stack is starting up:";
  step-4: run cmd=echo "  - Frontend:   http://localhost:18000";
  step-5: run cmd=echo "  - API:        http://localhost:18080";
  step-6: run cmd=echo "  - API docs:   http://localhost:18080/docs";
  step-7: run cmd=echo "  - Schemas:    http://localhost:18090";
  step-8: run cmd=echo "  - Sample data: http://localhost:18091";
}

workflow[name="down"] {
  trigger: manual;
  step-1: run cmd=docker compose down;
}

workflow[name="logs"] {
  trigger: manual;
  step-1: run cmd=docker compose logs -f api;
}

workflow[name="restart"] {
  trigger: manual;
  step-1: run cmd=docker compose up -d --build api;
}

workflow[name="token"] {
  trigger: manual;
  step-1: run cmd=curl -s -X POST http://localhost:18080/auth/token \;
  step-2: run cmd=-H "Content-Type: application/json" \;
  step-3: run cmd=-d '{"username":"admin","password":"admin"}' | python3 -m json.tool;
}

workflow[name="token-user"] {
  trigger: manual;
  step-1: run cmd=curl -s -X POST http://localhost:18080/auth/token \;
  step-2: run cmd=-H "Content-Type: application/json" \;
  step-3: run cmd=-d '{"username":"alice","password":"alice"}' | python3 -m json.tool;
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=bash tests/smoke.sh;
}

workflow[name="test-agent"] {
  trigger: manual;
  step-1: run cmd=cd api && python3 test_all_agents.py;
}

workflow[name="workflow"] {
  trigger: manual;
  step-1: run cmd=python3 codot_run.py examples/workflow_agent_mcp.json --url http://localhost:18080;
}

workflow[name="clean"] {
  trigger: manual;
  step-1: run cmd=docker compose down -v --remove-orphans;
}

deploy {
  target: docker-compose;
  compose_file: docker-compose.yml;
  ansible: true;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
  python_version: >=3.8;
}
```

## Workflows

## Dependencies

### Runtime

```text markpact:deps python
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
pydantic>=2.9.0
httpx>=0.27.0
PyJWT>=2.9.0
passlib>=1.7.4
jsonschema>=4.23.0
PyYAML>=6.0.2
jinja2>=3.1.4
python-multipart>=0.0.12
xmltodict>=0.13.0
```

### Development

```text markpact:deps python scope=dev
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.27.0
goal>=2.1.0
costs>=0.1.20
pfix>=0.1.60
```

## Call Graph

*95 nodes · 82 edges · 26 modules · CC̄=1.2*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `main` *(in codot_run)* | 10 ⚠ | 0 | 33 | **33** |
| `execute` *(in api.commands.pipeline.PipelineCommand)* | 13 ⚠ | 0 | 31 | **31** |
| `cmd_compile` *(in service-factory.factory.cli)* | 9 | 0 | 24 | **24** |
| `fetchPreview` *(in cqrs-workflow-editor.src.App)* | 13 ⚠ | 1 | 14 | **15** |
| `_schema_object` *(in service-factory.factory.generators.code.node_fastify)* | 8 | 2 | 13 | **15** |
| `register_default_commands` *(in api.commands)* | 1 | 0 | 15 | **15** |
| `validate_against_schema_uri` *(in api.validators)* | 7 | 1 | 13 | **14** |
| `API` *(in frontend.html.js.api)* | 9 | 0 | 14 | **14** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/codot
# nodes: 95 | edges: 82 | modules: 26
# CC̄=1.2

HUBS[20]:
  codot_run.main
    CC=10  in:0  out:33  total:33
  api.commands.pipeline.PipelineCommand.execute
    CC=13  in:0  out:31  total:31
  service-factory.factory.cli.cmd_compile
    CC=9  in:0  out:24  total:24
  cqrs-workflow-editor.src.App.fetchPreview
    CC=13  in:1  out:14  total:15
  service-factory.factory.generators.code.node_fastify._schema_object
    CC=8  in:2  out:13  total:15
  api.commands.register_default_commands
    CC=1  in:0  out:15  total:15
  api.validators.validate_against_schema_uri
    CC=7  in:1  out:13  total:14
  frontend.html.js.api.API
    CC=9  in:0  out:14  total:14
  service-factory.factory.generators.infra.docker.DockerGenerator._compose
    CC=3  in:0  out:14  total:14
  service-factory.factory.generators.code.python_fastapi._pydantic_model
    CC=5  in:3  out:11  total:14
  frontend.html.js.api.request
    CC=9  in:6  out:8  total:14
  api.queries.from_url.FromUrlQuery.execute
    CC=9  in:0  out:13  total:13
  service-factory.factory.register_default_generators
    CC=1  in:2  out:11  total:13
  service-factory.factory.get_registry
    CC=1  in:12  out:0  total:12
  api.main.execute_command
    CC=3  in:0  out:11  total:11
  cqrs-workflow-editor.src.App.loadExampleFile
    CC=3  in:0  out:11  total:11
  service-factory.factory.generators.code.python_fastapi._query_route
    CC=7  in:1  out:10  total:11
  cqrs-workflow-editor.src.App.loadBackendWorkflow
    CC=3  in:0  out:11  total:11
  service-factory.factory.generators.wire.openapi._schema_from_fields
    CC=7  in:3  out:7  total:10
  api.commands.converttobase64.ConvertToBase64Command.execute
    CC=2  in:0  out:10  total:10

MODULES:
  api.agent  [1 funcs]
    execute_agent  CC=2  out:3
  api.auth  [2 funcs]
    authenticate  CC=3  out:1
    get_jwt_manager  CC=1  out:0
  api.commands  [2 funcs]
    get_registry  CC=1  out:0
    register_default_commands  CC=1  out:15
  api.commands.converttobase64  [1 funcs]
    execute  CC=2  out:10
  api.commands.converttojson  [1 funcs]
    _convert  CC=8  out:8
  api.commands.fetch  [1 funcs]
    execute  CC=2  out:7
  api.commands.pipeline  [3 funcs]
    execute  CC=13  out:31
    _substitute  CC=8  out:7
    _to_data_uri  CC=3  out:0
  api.main  [5 funcs]
    execute_command  CC=3  out:11
    execute_query  CC=3  out:9
    execute_query_get  CC=1  out:5
    issue_token  CC=2  out:6
    run_agent  CC=2  out:7
  api.policy  [1 funcs]
    get_engine  CC=2  out:1
  api.protocols  [2 funcs]
    get_registry  CC=1  out:0
    register_default_protocols  CC=1  out:9
  api.queries  [2 funcs]
    get_registry  CC=1  out:0
    register_default_queries  CC=1  out:5
  api.queries.from_url  [1 funcs]
    execute  CC=9  out:13
  api.validators  [1 funcs]
    validate_against_schema_uri  CC=7  out:13
  codot_run  [3 funcs]
    _get_token  CC=1  out:3
    main  CC=10  out:33
    run_agent  CC=1  out:7
  cqrs-backend-workflows.server  [7 funcs]
    _handle_command  CC=5  out:3
    _handle_render  CC=3  out:3
    _result_to_data_uri  CC=2  out:2
    create_workflow  CC=2  out:5
    list_workflows  CC=1  out:3
    update_workflow  CC=2  out:4
    validate_workflow  CC=2  out:2
  cqrs-workflow-editor.src.App  [21 funcs]
    blob  CC=1  out:2
    exportWorkflow  CC=1  out:4
    fetchBackendWorkflows  CC=4  out:5
    fetchExampleFiles  CC=4  out:5
    fetchPreview  CC=13  out:14
    file  CC=2  out:8
    json  CC=1  out:1
    loadBackendWorkflow  CC=3  out:11
    loadExampleFile  CC=3  out:11
    loadPredefinedWorkflow  CC=2  out:7
  frontend.html.js.api  [10 funcs]
    API  CC=9  out:14
    catalog  CC=1  out:1
    data  CC=1  out:1
    getToken  CC=1  out:1
    login  CC=1  out:3
    request  CC=9  out:8
    runCommand  CC=1  out:1
    runQuery  CC=1  out:1
    setRole  CC=1  out:1
    setToken  CC=1  out:1
  frontend.html.js.app  [2 funcs]
    decodeB64  CC=3  out:3
    renderDecoded  CC=9  out:10
  mcp_servers.summary_server  [3 funcs]
    _handle  CC=8  out:7
    _send  CC=1  out:3
    main  CC=5  out:5
  service-factory.factory  [3 funcs]
    list  CC=2  out:1
    get_registry  CC=1  out:0
    register_default_generators  CC=1  out:11
  service-factory.factory.cli  [2 funcs]
    cmd_compile  CC=9  out:24
    cmd_list  CC=2  out:5
  service-factory.factory.generators.code.node_fastify  [6 funcs]
    _server  CC=3  out:5
    _ts_interface  CC=3  out:8
    _camel  CC=2  out:1
    _command_route_lines  CC=2  out:4
    _query_route_lines  CC=3  out:2
    _schema_object  CC=8  out:13
  service-factory.factory.generators.code.python_fastapi  [7 funcs]
    _events  CC=2  out:4
    _models  CC=4  out:7
    _command_route  CC=6  out:6
    _event_model  CC=1  out:1
    _pydantic_model  CC=5  out:11
    _query_route  CC=7  out:10
    _snake  CC=4  out:6
  service-factory.factory.generators.infra.docker  [2 funcs]
    _compose  CC=3  out:14
    _indent_block  CC=3  out:2
  service-factory.factory.generators.types  [3 funcs]
    openapi_type  CC=2  out:2
    py_type  CC=2  out:1
    ts_type  CC=2  out:1
  service-factory.factory.generators.wire.openapi  [3 funcs]
    generate  CC=6  out:6
    _path_item  CC=10  out:8
    _schema_from_fields  CC=7  out:7

EDGES:
  codot_run.main → codot_run._get_token
  codot_run.main → codot_run.run_agent
  frontend.html.js.api.API → frontend.html.js.api.getToken
  frontend.html.js.api.request → frontend.html.js.api.getToken
  frontend.html.js.api.login → frontend.html.js.api.request
  frontend.html.js.api.login → frontend.html.js.api.setToken
  frontend.html.js.api.login → frontend.html.js.api.setRole
  frontend.html.js.api.data → frontend.html.js.api.request
  frontend.html.js.api.catalog → frontend.html.js.api.request
  frontend.html.js.api.runCommand → frontend.html.js.api.request
  frontend.html.js.api.runQuery → frontend.html.js.api.request
  frontend.html.js.app.renderDecoded → frontend.html.js.app.decodeB64
  service-factory.factory.cli.cmd_compile → service-factory.factory.register_default_generators
  service-factory.factory.cli.cmd_compile → service-factory.factory.get_registry
  service-factory.factory.cli.cmd_list → service-factory.factory.register_default_generators
  service-factory.factory.cli.cmd_list → service-factory.factory.get_registry
  service-factory.factory.register_default_generators → service-factory.factory.get_registry
  service-factory.factory.generators.infra.docker.DockerGenerator._compose → service-factory.factory.generators.infra.docker._indent_block
  service-factory.factory.generators.wire.openapi._schema_from_fields → service-factory.factory.generators.types.openapi_type
  service-factory.factory.generators.wire.openapi._path_item → service-factory.factory.generators.types.openapi_type
  service-factory.factory.generators.wire.openapi.OpenApiGenerator.generate → service-factory.factory.generators.wire.openapi._schema_from_fields
  service-factory.factory.generators.wire.openapi.OpenApiGenerator.generate → service-factory.factory.generators.wire.openapi._path_item
  service-factory.factory.generators.code.node_fastify._command_route_lines → service-factory.factory.generators.code.node_fastify._schema_object
  service-factory.factory.generators.code.node_fastify._command_route_lines → service-factory.factory.generators.code.node_fastify._camel
  service-factory.factory.generators.code.node_fastify._query_route_lines → service-factory.factory.generators.code.node_fastify._camel
  service-factory.factory.generators.code.node_fastify.NodeFastifyGenerator._server → service-factory.factory.generators.code.node_fastify._command_route_lines
  service-factory.factory.generators.code.node_fastify.NodeFastifyGenerator._server → service-factory.factory.generators.code.node_fastify._query_route_lines
  service-factory.factory.generators.code.node_fastify.NodeFastifyGenerator._ts_interface → service-factory.factory.generators.types.ts_type
  service-factory.factory.generators.code.python_fastapi._pydantic_model → service-factory.factory.generators.types.py_type
  service-factory.factory.generators.code.python_fastapi._command_route → service-factory.factory.generators.code.python_fastapi._snake
  service-factory.factory.generators.code.python_fastapi._query_route → service-factory.factory.generators.code.python_fastapi._snake
  service-factory.factory.generators.code.python_fastapi._query_route → service-factory.factory.generators.types.py_type
  service-factory.factory.generators.code.python_fastapi._event_model → service-factory.factory.generators.code.python_fastapi._pydantic_model
  service-factory.factory.generators.code.python_fastapi.PythonFastApiGenerator._models → service-factory.factory.generators.code.python_fastapi._pydantic_model
  service-factory.factory.generators.code.python_fastapi.PythonFastApiGenerator._events → service-factory.factory.generators.code.python_fastapi._event_model
  mcp_servers.summary_server.main → mcp_servers.summary_server._handle
  mcp_servers.summary_server.main → mcp_servers.summary_server._send
  cqrs-backend-workflows.server._handle_command → cqrs-backend-workflows.server._result_to_data_uri
  cqrs-backend-workflows.server._handle_render → cqrs-backend-workflows.server._result_to_data_uri
  cqrs-backend-workflows.server.list_workflows → service-factory.factory.GeneratorRegistry.list
  cqrs-backend-workflows.server.create_workflow → cqrs-backend-workflows.server.validate_workflow
  cqrs-backend-workflows.server.update_workflow → cqrs-backend-workflows.server.validate_workflow
  api.main.issue_token → api.auth.authenticate
  api.main.issue_token → api.auth.get_jwt_manager
  api.main.execute_command → api.policy.get_engine
  api.main.execute_query → api.policy.get_engine
  api.main.execute_query_get → api.main.execute_query
  api.main.run_agent → api.agent.execute_agent
  api.main.run_agent → api.policy.get_engine
  api.commands.fetch.FetchCommand.execute → service-factory.factory.get_registry
```

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/codot
# nodes: 95 | edges: 82 | modules: 26
# CC̄=1.2

HUBS[20]:
  codot_run.main
    CC=10  in:0  out:33  total:33
  api.commands.pipeline.PipelineCommand.execute
    CC=13  in:0  out:31  total:31
  service-factory.factory.cli.cmd_compile
    CC=9  in:0  out:24  total:24
  cqrs-workflow-editor.src.App.fetchPreview
    CC=13  in:1  out:14  total:15
  service-factory.factory.generators.code.node_fastify._schema_object
    CC=8  in:2  out:13  total:15
  api.commands.register_default_commands
    CC=1  in:0  out:15  total:15
  api.validators.validate_against_schema_uri
    CC=7  in:1  out:13  total:14
  frontend.html.js.api.API
    CC=9  in:0  out:14  total:14
  service-factory.factory.generators.infra.docker.DockerGenerator._compose
    CC=3  in:0  out:14  total:14
  service-factory.factory.generators.code.python_fastapi._pydantic_model
    CC=5  in:3  out:11  total:14
  frontend.html.js.api.request
    CC=9  in:6  out:8  total:14
  api.queries.from_url.FromUrlQuery.execute
    CC=9  in:0  out:13  total:13
  service-factory.factory.register_default_generators
    CC=1  in:2  out:11  total:13
  service-factory.factory.get_registry
    CC=1  in:12  out:0  total:12
  api.main.execute_command
    CC=3  in:0  out:11  total:11
  cqrs-workflow-editor.src.App.loadExampleFile
    CC=3  in:0  out:11  total:11
  service-factory.factory.generators.code.python_fastapi._query_route
    CC=7  in:1  out:10  total:11
  cqrs-workflow-editor.src.App.loadBackendWorkflow
    CC=3  in:0  out:11  total:11
  service-factory.factory.generators.wire.openapi._schema_from_fields
    CC=7  in:3  out:7  total:10
  api.commands.converttobase64.ConvertToBase64Command.execute
    CC=2  in:0  out:10  total:10

MODULES:
  api.agent  [1 funcs]
    execute_agent  CC=2  out:3
  api.auth  [2 funcs]
    authenticate  CC=3  out:1
    get_jwt_manager  CC=1  out:0
  api.commands  [2 funcs]
    get_registry  CC=1  out:0
    register_default_commands  CC=1  out:15
  api.commands.converttobase64  [1 funcs]
    execute  CC=2  out:10
  api.commands.converttojson  [1 funcs]
    _convert  CC=8  out:8
  api.commands.fetch  [1 funcs]
    execute  CC=2  out:7
  api.commands.pipeline  [3 funcs]
    execute  CC=13  out:31
    _substitute  CC=8  out:7
    _to_data_uri  CC=3  out:0
  api.main  [5 funcs]
    execute_command  CC=3  out:11
    execute_query  CC=3  out:9
    execute_query_get  CC=1  out:5
    issue_token  CC=2  out:6
    run_agent  CC=2  out:7
  api.policy  [1 funcs]
    get_engine  CC=2  out:1
  api.protocols  [2 funcs]
    get_registry  CC=1  out:0
    register_default_protocols  CC=1  out:9
  api.queries  [2 funcs]
    get_registry  CC=1  out:0
    register_default_queries  CC=1  out:5
  api.queries.from_url  [1 funcs]
    execute  CC=9  out:13
  api.validators  [1 funcs]
    validate_against_schema_uri  CC=7  out:13
  codot_run  [3 funcs]
    _get_token  CC=1  out:3
    main  CC=10  out:33
    run_agent  CC=1  out:7
  cqrs-backend-workflows.server  [7 funcs]
    _handle_command  CC=5  out:3
    _handle_render  CC=3  out:3
    _result_to_data_uri  CC=2  out:2
    create_workflow  CC=2  out:5
    list_workflows  CC=1  out:3
    update_workflow  CC=2  out:4
    validate_workflow  CC=2  out:2
  cqrs-workflow-editor.src.App  [21 funcs]
    blob  CC=1  out:2
    exportWorkflow  CC=1  out:4
    fetchBackendWorkflows  CC=4  out:5
    fetchExampleFiles  CC=4  out:5
    fetchPreview  CC=13  out:14
    file  CC=2  out:8
    json  CC=1  out:1
    loadBackendWorkflow  CC=3  out:11
    loadExampleFile  CC=3  out:11
    loadPredefinedWorkflow  CC=2  out:7
  frontend.html.js.api  [10 funcs]
    API  CC=9  out:14
    catalog  CC=1  out:1
    data  CC=1  out:1
    getToken  CC=1  out:1
    login  CC=1  out:3
    request  CC=9  out:8
    runCommand  CC=1  out:1
    runQuery  CC=1  out:1
    setRole  CC=1  out:1
    setToken  CC=1  out:1
  frontend.html.js.app  [2 funcs]
    decodeB64  CC=3  out:3
    renderDecoded  CC=9  out:10
  mcp_servers.summary_server  [3 funcs]
    _handle  CC=8  out:7
    _send  CC=1  out:3
    main  CC=5  out:5
  service-factory.factory  [3 funcs]
    list  CC=2  out:1
    get_registry  CC=1  out:0
    register_default_generators  CC=1  out:11
  service-factory.factory.cli  [2 funcs]
    cmd_compile  CC=9  out:24
    cmd_list  CC=2  out:5
  service-factory.factory.generators.code.node_fastify  [6 funcs]
    _server  CC=3  out:5
    _ts_interface  CC=3  out:8
    _camel  CC=2  out:1
    _command_route_lines  CC=2  out:4
    _query_route_lines  CC=3  out:2
    _schema_object  CC=8  out:13
  service-factory.factory.generators.code.python_fastapi  [7 funcs]
    _events  CC=2  out:4
    _models  CC=4  out:7
    _command_route  CC=6  out:6
    _event_model  CC=1  out:1
    _pydantic_model  CC=5  out:11
    _query_route  CC=7  out:10
    _snake  CC=4  out:6
  service-factory.factory.generators.infra.docker  [2 funcs]
    _compose  CC=3  out:14
    _indent_block  CC=3  out:2
  service-factory.factory.generators.types  [3 funcs]
    openapi_type  CC=2  out:2
    py_type  CC=2  out:1
    ts_type  CC=2  out:1
  service-factory.factory.generators.wire.openapi  [3 funcs]
    generate  CC=6  out:6
    _path_item  CC=10  out:8
    _schema_from_fields  CC=7  out:7

EDGES:
  codot_run.main → codot_run._get_token
  codot_run.main → codot_run.run_agent
  frontend.html.js.api.API → frontend.html.js.api.getToken
  frontend.html.js.api.request → frontend.html.js.api.getToken
  frontend.html.js.api.login → frontend.html.js.api.request
  frontend.html.js.api.login → frontend.html.js.api.setToken
  frontend.html.js.api.login → frontend.html.js.api.setRole
  frontend.html.js.api.data → frontend.html.js.api.request
  frontend.html.js.api.catalog → frontend.html.js.api.request
  frontend.html.js.api.runCommand → frontend.html.js.api.request
  frontend.html.js.api.runQuery → frontend.html.js.api.request
  frontend.html.js.app.renderDecoded → frontend.html.js.app.decodeB64
  service-factory.factory.cli.cmd_compile → service-factory.factory.register_default_generators
  service-factory.factory.cli.cmd_compile → service-factory.factory.get_registry
  service-factory.factory.cli.cmd_list → service-factory.factory.register_default_generators
  service-factory.factory.cli.cmd_list → service-factory.factory.get_registry
  service-factory.factory.register_default_generators → service-factory.factory.get_registry
  service-factory.factory.generators.infra.docker.DockerGenerator._compose → service-factory.factory.generators.infra.docker._indent_block
  service-factory.factory.generators.wire.openapi._schema_from_fields → service-factory.factory.generators.types.openapi_type
  service-factory.factory.generators.wire.openapi._path_item → service-factory.factory.generators.types.openapi_type
  service-factory.factory.generators.wire.openapi.OpenApiGenerator.generate → service-factory.factory.generators.wire.openapi._schema_from_fields
  service-factory.factory.generators.wire.openapi.OpenApiGenerator.generate → service-factory.factory.generators.wire.openapi._path_item
  service-factory.factory.generators.code.node_fastify._command_route_lines → service-factory.factory.generators.code.node_fastify._schema_object
  service-factory.factory.generators.code.node_fastify._command_route_lines → service-factory.factory.generators.code.node_fastify._camel
  service-factory.factory.generators.code.node_fastify._query_route_lines → service-factory.factory.generators.code.node_fastify._camel
  service-factory.factory.generators.code.node_fastify.NodeFastifyGenerator._server → service-factory.factory.generators.code.node_fastify._command_route_lines
  service-factory.factory.generators.code.node_fastify.NodeFastifyGenerator._server → service-factory.factory.generators.code.node_fastify._query_route_lines
  service-factory.factory.generators.code.node_fastify.NodeFastifyGenerator._ts_interface → service-factory.factory.generators.types.ts_type
  service-factory.factory.generators.code.python_fastapi._pydantic_model → service-factory.factory.generators.types.py_type
  service-factory.factory.generators.code.python_fastapi._command_route → service-factory.factory.generators.code.python_fastapi._snake
  service-factory.factory.generators.code.python_fastapi._query_route → service-factory.factory.generators.code.python_fastapi._snake
  service-factory.factory.generators.code.python_fastapi._query_route → service-factory.factory.generators.types.py_type
  service-factory.factory.generators.code.python_fastapi._event_model → service-factory.factory.generators.code.python_fastapi._pydantic_model
  service-factory.factory.generators.code.python_fastapi.PythonFastApiGenerator._models → service-factory.factory.generators.code.python_fastapi._pydantic_model
  service-factory.factory.generators.code.python_fastapi.PythonFastApiGenerator._events → service-factory.factory.generators.code.python_fastapi._event_model
  mcp_servers.summary_server.main → mcp_servers.summary_server._handle
  mcp_servers.summary_server.main → mcp_servers.summary_server._send
  cqrs-backend-workflows.server._handle_command → cqrs-backend-workflows.server._result_to_data_uri
  cqrs-backend-workflows.server._handle_render → cqrs-backend-workflows.server._result_to_data_uri
  cqrs-backend-workflows.server.list_workflows → service-factory.factory.GeneratorRegistry.list
  cqrs-backend-workflows.server.create_workflow → cqrs-backend-workflows.server.validate_workflow
  cqrs-backend-workflows.server.update_workflow → cqrs-backend-workflows.server.validate_workflow
  api.main.issue_token → api.auth.authenticate
  api.main.issue_token → api.auth.get_jwt_manager
  api.main.execute_command → api.policy.get_engine
  api.main.execute_query → api.policy.get_engine
  api.main.execute_query_get → api.main.execute_query
  api.main.run_agent → api.agent.execute_agent
  api.main.run_agent → api.policy.get_engine
  api.commands.fetch.FetchCommand.execute → service-factory.factory.get_registry
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 128f 16546L | python:36,md:27,json:23,yaml:13,shell:7,txt:4,typescript:3,yml:2,conf:2,javascript:2,toml:1,ini:1,cfg:1 | 2026-04-23
# CC̄=1.2 | critical:0/603 | dups:0 | cycles:0

HEALTH[0]: ok

REFACTOR[0]: none needed

PIPELINES[174]:
  [1] Src [main]: main → _get_token
      PURITY: 100% pure
  [2] Src [API]: API → getToken
      PURITY: 100% pure
  [3] Src [clearToken]: clearToken
      PURITY: 100% pure
  [4] Src [getRole]: getRole
      PURITY: 100% pure
  [5] Src [resp]: resp
      PURITY: 100% pure

LAYERS:
  mcp_servers/                    CC̄=4.7    ←in:0  →out:0
  │ summary_server             109L  0C    3m  CC=8      ←0
  │
  service-factory/                CC̄=2.8    ←in:18  →out:0
  │ __init__                   237L  8C    5m  CC=6      ←0
  │ docker                     207L  1C   12m  CC=3      ←0
  │ python_fastapi             206L  1C   10m  CC=9      ←0
  │ README.md                  201L  1C    1m  CC=0.0    ←0
  │ node_fastify               165L  1C    9m  CC=8      ←0
  │ openapi                    124L  1C    3m  CC=10     ←0
  │ kubernetes                 109L  1C    4m  CC=1      ←0
  │ cli                        105L  0C    4m  CC=9      ←0
  │ 01-service-factory-status.md    84L  1C    1m  CC=0.0    ←0
  │ __init__                    72L  2C    8m  CC=3      ←10
  │ types                       54L  0C    3m  CC=2      ←3
  │ connect-test-service.bundle.json    47L  0C    0m  CC=0.0    ←0
  │ CompleteProtocol.command.json    43L  0C    0m  CC=0.0    ←0
  │ connect-test-service-node.bundle.json    39L  0C    0m  CC=0.0    ←0
  │ DemoLogin.command.json      30L  0C    0m  CC=0.0    ←0
  │ DeviceCreated.event.json    23L  0C    0m  CC=0.0    ←0
  │ DeviceUpdated.event.json    22L  0C    0m  CC=0.0    ←0
  │ pytest.ini                   6L  0C    0m  CC=0.0    ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  frontend/                       CC̄=2.5    ←in:0  →out:0
  │ app.js                     187L  0C   15m  CC=9      ←0
  │ SUMD.md                    160L  0C    0m  CC=0.0    ←0
  │ SUMR.md                     98L  0C    0m  CC=0.0    ←0
  │ sumd.json                   84L  0C    0m  CC=0.0    ←0
  │ api.js                      61L  0C   15m  CC=9      ←0
  │ package.json                28L  0C    0m  CC=0.0    ←0
  │ nginx.conf                  17L  0C    0m  CC=0.0    ←0
  │ map.toon.yaml               13L  0C    0m  CC=0.0    ←0
  │ Dockerfile                   0L  0C    0m  CC=0.0    ←0
  │
  cqrs-workflow-editor/           CC̄=2.3    ←in:0  →out:0
  │ !! App.tsx                    827L  0C   44m  CC=13     ←0
  │ SUMD.md                    179L  0C    0m  CC=0.0    ←0
  │ SUMR.md                    116L  0C    0m  CC=0.0    ←0
  │ README.md                   92L  0C    0m  CC=0.0    ←0
  │ vite.config.ts              41L  0C    0m  CC=0.0    ←0
  │ tsconfig.json               26L  0C    0m  CC=0.0    ←0
  │ package.json                25L  0C    0m  CC=0.0    ←0
  │ nginx.conf                  21L  0C    0m  CC=0.0    ←0
  │ main.tsx                    11L  0C    1m  CC=1      ←0
  │ map.toon.yaml               11L  0C    0m  CC=0.0    ←0
  │ Dockerfile                   0L  0C    0m  CC=0.0    ←0
  │
  api/                            CC̄=1.6    ←in:2  →out:2
  │ agent                      362L  0C    7m  CC=10     ←2
  │ SUMD.md                    334L  0C   42m  CC=0.0    ←0
  │ main                       234L  0C   15m  CC=3      ←0
  │ map.toon.yaml              174L  0C   42m  CC=0.0    ←0
  │ mcp_client                 173L  4C   15m  CC=7      ←0
  │ __init__                   149L  3C   11m  CC=8      ←1
  │ models                     125L  13C    0m  CC=0.0    ←0
  │ pipeline                   111L  1C    3m  CC=13     ←0
  │ __init__                   102L  1C    6m  CC=3      ←1
  │ SUMR.md                     98L  0C    0m  CC=0.0    ←0
  │ render                      97L  1C    1m  CC=6      ←0
  │ sumd.json                   90L  0C    0m  CC=0.0    ←0
  │ __init__                    80L  2C    7m  CC=2      ←0
  │ converttojson               80L  1C    3m  CC=8      ←0
  │ __init__                    69L  3C    7m  CC=3      ←0
  │ rules.yaml                  66L  0C    0m  CC=0.0    ←0
  │ converttocsv                60L  1C    1m  CC=13     ←0
  │ __init__                    56L  2C    7m  CC=2      ←0
  │ converttoxml                51L  1C    1m  CC=9      ←0
  │ file_protocol               51L  1C    2m  CC=10     ←0
  │ __init__                    48L  1C    2m  CC=7      ←1
  │ from_url                    45L  1C    1m  CC=9      ←0
  │ data_protocol               40L  1C    1m  CC=9      ←0
  │ config                      34L  1C    1m  CC=3      ←0
  │ converttobase64             34L  1C    1m  CC=2      ←0
  │ http_protocol               33L  1C    2m  CC=2      ←0
  │ fetch                       27L  1C    1m  CC=2      ←0
  │ introspect                  22L  1C    1m  CC=1      ←0
  │ requirements.txt            11L  0C    0m  CC=0.0    ←0
  │ Dockerfile                   0L  0C    0m  CC=0.0    ←0
  │
  cqrs-backend-workflows/         CC̄=0.8    ←in:0  →out:1
  │ server                     400L  5C   18m  CC=8      ←0
  │ SUMD.md                    205L  0C   20m  CC=0.0    ←0
  │ README.md                  135L  0C    0m  CC=0.0    ←0
  │ SUMR.md                     98L  0C    0m  CC=0.0    ←0
  │ sumd.json                   96L  0C    0m  CC=0.0    ←0
  │ workflow.schema.json        69L  0C    0m  CC=0.0    ←0
  │ 04-agent-research-pipeline.json    46L  0C    0m  CC=0.0    ←0
  │ map.toon.yaml               40L  0C   20m  CC=0.0    ←0
  │ 01-products-csv-to-html.json    36L  0C    0m  CC=0.0    ←0
  │ 02-posts-json-feed.json     36L  0C    0m  CC=0.0    ←0
  │ example-workflow.json       35L  0C    0m  CC=0.0    ←0
  │ 03-api-health-monitor.json    35L  0C    0m  CC=0.0    ←0
  │ requirements.txt             5L  0C    0m  CC=0.0    ←0
  │ Makefile                     0L  0C    0m  CC=0.0    ←0
  │ Dockerfile                   0L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=0.2    ←in:0  →out:0
  │ !! SUMR.md                    908L  0C    0m  CC=0.0    ←0
  │ !! SUMD.md                    820L  0C  111m  CC=0.0    ←0
  │ !! goal.yaml                  512L  0C    0m  CC=0.0    ←0
  │ README.md                  198L  1C    0m  CC=0.0    ←0
  │ CHANGELOG.md               187L  0C    0m  CC=0.0    ←0
  │ codot_run                  147L  0C    4m  CC=10     ←0
  │ pyproject.toml              94L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          89L  0C    0m  CC=0.0    ←0
  │ project.sh                  40L  0C    0m  CC=0.0    ←0
  │ Makefile                     0L  0C    0m  CC=0.0    ←0
  │
  docs/                           CC̄=0.0    ←in:0  →out:0
  │ !! 04-workflow-editor-spec.md   573L  3C    1m  CC=0.0    ←0
  │ 02-market-comparison.md    276L  0C    0m  CC=0.0    ←0
  │ 03-multi-agent-architecture.md   205L  4C    0m  CC=0.0    ←0
  │ 01-cqrs-url-platform-status.md    98L  0C    0m  CC=0.0    ←0
  │ 05-pipeline-composition-status.md    63L  0C    0m  CC=0.0    ←0
  │ 03-policy-engine-status.md    58L  0C    0m  CC=0.0    ←0
  │ 02-protocol-registry-status.md    55L  1C    0m  CC=0.0    ←0
  │ 04-frontend-playground-status.md    45L  0C    0m  CC=0.0    ←0
  │
  project/                        CC̄=0.0    ←in:0  →out:0
  │ !! calls.yaml                1600L  0C    0m  CC=0.0    ←0
  │ !! context.md                 522L  0C    0m  CC=0.0    ←0
  │ map.toon.yaml              345L  0C  111m  CC=0.0    ←0
  │ README.md                  339L  0C    0m  CC=0.0    ←0
  │ calls.toon.yaml            211L  0C    0m  CC=0.0    ←0
  │ analysis.toon.yaml         199L  0C    0m  CC=0.0    ←0
  │ project.toon.yaml           51L  0C    0m  CC=0.0    ←0
  │ prompt.txt                  47L  0C    0m  CC=0.0    ←0
  │ evolution.toon.yaml         39L  0C    0m  CC=0.0    ←0
  │ duplication.toon.yaml       29L  0C    0m  CC=0.0    ←0
  │
  schemas/                        CC̄=0.0    ←in:0  →out:0
  │ public-products.json        23L  0C    0m  CC=0.0    ←0
  │ public-posts.json           16L  0C    0m  CC=0.0    ←0
  │
  examples/                       CC̄=0.0    ←in:0  →out:0
  │ 04-pipeline.sh             124L  0C    0m  CC=0.0    ←0
  │ README.md                  122L  0C    0m  CC=0.0    ←0
  │ 06-rbac.sh                  66L  0C    0m  CC=0.0    ←0
  │ 05-query.sh                 51L  0C    0m  CC=0.0    ←0
  │ 01-fetch.sh                 48L  0C    0m  CC=0.0    ←0
  │ 02-convert-to-json.sh       48L  0C    0m  CC=0.0    ←0
  │ 03-render-html.sh           40L  0C    0m  CC=0.0    ←0
  │ workflow_agent_mcp.json     29L  0C    0m  CC=0.0    ←0
  │ agent_mcp.json              13L  0C    0m  CC=0.0    ←0
  │
  sample-data/                    CC̄=0.0    ←in:0  →out:0
  │ doc.txt                      6L  0C    0m  CC=0.0    ←0
  │ posts.json                   5L  0C    0m  CC=0.0    ←0
  │
  ansible/                        CC̄=0.0    ←in:0  →out:0
  │ test-services.yml          229L  0C    0m  CC=0.0    ←0
  │ ansible.cfg                  4L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     Makefile                                  0L
     api/Dockerfile                            0L
     cqrs-backend-workflows/Dockerfile         0L
     cqrs-backend-workflows/Makefile           0L
     cqrs-workflow-editor/Dockerfile           0L
     frontend/Dockerfile                       0L
     service-factory/factory/generators/__init__.py  0L

COUPLING:
                                   service-factory             api.commands                      api  service-factory.factory              api.queries   cqrs-backend-workflows
          service-factory                       ──                      ←10                       ←2                       ←4                       ←1                       ←1  hub
             api.commands                       10                       ──                        2                                                                             !! fan-out
                      api                        2                       ←2                       ──                                                                           
  service-factory.factory                        4                                                                         ──                                                  
              api.queries                        1                                                                                                  ──                         
   cqrs-backend-workflows                        1                                                                                                                           ──
  CYCLES: none
  HUB: service-factory/ (fan-in=18)
  SMELL: api.commands/ fan-out=12 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 1 groups | 38f 3812L | 2026-04-23

SUMMARY:
  files_scanned: 38
  total_lines:   3812
  dup_groups:    1
  dup_fragments: 2
  saved_lines:   3
  scan_ms:       8760

HOTSPOTS[1] (files with most duplication):
  service-factory/factory/generators/types.py  dup=6L  groups=1  frags=2  (0.2%)

DUPLICATES[1] (ranked by impact):
  [65816a4a09f45ef7]   STRU  py_type  L=3 N=2 saved=3 sim=1.00
      service-factory/factory/generators/types.py:40-42  (py_type)
      service-factory/factory/generators/types.py:45-47  (ts_type)

REFACTOR[1] (ranked by priority):
  [1] ○ extract_function   → service-factory/factory/generators/utils/py_type.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: service-factory/factory/generators/types.py

EFFORT_ESTIMATE (total ≈ 0.1h):
  easy   py_type                             saved=3L  ~6min

METRICS-TARGET:
  dup_groups:  1 → 0
  saved_lines: 3 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 603 func | 47f | 2026-04-23

NEXT[0]: no refactoring needed

RISKS[0]: none

METRICS-TARGET:
  CC̄:          1.2 → ≤0.8
  max-CC:      13 → ≤6
  god-modules: 0 → 0
  high-CC(≥15): 0 → ≤0
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=1.2 → now CC̄=1.2
```

## Intent

CQRS-URL Platform - Commands and Queries as URL-addressable resources

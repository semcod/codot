# codot is CQRS-URL Platform

CQRS-URL Platform - Commands and Queries as URL-addressable resources

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Environment Variables (`.env.example`)](#environment-variables-envexample)
- [Release Management (`goal.yaml`)](#release-management-goalyaml)
- [Makefile Targets](#makefile-targets)
- [Code Analysis](#code-analysis)
- [Call Graph](#call-graph)
- [Intent](#intent)

## Metadata

- **name**: `codot`
- **version**: `0.1.4`
- **python_requires**: `>=3.8`
- **license**: Apache-2.0
- **ai_model**: `openrouter/qwen/qwen3-coder-next`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Makefile, app.doql.less, goal.yaml, .env.example, docker-compose.yml, project/(2 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: codot;
  version: 0.1.4;
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

## Configuration

```yaml
project:
  name: codot
  version: 0.1.4
  env: local
```

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

## Deployment

```bash markpact:run
pip install codot

# development install
pip install -e .[dev]
```

### Docker Compose (`docker-compose.yml`)

- **api** image=`{'context': './api', 'dockerfile': 'Dockerfile'}` ports: `18080:8080`
- **schemas** image=`nginx:alpine` ports: `18090:80`
- **data** image=`nginx:alpine` ports: `18091:80`
- **frontend** image=`{'context': './frontend', 'dockerfile': 'Dockerfile'}` ports: `18000:80`
- **workflow-api** image=`{'context': './cqrs-backend-workflows', 'dockerfile': 'Dockerfile'}` ports: `18001:8000`
- **workflow-editor** image=`{'context': './cqrs-workflow-editor', 'dockerfile': 'Dockerfile'}` ports: `18002:80`

## Environment Variables (`.env.example`)

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `change-this-in-production-min-32-characters-long-xyz` | Copy to .env and adjust values |
| `JWT_ALGORITHM` | `HS256` |  |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |  |
| `LOG_LEVEL` | `INFO` |  |

## Release Management (`goal.yaml`)

- **versioning**: `semver`
- **commits**: `conventional` scope=`codot`
- **changelog**: `keep-a-changelog`
- **build strategies**: `python`, `nodejs`, `rust`
- **version files**: `VERSION`, `pyproject.toml:version`, `venv/lib/python3.13/site-packages/matplotlib/__init__.py:__version__`

## Makefile Targets

- `help`
- `build`
- `up`
- `down`
- `logs`
- `restart`
- `token`
- `token-user`
- `test`
- `clean`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# codot | 47f 3823L | python:28,shell:8,less:5,javascript:4,typescript:1,css:1 | 2026-04-23
# stats: 71 func | 47 cls | 47 mod | CC̄=2.4 | critical:1 | cycles:0
# alerts[5]: CC _mcp_execute=10; CC _substitute=8; CC run_workflow=8; CC validate_against_schema_uri=7; CC _websocket_execute=6
# hotspots[5]: _bash_cli_execute fan=12; _websocket_execute fan=11; validate_against_schema_uri fan=11; _mcp_execute fan=10; _litellm_execute fan=10
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[47]:
  api/agent.py,363
  api/app.doql.less,60
  api/auth/__init__.py,103
  api/commands/__init__.py,81
  api/commands/converttobase64.py,35
  api/commands/converttocsv.py,61
  api/commands/converttojson.py,81
  api/commands/converttoxml.py,52
  api/commands/fetch.py,28
  api/commands/pipeline.py,98
  api/commands/render.py,98
  api/config.py,35
  api/main.py,235
  api/mcp_client.py,165
  api/models.py,126
  api/policy/__init__.py,150
  api/protocols/__init__.py,70
  api/protocols/data_protocol.py,41
  api/protocols/file_protocol.py,52
  api/protocols/http_protocol.py,34
  api/queries/__init__.py,57
  api/queries/from_url.py,46
  api/queries/introspect.py,23
  api/tests/test_api.py,12
  api/validators/__init__.py,49
  app.doql.less,104
  cqrs-backend-workflows/app.doql.less,60
  cqrs-backend-workflows/server.py,400
  cqrs-backend-workflows/tests/test_cqrs_backend_workflows.py,16
  cqrs-workflow-editor/app.doql.less,65
  cqrs-workflow-editor/test/cqrs-workflow-editor.test.js,8
  cqrs-workflow-editor/vite.config.ts,36
  examples/01-fetch.sh,49
  examples/02-convert-to-json.sh,49
  examples/03-render-html.sh,41
  examples/04-pipeline.sh,125
  examples/05-query.sh,52
  examples/06-rbac.sh,67
  frontend/app.doql.less,60
  frontend/html/css/style.css,35
  frontend/html/js/api.js,62
  frontend/html/js/app.js,188
  frontend/test/codot.test.js,8
  project.sh,40
  tests/smoke.sh,79
  tests/test_policy.py,63
  tests/test_protocols.py,61
D:
  api/agent.py:
    e: register_backend,_mcp_execute,_litellm_execute,_bash_cli_execute,_http_api_execute,_websocket_execute,execute_agent
    register_backend(backend;executor)
    _mcp_execute(node;request)
    _litellm_execute(node;request)
    _bash_cli_execute(node;request)
    _http_api_execute(node;request)
    _websocket_execute(node;request)
    execute_agent(request)
  api/auth/__init__.py:
    e: get_jwt_manager,authenticate,current_user,JWTManager
    JWTManager: __init__(3),issue(3),verify(1)
    get_jwt_manager()
    authenticate(username;password)
    current_user(creds)
  api/commands/__init__.py:
    e: get_registry,register_default_commands,Command,CommandRegistry
    Command: execute(1)
    CommandRegistry: __init__(0),register(1),get(1),list(0)
    get_registry()
    register_default_commands()
  api/commands/converttobase64.py:
    e: ConvertToBase64Command
    ConvertToBase64Command: execute(1)
  api/commands/converttocsv.py:
    e: ConvertToCsvCommand
    ConvertToCsvCommand: execute(1)
  api/commands/converttojson.py:
    e: ConvertToJsonCommand
    ConvertToJsonCommand: _detect_mode(3),_convert(2),execute(1)
  api/commands/converttoxml.py:
    e: ConvertToXmlCommand
    ConvertToXmlCommand: execute(1)
  api/commands/fetch.py:
    e: FetchCommand
    FetchCommand: execute(1)
  api/commands/pipeline.py:
    e: _to_data_uri,_substitute,PipelineCommand
    PipelineCommand: execute(1)
    _to_data_uri(resp)
    _substitute(value;previous)
  api/commands/render.py:
    e: RenderCommand
    RenderCommand: execute(1)
  api/config.py:
    e: load_settings,Settings
    Settings:
    load_settings()
  api/main.py:
    e: _value_error,_perm_error,_nf_error,_key_error,health,issue_token,me,list_commands,execute_command,list_queries,execute_query,execute_query_get,catalog,run_agent,list_agent_backends
    _value_error(_;exc)
    _perm_error(_;exc)
    _nf_error(_;exc)
    _key_error(_;exc)
    health()
    issue_token(req)
    me(user)
    list_commands(user)
    execute_command(name;body;user)
    list_queries(user)
    execute_query(name;body;user)
    execute_query_get(name;source_uris;user)
    catalog()
    run_agent(agent_id;body;user)
    list_agent_backends()
  api/mcp_client.py:
    e: MCPError,MCPClient,MCPStdioClient,MCPSseClient
    MCPError:
    MCPClient: __init__(0),_next_id(0),_send(1),initialize(2),list_tools(0),call_tool(2),close(0)  # Base MCP client (transport-agnostic).
    MCPStdioClient: __init__(2),_read_message(0),_send(1),close(0)  # Spawn an MCP server as a subprocess and speak JSON-RPC over 
    MCPSseClient: __init__(2),_send(1),initialize(2),close(0)  # Connect to an MCP server via HTTP SSE transport.
  api/models.py:
    e: CommandRequest,CommandResponse,QueryRequest,QueryResponse,TokenRequest,TokenResponse,PipelineStep,PipelineRequest,ErrorResponse,AgentCommunicationBackend,AgentNode,AgentRequest,AgentResponse
    CommandRequest:  # Envelope for every command invocation.
    CommandResponse:
    QueryRequest:
    QueryResponse:
    TokenRequest:
    TokenResponse:
    PipelineStep:
    PipelineRequest:
    ErrorResponse:
    AgentCommunicationBackend:  # Supported communication backends for Agent formula.
    AgentNode:  # Agent node definition for DAG / orchestration.
    AgentRequest:  # Request to execute an Agent node.
    AgentResponse:
  api/policy/__init__.py:
    e: get_engine,reload_engine,User,PolicyDecision,PolicyEngine
    User: has_role(1)
    PolicyDecision: allow(2),deny(2)
    PolicyEngine: __init__(1),from_file(2),_rules_for(1),_match_any(2),can_execute_command(4),can_execute_query(4)
    get_engine()
    reload_engine()
  api/protocols/__init__.py:
    e: get_registry,register_default_protocols,FetchResult,Protocol,ProtocolRegistry
    FetchResult:
    Protocol: fetch(1)
    ProtocolRegistry: __init__(0),register(1),supported(0),fetch(1)
    get_registry()
    register_default_protocols()
  api/protocols/data_protocol.py:
    e: DataProtocol
    DataProtocol: fetch(1)  # Implements RFC 2397 data URIs: data:[<mime>][;base64],<data>
  api/protocols/file_protocol.py:
    e: FileProtocol
    FileProtocol: _resolve(1),fetch(1)  # Access local files. Only paths under ALLOWED_LOCAL_ROOTS are
  api/protocols/http_protocol.py:
    e: HttpProtocol
    HttpProtocol: __init__(1),fetch(1)
  api/queries/__init__.py:
    e: get_registry,register_default_queries,Query,QueryRegistry
    Query: execute(1)
    QueryRegistry: __init__(0),register(1),get(1),list(0)
    get_registry()
    register_default_queries()
  api/queries/from_url.py:
    e: FromUrlQuery
    FromUrlQuery: execute(1)
  api/queries/introspect.py:
    e: IntrospectQuery
    IntrospectQuery: execute(1)
  api/tests/test_api.py:
    e: test_placeholder,test_import
    test_placeholder()
    test_import()
  api/validators/__init__.py:
    e: validate_against_schema_uri,SchemaValidationError
    SchemaValidationError: __init__(2)
    validate_against_schema_uri(instance;schema_uri)
  cqrs-backend-workflows/server.py:
    e: validate_workflow,_result_to_data_uri,_handle_fetch,_handle_http,_handle_command,_handle_render,_handle_agent,execute_node,root,health,list_workflows,get_workflow,create_workflow,update_workflow,delete_workflow,list_examples,get_example,run_workflow,WorkflowNode,WorkflowOutput,Workflow,WorkflowExecutionRequest,WorkflowExecutionResponse
    WorkflowNode:
    WorkflowOutput:
    Workflow:
    WorkflowExecutionRequest:
    WorkflowExecutionResponse:
    validate_workflow(workflow)
    _result_to_data_uri(prev_result)
    _handle_fetch(node;_node_results;headers;client)
    _handle_http(node;_node_results;headers;client)
    _handle_command(node;node_results;headers;client)
    _handle_render(node;node_results;headers;client)
    _handle_agent(node;_node_results;_headers;_client)
    execute_node(node;node_results;client;token)
    root()
    health()
    list_workflows()
    get_workflow(workflow_id)
    create_workflow(workflow)
    update_workflow(workflow_id;workflow)
    delete_workflow(workflow_id)
    list_examples()
    get_example(filename)
    run_workflow(workflow_id;request)
  cqrs-backend-workflows/tests/test_cqrs_backend_workflows.py:
    e: test_placeholder,test_import
    test_placeholder()
    test_import()
  tests/test_policy.py:
    e: _engine,_user,test_admin_can_do_anything,test_user_denied_internal_path,test_user_allowed_public_path,test_unknown_role_denied,test_analyst_can_run_pipeline,test_query_access_respects_uris
    _engine()
    _user(role)
    test_admin_can_do_anything()
    test_user_denied_internal_path()
    test_user_allowed_public_path()
    test_unknown_role_denied()
    test_analyst_can_run_pipeline()
    test_query_access_respects_uris()
  tests/test_protocols.py:
    e: test_data_uri_plain,test_data_uri_base64,test_file_protocol_rejects_outside_root,test_file_protocol_reads_inside_root
    test_data_uri_plain()
    test_data_uri_base64()
    test_file_protocol_rejects_outside_root()
    test_file_protocol_reads_inside_root()
```

## Call Graph

*64 nodes · 55 edges · 17 modules · CC̄=1.2*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `execute` *(in api.commands.pipeline.PipelineCommand)* | 9 | 0 | 22 | **22** |
| `register_default_commands` *(in api.commands)* | 1 | 0 | 15 | **15** |
| `fetchPreview` *(in cqrs-workflow-editor.src.App)* | 13 ⚠ | 1 | 14 | **15** |
| `validate_against_schema_uri` *(in api.validators)* | 7 | 1 | 13 | **14** |
| `API` *(in frontend.html.js.api)* | 9 | 0 | 14 | **14** |
| `request` *(in frontend.html.js.api)* | 9 | 6 | 8 | **14** |
| `execute` *(in api.queries.from_url.FromUrlQuery)* | 9 | 0 | 13 | **13** |
| `loadBackendWorkflow` *(in cqrs-workflow-editor.src.App)* | 3 | 0 | 11 | **11** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/codot
# nodes: 64 | edges: 55 | modules: 17
# CC̄=1.2

HUBS[20]:
  api.commands.pipeline.PipelineCommand.execute
    CC=9  in:0  out:22  total:22
  api.commands.register_default_commands
    CC=1  in:0  out:15  total:15
  cqrs-workflow-editor.src.App.fetchPreview
    CC=13  in:1  out:14  total:15
  api.validators.validate_against_schema_uri
    CC=7  in:1  out:13  total:14
  frontend.html.js.api.API
    CC=9  in:0  out:14  total:14
  frontend.html.js.api.request
    CC=9  in:6  out:8  total:14
  api.queries.from_url.FromUrlQuery.execute
    CC=9  in:0  out:13  total:13
  cqrs-workflow-editor.src.App.loadBackendWorkflow
    CC=3  in:0  out:11  total:11
  cqrs-workflow-editor.src.App.loadExampleFile
    CC=3  in:0  out:11  total:11
  api.main.execute_command
    CC=3  in:0  out:11  total:11
  api.commands.get_registry
    CC=1  in:10  out:0  total:10
  frontend.html.js.app.renderDecoded
    CC=9  in:0  out:10  total:10
  api.main.execute_query
    CC=3  in:1  out:9  total:10
  cqrs-workflow-editor.src.App.onUploadWorkflow
    CC=4  in:0  out:10  total:10
  api.commands.converttobase64.ConvertToBase64Command.execute
    CC=2  in:0  out:10  total:10
  api.commands.pipeline._substitute
    CC=8  in:3  out:7  total:10
  api.protocols.register_default_protocols
    CC=1  in:0  out:9  total:9
  cqrs-workflow-editor.src.App.mapToEdges
    CC=4  in:6  out:2  total:8
  cqrs-workflow-editor.src.App.reader
    CC=2  in:0  out:8  total:8
  cqrs-workflow-editor.src.App.file
    CC=2  in:0  out:8  total:8

MODULES:
  api.agent  [1 funcs]
    execute_agent  CC=2  out:3
  api.auth  [2 funcs]
    authenticate  CC=3  out:1
    get_jwt_manager  CC=1  out:0
  api.commands  [3 funcs]
    list  CC=2  out:1
    get_registry  CC=1  out:0
    register_default_commands  CC=1  out:15
  api.commands.converttobase64  [1 funcs]
    execute  CC=2  out:10
  api.commands.converttojson  [1 funcs]
    _convert  CC=8  out:8
  api.commands.fetch  [1 funcs]
    execute  CC=2  out:7
  api.commands.pipeline  [3 funcs]
    execute  CC=9  out:22
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

EDGES:
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
  cqrs-workflow-editor.src.App.fetchBackendWorkflows → cqrs-workflow-editor.src.App.json
  cqrs-workflow-editor.src.App.loadBackendWorkflow → cqrs-workflow-editor.src.App.json
  cqrs-workflow-editor.src.App.loadBackendWorkflow → cqrs-workflow-editor.src.App.mapToNodes
  cqrs-workflow-editor.src.App.loadBackendWorkflow → cqrs-workflow-editor.src.App.mapToEdges
  cqrs-workflow-editor.src.App.runBackendWorkflow → cqrs-workflow-editor.src.App.json
  cqrs-workflow-editor.src.App.fetchExampleFiles → cqrs-workflow-editor.src.App.json
  cqrs-workflow-editor.src.App.loadExampleFile → cqrs-workflow-editor.src.App.json
  cqrs-workflow-editor.src.App.loadExampleFile → cqrs-workflow-editor.src.App.mapToNodes
  cqrs-workflow-editor.src.App.loadExampleFile → cqrs-workflow-editor.src.App.mapToEdges
  cqrs-workflow-editor.src.App.loadPredefinedWorkflow → cqrs-workflow-editor.src.App.mapToNodes
  cqrs-workflow-editor.src.App.loadPredefinedWorkflow → cqrs-workflow-editor.src.App.mapToEdges
  cqrs-workflow-editor.src.App.fetchPreview → cqrs-workflow-editor.src.App.blob
  cqrs-workflow-editor.src.App.sizeKB → cqrs-workflow-editor.src.App.text
  cqrs-workflow-editor.src.App.mime → cqrs-workflow-editor.src.App.text
  cqrs-workflow-editor.src.App.timer → cqrs-workflow-editor.src.App.fetchPreview
  cqrs-workflow-editor.src.App.onDownloadWorkflow → cqrs-workflow-editor.src.App.exportWorkflow
  cqrs-workflow-editor.src.App.workflow → cqrs-workflow-editor.src.App.json
  cqrs-workflow-editor.src.App.onUploadWorkflow → cqrs-workflow-editor.src.App.mapToNodes
  cqrs-workflow-editor.src.App.onUploadWorkflow → cqrs-workflow-editor.src.App.mapToEdges
  cqrs-workflow-editor.src.App.file → cqrs-workflow-editor.src.App.mapToNodes
  cqrs-workflow-editor.src.App.file → cqrs-workflow-editor.src.App.mapToEdges
  cqrs-workflow-editor.src.App.reader → cqrs-workflow-editor.src.App.mapToNodes
  cqrs-workflow-editor.src.App.reader → cqrs-workflow-editor.src.App.mapToEdges
  cqrs-backend-workflows.server._handle_command → cqrs-backend-workflows.server._result_to_data_uri
  cqrs-backend-workflows.server._handle_render → cqrs-backend-workflows.server._result_to_data_uri
  cqrs-backend-workflows.server.list_workflows → api.commands.CommandRegistry.list
  cqrs-backend-workflows.server.create_workflow → cqrs-backend-workflows.server.validate_workflow
  cqrs-backend-workflows.server.update_workflow → cqrs-backend-workflows.server.validate_workflow
  api.main.issue_token → api.auth.authenticate
  api.main.issue_token → api.auth.get_jwt_manager
  api.main.execute_command → api.policy.get_engine
  api.main.execute_query → api.policy.get_engine
  api.main.execute_query_get → api.main.execute_query
  api.main.run_agent → api.agent.execute_agent
  api.main.run_agent → api.policy.get_engine
  api.commands.fetch.FetchCommand.execute → api.commands.get_registry
  api.commands.register_default_commands → api.commands.get_registry
  api.commands.converttojson.ConvertToJsonCommand._convert → api.commands.CommandRegistry.list
  api.commands.converttobase64.ConvertToBase64Command.execute → api.commands.get_registry
  api.commands.pipeline._substitute → api.commands.pipeline._to_data_uri
```

## Intent

CQRS-URL Platform - Commands and Queries as URL-addressable resources

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
- **version**: `0.1.8`
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
  version: 0.1.8;
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
  step-4: run cmd=bash -c 'source .env && echo "  - Frontend:   http://localhost:$${FRONTEND_PORT:-18000}"';
  step-5: run cmd=bash -c 'source .env && echo "  - API:        http://localhost:$${API_PORT:-18080}"';
  step-6: run cmd=bash -c 'source .env && echo "  - API docs:   http://localhost:$${API_PORT:-18080}/docs"';
  step-7: run cmd=bash -c 'source .env && echo "  - Schemas:    http://localhost:$${SCHEMAS_PORT:-18090}"';
  step-8: run cmd=bash -c 'source .env && echo "  - Sample data: http://localhost:$${DATA_PORT:-18091}"';
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
  step-1: run cmd=bash -c 'source .env && curl -s -X POST http://localhost:$${API_PORT:-18080}/auth/token \';
  step-2: run cmd=-H "Content-Type: application/json" \;
  step-3: run cmd=-d '{"username":"admin","password":"admin"}' | python3 -m json.tool;
}

workflow[name="token-user"] {
  trigger: manual;
  step-1: run cmd=bash -c 'source .env && curl -s -X POST http://localhost:$${API_PORT:-18080}/auth/token \';
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
  step-1: run cmd=bash -c 'source .env && python3 codot_run.py examples/workflow_agent_mcp.json --url $${API_BASE_URL:-http://localhost:18080}';
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
  version: 0.1.8
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
- `test-agent`
- `workflow`
- `clean`

## Code Analysis

### `project/map.toon.yaml`

```toon markpact:analysis path=project/map.toon.yaml
# codot | 69f 6888L | python:50,shell:8,less:5,javascript:4,typescript:1,css:1 | 2026-04-23
# stats: 156 func | 67 cls | 69 mod | CC̄=3.1 | critical:4 | cycles:0
# alerts[5]: CC _php_array=11; CC _mcp_execute=10; CC main=10; CC _path_item=10; CC cmd_compile=9
# hotspots[5]: test_php_standalone_health_endpoint_runs fan=16; cmd_compile fan=15; test_litellm_mock fan=14; _bash_cli_execute fan=12; test_static_html_parses_as_valid_html fan=12
# evolution: baseline
# Keys: M=modules, D=details, i=imports, e=exports, c=classes, f=functions, m=methods
M[69]:
  api/agent.py,363
  api/app.doql.less,60
  api/auth/__init__.py,103
  api/commands/__init__.py,81
  api/commands/converttobase64.py,35
  api/commands/converttocsv.py,61
  api/commands/converttojson.py,81
  api/commands/converttoxml.py,52
  api/commands/fetch.py,28
  api/commands/pipeline.py,112
  api/commands/render.py,98
  api/config.py,35
  api/main.py,235
  api/mcp_client.py,174
  api/models.py,126
  api/policy/__init__.py,150
  api/protocols/__init__.py,70
  api/protocols/data_protocol.py,41
  api/protocols/file_protocol.py,52
  api/protocols/http_protocol.py,34
  api/queries/__init__.py,57
  api/queries/from_url.py,46
  api/queries/introspect.py,23
  api/test_all_agents.py,144
  api/test_mcp_agent.py,42
  api/tests/test_api.py,12
  api/validators/__init__.py,49
  app.doql.less,114
  codot_run.py,148
  cqrs-backend-workflows/app.doql.less,60
  cqrs-backend-workflows/server.py,440
  cqrs-backend-workflows/tests/test_cqrs_backend_workflows.py,45
  cqrs-workflow-editor/app.doql.less,65
  cqrs-workflow-editor/test/cqrs-workflow-editor.test.js,8
  cqrs-workflow-editor/vite.config.ts,41
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
  mcp_servers/summary_server.py,110
  project.sh,40
  service-factory/factory/__init__.py,83
  service-factory/factory/cli.py,106
  service-factory/factory/generators/__init__.py,1
  service-factory/factory/generators/code/__init__.py,1
  service-factory/factory/generators/code/node_fastify.py,166
  service-factory/factory/generators/code/python_fastapi.py,207
  service-factory/factory/generators/infra/__init__.py,1
  service-factory/factory/generators/infra/docker.py,208
  service-factory/factory/generators/infra/kubernetes.py,110
  service-factory/factory/generators/types.py,55
  service-factory/factory/generators/view/__init__.py,1
  service-factory/factory/generators/view/_shared.py,34
  service-factory/factory/generators/view/php_standalone.py,315
  service-factory/factory/generators/view/static_html.py,241
  service-factory/factory/generators/wire/__init__.py,1
  service-factory/factory/generators/wire/openapi.py,125
  service-factory/factory/ir/__init__.py,335
  service-factory/tests/test_factory.py,487
  tests/smoke.sh,116
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
  api/test_all_agents.py:
    e: test_mcp,test_bash,test_litellm_mock,test_pipeline_with_agent,main
    test_mcp()
    test_bash()
    test_litellm_mock()
    test_pipeline_with_agent()
    main()
  api/test_mcp_agent.py:
    e: main
    main()
  api/tests/test_api.py:
    e: test_placeholder,test_import
    test_placeholder()
    test_import()
  api/validators/__init__.py:
    e: validate_against_schema_uri,SchemaValidationError
    SchemaValidationError: __init__(2)
    validate_against_schema_uri(instance;schema_uri)
  codot_run.py:
    e: _get_token,run_pipeline,run_agent,main
    _get_token(base;username;password)
    run_pipeline(base;token;workflow_path)
    run_agent(base;token;agent_path)
    main()
  cqrs-backend-workflows/server.py:
    e: validate_workflow,_result_to_data_uri,_handle_fetch,_handle_http,_handle_command,_handle_render,_decode_payload_b64,_build_agent_context,_build_agent_body,_handle_agent,execute_node,root,health,list_workflows,get_workflow,create_workflow,update_workflow,delete_workflow,list_examples,get_example,run_workflow,WorkflowNode,WorkflowOutput,Workflow,WorkflowExecutionRequest,WorkflowExecutionResponse
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
    _decode_payload_b64(payload_b64)
    _build_agent_context(node;node_results)
    _build_agent_body(node;context)
    _handle_agent(node;node_results;headers;client)
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
    e: test_placeholder,test_import,test_agent_node_fields,test_workflow_schema_validation
    test_placeholder()
    test_import()
    test_agent_node_fields()
    test_workflow_schema_validation()
  mcp_servers/summary_server.py:
    e: _send,_handle,main
    _send(msg)
    _handle(req)
    main()
  service-factory/factory/__init__.py:
    e: get_registry,register_default_generators,Generator,GeneratorRegistry
    Generator: generate(1)
    GeneratorRegistry: __init__(0),register(1),get(1),by_category(1),list(0)
    get_registry()
    register_default_generators()
  service-factory/factory/cli.py:
    e: cmd_compile,cmd_list,cmd_hash,main
    cmd_compile(args)
    cmd_list(args)
    cmd_hash(args)
    main(argv)
  service-factory/factory/generators/__init__.py:
  service-factory/factory/generators/code/__init__.py:
  service-factory/factory/generators/code/node_fastify.py:
    e: _camel,_schema_object,_command_route_lines,_query_route_lines,NodeFastifyGenerator
    NodeFastifyGenerator: generate(1),_package_json(1),_server(1),_types(1),_ts_interface(2)
    _camel(name)
    _schema_object(fields;indent)
    _command_route_lines(c)
    _query_route_lines(c)
  service-factory/factory/generators/code/python_fastapi.py:
    e: _snake,_pydantic_model,_command_route,_query_route,_event_model,PythonFastApiGenerator
    PythonFastApiGenerator: generate(1),_requirements(0),_models(1),_events(1),_main(1)
    _snake(name)
    _pydantic_model(name;fields)
    _command_route(c)
    _query_route(c)
    _event_model(c)
  service-factory/factory/generators/infra/__init__.py:
  service-factory/factory/generators/infra/docker.py:
    e: _indent_block,DockerGenerator
    DockerGenerator: generate(1),_dockerfile(1),_python_dockerfile(1),_node_dockerfile(1),_dockerignore(0),_compose(1),_main_service_block(3),_companion_block(1),_storage_block(1),_cpu_to_docker(1),_mem_to_docker(1)
    _indent_block(block;spaces)
  service-factory/factory/generators/infra/kubernetes.py:
    e: KubernetesGenerator
    KubernetesGenerator: generate(1),_deployment(1),_service(1),_kustomization(1)
  service-factory/factory/generators/types.py:
    e: py_type,ts_type,openapi_type
    py_type(t;required)
    ts_type(t;required)
    openapi_type(t;fmt)
  service-factory/factory/generators/view/__init__.py:
  service-factory/factory/generators/view/_shared.py:
    e: refresh_to_ms,is_never
    refresh_to_ms(value)
    is_never(value)
  service-factory/factory/generators/view/php_standalone.py:
    e: _php_quote,_php_array,_sources_php_literal,PhpStandaloneViewGenerator
    PhpStandaloneViewGenerator: generate(1),_index_php(1),_readme(1)
    _php_quote(value)
    _php_array(data;indent)
    _sources_php_literal(bundle)
  service-factory/factory/generators/view/static_html.py:
    e: _source_to_js,StaticHtmlViewGenerator
    StaticHtmlViewGenerator: generate(1),_index_html(1),_readme(1)
    _source_to_js(src)
  service-factory/factory/generators/wire/__init__.py:
  service-factory/factory/generators/wire/openapi.py:
    e: _schema_from_fields,_path_item,OpenApiGenerator
    OpenApiGenerator: generate(1)
    _schema_from_fields(fields)
    _path_item(c)
  service-factory/factory/ir/__init__.py:
    e: Contract,Runtime,Storage,Companion,Resources,Exposure,Bundle,Source,Template,ViewBundle,BundleLoader
    Contract: kind(0),name(0),is_command(0),is_query(0),is_event(0),module(0),description(0),version(0),http_method(0),http_endpoint(0),ws_channel(0),input_fields(0),output_fields(0),payload_fields(0),success_event(0),failure_event(0)  # Unified view over command/query/event contract JSON.
    Runtime:
    Storage:
    Companion:
    Resources:
    Exposure:
    Bundle: commands(0),queries(0),events(0),contract_hash(0)
    Source:  # A URL the view aggregates from. Refresh is advisory metadata
    Template:  # How the view is rendered. ``engine`` is a hint for generator
    ViewBundle: contract_hash(0)
    BundleLoader: __init__(1),load(1),_load_service(2),_load_view(2),_resolve_contract(2),_validate_service(2),_validate_view(2)  # Reads a bundle.json from disk.
  service-factory/tests/test_factory.py:
    e: _register,bundle,test_bundle_loads_with_contracts,test_hash_is_deterministic,test_hash_changes_when_runtime_changes,test_contract_accessors,test_missing_contract_raises_clear_error,test_all_generators_registered,test_python_fastapi_generates_valid_python,test_python_fastapi_routes_match_contracts,test_node_fastify_generates_valid_json,test_docker_generates_valid_yaml,test_docker_dockerfile_has_healthcheck,test_kubernetes_generates_valid_yaml,test_openapi_generates_valid_json,test_same_bundle_compiles_to_different_languages,test_same_bundle_compiles_to_different_infra,view_bundle,test_view_bundle_loads_with_sources,test_view_bundle_hash_is_deterministic,test_view_bundle_hash_changes_when_source_changes,test_view_bundle_rejects_missing_sources,test_view_bundle_rejects_unknown_transport,test_service_bundle_still_loads_as_bundle,test_php_standalone_registered,test_php_standalone_rejects_service_bundle,test_php_standalone_emits_expected_files,test_php_standalone_passes_php_lint,_pick_free_port,_wait_for_http,test_static_html_registered,test_static_html_rejects_service_bundle,test_static_html_emits_expected_files,test_static_html_embeds_every_source_uri,test_static_html_parses_as_valid_html,test_static_html_readme_mentions_cors_and_serve,test_static_html_script_is_syntactically_valid,test_static_html_inline_js_is_valid,test_view_bundle_compiles_to_multiple_targets,test_php_standalone_health_endpoint_runs
    _register()
    bundle()
    test_bundle_loads_with_contracts(bundle)
    test_hash_is_deterministic(bundle)
    test_hash_changes_when_runtime_changes(bundle)
    test_contract_accessors()
    test_missing_contract_raises_clear_error()
    test_all_generators_registered()
    test_python_fastapi_generates_valid_python(bundle;tmp_path)
    test_python_fastapi_routes_match_contracts(bundle)
    test_node_fastify_generates_valid_json(bundle)
    test_docker_generates_valid_yaml(bundle)
    test_docker_dockerfile_has_healthcheck(bundle)
    test_kubernetes_generates_valid_yaml(bundle)
    test_openapi_generates_valid_json(bundle)
    test_same_bundle_compiles_to_different_languages(bundle)
    test_same_bundle_compiles_to_different_infra(bundle)
    view_bundle()
    test_view_bundle_loads_with_sources(view_bundle)
    test_view_bundle_hash_is_deterministic(view_bundle)
    test_view_bundle_hash_changes_when_source_changes(view_bundle)
    test_view_bundle_rejects_missing_sources(tmp_path)
    test_view_bundle_rejects_unknown_transport(tmp_path)
    test_service_bundle_still_loads_as_bundle()
    test_php_standalone_registered()
    test_php_standalone_rejects_service_bundle(bundle)
    test_php_standalone_emits_expected_files(view_bundle)
    test_php_standalone_passes_php_lint(view_bundle;tmp_path)
    _pick_free_port()
    _wait_for_http(url;timeout)
    test_static_html_registered()
    test_static_html_rejects_service_bundle(bundle)
    test_static_html_emits_expected_files(view_bundle)
    test_static_html_embeds_every_source_uri(view_bundle)
    test_static_html_parses_as_valid_html(view_bundle)
    test_static_html_readme_mentions_cors_and_serve(view_bundle)
    test_static_html_script_is_syntactically_valid(view_bundle)
    test_static_html_inline_js_is_valid(view_bundle;tmp_path)
    test_view_bundle_compiles_to_multiple_targets(view_bundle)
    test_php_standalone_health_endpoint_runs(view_bundle;tmp_path)
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

*96 nodes · 82 edges · 24 modules · CC̄=1.2*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `main` *(in codot_run)* | 10 ⚠ | 0 | 33 | **33** |
| `execute` *(in api.commands.pipeline.PipelineCommand)* | 13 ⚠ | 0 | 31 | **31** |
| `cmd_compile` *(in service-factory.factory.cli)* | 9 | 0 | 24 | **24** |
| `_schema_object` *(in service-factory.factory.generators.code.node_fastify)* | 8 | 2 | 13 | **15** |
| `register_default_commands` *(in api.commands)* | 1 | 0 | 15 | **15** |
| `fetchPreview` *(in cqrs-workflow-editor.src.App)* | 13 ⚠ | 1 | 14 | **15** |
| `request` *(in frontend.html.js.api)* | 9 | 6 | 8 | **14** |
| `_compose` *(in service-factory.factory.generators.infra.docker.DockerGenerator)* | 3 | 0 | 14 | **14** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/codot
# nodes: 96 | edges: 82 | modules: 24
# CC̄=1.2

HUBS[20]:
  codot_run.main
    CC=10  in:0  out:33  total:33
  api.commands.pipeline.PipelineCommand.execute
    CC=13  in:0  out:31  total:31
  service-factory.factory.cli.cmd_compile
    CC=9  in:0  out:24  total:24
  service-factory.factory.generators.code.node_fastify._schema_object
    CC=8  in:2  out:13  total:15
  api.commands.register_default_commands
    CC=1  in:0  out:15  total:15
  cqrs-workflow-editor.src.App.fetchPreview
    CC=13  in:1  out:14  total:15
  frontend.html.js.api.request
    CC=9  in:6  out:8  total:14
  service-factory.factory.generators.infra.docker.DockerGenerator._compose
    CC=3  in:0  out:14  total:14
  service-factory.factory.generators.code.python_fastapi._pydantic_model
    CC=5  in:3  out:11  total:14
  frontend.html.js.api.API
    CC=9  in:0  out:14  total:14
  service-factory.factory.register_default_generators
    CC=1  in:2  out:11  total:13
  api.queries.from_url.FromUrlQuery.execute
    CC=9  in:0  out:13  total:13
  api.validators.validate_against_schema_uri
    CC=7  in:0  out:13  total:13
  service-factory.factory.get_registry
    CC=1  in:12  out:0  total:12
  api.main.execute_command
    CC=3  in:0  out:11  total:11
  service-factory.factory.generators.code.python_fastapi._query_route
    CC=7  in:1  out:10  total:11
  cqrs-workflow-editor.src.App.loadBackendWorkflow
    CC=3  in:0  out:11  total:11
  cqrs-workflow-editor.src.App.loadExampleFile
    CC=3  in:0  out:11  total:11
  service-factory.factory.generators.wire.openapi._schema_from_fields
    CC=7  in:3  out:7  total:10
  api.main.execute_query
    CC=3  in:1  out:9  total:10

MODULES:
  api.SUMD  [5 funcs]
    _substitute  CC=0  out:0
    authenticate  CC=0  out:0
    execute_agent  CC=0  out:0
    get_engine  CC=0  out:0
    get_jwt_manager  CC=0  out:0
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
```

## Intent

CQRS-URL Platform - Commands and Queries as URL-addressable resources

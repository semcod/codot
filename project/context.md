# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/semcod/codot
- **Primary Language**: python
- **Languages**: python: 23, md: 13, json: 9, shell: 7, txt: 4
- **Analysis Mode**: static
- **Total Functions**: 154
- **Total Classes**: 48
- **Modules**: 75
- **Entry Points**: 128

## Architecture by Module

### cqrs-workflow-editor.src.App
- **Functions**: 36
- **File**: `App.tsx`

### frontend.html.js.app
- **Functions**: 19
- **File**: `app.js`

### frontend.html.js.api
- **Functions**: 15
- **File**: `api.js`

### api.main
- **Functions**: 15
- **File**: `main.py`

### api.policy
- **Functions**: 11
- **Classes**: 3
- **File**: `__init__.py`

### cqrs-backend-workflows.server
- **Functions**: 10
- **Classes**: 5
- **File**: `server.py`

### api.queries
- **Functions**: 7
- **Classes**: 2
- **File**: `__init__.py`

### api.commands
- **Functions**: 7
- **Classes**: 2
- **File**: `__init__.py`

### api.agent
- **Functions**: 7
- **File**: `agent.py`

### api.protocols
- **Functions**: 7
- **Classes**: 3
- **File**: `__init__.py`

### api.auth
- **Functions**: 6
- **Classes**: 1
- **File**: `__init__.py`

### api.commands.pipeline
- **Functions**: 3
- **Classes**: 1
- **File**: `pipeline.py`

### api.protocols.http_protocol
- **Functions**: 2
- **Classes**: 1
- **File**: `http_protocol.py`

### api.protocols.file_protocol
- **Functions**: 2
- **Classes**: 1
- **File**: `file_protocol.py`

### api.validators
- **Functions**: 2
- **Classes**: 1
- **File**: `__init__.py`

### docs.04-workflow-editor-spec
- **Functions**: 1
- **Classes**: 3
- **File**: `04-workflow-editor-spec.md`

### cqrs-workflow-editor.src.main
- **Functions**: 1
- **File**: `main.tsx`

### api.commands.converttobase64
- **Functions**: 1
- **Classes**: 1
- **File**: `converttobase64.py`

### api.commands.fetch
- **Functions**: 1
- **Classes**: 1
- **File**: `fetch.py`

### api.protocols.data_protocol
- **Functions**: 1
- **Classes**: 1
- **File**: `data_protocol.py`

## Key Entry Points

Main execution flows into the system:

### api.agent._mcp_execute
> Execute agent via MCP server.

backend_config keys:
    - server_url: SSE endpoint URL (or stdio command if absent)
    - stdio_command: list[str] com
- **Calls**: cfg.get, cfg.get, AgentResponse, trace.append, trace.append, AgentResponse, httpx.AsyncClient, resp.raise_for_status

### api.commands.converttojson.ConvertToJsonCommand.execute
- **Calls**: None.get, None.lower, fetched.content.decode, None.encode, CommandResponse, ValueError, None.fetch, None.strip

### api.commands.converttocsv.ConvertToCsvCommand.execute
- **Calls**: json.loads, io.StringIO, csv.DictWriter, writer.writeheader, None.encode, CommandResponse, ValueError, None.fetch

### api.agent._litellm_execute
> Execute agent via LiteLLM proxy.

backend_config keys:
    - model: LiteLLM model string (e.g. "gpt-4", "openrouter/qwen/...")
    - api_base: LiteLLM
- **Calls**: cfg.get, cfg.get, cfg.get, cfg.get, cfg.get, AgentResponse, os.environ.get, os.environ.get

### api.commands.render.RenderCommand.execute
- **Calls**: meta.get, Environment, env.from_string, template.render, html.encode, CommandResponse, meta.get, t.content.decode

### api.agent._bash_cli_execute
> Execute agent via shell / CLI.

backend_config keys:
    - shell: shell path (default /bin/bash)
    - timeout: seconds (default 30)
    - working_dir
- **Calls**: cfg.get, cfg.get, cfg.get, cfg.get, AgentResponse, None.replace, request.context.get, stdout.decode

### api.commands.converttoxml.ConvertToXmlCommand.execute
- **Calls**: None.get, None.lower, fetched.content.decode, isinstance, xmltodict.unparse, xml.encode, CommandResponse, ValueError

### api.agent._websocket_execute
> Execute agent via WebSocket (sends JSON, waits for first text message).

backend_config keys:
    - uri: WebSocket URI (ws://... / wss://...)
    - su
- **Calls**: cfg.get, cfg.get, float, json.dumps, AgentResponse, cfg.get, AgentResponse, trace.append

### api.protocols.file_protocol.FileProtocol._resolve
- **Calls**: urlparse, unquote, None.resolve, ValueError, None.resolve, any, PermissionError, path.exists

### api.config.load_settings
- **Calls**: os.environ.get, Settings, os.environ.get, os.environ.get, int, os.environ.get, tuple, os.environ.get

### api.agent._http_api_execute
> Execute agent via generic HTTP REST API.

backend_config keys:
    - url: endpoint URL
    - method: HTTP method (default POST)
    - headers: dict
  
- **Calls**: cfg.get, cfg.get, cfg.get, cfg.get, AgentResponse, AgentResponse, httpx.AsyncClient, resp.raise_for_status

### api.commands.register_default_commands
- **Calls**: api.commands.get_registry, reg.register, reg.register, reg.register, reg.register, reg.register, reg.register, reg.register

### cqrs-backend-workflows.server.run_workflow
> Execute a workflow
- **Calls**: app.post, HTTPException, workflow.get, WorkflowExecutionResponse, httpx.AsyncClient, output_def.get, WorkflowExecutionResponse, WorkflowNode

### frontend.html.js.api.API
- **Calls**: frontend.html.js.api.getItem, frontend.html.js.api.setItem, frontend.html.js.api.removeItem, frontend.html.js.api.getToken, frontend.html.js.api.fetch, frontend.html.js.api.stringify, frontend.html.js.api.get, frontend.html.js.api.includes

### api.queries.from_url.FromUrlQuery.execute
- **Calls**: api.queries.get_registry, QueryResponse, ValueError, parts.append, registry.fetch, mime.startswith, None.decode, fetched.content.decode

### api.commands.pipeline.PipelineCommand.execute
- **Calls**: get_command_registry, enumerate, CommandResponse, None.get, ValueError, step.get, api.commands.pipeline._substitute, CommandRequest

### api.main.execute_command
- **Calls**: app.put, Depends, None.can_execute_command, log.info, log.info, HTTPException, None.get, command.execute

### api.policy.PolicyEngine.can_execute_query
- **Calls**: self._rules_for, PolicyDecision.deny, PolicyDecision.deny, rule.get, rule.get, PolicyDecision.allow, self._match_any, all

### frontend.html.js.app.renderDecoded
- **Calls**: frontend.html.js.app.decodeB64, frontend.html.js.app.startsWith, frontend.html.js.app.createElement, frontend.html.js.app.TextDecoder, frontend.html.js.app.decode, frontend.html.js.app.appendChild, frontend.html.js.app.Blob, frontend.html.js.app.createObjectURL

### api.commands.converttobase64.ConvertToBase64Command.execute
- **Calls**: None.decode, encoded.encode, CommandResponse, ValueError, None.fetch, base64.b64encode, None.decode, api.queries.get_registry

### api.protocols.file_protocol.FileProtocol.fetch
- **Calls**: self._resolve, path.read_bytes, mimetypes.guess_type, FetchResult, len, ValueError, str, str

### api.policy.PolicyEngine.can_execute_command
- **Calls**: self._rules_for, PolicyDecision.deny, PolicyDecision.deny, rule.get, PolicyDecision.allow, self._match_any, rule.get, rule.get

### frontend.html.js.app.bytes
- **Calls**: frontend.html.js.app.startsWith, frontend.html.js.app.createElement, frontend.html.js.app.TextDecoder, frontend.html.js.app.decode, frontend.html.js.app.appendChild, frontend.html.js.app.Blob, frontend.html.js.app.createObjectURL, frontend.html.js.app.includes

### api.protocols.http_protocol.HttpProtocol.fetch
- **Calls**: httpx.AsyncClient, resp.raise_for_status, FetchResult, client.get, len, ValueError, resp.headers.get, dict

### api.protocols.data_protocol.DataProtocol.fetch
- **Calls**: None.partition, FetchResult, uri.startswith, ValueError, ValueError, header.split, base64.b64decode, None.encode

### api.protocols.register_default_protocols
- **Calls**: api.protocols.get_registry, reg.register, reg.register, reg.register, reg.register, HttpProtocol, HttpProtocol, FileProtocol

### cqrs-workflow-editor.src.App.onUploadWorkflow
- **Calls**: cqrs-workflow-editor.src.App.FileReader, cqrs-workflow-editor.src.App.parse, cqrs-workflow-editor.src.App.mapToNodes, cqrs-workflow-editor.src.App.mapToEdges, cqrs-workflow-editor.src.App.setNodes, cqrs-workflow-editor.src.App.setEdges, cqrs-workflow-editor.src.App.alert, cqrs-workflow-editor.src.App.readAsText

### api.auth.JWTManager.issue
- **Calls**: datetime.now, jwt.encode, int, int, int, now.timestamp, exp.timestamp, self.expires.total_seconds

### api.policy.PolicyEngine.from_file
- **Calls**: Path, cls, p.exists, logger.warning, cls, yaml.safe_load, data.get, p.read_text

### cqrs-workflow-editor.src.App.workflow
- **Calls**: cqrs-workflow-editor.src.App.fetch, cqrs-workflow-editor.src.App.stringify, cqrs-workflow-editor.src.App.Error, cqrs-workflow-editor.src.App.json, cqrs-workflow-editor.src.App.setRunResult, cqrs-workflow-editor.src.App.String, cqrs-workflow-editor.src.App.setRunLoading

## Process Flows

Key execution flows identified:

### Flow 1: _mcp_execute
```
_mcp_execute [api.agent]
```

### Flow 2: execute
```
execute [api.commands.converttojson.ConvertToJsonCommand]
```

### Flow 3: _litellm_execute
```
_litellm_execute [api.agent]
```

### Flow 4: _bash_cli_execute
```
_bash_cli_execute [api.agent]
```

### Flow 5: _websocket_execute
```
_websocket_execute [api.agent]
```

### Flow 6: _resolve
```
_resolve [api.protocols.file_protocol.FileProtocol]
```

### Flow 7: load_settings
```
load_settings [api.config]
```

### Flow 8: _http_api_execute
```
_http_api_execute [api.agent]
```

### Flow 9: register_default_commands
```
register_default_commands [api.commands]
  └─> get_registry
```

### Flow 10: run_workflow
```
run_workflow [cqrs-backend-workflows.server]
```

## Key Classes

### api.policy.PolicyEngine
- **Methods**: 6
- **Key Methods**: api.policy.PolicyEngine.__init__, api.policy.PolicyEngine.from_file, api.policy.PolicyEngine._rules_for, api.policy.PolicyEngine._match_any, api.policy.PolicyEngine.can_execute_command, api.policy.PolicyEngine.can_execute_query

### api.queries.QueryRegistry
- **Methods**: 4
- **Key Methods**: api.queries.QueryRegistry.__init__, api.queries.QueryRegistry.register, api.queries.QueryRegistry.get, api.queries.QueryRegistry.list

### api.commands.CommandRegistry
- **Methods**: 4
- **Key Methods**: api.commands.CommandRegistry.__init__, api.commands.CommandRegistry.register, api.commands.CommandRegistry.get, api.commands.CommandRegistry.list

### api.protocols.ProtocolRegistry
- **Methods**: 4
- **Key Methods**: api.protocols.ProtocolRegistry.__init__, api.protocols.ProtocolRegistry.register, api.protocols.ProtocolRegistry.supported, api.protocols.ProtocolRegistry.fetch

### api.auth.JWTManager
- **Methods**: 3
- **Key Methods**: api.auth.JWTManager.__init__, api.auth.JWTManager.issue, api.auth.JWTManager.verify

### api.protocols.http_protocol.HttpProtocol
- **Methods**: 2
- **Key Methods**: api.protocols.http_protocol.HttpProtocol.__init__, api.protocols.http_protocol.HttpProtocol.fetch

### api.protocols.file_protocol.FileProtocol
> Access local files. Only paths under ALLOWED_LOCAL_ROOTS are permitted
(by default /data and /schema
- **Methods**: 2
- **Key Methods**: api.protocols.file_protocol.FileProtocol._resolve, api.protocols.file_protocol.FileProtocol.fetch

### api.policy.PolicyDecision
- **Methods**: 2
- **Key Methods**: api.policy.PolicyDecision.allow, api.policy.PolicyDecision.deny

### api.commands.converttobase64.ConvertToBase64Command
- **Methods**: 1
- **Key Methods**: api.commands.converttobase64.ConvertToBase64Command.execute
- **Inherits**: Command

### api.commands.fetch.FetchCommand
- **Methods**: 1
- **Key Methods**: api.commands.fetch.FetchCommand.execute
- **Inherits**: Command

### api.protocols.data_protocol.DataProtocol
> Implements RFC 2397 data URIs: data:[<mime>][;base64],<data>.

Useful when callers want to pass inli
- **Methods**: 1
- **Key Methods**: api.protocols.data_protocol.DataProtocol.fetch

### api.queries.introspect.IntrospectQuery
- **Methods**: 1
- **Key Methods**: api.queries.introspect.IntrospectQuery.execute
- **Inherits**: Query

### api.queries.from_url.FromUrlQuery
- **Methods**: 1
- **Key Methods**: api.queries.from_url.FromUrlQuery.execute
- **Inherits**: Query

### api.commands.converttojson.ConvertToJsonCommand
- **Methods**: 1
- **Key Methods**: api.commands.converttojson.ConvertToJsonCommand.execute
- **Inherits**: Command

### api.queries.Query
- **Methods**: 1
- **Key Methods**: api.queries.Query.execute
- **Inherits**: abc.ABC

### api.commands.converttocsv.ConvertToCsvCommand
- **Methods**: 1
- **Key Methods**: api.commands.converttocsv.ConvertToCsvCommand.execute
- **Inherits**: Command

### api.commands.Command
- **Methods**: 1
- **Key Methods**: api.commands.Command.execute
- **Inherits**: abc.ABC

### api.policy.User
- **Methods**: 1
- **Key Methods**: api.policy.User.has_role

### api.commands.pipeline.PipelineCommand
- **Methods**: 1
- **Key Methods**: api.commands.pipeline.PipelineCommand.execute
- **Inherits**: Command

### api.commands.render.RenderCommand
- **Methods**: 1
- **Key Methods**: api.commands.render.RenderCommand.execute
- **Inherits**: Command

## Data Transformation Functions

Key functions that process and transform data:

### frontend.html.js.app.parseMeta
- **Output to**: frontend.html.js.app.trim, frontend.html.js.app.parse, frontend.html.js.app.Error

### frontend.html.js.app.decodeB64
- **Output to**: frontend.html.js.app.atob, frontend.html.js.app.Uint8Array, frontend.html.js.app.charCodeAt

### frontend.html.js.app.renderDecoded
- **Output to**: frontend.html.js.app.decodeB64, frontend.html.js.app.startsWith, frontend.html.js.app.createElement, frontend.html.js.app.TextDecoder, frontend.html.js.app.decode

### api.validators.validate_against_schema_uri
> Fetch a JSON Schema from the given URI and validate the instance.

The URI is resolved via the proto
- **Output to**: Draft202012Validator, sorted, json.loads, validator.iter_errors, SchemaValidationError

### cqrs-backend-workflows.server.validate_workflow
> Validate workflow against JSON Schema
- **Output to**: jsonschema.validate, HTTPException

## Behavioral Patterns

### recursion__substitute
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: api.commands.pipeline._substitute

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `api.commands.converttojson.ConvertToJsonCommand.execute` - 27 calls
- `api.commands.converttocsv.ConvertToCsvCommand.execute` - 23 calls
- `api.commands.render.RenderCommand.execute` - 22 calls
- `api.commands.converttoxml.ConvertToXmlCommand.execute` - 21 calls
- `api.config.load_settings` - 17 calls
- `api.commands.register_default_commands` - 15 calls
- `cqrs-backend-workflows.server.run_workflow` - 15 calls
- `frontend.html.js.api.API` - 14 calls
- `api.queries.from_url.FromUrlQuery.execute` - 13 calls
- `api.commands.pipeline.PipelineCommand.execute` - 13 calls
- `api.validators.validate_against_schema_uri` - 13 calls
- `cqrs-backend-workflows.server.execute_node` - 13 calls
- `cqrs-workflow-editor.src.App.fetchPreview` - 11 calls
- `api.main.execute_command` - 11 calls
- `api.policy.PolicyEngine.can_execute_query` - 11 calls
- `frontend.html.js.app.renderDecoded` - 10 calls
- `api.commands.converttobase64.ConvertToBase64Command.execute` - 10 calls
- `api.protocols.file_protocol.FileProtocol.fetch` - 10 calls
- `api.policy.PolicyEngine.can_execute_command` - 10 calls
- `frontend.html.js.app.bytes` - 9 calls
- `api.protocols.http_protocol.HttpProtocol.fetch` - 9 calls
- `api.main.execute_query` - 9 calls
- `api.protocols.data_protocol.DataProtocol.fetch` - 9 calls
- `api.protocols.register_default_protocols` - 9 calls
- `frontend.html.js.api.request` - 8 calls
- `cqrs-workflow-editor.src.App.onUploadWorkflow` - 8 calls
- `api.auth.JWTManager.issue` - 8 calls
- `api.policy.PolicyEngine.from_file` - 8 calls
- `cqrs-workflow-editor.src.App.workflow` - 7 calls
- `api.commands.fetch.FetchCommand.execute` - 7 calls
- `api.main.catalog` - 7 calls
- `api.main.run_agent` - 7 calls
- `api.queries.introspect.IntrospectQuery.execute` - 7 calls
- `api.auth.current_user` - 7 calls
- `api.protocols.ProtocolRegistry.fetch` - 7 calls
- `cqrs-workflow-editor.src.App.onDownloadWorkflow` - 6 calls
- `cqrs-workflow-editor.src.App.file` - 6 calls
- `cqrs-workflow-editor.src.App.reader` - 6 calls
- `api.main.issue_token` - 6 calls
- `frontend.html.js.app.loadCatalog` - 5 calls

## System Interactions

How components interact:

```mermaid
graph TD
    _mcp_execute --> get
    _mcp_execute --> AgentResponse
    _mcp_execute --> append
    execute --> get
    execute --> lower
    execute --> decode
    execute --> encode
    execute --> CommandResponse
    execute --> loads
    execute --> StringIO
    execute --> DictWriter
    execute --> writeheader
    _litellm_execute --> get
    execute --> Environment
    execute --> from_string
    execute --> render
    _bash_cli_execute --> get
    _bash_cli_execute --> AgentResponse
    execute --> isinstance
    execute --> unparse
    _websocket_execute --> get
    _websocket_execute --> float
    _websocket_execute --> dumps
    _websocket_execute --> AgentResponse
    _resolve --> urlparse
    _resolve --> unquote
    _resolve --> resolve
    _resolve --> ValueError
    load_settings --> get
    load_settings --> Settings
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.
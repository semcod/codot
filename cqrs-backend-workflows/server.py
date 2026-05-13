"""
Workflow API Server - Integrates with codot CQRS API
Provides CRUD endpoints for workflows and execution engine
"""

from typing import Dict, List, Any, Optional
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jsonschema
from pathlib import Path
import os

app = FastAPI(title="codot Workflow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load JSON Schema for validation
SCHEMA_PATH = Path(__file__).parent / "workflow.schema.json"
with open(SCHEMA_PATH, "r") as f:
    WORKFLOW_SCHEMA = json.load(f)

# Configuration
CODOT_API_URL = os.environ.get(
    "CODOT_API_URL", os.environ.get("API_BASE_URL", "http://localhost:18080")
)
_DATA_PORT = os.environ.get("DATA_PORT", "18091")
_SCHEMAS_PORT = os.environ.get("SCHEMAS_PORT", "18090")
workflow_store: Dict[str, Dict[str, Any]] = {
    "example": {
        "version": "1.0",
        "nodes": [
            {
                "id": "fetch1",
                "label": "Fetch CSV",
                "type": "fetch",
                "uri": f"http://localhost:{_DATA_PORT}/products.csv",
                "mime_type": "text/csv",
                "description": "Get CSV from local data server",
            },
            {
                "id": "convert1",
                "label": "Convert to JSON",
                "type": "command",
                "command_type": "converttojson",
                "input": "fetch1",
                "schema_uri": f"http://localhost:{_SCHEMAS_PORT}/public-products.json",
                "description": "Convert CSV to JSON table",
            },
            {
                "id": "render_table1",
                "label": "Render CSV Table HTML",
                "type": "command",
                "command_type": "render",
                "input": "convert1",
                "mime_type": "text/html",
                "description": "Generate HTML table",
                "meta": {"title": "Products Table"},
            },
        ],
        "outputs": [{"id": "csv_view", "label": "CSV View", "source": "render_table1"}],
    }
}


# Pydantic models
class WorkflowNode(BaseModel):
    id: str
    label: str
    type: str
    uri: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    command_type: Optional[str] = None
    input: Optional[str] = None
    inputs: Optional[List[str]] = None
    schema_uri: Optional[str] = None
    mime_type: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    goal: Optional[str] = None
    tools: Optional[List[str]] = None
    backend: Optional[str] = None
    backend_config: Optional[Dict[str, Any]] = None
    memory_uri: Optional[str] = None


class WorkflowOutput(BaseModel):
    id: str
    label: Optional[str] = None
    source: str
    description: Optional[str] = None


class Workflow(BaseModel):
    version: str
    nodes: List[WorkflowNode]
    outputs: List[WorkflowOutput]
    ui: Optional[Dict[str, Any]] = None


class WorkflowExecutionRequest(BaseModel):
    workflow_id: str
    token: Optional[str] = None


class WorkflowExecutionResponse(BaseModel):
    success: bool
    outputs: Dict[str, Any]
    trace: List[Dict[str, Any]]
    error: Optional[str] = None


# Helper functions
def validate_workflow(workflow: Dict[str, Any]) -> bool:
    """Validate workflow against JSON Schema"""
    try:
        jsonschema.validate(instance=workflow, schema=WORKFLOW_SCHEMA)
        return True
    except jsonschema.ValidationError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid workflow schema: {e.message}"
        )


def _result_to_data_uri(prev_result: Dict[str, Any]) -> str | None:
    """Convert a previous node result payload into a data: URI."""
    if prev_result.get("payload_b64"):
        mime = prev_result.get("mime", "application/octet-stream")
        return f"data:{mime};base64,{prev_result['payload_b64']}"
    return None


async def _handle_fetch(
    node: WorkflowNode,
    _node_results: Dict[str, Any],
    headers: Dict[str, str],
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    body = {"input_uri": node.uri or node.url, "meta": {}}
    response = await client.put(
        f"{CODOT_API_URL}/commands/fetch", json=body, headers=headers
    )
    return response.json()


async def _handle_http(
    node: WorkflowNode,
    _node_results: Dict[str, Any],
    headers: Dict[str, str],
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    body = {"input_uri": node.url, "meta": {"method": node.method or "GET"}}
    if node.headers:
        body["meta"]["headers"] = node.headers
    response = await client.put(
        f"{CODOT_API_URL}/commands/fetch", json=body, headers=headers
    )
    return response.json()


async def _handle_command(
    node: WorkflowNode,
    node_results: Dict[str, Any],
    headers: Dict[str, str],
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    command_type = node.command_type or "fetch"
    input_uri = None
    if node.input and node.input in node_results:
        input_uri = _result_to_data_uri(node_results[node.input])

    body = {"input_uri": input_uri, "schema_uri": node.schema_uri, "meta": {}}
    if command_type == "converttojson":
        body["meta"]["mode"] = "csv"

    response = await client.put(
        f"{CODOT_API_URL}/commands/{command_type}", json=body, headers=headers
    )
    return response.json()


async def _handle_render(
    node: WorkflowNode,
    node_results: Dict[str, Any],
    headers: Dict[str, str],
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    input_uri = None
    if node.input and node.input in node_results:
        input_uri = _result_to_data_uri(node_results[node.input])

    body = {"input_uri": input_uri, "meta": {"title": "Rendered Output"}}
    response = await client.put(
        f"{CODOT_API_URL}/commands/render", json=body, headers=headers
    )
    return response.json()


def _decode_payload_b64(payload_b64: str) -> str | None:
    """Decode a base64 payload to text, or return None if it cannot be decoded."""
    if not payload_b64:
        return None
    import base64

    try:
        return base64.b64decode(payload_b64).decode("utf-8", errors="replace")
    except Exception:
        return None


def _build_agent_context(
    node: WorkflowNode, node_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Build the context dict passed to an agent from the previous node's result."""
    if not node.input or node.input not in node_results:
        return {}
    prev = node_results[node.input]
    decoded = _decode_payload_b64(prev.get("payload_b64", ""))
    if decoded is not None:
        return {"text": decoded}
    return {"previous_result": prev}


def _build_agent_body(node: WorkflowNode, context: Dict[str, Any]) -> Dict[str, Any]:
    """Build the JSON body sent to /agents/{id}/run."""
    return {
        "agent_node": {
            "id": node.id,
            "role": node.role or "agent",
            "goal": node.goal or "",
            "tools": node.tools or [],
            "backend": node.backend or "mcp",
            "backend_config": node.backend_config or {},
        },
        "context": context,
    }


async def _handle_agent(
    node: WorkflowNode,
    node_results: Dict[str, Any],
    headers: Dict[str, str],
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    context = _build_agent_context(node, node_results)
    body = _build_agent_body(node, context)
    response = await client.post(
        f"{CODOT_API_URL}/agents/{node.id}/run",
        json=body,
        headers=headers,
    )
    return response.json()


_NODE_HANDLERS: Dict[str, Any] = {
    "fetch": _handle_fetch,
    "http": _handle_http,
    "command": _handle_command,
    "render": _handle_render,
    "agent": _handle_agent,
}


async def execute_node(
    node: WorkflowNode,
    node_results: Dict[str, Any],
    client: httpx.AsyncClient,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a single workflow node by calling codot API"""
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    handler = _NODE_HANDLERS.get(node.type)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown node type: {node.type}")

    return await handler(node, node_results, headers, client)


# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "codot Workflow API",
        "version": "1.0.0",
        "codot_api": CODOT_API_URL,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/workflows")
async def list_workflows():
    """List all available workflows"""
    return {"workflows": list(workflow_store.keys())}


@app.get("/v1/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow by ID"""
    if workflow_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow_store[workflow_id]


@app.post("/v1/workflows")
async def create_workflow(workflow: Workflow):
    """Create a new workflow"""
    workflow_dict = workflow.model_dump(exclude_none=True)
    validate_workflow(workflow_dict)

    workflow_id = workflow_dict.get("id") or f"workflow_{len(workflow_store) + 1}"
    workflow_store[workflow_id] = workflow_dict

    return {"id": workflow_id, "status": "created"}


@app.put("/v1/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: Workflow):
    """Update an existing workflow"""
    if workflow_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow_dict = workflow.model_dump(exclude_none=True)
    validate_workflow(workflow_dict)

    workflow_store[workflow_id] = workflow_dict
    return {"id": workflow_id, "status": "updated"}


@app.delete("/v1/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    if workflow_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")

    del workflow_store[workflow_id]
    return {"id": workflow_id, "status": "deleted"}


@app.get("/v1/examples")
async def list_examples():
    """List example workflow files from examples/ folder"""
    examples_path = Path(__file__).parent / "examples"
    if not examples_path.exists():
        return {"files": []}

    files = sorted([f.name for f in examples_path.glob("*.json") if f.is_file()])
    return {"files": files}


@app.get("/v1/examples/{filename}")
async def get_example(filename: str):
    """Get example workflow file content"""
    examples_path = Path(__file__).parent / "examples"
    file_path = examples_path / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Example file not found")

    with open(file_path, "r") as f:
        return json.load(f)


@app.post("/v1/workflows/{workflow_id}/run")
async def run_workflow(workflow_id: str, request: WorkflowExecutionRequest):
    """Execute a workflow"""
    if workflow_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflow_store[workflow_id]
    node_results: Dict[str, Any] = {}
    trace: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient() as client:
            # Execute nodes in order
            for node_data in workflow["nodes"]:
                node = WorkflowNode(**node_data)

                trace_entry = {
                    "node_id": node.id,
                    "node_type": node.type,
                    "status": "running",
                }
                trace.append(trace_entry)

                try:
                    result = await execute_node(
                        node, node_results, client, request.token
                    )
                    node_results[node.id] = result
                    trace_entry["status"] = "completed"
                    trace_entry["mime"] = result.get("mime")
                except Exception as e:
                    trace_entry["status"] = "failed"
                    trace_entry["error"] = str(e)
                    raise HTTPException(
                        status_code=500, detail=f"Node {node.id} failed: {str(e)}"
                    )

        # Collect outputs
        outputs = {}
        for output_def in workflow.get("outputs", []):
            source_node = output_def.get("source")
            if source_node in node_results:
                outputs[output_def["id"]] = node_results[source_node]

        return WorkflowExecutionResponse(success=True, outputs=outputs, trace=trace)

    except HTTPException:
        raise
    except Exception as e:
        return WorkflowExecutionResponse(
            success=False, outputs={}, trace=trace, error=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

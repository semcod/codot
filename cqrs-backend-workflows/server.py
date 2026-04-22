"""
Workflow API Server - Integrates with codot CQRS API
Provides CRUD endpoints for workflows and execution engine
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jsonschema
from pathlib import Path

app = FastAPI(title="codot Workflow API", version="1.0.0")

# Load JSON Schema for validation
SCHEMA_PATH = Path(__file__).parent / "workflow.schema.json"
with open(SCHEMA_PATH, "r") as f:
    WORKFLOW_SCHEMA = json.load(f)

# Configuration
CODOT_API_URL = "http://localhost:18080"
workflow_store: Dict[str, Dict[str, Any]] = {
    "example": {
        "version": "1.0",
        "nodes": [
            {
                "id": "fetch1",
                "label": "Fetch CSV",
                "type": "fetch",
                "uri": "http://localhost:18091/products.csv",
                "mime_type": "text/csv",
                "description": "Get CSV from local data server"
            },
            {
                "id": "convert1",
                "label": "Convert to JSON",
                "type": "command",
                "command_type": "converttojson",
                "input": "fetch1",
                "schema_uri": "http://localhost:18090/public-products.json",
                "description": "Convert CSV to JSON table"
            },
            {
                "id": "render_table1",
                "label": "Render CSV Table HTML",
                "type": "command",
                "command_type": "render",
                "input": "convert1",
                "mime_type": "text/html",
                "description": "Generate HTML table",
                "meta": {"title": "Products Table"}
            }
        ],
        "outputs": [
            {"id": "csv_view", "label": "CSV View", "source": "render_table1"}
        ]
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
        raise HTTPException(status_code=400, detail=f"Invalid workflow schema: {e.message}")


async def execute_node(
    node: WorkflowNode,
    node_results: Dict[str, Any],
    client: httpx.AsyncClient,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a single workflow node by calling codot API"""
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    if node.type == "fetch":
        # Use fetch command
        body = {
            "input_uri": node.uri or node.url,
            "meta": {}
        }
        response = await client.put(
            f"{CODOT_API_URL}/commands/fetch",
            json=body,
            headers=headers
        )
        return response.json()
    
    elif node.type == "http":
        # Use fetch command with HTTP URL
        body = {
            "input_uri": node.url,
            "meta": {"method": node.method or "GET"}
        }
        if node.headers:
            body["meta"]["headers"] = node.headers
        response = await client.put(
            f"{CODOT_API_URL}/commands/fetch",
            json=body,
            headers=headers
        )
        return response.json()
    
    elif node.type == "command":
        # Execute command via pipeline or direct command
        command_type = node.command_type or "fetch"
        
        # Build input_uri from previous node results
        input_uri = None
        if node.input and node.input in node_results:
            # Convert previous result to data: URI
            prev_result = node_results[node.input]
            if prev_result.get("payload_b64"):
                mime = prev_result.get("mime", "application/octet-stream")
                input_uri = f"data:{mime};base64,{prev_result['payload_b64']}"
        
        body = {
            "input_uri": input_uri,
            "schema_uri": node.schema_uri,
            "meta": {}
        }
        
        if command_type == "converttojson":
            body["meta"]["mode"] = "csv"
        
        response = await client.put(
            f"{CODOT_API_URL}/commands/{command_type}",
            json=body,
            headers=headers
        )
        return response.json()
    
    elif node.type == "render":
        # Render command
        input_uri = None
        if node.input and node.input in node_results:
            prev_result = node_results[node.input]
            if prev_result.get("payload_b64"):
                mime = prev_result.get("mime", "application/octet-stream")
                input_uri = f"data:{mime};base64,{prev_result['payload_b64']}"
        
        body = {
            "input_uri": input_uri,
            "meta": {"title": "Rendered Output"}
        }
        
        response = await client.put(
            f"{CODOT_API_URL}/commands/render",
            json=body,
            headers=headers
        )
        return response.json()
    
    elif node.type == "agent":
        # Agent node - for multi-agent orchestration
        return {
            "ok": True,
            "payload_b64": "",
            "mime": "text/plain",
            "meta": {
                "agent_role": node.role,
                "agent_goal": node.goal,
                "agent_tools": node.tools,
                "message": "Agent execution not yet fully implemented"
            }
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown node type: {node.type}")


# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "codot Workflow API",
        "version": "1.0.0",
        "codot_api": CODOT_API_URL
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
    workflow_dict = workflow.model_dump()
    validate_workflow(workflow_dict)
    
    workflow_id = workflow_dict.get("id") or f"workflow_{len(workflow_store) + 1}"
    workflow_store[workflow_id] = workflow_dict
    
    return {"id": workflow_id, "status": "created"}


@app.put("/v1/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: Workflow):
    """Update an existing workflow"""
    if workflow_id not in workflow_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow_dict = workflow.model_dump()
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
                    "status": "running"
                }
                trace.append(trace_entry)
                
                try:
                    result = await execute_node(node, node_results, client, request.token)
                    node_results[node.id] = result
                    trace_entry["status"] = "completed"
                    trace_entry["mime"] = result.get("mime")
                except Exception as e:
                    trace_entry["status"] = "failed"
                    trace_entry["error"] = str(e)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Node {node.id} failed: {str(e)}"
                    )
        
        # Collect outputs
        outputs = {}
        for output_def in workflow.get("outputs", []):
            source_node = output_def.get("source")
            if source_node in node_results:
                outputs[output_def["id"]] = node_results[source_node]
        
        return WorkflowExecutionResponse(
            success=True,
            outputs=outputs,
            trace=trace
        )
    
    except HTTPException:
        raise
    except Exception as e:
        return WorkflowExecutionResponse(
            success=False,
            outputs={},
            trace=trace,
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
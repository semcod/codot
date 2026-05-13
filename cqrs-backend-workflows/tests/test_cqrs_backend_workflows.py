"""Tests for cqrs-backend-workflows server."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_placeholder():
    """Placeholder test to verify the test setup works."""
    assert True


def test_import():
    """Verify the server module can be imported."""
    import server  # noqa: F401


def test_agent_node_fields():
    """Verify WorkflowNode accepts agent-specific fields."""
    from server import WorkflowNode

    node = WorkflowNode(
        id="agent1",
        label="Test Agent",
        type="agent",
        role="tester",
        goal="test",
        tools=["summarize"],
        backend="mcp",
        backend_config={"stdio_command": ["python3", "server.py"]},
    )
    assert node.backend == "mcp"
    assert node.backend_config == {"stdio_command": ["python3", "server.py"]}


def test_workflow_schema_validation():
    """Verify example workflow with agent passes schema validation."""
    import json
    from server import validate_workflow

    path = os.path.join(
        os.path.dirname(__file__), "..", "examples", "04-agent-research-pipeline.json"
    )
    with open(path) as f:
        wf = json.load(f)
    validate_workflow(wf)  # should not raise

import React, { useCallback, useState, useEffect } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  Node,
  Edge,
  Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { PrismAsync as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// Node palette configuration
const NODE_TYPES = [
  { type: "fetch", label: "Fetch", color: "#3b82f6" },
  { type: "http", label: "HTTP", color: "#10b981" },
  { type: "command", label: "Command", color: "#f59e0b" },
  { type: "query", label: "Query", color: "#8b5cf6" },
  { type: "render", label: "Render", color: "#ec4899" },
  { type: "agent", label: "Agent", color: "#6366f1" },
];

// Types matching your DAG-JSON workflow

type WorkflowNode = {
  id: string;
  label: string;
  type: "fetch" | "http" | "command" | "query" | "render" | "agent" | "group";
  uri?: string;
  method?: "GET" | "POST" | "PUT" | "DELETE";
  url?: string;
  headers?: Record<string, string>;
  command_type?: string;
  input?: string;
  inputs?: string[];
  schema_uri?: string;
  mime_type?: string;
  description?: string;
  role?: string;
  goal?: string;
  tools?: string[];
  memory_uri?: string;
};

type Workflow = {
  version: string;
  nodes: WorkflowNode[];
  outputs: { id: string; source: string }[];
};

// Minimal default workflow
const defaultWorkflow: Workflow = {
  version: "1.0",
  nodes: [
    {
      id: "fetch1",
      label: "Fetch CSV",
      type: "fetch",
      uri: "http://localhost:18091/products.csv",
      mime_type: "text/csv",
    },
  ],
  outputs: [
    { id: "default", source: "fetch1" },
  ],
};

// Map workflow.nodes to ReactFlow nodes
type RFNode = Node & { 
  data: WorkflowNode;
};

type RFEdge = Edge & {
  animated?: boolean;
};

const mapToNodes = (nodes: WorkflowNode[]): RFNode[] => {
  return nodes.map((n, index) => ({
    id: n.id,
    type: "default",
    position: { x: 20, y: 20 + index * 110 },
    data: n,
  }));
};

const mapToEdges = (nodes: WorkflowNode[]): RFEdge[] => {
  const edges: RFEdge[] = [];
  for (const node of nodes) {
    if (node.input) {
      edges.push({
        id: `e-${node.id}-${node.input}`,
        source: node.input,
        target: node.id,
      });
    }
    if (node.inputs) {
      node.inputs.forEach((src) => {
        edges.push({
          id: `e-${node.id}-${src}`,
          source: src,
          target: node.id,
        });
      });
    }
  }
  return edges;
};

function rewritePreviewUri(uri: string): string {
  if (uri.startsWith("http://localhost:18091/")) {
    return uri.replace("http://localhost:18091/", "/data/");
  }
  if (uri.startsWith("http://localhost:18090/")) {
    return uri.replace("http://localhost:18090/", "/schemas/");
  }
  return uri;
}

async function formatPreviewContent(blob: Blob, response: Response) {
  const sizeKB = (blob.size / 1024).toFixed(2);
  const mime = blob.type || response.headers.get("content-type") || "unknown";
  let content = "";
  if (blob.size < 10000) {
    const text = await blob.text();
    content = text.length > 500 ? text.substring(0, 500) + "..." : text;
  } else {
    content = `(Preview skipped - file too large: ${sizeKB} KB)`;
  }
  return { content, mime, size: parseFloat(sizeKB) };
}

function getPreviewErrorMessage(err: unknown): string {
  const msg = err instanceof Error ? err.message : "Failed to fetch";
  if (msg === "Failed to fetch") {
    return "CORS blocked or network error. Preview unavailable for cross-origin URLs, but workflow execution will work via backend.";
  }
  return msg;
}

export default function App() {
  const { screenToFlowPosition, setViewport } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<RFNode>(
    mapToNodes(defaultWorkflow.nodes)
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(mapToEdges(defaultWorkflow.nodes));
  const initialNodes = mapToNodes(defaultWorkflow.nodes);
  const [selectedNode, setSelectedNode] = useState<RFNode | null>(null);
  const [preview, setPreview] = useState<{ content: string; mime: string; size: number } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [workflowId, setWorkflowId] = useState<string>("current");
  const [runResult, setRunResult] = useState<string | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [backendWorkflows, setBackendWorkflows] = useState<string[]>([]);
  const [backendWorkflowsLoading, setBackendWorkflowsLoading] = useState(false);
  const [exampleFiles, setExampleFiles] = useState<string[]>([]);
  const [exampleFilesLoading, setExampleFilesLoading] = useState(false);

  // Fetch workflows list from backend
  const fetchBackendWorkflows = async () => {
    setBackendWorkflowsLoading(true);
    try {
      const res = await fetch("/api/v1/workflows");
      if (res.ok) {
        const data = await res.json();
        setBackendWorkflows(data.workflows || []);
      }
    } catch (err) {
      console.error("Failed to fetch workflows list", err);
    } finally {
      setBackendWorkflowsLoading(false);
    }
  };

  // Load workflow from backend
  const loadBackendWorkflow = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/workflows/${id}`);
      if (res.ok) {
        const wf = await res.json();
        setNodes(mapToNodes(wf.nodes));
        setEdges(mapToEdges(wf.nodes));
        setWorkflowId(id);
        setRunResult(null);
        setSelectedNode(null);
        setViewport({ x: 0, y: 0, zoom: 1 });
      }
    } catch (err) {
      alert("Failed to load workflow");
    }
  };

  // Run workflow from backend
  const runBackendWorkflow = async (id: string) => {
    setRunLoading(true);
    setRunResult(null);
    try {
      const res = await fetch(`/api/v1/workflows/${id}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow_id: id }),
      });
      const result = await res.json();
      setRunResult(JSON.stringify(result, null, 2));
    } catch (err) {
      setRunResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setRunLoading(false);
    }
  };

  // Load workflows list on mount
  useEffect(() => {
    fetchBackendWorkflows();
    fetchExampleFiles();
  }, []);

  // Delete selected node with keyboard
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === "Delete" || e.key === "Backspace") && selectedNode) {
        e.preventDefault();
        setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
        setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
        setSelectedNode(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedNode]);

  // Fetch example files list from backend
  const fetchExampleFiles = async () => {
    setExampleFilesLoading(true);
    try {
      const res = await fetch("/api/v1/examples");
      if (res.ok) {
        const data = await res.json();
        setExampleFiles(data.files || []);
      }
    } catch (err) {
      console.error("Failed to fetch example files list", err);
    } finally {
      setExampleFilesLoading(false);
    }
  };

  // Load example file to editor
  const loadExampleFile = async (filename: string) => {
    try {
      const res = await fetch(`/api/v1/examples/${filename}`);
      if (res.ok) {
        const wf = await res.json();
        setNodes(mapToNodes(wf.nodes));
        setEdges(mapToEdges(wf.nodes));
        setWorkflowId(filename);
        setRunResult(null);
        setSelectedNode(null);
        setViewport({ x: 0, y: 0, zoom: 1 });
      }
    } catch (err) {
      alert("Failed to load example file");
    }
  };

  const loadPredefinedWorkflow = (name: string) => {
    const predefined: Record<string, Workflow> = {
      basic_csv_pipeline: {
        version: "1.0",
        nodes: [
          { id: "fetch1", label: "Fetch CSV", type: "fetch", uri: "http://localhost:18091/products.csv", mime_type: "text/csv" },
          { id: "convert1", label: "Convert to JSON", type: "command", command_type: "converttojson", input: "fetch1", schema_uri: "http://localhost:18090/public-products.json" },
          { id: "render1", label: "Render Table", type: "render", input: "convert1" },
        ],
        outputs: [{ id: "csv_view", source: "render1" }],
      },
      http_fetch_pipeline: {
        version: "1.0",
        nodes: [
          { id: "http1", label: "Get API Data", type: "http", url: "http://localhost:18080/health", method: "GET" },
          { id: "render1", label: "Render Response", type: "render", input: "http1" },
        ],
        outputs: [{ id: "api_view", source: "render1" }],
      },
    };
    const wf = predefined[name];
    if (!wf) return;
    setNodes(mapToNodes(wf.nodes));
    setEdges(mapToEdges(wf.nodes));
    setRunResult(null);
    setSelectedNode(null);
    setViewport({ x: 0, y: 0, zoom: 1 });
  };

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge(params, eds));
    },
    [setEdges]
  );

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNode(node as RFNode);
    setPreview(null);
    setPreviewError(null);
  }, []);

  const onEdgeClick = useCallback((_: any, edge: Edge) => {
    setEdges((eds) => eds.filter((e) => e.id !== edge.id));
  }, [setEdges]);

  const updateNodeData = (field: string, value: any) => {
    if (!selectedNode) return;
    setNodes((nds) =>
      nds.map((n) =>
        n.id === selectedNode.id
          ? { ...n, data: { ...n.data, [field]: value } }
          : n
      )
    );
    setSelectedNode((prev) =>
      prev ? { ...prev, data: { ...prev.data, [field]: value } } : null
    );
  };

  const fetchPreview = async (uri: string) => {
    if (!uri) return;
    setPreviewLoading(true);
    setPreviewError(null);

    try {
      const response = await fetch(rewritePreviewUri(uri));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      setPreview(await formatPreviewContent(blob, response));
    } catch (err) {
      setPreviewError(getPreviewErrorMessage(err));
    } finally {
      setPreviewLoading(false);
    }
  };

  // Auto-fetch preview when URI changes for fetch nodes
  useEffect(() => {
    if (selectedNode?.data.type === "fetch" && selectedNode.data.uri) {
      const timer = setTimeout(() => {
        fetchPreview(selectedNode.data.uri!);
      }, 500); // Debounce 500ms to avoid too many requests
      return () => clearTimeout(timer);
    }
  }, [selectedNode?.data.uri]);

  // 1. Export workflow back to your JSON format
  const exportWorkflow = (): Workflow => {
    const wfNodes: WorkflowNode[] = nodes.map((n) => ({
      id: n.id,
      label: n.data.label,
      type: n.data.type as any,
      uri: n.data.uri,
      method: n.data.method,
      url: n.data.url,
      headers: n.data.headers,
      command_type: n.data.command_type,
      input: n.data.input,
      inputs: n.data.inputs,
      schema_uri: n.data.schema_uri,
      mime_type: n.data.mime_type,
      description: n.data.description,
      role: n.data.role,
      goal: n.data.goal,
      tools: n.data.tools,
      memory_uri: n.data.memory_uri,
    }));

    // In real app you'd store outputs in UI (e.g. "output nodes")
    const outputs = wfNodes
      .filter((n) => n.type.startsWith("render"))
      .map((n, i) => ({ id: `output-${i}`, source: n.id }));

    return {
      version: "1.0",
      nodes: wfNodes,
      outputs,
    };
  };

  const onDownloadWorkflow = () => {
    const workflow = exportWorkflow();
    const blob = new Blob([JSON.stringify(workflow, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workflow.json";
    a.click();
  };

  const onUploadWorkflow = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const json = JSON.parse(reader.result as string) as Workflow;

        const newNodes = mapToNodes(json.nodes);
        const newEdges = mapToEdges(json.nodes);

        setNodes(newNodes);
        setEdges(newEdges);
        setSelectedNode(null);
        setViewport({ x: 0, y: 0, zoom: 1 });
      } catch (err) {
        alert("Invalid JSON");
      }
    };
    reader.readAsText(file);
  };

  const onAddNode = (nodeType: string) => {
    const newId = `${nodeType}${nodes.length + 1}`;
    // Place at center of current viewport
    const center = screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
    });
    const newNode: RFNode = {
      id: newId,
      type: "default",
      position: { x: center.x, y: center.y },
      data: {
        id: newId,
        label: `${NODE_TYPES.find(t => t.type === nodeType)?.label || nodeType} ${nodes.length + 1}`,
        type: nodeType as any,
        description: ""
      },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  return (
    <div style={{ width: "100%", height: "100vh", display: "flex", overflow: "hidden" }}>
      {/* Node Palette Sidebar */}
      <div style={{ width: 180, padding: 8, background: "#f3f4f6", borderRight: "1px solid #e5e7eb", boxSizing: "border-box", overflowY: "auto" }}>
        <h3 style={{ marginTop: 0, marginBottom: 16 }}>Node Palette</h3>
        {NODE_TYPES.map((nt) => (
          <button
            key={nt.type}
            onClick={() => onAddNode(nt.type)}
            style={{
              width: "100%",
              padding: 8,
              marginBottom: 8,
              background: nt.color,
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {nt.label}
          </button>
        ))}
        <div style={{ marginTop: 24, borderTop: "1px solid #e5e7eb", paddingTop: 16 }}>
          <button onClick={onDownloadWorkflow} style={{ width: "100%", padding: 8, marginBottom: 8 }}>
            Export workflow
          </button>
          <input type="file" accept=".json" onChange={onUploadWorkflow} style={{ width: "100%", marginBottom: 8 }} />
          <div style={{ marginBottom: 8 }}>
            <strong style={{ fontSize: 12 }}>Predefined Workflows</strong>
            <button
              onClick={() => loadPredefinedWorkflow("basic_csv_pipeline")}
              style={{ width: "100%", padding: 6, marginTop: 4, fontSize: 11 }}
            >Basic CSV → JSON</button>
            <button
              onClick={() => loadPredefinedWorkflow("http_fetch_pipeline")}
              style={{ width: "100%", padding: 6, marginTop: 4, fontSize: 11 }}
            >HTTP Fetch</button>
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong style={{ fontSize: 12 }}>Example Files (examples/)</strong>
            {exampleFilesLoading && <div style={{ fontSize: 11, marginTop: 4 }}>Loading...</div>}
            {exampleFiles.length === 0 && !exampleFilesLoading && (
              <button onClick={fetchExampleFiles} style={{ width: "100%", padding: 6, marginTop: 4, fontSize: 11 }}>
                Refresh
              </button>
            )}
            {exampleFiles.map((filename) => (
              <div key={filename} style={{ marginTop: 4 }}>
                <button
                  onClick={() => loadExampleFile(filename)}
                  style={{ width: "100%", padding: 6, fontSize: 11 }}
                >
                  {filename}
                </button>
              </div>
            ))}
            {exampleFiles.length > 0 && (
              <button onClick={fetchExampleFiles} style={{ width: "100%", padding: 6, marginTop: 4, fontSize: 11 }}>
                Refresh
              </button>
            )}
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong style={{ fontSize: 12 }}>Backend Workflows</strong>
            {backendWorkflowsLoading && <div style={{ fontSize: 11, marginTop: 4 }}>Loading...</div>}
            {backendWorkflows.length === 0 && !backendWorkflowsLoading && (
              <button onClick={fetchBackendWorkflows} style={{ width: "100%", padding: 6, marginTop: 4, fontSize: 11 }}>
                Refresh
              </button>
            )}
            {backendWorkflows.map((id) => (
              <div key={id} style={{ marginTop: 4 }}>
                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                  <button
                    onClick={() => loadBackendWorkflow(id)}
                    style={{ flex: 1, padding: 6, fontSize: 11 }}
                  >
                    Load
                  </button>
                  <button
                    onClick={() => runBackendWorkflow(id)}
                    style={{ flex: 1, padding: 6, fontSize: 11, background: "#10b981", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}
                    disabled={runLoading}
                  >
                    {runLoading ? "..." : "Run"}
                  </button>
                </div>
                <div style={{ fontSize: 10, color: "#6b7280", marginTop: 2 }}>{id}</div>
              </div>
            ))}
            {backendWorkflows.length > 0 && (
              <button onClick={fetchBackendWorkflows} style={{ width: "100%", padding: 6, marginTop: 4, fontSize: 11 }}>
                Refresh
              </button>
            )}
          </div>
          <button
            onClick={() => {
              const workflow = exportWorkflow();
              console.log("Workflow JSON:", workflow);
            }}
            style={{ width: "100%", padding: 8, marginBottom: 8 }}
          >
            Log JSON
          </button>
          <button
            onClick={async () => {
              const workflow = exportWorkflow();
              setRunLoading(true);
              setRunResult(null);
              try {
                // Save workflow first
                const saveRes = await fetch(`/api/v1/workflows/${workflowId}`, {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(workflow),
                });
                if (!saveRes.ok) {
                  // If not found, create it
                  const createRes = await fetch(`/api/v1/workflows`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ ...workflow, id: workflowId }),
                  });
                  if (!createRes.ok) throw new Error("Failed to save workflow");
                }
                // Run workflow
                const runRes = await fetch(`/api/v1/workflows/${workflowId}/run`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ workflow_id: workflowId }),
                });
                const result = await runRes.json();
                setRunResult(JSON.stringify(result, null, 2));
              } catch (err) {
                setRunResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
              } finally {
                setRunLoading(false);
              }
            }}
            disabled={runLoading}
            style={{ width: "100%", padding: 8, background: "#10b981", color: "white", border: "none", borderRadius: 4, cursor: runLoading ? "not-allowed" : "pointer" }}
          >
            {runLoading ? "Running..." : "Save & Run"}
          </button>
        </div>
      </div>

      {/* Main Canvas */}
      <div style={{ flex: 1 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>

      {/* Property Editor Panel */}
      {selectedNode && (
        <div style={{ width: 340, padding: 8, background: "#f9fafb", borderLeft: "1px solid #e5e7eb", overflowY: "auto", boxSizing: "border-box" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ marginTop: 0, marginBottom: 0 }}>Properties</h3>
            <button
              onClick={() => setSelectedNode(null)}
              style={{ padding: 4, border: "1px solid #d1d5db", background: "white", borderRadius: 4, cursor: "pointer" }}
            >
              ×
            </button>
          </div>
          
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>ID</label>
            <input
              type="text"
              value={selectedNode.data.id}
              disabled
              style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4, background: "#f3f4f6" }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Label</label>
            <input
              type="text"
              value={selectedNode.data.label}
              onChange={(e) => updateNodeData("label", e.target.value)}
              style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Type</label>
            <input
              type="text"
              value={selectedNode.data.type}
              disabled
              style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4, background: "#f3f4f6" }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Description</label>
            <textarea
              value={selectedNode.data.description || ""}
              onChange={(e) => updateNodeData("description", e.target.value)}
              style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4, minHeight: 60 }}
            />
          </div>

          {selectedNode.data.type === "fetch" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>URI</label>
                <input
                  type="text"
                  value={selectedNode.data.uri || ""}
                  onChange={(e) => updateNodeData("uri", e.target.value)}
                  placeholder="file://, http://, https://, data:"
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              {previewLoading && (
                <div style={{ marginBottom: 12, padding: 8, background: "#dbeafe", color: "#1e40af", borderRadius: 4, fontSize: 11 }}>
                  Loading preview...
                </div>
              )}
              {preview && (
                <div style={{ marginBottom: 12, padding: 8, background: "#e5e7eb", borderRadius: 4, fontSize: 11 }}>
                  <div style={{ marginBottom: 4 }}><strong>MIME Type:</strong> {preview.mime}</div>
                  <div style={{ marginBottom: 4 }}><strong>Size:</strong> {preview.size} KB</div>
                  <div><strong>Content:</strong></div>
                  <pre style={{ marginTop: 4, whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 100, overflow: "auto" }}>{preview.content}</pre>
                </div>
              )}
              {previewError && (
                <div style={{ marginBottom: 12, padding: 8, background: "#fee2e2", color: "#991b1b", borderRadius: 4, fontSize: 11 }}>
                  <strong>Error:</strong> {previewError}
                </div>
              )}
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>MIME Type</label>
                <input
                  type="text"
                  value={selectedNode.data.mime_type || ""}
                  onChange={(e) => updateNodeData("mime_type", e.target.value)}
                  placeholder="text/csv, application/json, etc."
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
            </>
          )}

          {selectedNode.data.type === "http" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>URL</label>
                <input
                  type="text"
                  value={selectedNode.data.url || ""}
                  onChange={(e) => updateNodeData("url", e.target.value)}
                  placeholder="https://api.example.com/endpoint"
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Method</label>
                <select
                  value={selectedNode.data.method || "GET"}
                  onChange={(e) => updateNodeData("method", e.target.value)}
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                </select>
              </div>
            </>
          )}

          {selectedNode.data.type === "command" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Command Type</label>
                <input
                  type="text"
                  value={selectedNode.data.command_type || ""}
                  onChange={(e) => updateNodeData("command_type", e.target.value)}
                  placeholder="converttojson, render, etc."
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Input Node</label>
                <input
                  type="text"
                  value={selectedNode.data.input || ""}
                  onChange={(e) => updateNodeData("input", e.target.value)}
                  placeholder="Node ID to use as input"
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Schema URI</label>
                <input
                  type="text"
                  value={selectedNode.data.schema_uri || ""}
                  onChange={(e) => updateNodeData("schema_uri", e.target.value)}
                  placeholder="http://schemas.example.com/schema.json"
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
            </>
          )}

          {selectedNode.data.type === "agent" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Role</label>
                <input
                  type="text"
                  value={selectedNode.data.role || ""}
                  onChange={(e) => updateNodeData("role", e.target.value)}
                  placeholder="data-researcher, transformer, etc."
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Goal</label>
                <input
                  type="text"
                  value={selectedNode.data.goal || ""}
                  onChange={(e) => updateNodeData("goal", e.target.value)}
                  placeholder="What this agent should accomplish"
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: "bold", marginBottom: 4 }}>Tools (comma-separated)</label>
                <input
                  type="text"
                  value={selectedNode.data.tools?.join(", ") || ""}
                  onChange={(e) => updateNodeData("tools", e.target.value.split(", ").filter(t => t))}
                  placeholder="fetch, converttojson, render"
                  style={{ width: "100%", padding: 6, border: "1px solid #d1d5db", borderRadius: 4 }}
                />
              </div>
            </>
          )}
          {runResult && (
            <div style={{ marginTop: 16, borderTop: "1px solid #e5e7eb", paddingTop: 12 }}>
              <h4 style={{ marginTop: 0, marginBottom: 8, fontSize: 12 }}>Run Result</h4>
              <div style={{ padding: 8, background: "#e5e7eb", borderRadius: 4, fontSize: 11, maxHeight: 200, overflow: "auto" }}>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{runResult}</pre>
              </div>
            </div>
          )}
        </div>
      )}

      {!selectedNode && (
        <div style={{ width: 340, padding: 8, background: "#f9fafb", borderLeft: "1px solid #e5e7eb", boxSizing: "border-box", display: "flex", flexDirection: "column", height: "100vh" }}>
          <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: 14, flexShrink: 0 }}>Workflow JSON</h3>
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
            <SyntaxHighlighter
              language="json"
              style={oneDark}
              customStyle={{ fontSize: 10, margin: 0, borderRadius: 4 }}
              wrapLongLines
            >
              {JSON.stringify(exportWorkflow(), null, 2)}
            </SyntaxHighlighter>
          </div>
          {runResult && (
            <div style={{ marginTop: 16, flexShrink: 0 }}>
              <h4 style={{ marginTop: 0, marginBottom: 8, fontSize: 12 }}>Run Result</h4>
              <div style={{ padding: 8, background: "#e5e7eb", borderRadius: 4, fontSize: 11, maxHeight: 200, overflow: "auto" }}>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{runResult}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
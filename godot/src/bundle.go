package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/xeipuuv/gojsonschema"
	"go.temporal.io/sdk/client"
)

// Bundle matches bundle.schema.json 1:1
type Bundle struct {
	Bundle      string   `json:"bundle"`
	Kind        string   `json:"kind"`
	Version     string   `json:"version,omitempty"`
	Description string   `json:"description,omitempty"`
	SchemaURI   string   `json:"schema_uri"`
	Runner      string   `json:"runner"`
	Sources     []Source `json:"sources,omitempty"`
	Output      Output   `json:"output,omitempty"`
}

// Source matches sources array items in bundle.schema.json
type Source struct {
	Name       string   `json:"name"`
	URI        string   `json:"uri"`
	RefreshSec int      `json:"refresh_sec,omitempty"`
	DependsOn  []string `json:"depends_on,omitempty"`
}

// Output matches output object in bundle.schema.json
type Output struct {
	Format  string `json:"format"`
	Runtime *struct {
		Port int    `json:"port,omitempty"`
		Lang string `json:"lang,omitempty"`
	} `json:"runtime,omitempty"`
}

// LoadSchema fetches the schema from schema_uri and validates the bundle
func (b *Bundle) LoadSchema() error {
	log.Printf("Validating bundle %s against schema %s", b.Bundle, b.SchemaURI)

	// Fetch schema from URI
	schemaBytes, err := fetchSchema(b.SchemaURI)
	if err != nil {
		return fmt.Errorf("fetch schema: %w", err)
	}

	// Load schema
	schemaLoader := gojsonschema.NewBytesLoader(schemaBytes)
	documentLoader := gojsonschema.NewGoLoader(b)

	// Validate
	result, err := gojsonschema.Validate(schemaLoader, documentLoader)
	if err != nil {
		return fmt.Errorf("validation error: %w", err)
	}

	if !result.Valid() {
		return fmt.Errorf("bundle validation failed: %v", result.Errors())
	}

	log.Printf("Bundle %s validated successfully", b.Bundle)
	return nil
}

// Run executes the bundle using the specified runner
func (b *Bundle) Run(ctx context.Context) error {
	switch b.Runner {
	case "go_temporal":
		return b.runGoTemporal(ctx)
	case "python_fastapi":
		return b.runPythonFastAPI(ctx)
	default:
		return fmt.Errorf("unknown runner: %s", b.Runner)
	}
}

// runGoTemporal executes the bundle using Temporal workflow
func (b *Bundle) runGoTemporal(ctx context.Context) error {
	log.Printf("Running bundle %s with Temporal runner", b.Bundle)

	// Create Temporal client
	c, err := client.Dial(client.Options{})
	if err != nil {
		return fmt.Errorf("dial temporal: %w", err)
	}
	defer c.Close()

	// Execute workflow based on bundle kind
	workflowName := "DeployViewBundle"
	if b.Kind == "SERVICE_BUNDLE" {
		workflowName = "DeployServiceBundle"
	} else if b.Kind == "WORKFLOW_BUNDLE" {
		workflowName = "DeployWorkflowBundle"
	}

	w, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
		ID:        fmt.Sprintf("deploy-%s", b.Bundle),
		TaskQueue: "bundle-queue",
	}, workflowName, b)
	if err != nil {
		return fmt.Errorf("start workflow: %w", err)
	}

	var result string
	if err := w.Get(ctx, &result); err != nil {
		return fmt.Errorf("workflow result: %w", err)
	}

	log.Printf("Bundle %s deployed at: %s", b.Bundle, result)
	return nil
}

// runPythonFastAPI executes the bundle using Python FastAPI
func (b *Bundle) runPythonFastAPI(ctx context.Context) error {
	log.Printf("Starting Python FastAPI for bundle %s", b.Bundle)
	// TODO: Implement Python FastAPI runner
	// This would involve:
	// 1. Generating main.py from bundle
	// 2. Running uvicorn or docker
	return fmt.Errorf("python_fastapi runner not yet implemented")
}

// fetchSchema downloads the JSON schema from the given URI
func fetchSchema(uri string) ([]byte, error) {
	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	resp, err := client.Get(uri)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to fetch schema: HTTP %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}

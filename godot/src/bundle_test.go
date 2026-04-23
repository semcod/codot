package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestBundleSchemaValidation(t *testing.T) {
	// Test that all bundle JSONs can be unmarshaled into Bundle struct
	bundlesDir := "../bundles"
	entries, err := os.ReadDir(bundlesDir)
	if err != nil {
		t.Fatalf("Failed to read bundles directory: %v", err)
	}

	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}

		t.Run(entry.Name(), func(t *testing.T) {
			bundlePath := filepath.Join(bundlesDir, entry.Name())
			data, err := os.ReadFile(bundlePath)
			if err != nil {
				t.Fatalf("Failed to read bundle: %v", err)
			}

			var bundle Bundle
			if err := json.Unmarshal(data, &bundle); err != nil {
				t.Fatalf("Failed to unmarshal bundle: %v", err)
			}

			// Validate required fields
			if bundle.Bundle == "" {
				t.Error("bundle field is required")
			}
			if bundle.Kind == "" {
				t.Error("kind field is required")
			}
			if bundle.SchemaURI == "" {
				t.Error("schema_uri field is required")
			}
			if bundle.Runner == "" {
				t.Error("runner field is required")
			}

			// Validate kind enum
			validKinds := map[string]bool{
				"SERVICE_BUNDLE":  true,
				"VIEW_BUNDLE":     true,
				"WORKFLOW_BUNDLE": true,
			}
			if !validKinds[bundle.Kind] {
				t.Errorf("invalid kind: %s", bundle.Kind)
			}

			// Validate runner
			validRunners := map[string]bool{
				"go_temporal":      true,
				"python_fastapi":   true,
			}
			if !validRunners[bundle.Runner] {
				t.Errorf("invalid runner: %s", bundle.Runner)
			}

			t.Logf("✓ Bundle %s validated successfully", bundle.Bundle)
		})
	}
}

func TestSourceValidation(t *testing.T) {
	source := Source{
		Name:       "test-source",
		URI:        "http://example.com/api",
		RefreshSec: 5,
		DependsOn:  []string{"other-source"},
	}

	data, err := json.Marshal(source)
	if err != nil {
		t.Fatalf("Failed to marshal source: %v", err)
	}

	var unmarshaled Source
	if err := json.Unmarshal(data, &unmarshaled); err != nil {
		t.Fatalf("Failed to unmarshal source: %v", err)
	}

	if unmarshaled.Name != source.Name {
		t.Errorf("Name mismatch: got %s, want %s", unmarshaled.Name, source.Name)
	}
	if unmarshaled.URI != source.URI {
		t.Errorf("URI mismatch: got %s, want %s", unmarshaled.URI, source.URI)
	}
	if unmarshaled.RefreshSec != source.RefreshSec {
		t.Errorf("RefreshSec mismatch: got %d, want %d", unmarshaled.RefreshSec, source.RefreshSec)
	}
}

func TestOutputValidation(t *testing.T) {
	output := Output{
		Format: "php",
		Runtime: &struct {
			Port int    `json:"port,omitempty"`
			Lang string `json:"lang,omitempty"`
		}{
			Port: 8080,
			Lang: "go",
		},
	}

	data, err := json.Marshal(output)
	if err != nil {
		t.Fatalf("Failed to marshal output: %v", err)
	}

	var unmarshaled Output
	if err := json.Unmarshal(data, &unmarshaled); err != nil {
		t.Fatalf("Failed to unmarshal output: %v", err)
	}

	if unmarshaled.Format != output.Format {
		t.Errorf("Format mismatch: got %s, want %s", unmarshaled.Format, output.Format)
	}
	if unmarshaled.Runtime == nil {
		t.Error("Runtime should not be nil")
	} else {
		if unmarshaled.Runtime.Port != output.Runtime.Port {
			t.Errorf("Port mismatch: got %d, want %d", unmarshaled.Runtime.Port, output.Runtime.Port)
		}
	}
}

func TestBundleUnmarshal(t *testing.T) {
	bundleJSON := `{
		"bundle": "test-bundle",
		"kind": "SERVICE_BUNDLE",
		"version": "1.0.0",
		"description": "Test bundle",
		"schema_uri": "https://example.com/bundle.schema.json",
		"runner": "go_temporal",
		"sources": [
			{
				"name": "test",
				"uri": "http://example.com",
				"refresh_sec": 10
			}
		],
		"output": {
			"format": "php",
			"runtime": {
				"port": 8080
			}
		}
	}`

	var bundle Bundle
	if err := json.Unmarshal([]byte(bundleJSON), &bundle); err != nil {
		t.Fatalf("Failed to unmarshal bundle: %v", err)
	}

	if bundle.Bundle != "test-bundle" {
		t.Errorf("Bundle mismatch: got %s, want test-bundle", bundle.Bundle)
	}
	if bundle.Kind != "SERVICE_BUNDLE" {
		t.Errorf("Kind mismatch: got %s, want SERVICE_BUNDLE", bundle.Kind)
	}
	if len(bundle.Sources) != 1 {
		t.Errorf("Sources count mismatch: got %d, want 1", len(bundle.Sources))
	}
}

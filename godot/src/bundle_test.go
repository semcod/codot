package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"
)

var validBundleKinds = map[string]struct{}{
	"SERVICE_BUNDLE":      {},
	"VIEW_BUNDLE":         {},
	"WORKFLOW_BUNDLE":     {},
	"APPLICATION_BUNDLE":  {},
}

var validTargets = map[string]struct{}{
	"desktop": {},
	"mobile":  {},
	"web":     {},
	"pwa":     {},
	"service": {},
	"cli":     {},
}

func collectBundleFiles(root string) ([]string, error) {
	var files []string
	if err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		if filepath.Ext(path) == ".json" {
			files = append(files, path)
		}
		return nil
	}); err != nil {
		return nil, err
	}
	sort.Strings(files)
	return files, nil
}

func validateBundleData(t *testing.T, bundlePath string) {
	t.Helper()
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

	if _, ok := validBundleKinds[bundle.Kind]; !ok {
		t.Errorf("invalid kind: %s", bundle.Kind)
	}

	validRunners := map[string]struct{}{
		"go_temporal":    {},
		"python_fastapi": {},
	}
	if _, ok := validRunners[bundle.Runner]; !ok {
		t.Errorf("invalid runner: %s", bundle.Runner)
	}

	if bundle.Kind == "APPLICATION_BUNDLE" && len(bundle.Targets) == 0 {
		t.Error("application bundles must declare at least one target")
	}
	for _, target := range bundle.Targets {
		if _, ok := validTargets[target]; !ok {
			t.Errorf("invalid target: %s", target)
		}
	}

	if len(bundle.Sources) > 0 {
		for i, source := range bundle.Sources {
			if source.Name == "" {
				t.Errorf("source[%d].name is required", i)
			}
			if source.URI == "" {
				t.Errorf("source[%d].uri is required", i)
			}
			if source.RefreshSec <= 0 {
				t.Errorf("source[%d].refresh_sec must be > 0", i)
			}
		}
	}

	t.Logf("✓ Bundle %s validated successfully", bundle.Bundle)
}

func TestBundleSchemaValidation(t *testing.T) {
	bundlesDir := "../bundles"
	entries, err := collectBundleFiles(bundlesDir)
	if err != nil {
		t.Fatalf("Failed to read bundles directory: %v", err)
	}

	for _, bundlePath := range entries {
		bundlePath := bundlePath
		t.Run(filepath.Base(bundlePath), func(t *testing.T) {
			validateBundleData(t, bundlePath)
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

func TestResolvedSchemaURIFallback(t *testing.T) {
	t.Setenv("BUNDLE_SCHEMA_URI", "file:///tmp/test-bundle.schema.json")

	bundleWithPlaceholder := Bundle{SchemaURI: placeholderSchemaURI}
	if got := bundleWithPlaceholder.resolvedSchemaURI(); got != "file:///tmp/test-bundle.schema.json" {
		t.Fatalf("placeholder schema URI fallback mismatch: got %s", got)
	}

	bundleWithEmptySchema := Bundle{}
	if got := bundleWithEmptySchema.resolvedSchemaURI(); got != "file:///tmp/test-bundle.schema.json" {
		t.Fatalf("empty schema URI fallback mismatch: got %s", got)
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
		"targets": ["web"],
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
	if len(bundle.Targets) != 1 || bundle.Targets[0] != "web" {
		t.Errorf("Targets mismatch: got %#v, want [web]", bundle.Targets)
	}
}

func TestWorkflowNameForKindInBundle(t *testing.T) {
	cases := []struct {
		kind     string
		expected string
	}{
		{"SERVICE_BUNDLE", "DeployServiceBundle"},
		{"VIEW_BUNDLE", "DeployViewBundle"},
		{"WORKFLOW_BUNDLE", "DeployWorkflowBundle"},
		{"APPLICATION_BUNDLE", "DeployApplicationBundle"},
		{"UNKNOWN_BUNDLE", "DeployViewBundle"},
	}
	for _, tc := range cases {
		got := workflowNameForKindInBundle(tc.kind)
		if got != tc.expected {
			t.Errorf("workflowNameForKindInBundle(%q) = %q, want %q", tc.kind, got, tc.expected)
		}
	}
}

func TestFetchSchemaFileURI(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "test.json")
	content := []byte(`{"type":"object"}`)
	if err := os.WriteFile(path, content, 0644); err != nil {
		t.Fatal(err)
	}
	uri := "file://" + path
	got, err := fetchSchema(uri)
	if err != nil {
		t.Fatalf("fetchSchema(file://): %v", err)
	}
	if !bytes.Equal(got, content) {
		t.Errorf("fetchSchema(file://) = %q, want %q", got, content)
	}
}

func TestFetchSchemaHTTPNotFound(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer server.Close()
	_, err := fetchSchema(server.URL + "/404")
	if err == nil {
		t.Fatal("expected error for HTTP 404")
	}
	if !strings.Contains(err.Error(), "HTTP 404") {
		t.Errorf("expected HTTP 404 error, got %v", err)
	}
}

func TestLoadSchemaFileURI(t *testing.T) {
	tmp := t.TempDir()
	schemaPath := filepath.Join(tmp, "schema.json")
	schemaContent := []byte(`{"$schema": "http://json-schema.org/draft-07/schema#", "type": "object"}`)
	if err := os.WriteFile(schemaPath, schemaContent, 0644); err != nil {
		t.Fatal(err)
	}
	t.Setenv("BUNDLE_SCHEMA_URI", "file://"+schemaPath)
	b := Bundle{}
	if err := b.LoadSchema(); err != nil {
		t.Fatalf("LoadSchema(file://): %v", err)
	}
}

func TestResolvedSchemaURIEnv(t *testing.T) {
	envURI := "file:///custom/schema.json"
	t.Setenv("BUNDLE_SCHEMA_URI", envURI)
	b := Bundle{}
	got := b.resolvedSchemaURI()
	if got != envURI {
		t.Errorf("resolvedSchemaURI() = %q, want %q", got, envURI)
	}
}

func TestRunPythonFastAPIPlaceholder(t *testing.T) {
	b := Bundle{Bundle: "dummy.bundle"}
	err := b.runPythonFastAPI(context.Background())
	if err == nil {
		t.Fatal("runPythonFastAPI: expected error for unimplemented runner")
	}
	if err.Error() != "python_fastapi runner not yet implemented" {
		t.Errorf("runPythonFastAPI error = %q, want 'not yet implemented'", err)
	}
}

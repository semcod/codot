package main

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
)

func TestGenerateCodeActivity(t *testing.T) {
	cases := []struct {
		kind     string
		bundle   string
		expected string
	}{
		{"APPLICATION_BUNDLE", "TestApp", "/output/testapp.php"},
		{"SERVICE_BUNDLE", "Api", "/output/dashboard.php"},
		{"VIEW_BUNDLE", "Dashboard", "/output/dashboard.php"},
	}
	for _, tc := range cases {
		b := Bundle{Kind: tc.kind, Bundle: tc.bundle}
		data, _ := json.Marshal(b)
		got, err := GenerateCodeActivity(context.Background(), data)
		if err != nil {
			t.Fatalf("GenerateCodeActivity(%s): %v", tc.kind, err)
		}
		if !strings.Contains(got, tc.expected) {
			t.Errorf("GenerateCodeActivity(%s) = %q, want %q", tc.kind, got, tc.expected)
		}
	}
}

func TestGenerateCodeActivityInvalidJSON(t *testing.T) {
	_, err := GenerateCodeActivity(context.Background(), []byte(`{bad`))
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

func TestDeployServiceActivity(t *testing.T) {
	got, err := DeployServiceActivity(context.Background(), "/tmp/code", 8080)
	if err != nil {
		t.Fatalf("DeployServiceActivity: %v", err)
	}
	if got != "http://localhost:8080" {
		t.Errorf("DeployServiceActivity = %q, want http://localhost:8080", got)
	}
}

func TestCleanupActivity(t *testing.T) {
	if err := CleanupActivity(context.Background(), []string{"a", "b"}); err != nil {
		t.Fatalf("CleanupActivity: %v", err)
	}
}

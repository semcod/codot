package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/worker"
	"go.temporal.io/sdk/workflow"
)

type Bundle struct {
	Bundle      string   `json:"bundle"`
	Kind        string   `json:"kind"`
	SchemaURI   string   `json:"schema_uri"`
	Runner      string   `json:"runner"`
	Targets     []string `json:"targets,omitempty"`
	Sources     []Source `json:"sources"`
	Output      Output   `json:"output"`
}
type Source struct {
	URI       string   `json:"uri"`
	RefreshSec int      `json:"refresh_sec,omitempty"`
	DependsOn []string `json:"depends_on,omitempty"`
}
type Output struct {
	Format  string `json:"format"`
	Runtime *struct {
		Port int    `json:"port,omitempty"`
		Lang string `json:"lang,omitempty"`
	} `json:"runtime,omitempty"`
}

func DeployViewBundle(ctx workflow.Context, bundleJSON []byte) (string, error) {
	var b Bundle
	if err := json.Unmarshal(bundleJSON, &b); err != nil {
		return "", err
	}
	opts := workflow.ActivityOptions{StartToCloseTimeout: 5 * time.Minute}
	ctx = workflow.WithActivityOptions(ctx, opts)

	var codePath string
	if err := workflow.ExecuteActivity(ctx, GenerateCodeActivity, bundleJSON).Get(ctx, &codePath); err != nil {
		_ = workflow.ExecuteActivity(ctx, CleanupActivity, []string{codePath}).Get(ctx, nil)
		return "", fmt.Errorf("generate: %w", err)
	}
	port := 8082
	if b.Output.Runtime != nil && b.Output.Runtime.Port > 0 {
		port = b.Output.Runtime.Port
	}
	var svcURL string
	if err := workflow.ExecuteActivity(ctx, DeployServiceActivity, codePath, port).Get(ctx, &svcURL); err != nil {
		_ = workflow.ExecuteActivity(ctx, CleanupActivity, []string{codePath, svcURL}).Get(ctx, nil)
		return "", fmt.Errorf("deploy: %w", err)
	}
	if err := workflow.ExecuteActivity(ctx, HealthcheckActivity, svcURL, b.Sources).Get(ctx, nil); err != nil {
		_ = workflow.ExecuteActivity(ctx, CleanupActivity, []string{codePath, svcURL}).Get(ctx, nil)
		return "", fmt.Errorf("healthcheck: %w", err)
	}
	return svcURL, nil
}

func DeployServiceBundle(ctx workflow.Context, bundleJSON []byte) (string, error) {
	return DeployViewBundle(ctx, bundleJSON)
}

func DeployWorkflowBundle(ctx workflow.Context, bundleJSON []byte) (string, error) {
	return DeployViewBundle(ctx, bundleJSON)
}

func DeployApplicationBundle(ctx workflow.Context, bundleJSON []byte) (string, error) {
	return DeployViewBundle(ctx, bundleJSON)
}

// BuildAppWorkflow generates and builds a DOQL application from an APPLICATION_BUNDLE.
func BuildAppWorkflow(ctx workflow.Context, bundleJSON []byte) (string, error) {
	var b Bundle
	if err := json.Unmarshal(bundleJSON, &b); err != nil {
		return "", err
	}
	opts := workflow.ActivityOptions{StartToCloseTimeout: 10 * time.Minute}
	ctx = workflow.WithActivityOptions(ctx, opts)

	var buildDir string
	if err := workflow.ExecuteActivity(ctx, BuildDOQLActivity, bundleJSON, b.Bundle).Get(ctx, &buildDir); err != nil {
		return "", fmt.Errorf("doql build: %w", err)
	}
	return buildDir, nil
}

func GenerateCodeActivity(ctx context.Context, bundleJSON []byte) (string, error) {
	var b Bundle
	if err := json.Unmarshal(bundleJSON, &b); err != nil {
		return "", err
	}
	switch b.Kind {
	case "SERVICE_BUNDLE":
		return "/output/service.py", nil
	case "WORKFLOW_BUNDLE":
		return "/output/workflow.go", nil
	case "APPLICATION_BUNDLE":
		for _, target := range b.Targets {
			if target == "desktop" || target == "mobile" {
				return "/output/app-native/", nil
			}
		}
		return "/output/app-web/", nil
	default:
		return "/output/dashboard.php", nil
	}
}
func DeployServiceActivity(ctx context.Context, codePath string, port int) (string, error) {
	return fmt.Sprintf("http://localhost:%d", port), nil
}

// BuildDOQLActivity writes the bundle to a temp file, generates app.doql.css,
// and invokes the DOQL CLI to produce build artifacts.
func BuildDOQLActivity(ctx context.Context, bundleJSON []byte, bundleName string) (string, error) {
	// 1. Write bundle JSON to a temp file
	tmpFile := fmt.Sprintf("/tmp/buildapp-%s.json", bundleName)
	if err := os.WriteFile(tmpFile, bundleJSON, 0644); err != nil {
		return "", fmt.Errorf("write temp bundle: %w", err)
	}

	// 2. Determine project root (assumes this binary runs from src/)
	root, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("get wd: %w", err)
	}
	root = filepath.Dir(root) // go up from src/ to godot/

	// 3. Generate app.doql.css
	genCmd := exec.CommandContext(ctx, "python3", "scripts/bundle-to-doql.py", tmpFile)
	genCmd.Dir = root
	genCmd.Env = os.Environ()
	cssPath := filepath.Join(root, "generated", "app.doql.css")
	outFile, err := os.Create(cssPath)
	if err != nil {
		return "", fmt.Errorf("create css file: %w", err)
	}
	defer outFile.Close()
	genCmd.Stdout = outFile
	genCmd.Stderr = os.Stderr
	if err := genCmd.Run(); err != nil {
		return "", fmt.Errorf("generate doql: %w", err)
	}

	// 4. Build DOQL artifacts
	buildCmd := exec.CommandContext(ctx,
		"python3", "-m", "doql.cli",
		"-f", "generated/app.doql.css",
		"build",
	)
	buildCmd.Dir = root
	buildCmd.Env = os.Environ()
	buildCmd.Stdout = os.Stdout
	buildCmd.Stderr = os.Stderr
	if err := buildCmd.Run(); err != nil {
		return "", fmt.Errorf("doql build: %w", err)
	}

	buildDir := filepath.Join(root, "generated", "build")
	return buildDir, nil
}
func HealthcheckActivity(ctx context.Context, svcURL string, sources []Source) error {
	c := &http.Client{Timeout: 10 * time.Second}
	for _, s := range sources {
		resp, err := c.Get(s.URI)
		if err != nil || resp.StatusCode != 200 {
			return fmt.Errorf("source failed: %s", s.URI)
		}
	}
	return nil
}
func CleanupActivity(ctx context.Context, resources []string) error {
	return nil
}

func main() {
	c, err := client.Dial(client.Options{})
	if err != nil {
		log.Fatalln(err)
	}
	defer c.Close()
	w := worker.New(c, "view-bundle-queue", worker.Options{})
	w.RegisterWorkflow(DeployViewBundle)
	w.RegisterWorkflow(DeployServiceBundle)
	w.RegisterWorkflow(DeployWorkflowBundle)
	w.RegisterWorkflow(DeployApplicationBundle)
	w.RegisterWorkflow(BuildAppWorkflow)
	w.RegisterActivity(GenerateCodeActivity)
	w.RegisterActivity(DeployServiceActivity)
	w.RegisterActivity(HealthcheckActivity)
	w.RegisterActivity(CleanupActivity)
	w.RegisterActivity(BuildDOQLActivity)
	if err := w.Run(worker.InterruptCh()); err != nil {
		log.Fatalln(err)
	}
}

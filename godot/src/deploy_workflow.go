package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
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
	w.RegisterActivity(GenerateCodeActivity)
	w.RegisterActivity(DeployServiceActivity)
	w.RegisterActivity(HealthcheckActivity)
	w.RegisterActivity(CleanupActivity)
	if err := w.Run(worker.InterruptCh()); err != nil {
		log.Fatalln(err)
	}
}

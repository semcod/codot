package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"go.temporal.io/sdk/client"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "Usage: go run starter.go '<bundle-json>'")
		fmt.Fprintln(os.Stderr, "   or: go run starter.go @bundles/protocol-dashboard.json")
		os.Exit(1)
	}

	var bundleJSON []byte
	arg := os.Args[1]
	if len(arg) > 0 && arg[0] == '@' {
		var err error
		bundleJSON, err = os.ReadFile(arg[1:])
		if err != nil {
			log.Fatalf("read bundle file: %v", err)
		}
	} else {
		bundleJSON = []byte(arg)
	}

	c, err := client.Dial(client.Options{})
	if err != nil {
		log.Fatalf("dial temporal: %v", err)
	}
	defer c.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	w, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
		ID:        "deploy-protocol-dashboard",
		TaskQueue: "view-bundle-queue",
	}, "DeployViewBundle", bundleJSON)
	if err != nil {
		log.Fatalf("start workflow: %v", err)
	}

	var serviceURL string
	if err := w.Get(ctx, &serviceURL); err != nil {
		log.Fatalf("workflow result: %v", err)
	}

	fmt.Println("Deployed at:", serviceURL)
}

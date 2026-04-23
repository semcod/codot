.PHONY: all build run deploy validate validate-all test clean help

BUNDLE := bundles/protocol-dashboard.json
PORT   := $(shell python3 -c "import json; print(json.load(open('$(BUNDLE)'))['output']['port'])")

help:
	@echo "Targets:"
	@echo "  build        - validate bundle + check Go structs"
	@echo "  run          - start PHP dev server (generated/dashboard.php)"
	@echo "  deploy       - start Temporal worker + deploy bundle"
	@echo "  validate     - validate single JSON bundle"
	@echo "  validate-all - validate all bundle JSONs"
	@echo "  test         - run Go tests for bundle validation"
	@echo "  clean        - kill running processes"

all: build run

build:
	bash scripts/build.sh

validate:
	bash scripts/validate-bundle.sh $(BUNDLE)

validate-all:
	bash scripts/validate-all.sh

test:
	cd src && go test -v -run TestBundle

run:
	@echo "Starting PHP server on port $(PORT)..."
	cd generated && php -S 0.0.0.0:$(PORT) dashboard.php

run-bundle:
	bash scripts/run-bundle.sh $(BUNDLE)

deploy:
	@echo "Starting Temporal worker (background)..."
	cd src && go run deploy_workflow.go &
	@echo "Starting workflow with bundle $(BUNDLE)..."
	cd src && go run starter.go @../$(BUNDLE)

clean:
	-pkill -f "php -S 0.0.0.0"
	-pkill -f "go run deploy_workflow.go"
	@echo "Cleaned up"

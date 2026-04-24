.PHONY: all build run deploy validate validate-all test clean docker-build docker-test docker-up docker-down start stop restart quickstart llm-test help

-include .env
export

BUNDLE := bundles/protocol-dashboard.json
PORT   := $(shell python3 -c "import json; data=json.load(open('$(BUNDLE)')); output=data.get('output', {}); runtime=output.get('runtime'); print((runtime or {}).get('port', output.get('port', 8082)) if isinstance(runtime, dict) else output.get('port', 8082))")

help:
	@echo "Targets:"
	@echo "  start        - FULL START: cleanup, build, start services, test (RECOMMENDED)"
	@echo "  stop         - Stop all services and kill processes on ports"
	@echo "  restart      - Stop and start fresh"
	@echo "  status       - Check service status"
	@echo "  build        - validate bundle + check Go structs"
	@echo "  run          - start PHP dev server (generated/dashboard.php)"
	@echo "  deploy       - start Temporal worker + deploy bundle"
	@echo "  validate     - validate single JSON bundle"
	@echo "  validate-all - validate all bundle JSONs"
	@echo "  test         - run Go tests for bundle validation"
	@echo "  test-services - run stack readiness plus LLM/ACL integration tests"
	@echo "  llm-test     - run LiteLLM/ACL/bundle-generation tests"
	@echo "  docker-build - build Docker image"
	@echo "  docker-test  - run validation tests in Docker"
	@echo "  docker-up    - start services with docker-compose"
	@echo "  docker-down  - stop services with docker-compose"
	@echo "  quickstart   - alias for start"
	@echo "  clean        - kill running processes"
	@echo "  generate-doql - generate app.doql.css from a bundle"
	@echo "  build-doql   - build DOQL app from generated app.doql.css"
	@echo "  run-doql     - build and run DOQL app in background"
	@echo "  render-report - render HTML report from a bundle with sources"
	@echo "  test-practical - test LLM inference for all practical bundles"
	@echo "  test-buildapp - test BuildAppWorkflow (bundle → DOQL → build)"
	@echo "  test-audit     - verify Postgres audit_log after LLM generation"
	@echo "  pending-bundle - list/approve/reject bundles pending approval"
	@echo "  test-human-in-the-loop - test WORKFLOW_BUNDLE approval workflow"
	@echo "  test-prometheus - verify Prometheus/Grafana scrape of LLM metrics"
	@echo "  test-temporal-ui - verify Temporal Web UI, gRPC, and namespace API"

all: build run

build:
	bash scripts/build.sh

validate:
	bash scripts/validate-bundle.sh $(BUNDLE)

validate-all:
	bash scripts/validate-all.sh

test:
	cd src && GOFLAGS=-mod=mod go test -v bundle.go bundle_test.go

docker-build:
	docker build -t godot-bundle-service .

docker-test:
	docker run --rm godot-bundle-service bash scripts/validate-all.sh

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

stop:
	@echo "=== Stopping Godot Bundle System ==="
	-docker-compose down 2>/dev/null
	-docker rm -f godot-bundle-service godot-llm godot-mock-api temporal-server temporal-ui temporal-postgres schema-server 2>/dev/null
	@echo "Killing processes on ports..."
	-for port in $(GODOT_PORT_8080) $(GODOT_PORT_8081) $(GODOT_PORT_8082) $(GODOT_PORT_8083) $(LLM_PORT) $(MOCK_API_PORT) $(POSTGRES_PORT) $(TEMPORAL_PORT) $(TEMPORAL_UI_PORT) $(SCHEMA_SERVER_PORT); do \
		pid=$$(lsof -t -i:$$port 2>/dev/null) && kill -9 $$pid 2>/dev/null || true; \
	done
	@echo "✓ Stopped"

restart: stop start

status:
	@echo "=== Godot Bundle System Status ==="
	@echo "Docker containers:"
	@docker ps --filter name=godot --filter name=temporal --filter name=schema --filter name=mock-api --filter name=godot-llm --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers running"
	@echo ""
	@echo "Port status:"
	@for port in $(GODOT_PORT_8080) $(GODOT_PORT_8081) $(GODOT_PORT_8082) $(GODOT_PORT_8083) $(LLM_PORT) $(MOCK_API_PORT) $(POSTGRES_PORT) $(TEMPORAL_PORT) $(TEMPORAL_UI_PORT) $(SCHEMA_SERVER_PORT); do \
		if lsof -i:$$port >/dev/null 2>&1; then \
			echo "  Port $$port: ✓ in use"; \
		else \
			echo "  Port $$port: - free"; \
		fi \
	done
	@echo ""
	@echo "Logs: docker-compose logs -f"

start:
	@echo "=== Starting Godot Bundle System ==="
	@echo "Step 1: Cleaning up existing containers and ports..."
	$(MAKE) stop
	@echo ""
	@echo "Step 2: Building Docker image..."
	$(MAKE) docker-build
	@echo ""
	@echo "Step 3: Starting Docker services..."
	docker-compose up -d
	@echo ""
	@echo "Waiting for services to start..."
	@sleep 5
	@echo ""
	@echo "Step 4: Running service tests..."
	$(MAKE) test-services
	@echo ""
	@echo "=== Godot Bundle System is running ==="
	@echo ""
	@bash -c 'source .env && echo "Service URLs:" && \
		echo "  Schema Server:  http://localhost:$${SCHEMA_SERVER_PORT:-8084}/bundle.schema.json" && \
		echo "  Temporal gRPC:  localhost:$${TEMPORAL_PORT:-7233}" && \
		echo "  Temporal Web:   http://localhost:$${TEMPORAL_UI_PORT:-8233}" && \
		echo "  PostgreSQL:     localhost:$${POSTGRES_PORT:-5433}" && \
		echo "  LLM API:        http://localhost:$${LLM_PORT:-18094}/health" && \
		echo "  Mock API:       http://localhost:$${MOCK_API_PORT:-18095}/health"'
	@echo ""
	@echo "Useful commands:"
	@echo "  make stop     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make status   - Check service status"

quickstart:
	$(MAKE) start

test-services:
	bash scripts/test-services.sh
	bash scripts/test-llm.sh

llm-test:
	bash scripts/test-llm.sh

run:
	@echo "Starting PHP server on port $(PORT)..."
	cd generated && php -S 0.0.0.0:$(PORT) dashboard.php

run-bundle:
	bash scripts/run-bundle.sh $(BUNDLE)

deploy:
	@echo "Starting Temporal worker (background)..."
	cd src && GOFLAGS=-mod=mod go run deploy_workflow.go &
	@echo "Starting workflow with bundle $(BUNDLE)..."
	cd src && GOFLAGS=-mod=mod go run starter.go @../$(BUNDLE)

generate-doql:
	@echo "=== Generating DOQL app.doql.css from bundle ==="
	@python3 scripts/bundle-to-doql.py $(BUNDLE) > generated/app.doql.css
	@echo "✓ Generated: generated/app.doql.css"

build-doql: generate-doql
	@echo "=== Building DOQL application ==="
	@cd generated && /home/tom/github/oqlos/venv/bin/python -m doql.cli -f app.doql.css build
	@echo "✓ DOQL build complete in generated/build/"

run-doql: build-doql
	@echo "=== Running DOQL application ==="
	@cd generated && /home/tom/github/oqlos/venv/bin/python -m doql.cli -f app.doql.css run 2>&1 &
	@echo "✓ DOQL app running in background (see generated/)"

render-report:
	@echo "=== Rendering report from bundle ==="
	@python3 scripts/render-report.py $(BUNDLE) generated/report.html
	@echo "✓ Report generated: generated/report.html"

test-practical:
	@echo "=== Testing practical bundle inference ==="
	@python3 scripts/test-practical-bundles.py

test-buildapp:
	@echo "=== Testing BuildAppWorkflow (bundle → DOQL → build) ==="
	@bash scripts/test-buildapp-workflow.sh $(BUNDLE)

test-audit:
	@echo "=== Testing Postgres audit_log after LLM generation ==="
	@bash scripts/test-audit.sh

pending-bundle:
	@echo "=== Pending WORKFLOW_BUNDLE approvals ==="
	@bash scripts/approve-bundle.sh $(ACTION) $(BUNDLE)

test-human-in-the-loop:
	@echo "=== Testing WORKFLOW_BUNDLE human-in-the-loop approval ==="
	@bash scripts/test-human-in-the-loop.sh

test-prometheus:
	@echo "=== Verifying Prometheus/Grafana LLM metrics ==="
	@echo "Grafana: http://localhost:$${GRAFANA_PORT:-3000}  (admin/$${GRAFANA_PASSWORD:-admin})"
	@echo "Prometheus: http://localhost:$${PROMETHEUS_PORT:-9090}"
	@bash scripts/test-prometheus.sh

test-temporal-ui:
	@echo "=== Verifying Temporal Web UI, gRPC, and namespace API ==="
	@bash scripts/test-temporal-ui.sh

clean:
	-pkill -f "php -S 0.0.0.0"
	-pkill -f "go run deploy_workflow.go"
	@echo "Cleaned up"

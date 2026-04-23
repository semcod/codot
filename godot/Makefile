.PHONY: all build run deploy validate validate-all test clean docker-build docker-test docker-up docker-down start stop restart quickstart llm-test help

BUNDLE := bundles/protocol-dashboard.json
PORT   := $(shell python3 -c "import json; print(json.load(open('$(BUNDLE)'))['output']['port'])")

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
	@echo "  test-services - run stack readiness tests (schema, Temporal, PostgreSQL)"
	@echo "  llm-test     - run LiteLLM/ACL/bundle-generation tests"
	@echo "  docker-build - build Docker image"
	@echo "  docker-test  - run validation tests in Docker"
	@echo "  docker-up    - start services with docker-compose"
	@echo "  docker-down  - stop services with docker-compose"
	@echo "  quickstart   - alias for start"
	@echo "  clean        - kill running processes"

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
	-docker rm -f godot-bundle-service godot-llm godot-mock-api temporal-server temporal-postgres schema-server 2>/dev/null
	@echo "Killing processes on ports..."
	-for port in 9000 9001 9002 9003 18094 18095 5433 8084; do \
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
	@for port in 9000 9001 9002 9003 18094 18095 5433 7233 8084; do \
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
		echo "  Temporal Web:   http://localhost:$${TEMPORAL_PORT:-7233}" && \
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

clean:
	-pkill -f "php -S 0.0.0.0"
	-pkill -f "go run deploy_workflow.go"
	@echo "Cleaned up"

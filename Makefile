.PHONY: help build up down logs restart test clean token

-include .env
export

help:
	@echo "CQRS-URL Platform - available targets:"
	@echo "  make build      - build all docker images"
	@echo "  make up         - start the stack (detached)"
	@echo "  make down       - stop the stack"
	@echo "  make logs       - tail logs from API"
	@echo "  make restart    - rebuild API and restart"
	@echo "  make token      - issue a development JWT (admin)"
	@echo "  make token-user - issue a development JWT (user)"
	@echo "  make test       - run smoke tests against the running API"
	@echo "  make test-agent - run agent integration tests (no API server needed)"
	@echo "  make workflow   - run example workflow via CLI (API must be up)"
	@echo "  make clean      - remove containers and volumes"

build:
	docker compose build

up:
	docker compose up -d
	@echo ""
	@echo "Stack is starting up:"
	@echo "  - Frontend:   http://localhost:$(FRONTEND_PORT)"
	@echo "  - API:        http://localhost:$(API_PORT)"
	@echo "  - API docs:   http://localhost:$(API_PORT)/docs"
	@echo "  - Schemas:    http://localhost:$(SCHEMAS_PORT)"
	@echo "  - Sample data: http://localhost:$(DATA_PORT)"

down:
	docker compose down

logs:
	docker compose logs -f api

restart:
	docker compose up -d --build api

token:
	@curl -s -X POST http://localhost:$(API_PORT)/auth/token \
		-H "Content-Type: application/json" \
		-d '{"username":"admin","password":"admin"}' | python3 -m json.tool

token-user:
	@curl -s -X POST http://localhost:$(API_PORT)/auth/token \
		-H "Content-Type: application/json" \
		-d '{"username":"alice","password":"alice"}' | python3 -m json.tool

test:
	@bash tests/smoke.sh

test-agent:
	@cd api && python3 test_all_agents.py

workflow:
	@python3 codot_run.py examples/workflow_agent_mcp.json --url $(API_BASE_URL)

clean:
	docker compose down -v --remove-orphans

.PHONY: help build up down logs restart test clean token

help:
	@echo "CQRS-URL Platform - available targets:"
	@echo "  make build     - build all docker images"
	@echo "  make up        - start the stack (detached)"
	@echo "  make down      - stop the stack"
	@echo "  make logs      - tail logs from API"
	@echo "  make restart   - rebuild API and restart"
	@echo "  make token     - issue a development JWT (admin)"
	@echo "  make token-user - issue a development JWT (user)"
	@echo "  make test      - run smoke tests against the running API"
	@echo "  make clean     - remove containers and volumes"

build:
	docker compose build

up:
	docker compose up -d
	@echo ""
	@echo "Stack is starting up:"
	@echo "  - Frontend:   http://localhost:18000"
	@echo "  - API:        http://localhost:18080"
	@echo "  - API docs:   http://localhost:18080/docs"
	@echo "  - Schemas:    http://localhost:18090"
	@echo "  - Sample data: http://localhost:18091"

down:
	docker compose down

logs:
	docker compose logs -f api

restart:
	docker compose up -d --build api

token:
	@curl -s -X POST http://localhost:18080/auth/token \
		-H "Content-Type: application/json" \
		-d '{"username":"admin","password":"admin"}' | python3 -m json.tool

token-user:
	@curl -s -X POST http://localhost:18080/auth/token \
		-H "Content-Type: application/json" \
		-d '{"username":"alice","password":"alice"}' | python3 -m json.tool

test:
	@bash tests/smoke.sh

clean:
	docker compose down -v --remove-orphans

# codot Workflow System Makefile
# Manages workflow API backend and frontend editor

-include ../.env
export

.PHONY: help start stop status clean install dev

# Default target
help:
	@echo "codot Workflow System - Available commands:"
	@echo ""
	@echo "  make install     - Install Python dependencies"
	@echo "  make dev         - Start backend in development mode"
	@echo "  make start       - Start all workflow services (backend + frontend)"
	@echo "  make stop        - Stop all workflow services"
	@echo "  make status      - Check status of all services"
	@echo "  make clean       - Clean up temporary files"
	@echo ""
	@echo "Services:"
	@echo "  - Workflow API (backend): http://localhost:8000"
	@echo "  - Workflow Editor (frontend): http://localhost:3000"
	@echo "  - codot API: $(API_BASE_URL)"
	@echo "  - codot Data: http://localhost:$(DATA_PORT)"
	@echo "  - codot Schemas: http://localhost:$(SCHEMAS_PORT)"

# Install dependencies
install:
	@echo "[install] Installing Python dependencies..."
	@python3 -m venv venv
	@./venv/bin/pip install --quiet -r requirements.txt
	@echo "[install] Dependencies installed successfully"

# Start backend in development mode
dev:
	@echo "[dev] Starting Workflow API backend on port 8000..."
	@./venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Start all workflow services
start:
	@echo "[start] Starting codot Workflow System..."
	@echo ""
	@echo "[start] Starting Workflow API backend (port 8000)..."
	@./venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 > workflow-api.log 2>&1 &
	@echo $$! > workflow-api.pid
	@sleep 2
	@if kill -0 $$(cat workflow-api.pid) 2>/dev/null; then \
		echo "[start] ✓ Workflow API started successfully (PID: $$(cat workflow-api.pid))"; \
	else \
		echo "[start] ✗ Failed to start Workflow API"; \
		rm -f workflow-api.pid; \
		exit 1; \
	fi
	@echo ""
	@echo "[start] Starting Workflow Editor frontend (port 3000)..."
	@cd ../cqrs-workflow-editor && npm run dev > ../cqrs-backend-workflows/workflow-editor.log 2>&1 &
	@echo $$! > ../cqrs-backend-workflows/workflow-editor.pid
	@sleep 3
	@if kill -0 $$(cat workflow-editor.pid) 2>/dev/null; then \
		echo "[start] ✓ Workflow Editor started successfully (PID: $$(cat workflow-editor.pid))"; \
	else \
		echo "[start] ✗ Failed to start Workflow Editor"; \
		rm -f workflow-editor.pid; \
	fi
	@echo ""
	@echo "[start] All services started:"
	@echo "  - Workflow API: http://localhost:8000"
	@echo "  - Workflow Editor: http://localhost:3000"
	@echo "  - API Docs: http://localhost:8000/docs"

# Stop all workflow services
stop:
	@echo "[stop] Stopping codot Workflow System..."
	@echo ""
	@if [ -f workflow-api.pid ]; then \
		pid=$$(cat workflow-api.pid); \
		if kill -0 $$pid 2>/dev/null; then \
			echo "[stop] Stopping Workflow API (PID: $$pid)..."; \
			kill $$pid; \
			rm -f workflow-api.pid; \
			echo "[stop] ✓ Workflow API stopped"; \
		else \
			echo "[stop] Workflow API not running (PID file exists but process dead)"; \
			rm -f workflow-api.pid; \
		fi; \
	else \
		echo "[stop] Workflow API not running (no PID file)"; \
	fi
	@echo ""
	@if [ -f workflow-editor.pid ]; then \
		pid=$$(cat workflow-editor.pid); \
		if kill -0 $$pid 2>/dev/null; then \
			echo "[stop] Stopping Workflow Editor (PID: $$pid)..."; \
			kill $$pid; \
			rm -f workflow-editor.pid; \
			echo "[stop] ✓ Workflow Editor stopped"; \
		else \
			echo "[stop] Workflow Editor not running (PID file exists but process dead)"; \
			rm -f workflow-editor.pid; \
		fi; \
	else \
		echo "[stop] Workflow Editor not running (no PID file)"; \
	fi
	@echo ""
	@echo "[stop] Killing any remaining processes on ports 8000 and 3000..."
	@pkill -f "uvicorn server:app" 2>/dev/null || true
	@pkill -f "vite.*3000" 2>/dev/null || true
	@fuser -k 8000/tcp 2>/dev/null || true
	@fuser -k 3000/tcp 2>/dev/null || true
	@echo "[stop] ✓ All services stopped"

# Check status of all services
status:
	@echo "[status] Checking codot Workflow System status..."
	@echo ""
	@echo "Workflow API (port 8000):"
	@if curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		echo "  ✓ Running"; \
	else \
		echo "  ✗ Not running"; \
	fi
	@echo ""
	@echo "Workflow Editor (port 3000):"
	@if curl -s http://localhost:3000 > /dev/null 2>&1; then \
		echo "  ✓ Running"; \
	else \
		echo "  ✗ Not running"; \
	fi
	@echo ""
	@echo "codot API (port $(API_PORT):"
	@if curl -s $(API_BASE_URL)/health > /dev/null 2>&1; then \
		echo "  ✓ Running"; \
	else \
		echo "  ✗ Not running"; \
	fi
	@echo ""
	@echo "codot Data (port $(DATA_PORT):"
	@if curl -s http://localhost:$(DATA_PORT) > /dev/null 2>&1; then \
		echo "  ✓ Running"; \
	else \
		echo "  ✗ Not running"; \
	fi
	@echo ""
	@echo "codot Schemas (port $(SCHEMAS_PORT):"
	@if curl -s http://localhost:$(SCHEMAS_PORT) > /dev/null 2>&1; then \
		echo "  ✓ Running"; \
	else \
		echo "  ✗ Not running"; \
	fi

# Clean up temporary files
clean:
	@echo "[clean] Cleaning up temporary files..."
	@rm -f workflow-api.log workflow-editor.log
	@rm -f workflow-api.pid workflow-editor.pid
	@echo "[clean] ✓ Cleanup complete"

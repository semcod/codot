#!/usr/bin/env bash
set -e

echo "=== Godot Bundle System - Quick Start ==="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Step 1: Build Docker image
echo "Step 1: Building Docker image..."
make docker-build
echo ""

# Step 2: Start services
echo "Step 2: Starting Docker services..."
make docker-up
echo ""

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5
echo ""

# Step 3: Run tests
echo "Step 3: Running service tests..."
bash scripts/test-services.sh
echo ""

echo "=== Quick Start Complete ==="
echo ""
echo "Your Godot Bundle System is now running!"
echo ""
echo "Useful commands:"
echo "  make docker-down    - Stop all services"
echo "  make docker-test    - Run bundle validation tests"
echo "  make help           - Show all available commands"
echo ""
echo "To enter the container:"
echo "  docker exec -it godot-bundle-service bash"

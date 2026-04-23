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
echo "This wrapper is deprecated; using 'make start' instead."
exec make start

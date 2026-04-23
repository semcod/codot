#!/usr/bin/env bash
set -e
PORT=$(python3 -c "import json; print(json.load(open('bundles/protocol-dashboard.json'))['output']['port'])")
echo "Starting PHP server on port $PORT..."
cd generated
exec php -S "0.0.0.0:${PORT}" dashboard.php

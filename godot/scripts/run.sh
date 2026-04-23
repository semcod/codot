#!/usr/bin/env bash
set -e
PORT=$(python3 -c "import json; data=json.load(open('bundles/protocol-dashboard.json')); output=data.get('output', {}); runtime=output.get('runtime'); print((runtime or {}).get('port', output.get('port', 8082)) if isinstance(runtime, dict) else output.get('port', 8082))")
echo "Starting PHP server on port $PORT..."
cd generated
exec php -S "0.0.0.0:${PORT}" dashboard.php

import json
import os

bundle_json = '''
{
  "bundle": "protocol-dashboard",
  "kind": "VIEW_BUNDLE",
  "version": "1.0.0",
  "description": "Live protocol dashboard",
  "sources": [
    {
      "name": "protocol",
      "uri": "http://localhost:8080/api/v3/protocols/123",
      "refresh": "1s",
      "type": "cqrs_query"
    },
    {
      "name": "devices",
      "uri": "http://localhost:8081/api/v3/devices",
      "refresh": "5s",
      "depends_on": ["protocol"],
      "type": "http_get"
    }
  ],
  "template": {
    "engine": "jinja2",
    "source_uri": "file:///templates/dashboard.html"
  },
  "output": {
    "format": "php",
    "runtime": "standalone",
    "port": 8082
  }
}
'''

# Save input JSON
with open('output/protocol-dashboard.json', 'w') as f:
    f.write(bundle_json)

print("Input bundle saved as protocol-dashboard.json")

# Go structs equivalent (as comment)
go_structs = '''
// structs.go - generated from JSON
type ViewBundle struct {
	Bundle     string     `json:"bundle"`
	Kind       string     `json:"kind"`
	Version    string     `json:"version"`
	Description string    `json:"description"`
	Sources    []Source   `json:"sources"`
	Template   Template   `json:"template"`
	Output     Output     `json:"output"`
}

type Source struct {
	Name      string   `json:"name"`
	URI       string   `json:"uri"`
	Refresh   string   `json:"refresh"`
	Type      string   `json:"type"`
	DependsOn []string `json:"depends_on,omitempty"`
}
'''
with open('output/structs.go', 'w') as f:
    f.write(go_structs)

print("Go structs saved as structs.go")

# Generated PHP standalone dashboard.php
php_code = '''<?php
// protocol-dashboard.php - generated from VIEW_BUNDLE
// Run: php -S 0.0.0.0:8082 protocol-dashboard.php

$sources = [
    "protocol" => ["uri" => "http://localhost:8080/api/v3/protocols/123", "refresh" => 1],
    "devices" => ["uri" => "http://localhost:8081/api/v3/devices", "refresh" => 5]
];

function fetchData($uri) {
    $ch = curl_init($uri);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    return json_decode(curl_exec($ch), true);
}

header("Content-Type: text/html");
?>
<!DOCTYPE html>
<html>
<head><title>Protocol Dashboard</title></head>
<body>
    <h1>Live Protocol Dashboard</h1>
    <div id="protocol"></div>
    <div id="devices"></div>
    <script>
        function updateData() {
            fetch("<?= $sources["protocol"]["uri"] ?>").then(r=>r.json()).then(d=>document.getElementById("protocol").innerHTML = "<pre>" + JSON.stringify(d, null, 2) + "</pre>");
            setTimeout(updateData, <?= $sources["protocol"]["refresh"] ?> * 1000);
        }
        updateData();
    </script>
</body>
</html>
'''

with open('output/dashboard.php', 'w') as f:
    f.write(php_code)

print("Generated PHP standalone: dashboard.php - run `php -S 0.0.0.0:8082 dashboard.php`")

# README
readme = """
# Generated Protocol Dashboard

## Files:
- `protocol-dashboard.json` - input VIEW_BUNDLE
- `structs.go` - Go structs for validation/codegen
- `dashboard.php` - standalone PHP service (php -S 0.0.0.0:8082)

## Deploy:
1. php -S 0.0.0.0:8082 dashboard.php
2. Open http://localhost:8082

Simulates sources refresh + template render.
"""
with open('output/README.md', 'w') as f:
    f.write(readme)

print("README.md saved")
print("All files in output/: JSON, Go structs, PHP dashboard, README")
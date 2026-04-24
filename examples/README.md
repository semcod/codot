# CQRS-URL Platform Examples

This directory contains practical examples demonstrating the platform's capabilities.

## Prerequisites

The stack must be running:
```bash
cd ..
make build
make up
```

## Examples

### 01-fetch.sh
Demonstrates fetching raw content from various protocols:
- `file://` - local file system
- `data:` - inline base64-encoded data
- Shows different MIME types (text, JSON, CSV)

```bash
./01-fetch.sh
```

### 02-convert-to-json.sh
Shows data transformation capabilities:
- CSV to JSON conversion
- Text to JSON conversion
- Schema validation with JSON Schema
- Custom field mapping

```bash
./02-convert-to-json.sh
```

### 03-render-html.sh
Demonstrates HTML rendering with Jinja2 templates:
- Render JSON data with default template
- Render inline data
- Custom inline templates
- Automatic table generation for structured data

```bash
./03-render-html.sh
```

### 04-pipeline.sh
Shows command composition via pipelines:
- Chain multiple commands together
- Use `$previous.output` to pass data between steps
- Complex workflows: CSV → JSON → Render
- Round-trip conversions

```bash
./04-pipeline.sh
```

### 05-query.sh
Demonstrates query operations:
- Fetch multiple resources in one request
- GET and POST query methods
- Introspection of available commands/queries/protocols
- Public catalog access (no auth required)

```bash
./05-query.sh
```

### 06-rbac.sh
Shows Role-Based Access Control:
- Admin role: full access
- Analyst role: broad access to data
- User role: restricted to public resources
- Permission enforcement at the API level

```bash
./06-rbac.sh
```

## Environment Variables

- `API` - API base URL (default reads from `API_BASE_URL` in `.env`, falls back to `http://localhost:18080`)

Example:
```bash
API_BASE_URL=http://localhost:18080 ./01-fetch.sh
```

## Users

- **admin** - full access (password: `admin`)
- **alice** - analyst role (password: `alice`)
- **bob** - user role, restricted (password: `bob`)

## API Endpoints Reference

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| POST | `/auth/token` | Issue JWT token |
| GET | `/auth/me` | Current user info |
| GET | `/catalog` | Public catalog |
| GET | `/commands` | List commands (auth) |
| PUT | `/commands/{name}` | Execute command |
| GET | `/queries` | List queries (auth) |
| POST | `/queries/{name}` | Execute query |

## Available Commands

- `fetch` - Fetch raw bytes from any protocol
- `converttojson` - Convert CSV/text/XML to JSON
- `converttoxml` - Convert JSON/CSV to XML
- `converttocsv` - Convert JSON to CSV
- `converttobase64` - Base64-encode any resource
- `render` - Render Jinja2 template to HTML
- `pipeline` - Chain commands with `$previous.output`

## Available Queries

- `from-url` - Fetch multiple URIs
- `introspect` - List commands, queries, protocols

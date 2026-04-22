# codot Workflow API

Backend API do zarządzania i wykonywania workflow dla systemu codot CQRS-URL Platform.

## Funkcjonalności

- **CRUD workflow**: Tworzenie, odczyt, aktualizacja, usuwanie workflow
- **Walidacja JSON Schema**: Walidacja workflow przed zapisem
- **Executor workflow**: Wykonywanie workflow przez wywoływanie codot API
- **Obsługa agentów**: Wsparcie dla węzłów typu agent
- **Integracja z codot**: Wykorzystuje istniejące API CQRS na porcie 18080

## Instalacja

```bash
cd cqrs-backend-workflows
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uruchomienie

```bash
python3 server.py
```

Lub z uvicorn:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

API będzie dostępne na http://localhost:8000

## Endpoints

### Zdrowie i info

- `GET /` - Informacje o serwisie
- `GET /health` - Status zdrowia

### Workflow CRUD

- `GET /v1/workflows` - Lista wszystkich workflow
- `GET /v1/workflows/{workflow_id}` - Pobierz konkretny workflow
- `POST /v1/workflows` - Utwórz nowy workflow
- `PUT /v1/workflows/{workflow_id}` - Zaktualizuj workflow
- `DELETE /v1/workflows/{workflow_id}` - Usuń workflow

### Wykonywanie

- `POST /v1/workflows/{workflow_id}/run` - Wykonaj workflow

## Przykład użycia

### Pobierz workflow

```bash
curl http://localhost:8000/v1/workflows/example
```

### Wykonaj workflow

```bash
curl -X POST http://localhost:8000/v1/workflows/example/run \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "example", "token": "optional_jwt_token"}'
```

### Utwórz nowy workflow

```bash
curl -X POST http://localhost:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

## Struktura workflow

Workflow jest definiowany jako JSON z następującą strukturą:

```json
{
  "version": "1.0",
  "nodes": [
    {
      "id": "fetch1",
      "label": "Fetch CSV",
      "type": "fetch",
      "uri": "http://localhost:18091/products.csv",
      "mime_type": "text/csv"
    },
    {
      "id": "convert1",
      "label": "Convert to JSON",
      "type": "command",
      "command_type": "converttojson",
      "input": "fetch1",
      "schema_uri": "http://localhost:18090/public-products.json"
    }
  ],
  "outputs": [
    {"id": "main_view", "source": "convert1"}
  ]
}
```

## Typy węzłów

- **fetch**: Pobiera dane z URI
- **http**: Wykonuje żądanie HTTP
- **command**: Wykonuje komendę CQRS
- **render**: Renderuje dane do HTML
- **agent**: Węzeł agenta (role, goal, tools, memory_uri)

## Integracja z codot

Workflow executor wywołuje endpointy codot API:
- `PUT /commands/fetch` - dla węzłów fetch/http
- `PUT /commands/{command_type}` - dla węzłów command
- `PUT /commands/render` - dla węzłów render

Wyniki są przekazywane między węzłami jako data: URI z base64-encoded payload.

## Walidacja

Wszystkie workflow są walidowane przeciwko JSON Schema zdefiniowanym w `workflow.schema.json`.

## Technologie

- FastAPI
- httpx (async HTTP client)
- Pydantic
- jsonschema

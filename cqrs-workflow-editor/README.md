# codot Workflow Editor

Graficzny edytor workflow dla systemu codot CQRS-URL Platform. Pozwala na wizualne tworzenie, edycję i eksport workflow w formacie JSON DAG.

## Funkcjonalności

- **Paleta węzłów**: Fetch, HTTP, Command, Query, Render, Agent
- **Wizualny edytor**: Drag & drop węzłów z React Flow
- **Import/Eksport**: Workflow JSON z/z do pliku
- **Obsługa agentów**: Węzły typu agent z rolą, celem, narzędziami i pamięcią
- **Integracja z codot API**: Workflow kompatybilne z backend CQRS

## Instalacja

```bash
cd cqrs-workflow-editor
npm install
```

## Uruchomienie

```bash
npm run dev
```

Edytor będzie dostępny na http://localhost:3000

## Użycie

1. Kliknij przycisk w paletce węzłów, aby dodać węzeł do canvas
2. Przeciągnij węzły, aby zmienić ich pozycję
3. Połącz węzły strzałkami, aby zdefiniować przepływ danych
4. Kliknij "Export workflow", aby pobrać workflow jako JSON
5. Kliknij "Import workflow", aby wczytać workflow z pliku JSON

## Struktura workflow JSON

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
    },
    {
      "id": "render1",
      "label": "Render HTML",
      "type": "render",
      "command_type": "render",
      "input": "convert1"
    }
  ],
  "outputs": [
    {"id": "main_view", "source": "render1"}
  ]
}
```

## Typy węzłów

- **fetch**: Pobiera dane z URI (file://, http://, https://, data:)
- **http**: Wykonuje żądanie HTTP z nagłówkami
- **command**: Wykonuje komendę CQRS (converttojson, converttoxml, itp.)
- **query**: Wykonuje zapytanie CQRS
- **render**: Renderuje dane do HTML/Jinja2
- **agent**: Węzeł agenta dla multi-agent orchestration (role, goal, tools, memory)

## Integracja z backend

Workflow JSON można wysłać do backend API:
- `POST /v1/workflows` - utwórz nowy workflow
- `PUT /v1/workflows/{id}` - zaktualizuj workflow
- `POST /v1/workflows/{id}/run` - wykonaj workflow

## Technologie

- React 18
- TypeScript
- Vite
- @xyflow/react (React Flow)

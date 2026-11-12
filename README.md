# clinical-note-extractor

An MCP server that turns free-text clinical notes into structured JSON (demographics, diagnoses, medications, allergies, vitals), using Claude with structured outputs. Every extracted value is checked against the source note and gets a source snippet.

## Setup

```bash
uv sync
# put your key in .env:  ANTHROPIC_API_KEY=...
```

## Run the server

```bash
uv run python src/server.py
```

Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "clinical-note-extractor": {
      "command": "uv",
      "args": ["--directory", "/path/to/clinical-note-extractor", "run", "python", "src/server.py"]
    }
  }
}
```

### Tools
- `extract_clinical_note(note_text)` – data, validation issues, and a source snippet per field
- `extract_note_by_id(note_id)` – same, for a note in `data/notes/`
- `validate_extraction(note_text, extraction_json)` – range and grounding checks only

### Resources
- `notes://list`, `notes://{note_id}`, `glossary://abbreviations`

## How it works

1. `extractor.py` asks Claude for a `ClinicalNote` (schema-constrained output).
2. `validator.py` checks plausible ranges and that every value appears in the note (with `glossary.py` mapping e.g. "hypertension" to "HTN").
3. If checks fail, the issues go back to the model and it retries (up to 2 times).
4. `tracing.py` attaches the source snippet for each field.

## Tests and eval

```bash
uv run pytest                    # offline, no API calls
uv run python eval/run_eval.py   # calls the API for every note in data/notes
```

`data/notes/*.txt` and `data/labels/*.json` are paired by filename. Use synthetic or de-identified notes only.

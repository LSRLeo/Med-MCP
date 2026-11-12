# clinical-note-extractor

An MCP server that turns free-text clinical notes into structured JSON — demographics,
diagnoses, medications, allergies, and vitals — using Claude (Opus 5.5) with structured outputs.

Every extracted value is checked against the source note ("did the model invent this?"),
checked for plausible ranges, and returned with the snippet of the note it came from.

> Use only synthetic or de-identified notes. Everything sent to the tools goes to the Anthropic API.

## How it works

```
note text
   │
   ▼
extractor.py ──► Claude Opus 5.5 ──► JSON matching schema.py (ClinicalNote)
   │
   ▼
validator.py   plausible ranges + every value must appear in the note
   │             (glossary.py: "hypertension" matches "HTN"; °F matches °C)
   ├── problems? ──► retry with the problems listed (up to 2 retries)
   ▼
tracing.py     source snippet for each field (a drug's dose/route/frequency is
   │             looked up next to that drug's name first)
   ▼
{ data, issues, attempts, sources }
```

## Setup

Requires [uv](https://docs.astral.sh/uv/) and an Anthropic API key.

```bash
uv sync
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # .env is git-ignored
```

## MCP tools and resources

| Tool | Input | What it does | API cost |
|---|---|---|---|
| `extract_clinical_note` | `note_text` | Extract, validate, retry, trace | 1 call per attempt |
| `extract_note_by_id` | `note_id` (e.g. `mts_01`) | Same, for a note in `data/notes/` | 1 call per attempt |
| `validate_extraction` | `note_text`, `extraction_json` | Range and grounding checks only | free |

| Resource | Returns |
|---|---|
| `notes://list` | IDs of the stored notes |
| `notes://{note_id}` | Raw text of one note |
| `glossary://abbreviations` | The abbreviation list |

Example output of `extract_clinical_note`:

```json
{
  "data": {
    "patient_age": 62, "patient_sex": "female",
    "diagnoses": ["HTN", "seasonal allergies"],
    "medications": [{"name": "Claritin", "dose": "10 mg", "route": "PO", "frequency": "daily"}],
    "allergies": ["Penicillin"], "no_known_allergies": false,
    "vitals": {"systolic_bp": 142, "diastolic_bp": 88, "heart_rate": 76, "temperature_c": 37.0}
  },
  "issues": [],
  "attempts": 1,
  "sources": {"vitals.temperature_c": "VITAL SIGNS: BP 142/88, HR 76, Temp 98.6, SpO2 98%."}
}
```

`issues` lists problems still present after the retries (empty is good).
The checks catch **invented** and **impossible** values, not **missing** ones — use the eval for that.

## Running it

**MCP Inspector** (web UI to call each tool by hand):

```bash
uv run mcp dev src/server.py
```

Open the URL it prints, go to **Tools → List Tools**, pick a tool, fill in the inputs, **Run Tool**.
This project uses `mcp` 2.x (`MCPServer`, formerly `FastMCP`), so the Inspector looks newer than in
older tutorials; it works the same way.

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json`
(use the full path to `uv`; find it with `which uv`), then quit (⌘Q) and reopen Claude Desktop:

```json
{
  "mcpServers": {
    "clinical-note-extractor": {
      "command": "/full/path/to/uv",
      "args": ["--directory", "/full/path/to/this/repo", "run", "python", "src/server.py"]
    }
  }
}
```

Then ask: *"Extract the clinical data from note mts_01"*. Logs:
`~/Library/Logs/Claude/mcp-server-clinical-note-extractor.log`. Restart Claude Desktop after code changes.

**Claude Code**:

```bash
claude mcp add clinical-notes -- uv --directory "$(pwd)" run python src/server.py
```

## Tests

```bash
uv run pytest
```

All tests run offline (the API is replaced with a stub) and cost nothing:

| File | Covers |
|---|---|
| `tests/test_server.py` | The three MCP tools, including rejecting `../` note IDs |
| `tests/test_extractor.py` | Retry-with-feedback loop, refusals, giving up after max retries |
| `tests/test_validator.py` | Range checks, invented values, °F/°C, dose spacing |
| `tests/test_tracing.py` | Snippets point at the right drug's dose/route/frequency |
| `tests/test_schema.py` | Every label file matches the schema |
| `tests/test_eval.py` | Eval scoring, including the same drug at two doses |

## Data and evaluation

```
data/
├── mtsamples.csv      # source dataset (git-ignored, download separately)
├── notes/             # notes the tools and eval run on (.txt)
├── labels/            # hand-reviewed labels (.json) — the eval's ground truth
└── labels_draft/      # model-drafted labels awaiting review
```

1. **Get notes.** `note_01` is synthetic. The `mts_XX` notes come from
   [MTSamples](https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions): download
   `mtsamples.csv` into `data/`, then pick 20 varied notes (free, deterministic):
   ```bash
   uv run python scripts/import_mtsamples.py [--n 20] [--seed 42]
   ```
2. **Draft labels** with the extractor (costs one API call per note, plus retries):
   ```bash
   uv run python scripts/draft_labels.py
   ```
3. **Review every draft** against its note following [LABELING.md](LABELING.md), fix it, and move it
   from `data/labels_draft/` to `data/labels/`. Unreviewed drafts are never used by the eval —
   scoring the model against its own unchecked output would measure nothing.
4. **Run the eval** (costs one API call per labeled note, plus retries):
   ```bash
   uv run python eval/run_eval.py [--limit N]
   ```
   Prints accuracy per field: exact match for scalars and vitals, set F1 for diagnoses / allergies /
   medication names, and per-attribute accuracy for dose / route / frequency.

## Labeling rules (summary)

Full rules in [LABELING.md](LABELING.md); the extractor prompt follows the same rules.

- **Medications:** every medication mentioned (home, given during the visit, discharge).
  Same drug at a different dose/route/frequency = separate entry.
- **Diagnoses:** current and past ongoing conditions, plus non-drug allergies.
  Not past surgeries, one-time events, minor findings, or negated conditions.
- **Allergies:** drug allergies only.
- **Vitals:** first set recorded; vague "stable" / "WNL" means empty; temperature in °C.

## Project layout

```
src/
├── server.py      # MCP tools and resources only
├── schema.py      # Pydantic models: ClinicalNote, Medication, Vitals
├── extractor.py   # prompt + Claude call + retry with validator feedback
├── validator.py   # range checks and "no invented values" checks
├── tracing.py     # source snippet for each field
└── glossary.py    # medical abbreviations (HTN, BID, NKDA, ...)
scripts/
├── import_mtsamples.py   # pick notes from the MTSamples CSV
└── draft_labels.py       # draft labels for review
eval/run_eval.py          # accuracy per field against data/labels/
LABELING.md               # labeling rules
```

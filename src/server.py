"""MCP server: tools and resources only. Logic lives in the other modules."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from extractor import extract
from glossary import ABBREVIATIONS
from schema import ClinicalNote
from tracing import trace_note
from validator import validate

NOTES_DIR = Path(__file__).resolve().parent.parent / "data" / "notes"

mcp = MCPServer("clinical-note-extractor")


def _traces_to_dict(note: ClinicalNote, text: str) -> dict:
    return {
        path: (span.snippet if span else None) for path, span in trace_note(note, text).items()
    }


@mcp.tool()
def extract_clinical_note(note_text: str) -> dict:
    """Extract structured fields (demographics, diagnoses, medications, allergies, vitals)
    from a clinical note. Returns the data, any validation issues, and the source snippet
    supporting each field."""
    result = extract(note_text)
    return {
        "data": result.note.model_dump(),
        "issues": result.issues,
        "attempts": result.attempts,
        "sources": _traces_to_dict(result.note, note_text),
    }


@mcp.tool()
def extract_note_by_id(note_id: str) -> dict:
    """Extract structured fields from a stored note in data/notes (e.g. 'note_01')."""
    return extract_clinical_note(_read_note(note_id))


@mcp.tool()
def validate_extraction(note_text: str, extraction_json: str) -> list[str]:
    """Check an existing extraction against its note: plausible ranges and no invented values."""
    note = ClinicalNote.model_validate_json(extraction_json)
    return validate(note, note_text)


@mcp.resource("notes://list")
def list_notes() -> str:
    """IDs of the stored clinical notes."""
    return json.dumps(sorted(p.stem for p in NOTES_DIR.glob("*.txt")))


@mcp.resource("notes://{note_id}")
def get_note(note_id: str) -> str:
    """Raw text of a stored clinical note."""
    return _read_note(note_id)


@mcp.resource("glossary://abbreviations")
def glossary() -> str:
    """Medical abbreviations the extractor understands."""
    return json.dumps(ABBREVIATIONS, indent=2)


def _read_note(note_id: str) -> str:
    path = (NOTES_DIR / f"{note_id}.txt").resolve()
    if path.parent != NOTES_DIR.resolve() or not path.exists():
        raise ValueError(f"Unknown note: {note_id}")
    return path.read_text()


if __name__ == "__main__":
    mcp.run()

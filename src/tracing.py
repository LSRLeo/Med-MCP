"""Find the source snippet in the note that supports each extracted value."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from glossary import variants
from schema import ClinicalNote

CONTEXT_CHARS = 40


@dataclass
class SourceSpan:
    start: int
    end: int
    snippet: str


def candidates_for(path: str, value: Any) -> list[str]:
    """All spellings of a value that count as 'found in the note'."""
    if isinstance(value, str):
        return variants(value)
    return [_format_number(value)]


_NUMBER = re.compile(r"(?<![\w.])\d{2,3}(?:\.\d+)?(?![\w])")


def _find_temperature(note_text: str, celsius: float) -> re.Match[str] | None:
    """Temperatures are converted to Celsius by the model, so compare numerically:
    accept a number in the note that equals the value in C, or converts to it from F,
    within rounding to one decimal place."""
    for m in _NUMBER.finditer(note_text):
        n = float(m.group(0))
        if abs(n - celsius) <= 0.051 or abs((n - 32) * 5 / 9 - celsius) <= 0.051:
            return m
    return None


def _pattern(cand: str) -> str:
    """Whole-word match; any whitespace in the value matches any (or no) whitespace."""
    parts = [re.escape(p) for p in cand.split()]
    return rf"(?<![\w.]){r'\s*'.join(parts)}(?![\w])"


def find_snippet(note_text: str, value: Any, path: str = "") -> SourceSpan | None:
    """Locate a value (or a glossary variant of it) in the note. Case-insensitive, whole-word."""
    if value is None or value == "":
        return None
    if path == "vitals.temperature_c":
        matches = [_find_temperature(note_text, float(value))]
    else:
        matches = [
            re.search(_pattern(c), note_text, re.IGNORECASE) for c in candidates_for(path, value)
        ]
    for m in matches:
        if m:
            lo = max(0, m.start() - CONTEXT_CHARS)
            hi = min(len(note_text), m.end() + CONTEXT_CHARS)
            return SourceSpan(m.start(), m.end(), note_text[lo:hi].strip())
    return None


def _format_number(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def trace_note(note: ClinicalNote, note_text: str) -> dict[str, SourceSpan | None]:
    """Map each populated field path (e.g. 'medications[0].name') to its source span."""
    traces: dict[str, SourceSpan | None] = {}
    for path, value in iter_leaf_values(note):
        traces[path] = find_snippet(note_text, value, path)
    return traces


def iter_leaf_values(note: ClinicalNote):
    """Yield (field_path, value) for every populated, traceable leaf field."""
    data = note.model_dump()
    for key in ("patient_age", "chief_complaint"):
        if data[key] is not None:
            yield key, data[key]
    for i, dx in enumerate(data["diagnoses"]):
        yield f"diagnoses[{i}]", dx
    for i, allergy in enumerate(data["allergies"]):
        yield f"allergies[{i}]", allergy
    for i, med in enumerate(data["medications"]):
        for k, v in med.items():
            if v is not None:
                yield f"medications[{i}].{k}", v
    for k, v in data["vitals"].items():
        if v is not None:
            yield f"vitals.{k}", v

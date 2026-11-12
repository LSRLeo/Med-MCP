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


def _find_temperature(note_text: str, celsius: float, lo: int, hi: int) -> re.Match[str] | None:
    """Temperatures are converted to Celsius by the model, so compare numerically:
    accept a number in the note that equals the value in C, or converts to it from F,
    within rounding to one decimal place."""
    for m in _NUMBER.finditer(note_text, lo, hi):
        n = float(m.group(0))
        if abs(n - celsius) <= 0.051 or abs((n - 32) * 5 / 9 - celsius) <= 0.051:
            return m
    return None


def _pattern(cand: str) -> re.Pattern[str]:
    """Whole-word match; any whitespace in the value matches any (or no) whitespace."""
    parts = [re.escape(p) for p in cand.split()]
    return re.compile(rf"(?<![\w.]){r'\s*'.join(parts)}(?![\w])", re.IGNORECASE)


# How far after a medication's name to look for its dose / route / frequency.
MED_WINDOW_CHARS = 120


def _match(note_text: str, value: Any, path: str, lo: int, hi: int) -> re.Match[str] | None:
    """First match of the value (or a variant) within note_text[lo:hi]."""
    if path == "vitals.temperature_c":
        return _find_temperature(note_text, float(value), lo, hi)
    for cand in candidates_for(path, value):
        if m := _pattern(cand).search(note_text, lo, hi):
            return m
    return None


def _windows_after(note_text: str, anchor: str):
    """(lo, hi) regions starting at each mention of anchor and running to the end of
    that line, at most MED_WINDOW_CHARS past the anchor."""
    for cand in candidates_for("", anchor):
        for a in _pattern(cand).finditer(note_text):
            hi = min(len(note_text), a.end() + MED_WINDOW_CHARS)
            newline = note_text.find("\n", a.end(), hi)
            yield a.start(), (newline if newline != -1 else hi)


def find_snippet(
    note_text: str, value: Any, path: str = "", near: str | None = None
) -> SourceSpan | None:
    """Locate a value (or a glossary variant of it) in the note. Case-insensitive, whole-word.

    If `near` is given (e.g. a medication name), first look just after each mention of it,
    so a dose/route/frequency is traced to its own drug rather than the first match anywhere.
    """
    if value is None or value == "":
        return None
    m = None
    if near:
        for lo, hi in _windows_after(note_text, near):
            if m := _match(note_text, value, path, lo, hi):
                break
    if m is None:
        m = _match(note_text, value, path, 0, len(note_text))
    if m is None:
        return None
    lo = max(0, m.start() - CONTEXT_CHARS)
    hi = min(len(note_text), m.end() + CONTEXT_CHARS)
    return SourceSpan(m.start(), m.end(), note_text[lo:hi].strip())


def _format_number(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def trace_note(note: ClinicalNote, note_text: str) -> dict[str, SourceSpan | None]:
    """Map each populated field path (e.g. 'medications[0].name') to its source span."""
    traces: dict[str, SourceSpan | None] = {}
    for path, value in iter_leaf_values(note):
        traces[path] = find_snippet(note_text, value, path, near=_anchor_for(note, path))
    return traces


_MED_ATTR = re.compile(r"medications\[(\d+)\]\.(dose|route|frequency)")


def _anchor_for(note: ClinicalNote, path: str) -> str | None:
    """A medication's dose/route/frequency is anchored to that medication's name."""
    if m := _MED_ATTR.fullmatch(path):
        return note.medications[int(m.group(1))].name
    return None


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

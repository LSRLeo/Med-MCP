"""Post-extraction checks: physiologic ranges and 'no invented values'."""

from __future__ import annotations

from schema import ClinicalNote
from tracing import iter_leaf_values, find_snippet

# Plausible (not normal) ranges: values outside these are almost certainly extraction errors.
VITAL_RANGES: dict[str, tuple[float, float]] = {
    "systolic_bp": (50, 300),
    "diastolic_bp": (20, 200),
    "heart_rate": (20, 250),
    "respiratory_rate": (4, 60),
    "temperature_c": (30.0, 45.0),
    "spo2": (50, 100),
}
AGE_RANGE = (0, 120)

# Free-text fields the model may paraphrase; not required to appear verbatim.
PARAPHRASE_OK = {"chief_complaint"}


def check_ranges(note: ClinicalNote) -> list[str]:
    issues: list[str] = []
    for field, (lo, hi) in VITAL_RANGES.items():
        v = getattr(note.vitals, field)
        if v is not None and not lo <= v <= hi:
            issues.append(f"vitals.{field}={v} is outside plausible range [{lo}, {hi}]")
    if (
        note.vitals.systolic_bp is not None
        and note.vitals.diastolic_bp is not None
        and note.vitals.systolic_bp <= note.vitals.diastolic_bp
    ):
        issues.append("vitals: systolic_bp must be greater than diastolic_bp")
    if note.patient_age is not None and not AGE_RANGE[0] <= note.patient_age <= AGE_RANGE[1]:
        issues.append(f"patient_age={note.patient_age} is outside plausible range {AGE_RANGE}")
    if note.no_known_allergies and note.allergies:
        issues.append("no_known_allergies is true but allergies list is non-empty")
    return issues


def check_grounded(note: ClinicalNote, note_text: str) -> list[str]:
    """Every extracted value must be findable in the source note (directly or via glossary)."""
    issues: list[str] = []
    for path, value in iter_leaf_values(note):
        if path.split("[")[0] in PARAPHRASE_OK:
            continue
        if find_snippet(note_text, value) is None:
            issues.append(f"{path}={value!r} not found in the note text (possibly invented)")
    return issues


def validate(note: ClinicalNote, note_text: str) -> list[str]:
    """Return a list of human-readable issues; empty means the extraction passed."""
    return check_ranges(note) + check_grounded(note, note_text)

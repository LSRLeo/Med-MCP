import json
from pathlib import Path

from schema import ClinicalNote, Medication

LABELS = Path(__file__).resolve().parent.parent / "data" / "labels"


def test_empty_note_is_valid():
    note = ClinicalNote()
    assert note.medications == []
    assert note.vitals.heart_rate is None


def test_all_labels_match_schema():
    for path in LABELS.glob("*.json"):
        ClinicalNote.model_validate(json.loads(path.read_text()))


def test_medication_optional_fields():
    med = Medication(name="aspirin")
    assert med.dose is None and med.frequency is None

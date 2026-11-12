"""Tests for the three MCP tools. The LLM call is replaced with a stub, so these run offline."""

import json

import pytest

import server
from extractor import ExtractionResult
from schema import ClinicalNote, Medication, Vitals

NOTE = (
    "62 yo F with HTN and seasonal allergies.\n"
    "MEDICATIONS: amlodipine 5 mg PO daily, Claritin 10 mg PO daily.\n"
    "ALLERGIES: Penicillin (rash).\n"
    "VITAL SIGNS: BP 142/88, HR 76, Temp 98.6, SpO2 98%."
)

GOOD = ClinicalNote(
    patient_age=62,
    patient_sex="female",
    diagnoses=["HTN", "seasonal allergies"],
    medications=[
        Medication(name="amlodipine", dose="5 mg", route="PO", frequency="daily"),
        Medication(name="Claritin", dose="10 mg", route="PO", frequency="daily"),
    ],
    allergies=["Penicillin"],
    vitals=Vitals(systolic_bp=142, diastolic_bp=88, heart_rate=76, temperature_c=37.0, spo2=98),
)


@pytest.fixture
def fake_extract(monkeypatch):
    """Make the tools return GOOD instead of calling the API; record the text sent."""
    seen = {}

    def _extract(text):
        seen["text"] = text
        return ExtractionResult(note=GOOD, issues=[], attempts=1)

    monkeypatch.setattr(server, "extract", _extract)
    return seen


# --- Tool 1: extract_clinical_note ---------------------------------------------------------

def test_extract_clinical_note_returns_data_issues_sources(fake_extract):
    out = server.extract_clinical_note(NOTE)

    assert set(out) == {"data", "issues", "attempts", "sources"}
    assert out["data"]["patient_age"] == 62
    assert out["data"]["allergies"] == ["Penicillin"]
    assert out["issues"] == []
    # every populated field points back to the note text
    assert "BP 142/88" in out["sources"]["vitals.systolic_bp"]
    assert "Temp 98.6" in out["sources"]["vitals.temperature_c"]  # 37.0 C traced to 98.6 F
    assert "amlodipine 5 mg" in out["sources"]["medications[0].name"]


# --- Tool 2: extract_note_by_id ------------------------------------------------------------

def test_extract_note_by_id_reads_stored_note(fake_extract):
    server.extract_note_by_id("note_01")
    assert fake_extract["text"].startswith("58 y/o male")


@pytest.mark.parametrize("bad_id", ["does_not_exist", "../../.env", "../labels/note_01"])
def test_extract_note_by_id_rejects_unknown_or_escaping_ids(fake_extract, bad_id):
    with pytest.raises(ValueError):
        server.extract_note_by_id(bad_id)


# --- Tool 3: validate_extraction (no API call at all) --------------------------------------

def test_validate_extraction_clean():
    assert server.validate_extraction(NOTE, GOOD.model_dump_json()) == []


def test_validate_extraction_catches_invented_and_impossible_values():
    bad = GOOD.model_copy(deep=True)
    bad.medications.append(Medication(name="metoprolol", dose="25 mg"))  # not in the note
    bad.vitals.heart_rate = 760  # typo for 76
    issues = server.validate_extraction(NOTE, bad.model_dump_json())

    assert any("metoprolol" in i for i in issues)
    assert any("heart_rate=760" in i and "range" in i for i in issues)


def test_validate_extraction_rejects_malformed_json():
    with pytest.raises(Exception):
        server.validate_extraction(NOTE, json.dumps({"patient_age": "sixty"}))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

from run_eval import match_medications, score  # noqa: E402
from schema import ClinicalNote, Medication  # noqa: E402


def test_same_drug_two_regimens_scored_separately():
    gold = [
        Medication(name="Compazine", dose="5 mg", route="IV"),
        Medication(name="Compazine", dose="10 mg", route="p.o."),
    ]
    pred = [
        Medication(name="compazine", dose="10mg", route="PO"),
        Medication(name="Compazine", dose="5 mg", route="IV"),
    ]
    s = match_medications(pred, gold)
    assert s["medications.dose"] == 1.0
    assert s["medications.route"] == 1.0


def test_missing_med_lowers_attribute_scores():
    gold = [Medication(name="a", dose="1 mg"), Medication(name="b", dose="2 mg")]
    pred = [Medication(name="a", dose="1 mg")]
    assert match_medications(pred, gold)["medications.dose"] == 0.5


def test_perfect_prediction_scores_one():
    note = ClinicalNote(patient_age=50, diagnoses=["HTN"], medications=[Medication(name="x")])
    assert all(v == 1.0 for v in score(note, note).values())

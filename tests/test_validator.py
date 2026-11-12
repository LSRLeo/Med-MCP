from schema import ClinicalNote, Medication, Vitals
from validator import check_grounded, check_ranges, validate

NOTE = "62 yo F with HTN. Meds: amlodipine 5 mg PO daily. BP 140/90, HR 72."


def test_clean_extraction_passes():
    note = ClinicalNote(
        patient_age=62,
        diagnoses=["hypertension"],  # matched via glossary -> HTN
        medications=[Medication(name="amlodipine", dose="5 mg", route="PO", frequency="daily")],
        vitals=Vitals(systolic_bp=140, diastolic_bp=90, heart_rate=72),
    )
    assert validate(note, NOTE) == []


def test_out_of_range_vitals():
    note = ClinicalNote(vitals=Vitals(heart_rate=900, spo2=120))
    issues = check_ranges(note)
    assert any("heart_rate" in i for i in issues)
    assert any("spo2" in i for i in issues)


def test_systolic_below_diastolic():
    note = ClinicalNote(vitals=Vitals(systolic_bp=80, diastolic_bp=120))
    assert any("systolic" in i for i in check_ranges(note))


def test_invented_medication_flagged():
    note = ClinicalNote(medications=[Medication(name="metoprolol")])
    issues = check_grounded(note, NOTE)
    assert any("metoprolol" in i for i in issues)


def test_invented_vital_flagged():
    note = ClinicalNote(vitals=Vitals(respiratory_rate=18))
    assert any("respiratory_rate" in i for i in check_grounded(note, NOTE))


def test_nkda_with_allergies_conflict():
    note = ClinicalNote(no_known_allergies=True, allergies=["penicillin"])
    assert any("no_known_allergies" in i for i in check_ranges(note))

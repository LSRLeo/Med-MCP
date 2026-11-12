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


def test_fahrenheit_note_accepts_celsius_value():
    note = ClinicalNote(vitals=Vitals(temperature_c=37.0))
    assert check_grounded(note, "Temp 98.6 F, HR 80") == []


def test_fahrenheit_rounding_is_tolerated():
    # 97.6 F = 36.44 C; the model rounds to 36.4, which converts back to 97.5 F
    note = ClinicalNote(vitals=Vitals(temperature_c=36.4))
    assert check_grounded(note, "Temperature 97.6, pulse 70") == []


def test_temperature_not_in_note_flagged():
    note = ClinicalNote(vitals=Vitals(temperature_c=38.5))
    assert check_grounded(note, "Temperature 97.6, pulse 70") != []


def test_dose_spacing_does_not_matter():
    note = ClinicalNote(medications=[Medication(name="amlodipine", dose="5 mg")])
    assert check_grounded(note, "amlodipine 5mg daily") == []


def test_number_inside_larger_number_not_matched():
    note = ClinicalNote(vitals=Vitals(heart_rate=37))
    assert check_grounded(note, "glucose 137") != []


def test_nkda_with_allergies_conflict():
    note = ClinicalNote(no_known_allergies=True, allergies=["penicillin"])
    assert any("no_known_allergies" in i for i in check_ranges(note))

# Labeling rules

Labels in `data/labels/` and the extractor prompt (`src/extractor.py`) follow these rules.
If you change a rule here, change the prompt too, and relabel affected notes.

## General
- Record only what the note states. If it isn't stated, leave the field `null` / empty.
- Vague statements ("vital signs stable", "within normal limits") are **not** values: leave them empty.
- Copy names as written (abbreviations like `HTN`, brand names like `Zyrtec` are fine).

## Medications: every medication mentioned
- Include home meds, meds given during the visit (ER, inpatient), and discharge prescriptions.
- The same drug with a **different** dose, route, or frequency is a separate entry
  (e.g. Compazine 5 mg IV in the ER and Compazine 10 mg PO at discharge = 2 entries).
- The same drug and regimen mentioned twice is **one** entry.
- Include IV fluids and supplements (e.g. normal saline, vitamins).
- Copy dose / route / frequency as written (`p.o.`, `q.8h. p.r.n.`); leave them `null` if not stated.
- Do not include drugs listed only as allergies, or drugs the patient explicitly is *not* taking.

## Diagnoses: current and past conditions
- Include the assessment / impression, the past medical history, and conditions mentioned
  as the reason for a medication ("fluoxetine for depression" -> `depression`).
- Include **non-drug allergies** (environmental, seasonal, food, mold), e.g. `environmental allergies`.
- Do not include symptoms that are only part of the history of present illness unless the note
  lists them as an assessment.
- Do not include negated conditions ("denies chest pain", "no history of diabetes").
- Do not include past surgeries or procedures ("s/p colostomy", "hernia repair"), one-time past
  events or injuries ("gunshot wound", "trauma to right thumb"), or minor incidental findings
  ("bug bites"). Keep ongoing / chronic conditions and the current assessment.

## Allergies: drug allergies only
- `allergies` holds drug / medication allergens (`penicillin`, `sulfa`, `IV dye`, `Fleet enema`).
- Non-drug allergies go in `diagnoses` instead (see above).
- `no_known_allergies` is `true` only if the note says NKDA / no known (drug) allergies.

## Vitals
- Use the first set of vitals recorded in the note (usually the physical exam).
- `temperature_c` in Celsius, rounded to one decimal (convert from °F if needed).

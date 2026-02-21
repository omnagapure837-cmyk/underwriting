# Automated Life Underwriting Engine

This repository contains a production-style, rules-driven underwriting tool that:

1. Extracts applicant information from a proposal form and medical report.
2. Calculates medical and occupational extra mortality points.
3. Assigns risk category and underwriting decision from configurable charts.
4. Calculates itemized final premium including mortality loading and rider costs.

## Input document format

The current parser is designed for controlled key-value text input.

**Proposal form fields**
- `Identity`
- `Age`
- `Gender`
- `Occupation`
- `Income`
- `Smoking`
- `Alcohol`
- `Riders` (comma-separated, e.g. `Accident, Critical_Illness`)

**Medical report fields**
- `Medical Conditions` with entries formatted like:
  - `Hypertension(Moderate), Diabetes(Controlled)`

## Configuration-driven charts

All rating logic is externalized in `config/charts.json`:
- `medical_chart`
- `occupation_chart`
- `risk_rating_chart`
- `premium_table`
- `rider_costs`

## Run the underwriting flow

```bash
python underwriting_engine.py \
  --proposal sample_input/proposal_form.txt \
  --medical sample_input/medical_report.txt
```

Optional JSON output:

```bash
python underwriting_engine.py \
  --proposal sample_input/proposal_form.txt \
  --medical sample_input/medical_report.txt \
  --json
```

## Example outcome for included sample

- Total Extra Mortality Points: `260`
- Risk Category: `Postpone`
- Final Underwriting Decision: `Postponement`
- Final Premium: `2530.00`

## Testing

```bash
pytest -q
```

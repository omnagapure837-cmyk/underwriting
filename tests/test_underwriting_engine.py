from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from underwriting_engine import extract_profile, evaluate_underwriting, load_chart_data


def test_end_to_end_scoring_and_decision():
    charts = load_chart_data(Path("config/charts.json"))
    proposal = Path("sample_input/proposal_form.txt").read_text(encoding="utf-8")
    medical = Path("sample_input/medical_report.txt").read_text(encoding="utf-8")

    profile = extract_profile(proposal, medical)
    result = evaluate_underwriting(profile, charts)

    assert result.total_extra_mortality_points == 260
    assert result.risk_category == "Postpone"
    assert result.underwriting_decision == "Postponement"
    assert result.base_premium == 600.0
    assert result.mortality_loading_amount == 1560.0
    assert result.rider_cost == 370.0
    assert result.final_premium == 2530.0

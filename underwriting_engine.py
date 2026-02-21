from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


KEY_VALUE_PATTERN = re.compile(r"^\s*([A-Za-z ]+):\s*(.*?)\s*$")


@dataclass
class ApplicantProfile:
    identity: str
    age: int
    gender: str
    occupation: str
    annual_income: float
    smoking: bool
    alcohol: str
    medical_conditions: List[Dict[str, str]]
    riders: List[str]


@dataclass
class UnderwritingResult:
    profile: ApplicantProfile
    medical_points_breakdown: List[Tuple[str, str, int]]
    occupation_points: int
    total_extra_mortality_points: int
    risk_category: str
    underwriting_decision: str
    base_premium: float
    mortality_loading_amount: float
    rider_cost: float
    final_premium: float


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"yes", "true", "1", "y"}


def parse_list(value: str) -> List[str]:
    if not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_chart_data(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_key_values(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for line in text.splitlines():
        match = KEY_VALUE_PATTERN.match(line)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_")
            data[key] = match.group(2).strip()
    return data


def parse_medical_conditions(value: str) -> List[Dict[str, str]]:
    conditions: List[Dict[str, str]] = []
    for raw in parse_list(value):
        if "(" in raw and raw.endswith(")"):
            condition, severity = raw.rsplit("(", 1)
            conditions.append(
                {"condition": condition.strip().lower(), "severity": severity[:-1].strip().lower()}
            )
        else:
            conditions.append({"condition": raw.strip().lower(), "severity": "default"})
    return conditions


def extract_profile(proposal_text: str, medical_text: str) -> ApplicantProfile:
    proposal = extract_key_values(proposal_text)
    medical = extract_key_values(medical_text)

    return ApplicantProfile(
        identity=proposal.get("identity", "Unknown"),
        age=int(proposal.get("age", 0)),
        gender=proposal.get("gender", "Unknown"),
        occupation=proposal.get("occupation", "Unknown").lower(),
        annual_income=float(proposal.get("income", 0)),
        smoking=parse_bool(proposal.get("smoking", "no")),
        alcohol=proposal.get("alcohol", "none").lower(),
        medical_conditions=parse_medical_conditions(medical.get("medical_conditions", "")),
        riders=parse_list(proposal.get("riders", "")),
    )


def get_medical_points(profile: ApplicantProfile, chart: Dict[str, Any]) -> List[Tuple[str, str, int]]:
    breakdown: List[Tuple[str, str, int]] = []

    for entry in profile.medical_conditions:
        condition = entry["condition"]
        severity = entry["severity"]
        condition_map = chart.get(condition, {})
        points = int(condition_map.get(severity, condition_map.get("default", 0)))
        breakdown.append((condition, severity, points))

    if profile.smoking:
        smoking_points = int(chart.get("smoker", {}).get("default", 0))
        breakdown.append(("smoker", "default", smoking_points))

    alcohol_points = int(chart.get("alcohol", {}).get(profile.alcohol, 0))
    if alcohol_points:
        breakdown.append(("alcohol", profile.alcohol, alcohol_points))

    return breakdown


def get_occupation_points(occupation: str, chart: Dict[str, int]) -> int:
    return int(chart.get(occupation.lower(), chart.get("default", 0)))


def get_risk_category(total_points: int, chart: List[Dict[str, Any]]) -> Tuple[str, str]:
    for bucket in chart:
        if bucket["min"] <= total_points <= bucket["max"]:
            return bucket["category"], bucket["decision"]
    return "Decline", "Decline"


def get_base_premium(age: int, table: List[Dict[str, Any]]) -> float:
    for row in table:
        if row["min_age"] <= age <= row["max_age"]:
            return float(row["base_premium"])
    raise ValueError(f"No base premium configured for age {age}")


def calculate_rider_cost(selected_riders: List[str], rider_table: Dict[str, float]) -> float:
    return float(sum(rider_table.get(rider.strip().lower(), 0) for rider in selected_riders))


def evaluate_underwriting(
    profile: ApplicantProfile,
    charts: Dict[str, Any],
) -> UnderwritingResult:
    medical_breakdown = get_medical_points(profile, charts["medical_chart"])
    medical_total = sum(points for _, _, points in medical_breakdown)
    occupation_points = get_occupation_points(profile.occupation, charts["occupation_chart"])
    total_points = medical_total + occupation_points

    risk_category, decision = get_risk_category(total_points, charts["risk_rating_chart"])
    base_premium = get_base_premium(profile.age, charts["premium_table"])

    # 1 point = 1% loading on base premium
    loading_amount = round(base_premium * (total_points / 100.0), 2)
    rider_cost = round(calculate_rider_cost(profile.riders, charts["rider_costs"]), 2)
    final_premium = round(base_premium + loading_amount + rider_cost, 2)

    return UnderwritingResult(
        profile=profile,
        medical_points_breakdown=medical_breakdown,
        occupation_points=occupation_points,
        total_extra_mortality_points=total_points,
        risk_category=risk_category,
        underwriting_decision=decision,
        base_premium=base_premium,
        mortality_loading_amount=loading_amount,
        rider_cost=rider_cost,
        final_premium=final_premium,
    )


def format_report(result: UnderwritingResult) -> str:
    lines = [
        "FINAL UNDERWRITING OUTPUT REPORT",
        "=" * 34,
        "",
        "1) Individual Risk Profile",
        f"- Identity: {result.profile.identity}",
        f"- Age/Gender: {result.profile.age} / {result.profile.gender}",
        f"- Occupation: {result.profile.occupation}",
        f"- Annual Income: {result.profile.annual_income:,.2f}",
        f"- Smoking: {'Yes' if result.profile.smoking else 'No'}",
        f"- Alcohol: {result.profile.alcohol}",
        f"- Riders: {', '.join(result.profile.riders) if result.profile.riders else 'None'}",
        "",
        "2) Medical & Occupational Risk Points",
    ]

    if result.medical_points_breakdown:
        for condition, severity, points in result.medical_points_breakdown:
            lines.append(f"- {condition} ({severity}): +{points} points")
    else:
        lines.append("- No medical extra mortality points")

    lines.extend(
        [
            f"- Occupation Loading: +{result.occupation_points} points",
            f"- Total Extra Mortality Points: {result.total_extra_mortality_points}",
            "",
            "3) Risk Classification & Decision",
            f"- Risk Category: {result.risk_category}",
            f"- Final Underwriting Decision: {result.underwriting_decision}",
            "",
            "4) Itemized Final Premium",
            f"- Base Premium: {result.base_premium:.2f}",
            f"- Mortality Loading Amount: {result.mortality_loading_amount:.2f}",
            f"- Rider Cost: {result.rider_cost:.2f}",
            f"- Final Premium: {result.final_premium:.2f}",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated life underwriting engine")
    parser.add_argument("--proposal", required=True, type=Path, help="Path to proposal form text file")
    parser.add_argument("--medical", required=True, type=Path, help="Path to medical report text file")
    parser.add_argument(
        "--charts",
        default=Path("config/charts.json"),
        type=Path,
        help="Path to underwriting chart configuration JSON",
    )
    parser.add_argument("--json", action="store_true", help="Return machine-readable JSON output")

    args = parser.parse_args()

    proposal_text = args.proposal.read_text(encoding="utf-8")
    medical_text = args.medical.read_text(encoding="utf-8")
    charts = load_chart_data(args.charts)

    profile = extract_profile(proposal_text, medical_text)
    result = evaluate_underwriting(profile, charts)

    if args.json:
        payload = asdict(result)
        print(json.dumps(payload, indent=2))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()

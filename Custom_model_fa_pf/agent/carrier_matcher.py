"""Carrier/market matching — dummy rules engine.

Matches risk profiles to eligible carriers based on appetite rules.
Replace with Guidewire integration later.
"""

import logging
from dataclasses import asdict, dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CarrierMatch:
    """A carrier eligibility result."""
    carrier_id: str
    carrier_name: str
    eligible: bool
    confidence: float  # 0.0 - 1.0
    reasoning: str
    supported_lobs: list = field(default_factory=list)
    strengths: list = field(default_factory=list)
    limitations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --- Dummy carrier appetite rules ---
# Each carrier has: name, supported LOBs, constraints, strengths

CARRIER_RULES = [
    {
        "carrier_id": "progressive_commercial",
        "carrier_name": "Progressive Commercial",
        "lobs": ["commercial_auto"],
        "max_fleet_size": 50,
        "max_vehicles": 50,
        "min_years_in_business": 1,
        "states_excluded": [],
        "max_loss_ratio": 0.75,
        "strengths": ["Competitive fleet pricing", "Fast quoting", "Flexible payment plans"],
        "limitations": ["Max 50 vehicles", "No long-haul trucking over 500 miles"],
    },
    {
        "carrier_id": "hartford",
        "carrier_name": "The Hartford",
        "lobs": ["commercial_auto", "general_liability", "workers_compensation", "bop"],
        "max_fleet_size": 200,
        "max_vehicles": 200,
        "min_years_in_business": 2,
        "states_excluded": [],
        "max_loss_ratio": 0.65,
        "strengths": ["Multi-line discounts", "Strong claims service", "Broad appetite"],
        "limitations": ["Higher minimum premium", "Requires 2+ years in business"],
    },
    {
        "carrier_id": "travelers",
        "carrier_name": "Travelers",
        "lobs": ["commercial_auto", "general_liability", "workers_compensation", "commercial_property", "umbrella"],
        "max_fleet_size": 500,
        "max_vehicles": 500,
        "min_years_in_business": 3,
        "states_excluded": [],
        "max_loss_ratio": 0.60,
        "strengths": ["Large fleet specialist", "National presence", "Umbrella capacity"],
        "limitations": ["Strict underwriting", "3+ years required", "No startups"],
    },
    {
        "carrier_id": "employers_mutual",
        "carrier_name": "EMC Insurance",
        "lobs": ["workers_compensation", "commercial_auto", "general_liability"],
        "max_fleet_size": 100,
        "max_vehicles": 100,
        "min_years_in_business": 3,
        "states_excluded": ["CA", "NY", "FL"],
        "max_loss_ratio": 0.55,
        "strengths": ["Workers Comp specialist", "Loss control services", "Competitive WC rates"],
        "limitations": ["Not available in CA, NY, FL", "3+ years required"],
    },
    {
        "carrier_id": "national_general",
        "carrier_name": "National General",
        "lobs": ["commercial_auto"],
        "max_fleet_size": 25,
        "max_vehicles": 25,
        "min_years_in_business": 0,
        "states_excluded": [],
        "max_loss_ratio": 0.80,
        "strengths": ["Accepts new businesses", "Quick bind", "Low minimum premium"],
        "limitations": ["Small fleets only", "Auto only", "Higher rates for new ventures"],
    },
    {
        "carrier_id": "berkshire_hathaway",
        "carrier_name": "Berkshire Hathaway GUARD",
        "lobs": ["general_liability", "workers_compensation", "bop", "commercial_property", "umbrella"],
        "max_fleet_size": 0,  # No auto
        "max_vehicles": 0,
        "min_years_in_business": 1,
        "states_excluded": [],
        "max_loss_ratio": 0.65,
        "strengths": ["Broad GL appetite", "BOP specialist", "Strong financials"],
        "limitations": ["No commercial auto", "Moderate pricing"],
    },
]


def match_carriers(
    risk_profile: dict,
    lobs: list,
) -> list[CarrierMatch]:
    """Match a risk profile against carrier appetite rules.

    Args:
        risk_profile: RiskProfile dict from quote_builder.
        lobs: List of requested LOB IDs.

    Returns:
        List of CarrierMatch results, sorted by eligibility then confidence.
    """
    results = []
    fleet_size = risk_profile.get("fleet_size", 0)
    years = risk_profile.get("years_in_business", 0)
    state = risk_profile.get("state", "")
    total_loss = risk_profile.get("total_loss_amount", 0.0)
    prior_premium = risk_profile.get("prior_premium", 0.0)
    loss_ratio = (total_loss / prior_premium) if prior_premium > 0 else 0.0

    for rule in CARRIER_RULES:
        carrier_lobs = set(rule["lobs"])
        requested_lobs = set(lobs)
        overlap = carrier_lobs & requested_lobs

        # No LOB overlap → not eligible
        if not overlap:
            results.append(CarrierMatch(
                carrier_id=rule["carrier_id"],
                carrier_name=rule["carrier_name"],
                eligible=False,
                confidence=0.0,
                reasoning=f"Does not write requested LOBs: {', '.join(requested_lobs - carrier_lobs)}",
                supported_lobs=rule["lobs"],
                strengths=rule["strengths"],
                limitations=rule["limitations"],
            ))
            continue

        # Check constraints
        issues = []
        confidence = 0.90  # Start high, deduct for issues

        if rule["max_fleet_size"] > 0 and fleet_size > rule["max_fleet_size"]:
            issues.append(f"Fleet size {fleet_size} exceeds max {rule['max_fleet_size']}")
            confidence = 0.0

        if years < rule["min_years_in_business"]:
            issues.append(f"Requires {rule['min_years_in_business']}+ years in business (has {years})")
            confidence = 0.0

        if state in rule.get("states_excluded", []):
            issues.append(f"Not available in {state}")
            confidence = 0.0

        if loss_ratio > rule["max_loss_ratio"] and prior_premium > 0:
            issues.append(f"Loss ratio {loss_ratio:.0%} exceeds max {rule['max_loss_ratio']:.0%}")
            confidence *= 0.5

        # Partial LOB coverage is a soft penalty
        missing_lobs = requested_lobs - carrier_lobs
        if missing_lobs and confidence > 0:
            confidence *= 0.8
            issues.append(f"Cannot write: {', '.join(missing_lobs)}")

        eligible = confidence > 0
        if issues and eligible:
            reasoning = f"Eligible with notes: {'; '.join(issues)}"
        elif issues:
            reasoning = f"Not eligible: {'; '.join(issues)}"
        else:
            reasoning = f"Fully eligible for {', '.join(overlap)}"

        results.append(CarrierMatch(
            carrier_id=rule["carrier_id"],
            carrier_name=rule["carrier_name"],
            eligible=eligible,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            supported_lobs=rule["lobs"],
            strengths=rule["strengths"],
            limitations=rule["limitations"],
        ))

    # Sort: eligible first, then by confidence descending
    results.sort(key=lambda m: (-int(m.eligible), -m.confidence))

    eligible_count = sum(1 for m in results if m.eligible)
    logger.info(
        "Carrier matching: %d/%d eligible for LOBs %s",
        eligible_count, len(results), lobs,
    )
    return results

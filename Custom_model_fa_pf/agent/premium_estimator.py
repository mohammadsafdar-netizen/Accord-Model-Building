"""Premium estimation — dummy rating engine.

Generates ballpark premium estimates using simple factor-based formulas.
Replace with Guidewire PolicyCenter rating API later.
"""

import logging
from dataclasses import asdict, dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CoveragePremium:
    """Premium for a single coverage line."""
    lob: str
    lob_display: str
    annual_premium: float
    monthly_premium: float
    factors_applied: list = field(default_factory=list)


@dataclass
class PaymentOption:
    """A payment plan option."""
    plan: str  # "annual", "semi_annual", "quarterly", "monthly"
    installment_amount: float
    installment_count: int
    total_cost: float  # Includes any installment fees
    fee_pct: float = 0.0


@dataclass
class Quote:
    """A complete insurance quote from one carrier."""
    quote_id: str
    carrier_id: str
    carrier_name: str
    coverage_premiums: list = field(default_factory=list)  # List of CoveragePremium dicts
    total_annual_premium: float = 0.0
    payment_options: list = field(default_factory=list)  # List of PaymentOption dicts
    disclaimer: str = ""
    confidence_level: str = "estimate"  # "estimate", "indication", "firm"

    def to_dict(self) -> dict:
        return asdict(self)


# --- Base rate tables (dummy) ---
# Rates per unit (per vehicle, per $100 payroll, per $1000 revenue, etc.)

LOB_DISPLAY_NAMES = {
    "commercial_auto": "Commercial Auto",
    "general_liability": "General Liability",
    "workers_compensation": "Workers Compensation",
    "commercial_property": "Commercial Property",
    "bop": "Business Owner's Policy",
    "umbrella": "Commercial Umbrella",
    "cyber": "Cyber Liability",
}

# Base annual rates per LOB
BASE_RATES = {
    "commercial_auto": 3500,    # Per vehicle
    "general_liability": 1200,  # Per $100K revenue
    "workers_compensation": 8,  # Per $100 payroll
    "commercial_property": 800, # Per location
    "bop": 2500,                # Flat base
    "umbrella": 1500,           # Flat base for $1M umbrella
    "cyber": 1200,              # Flat base
}

# Territory factors by state
TERRITORY_FACTORS = {
    "TX": 1.00, "CA": 1.35, "NY": 1.30, "FL": 1.25, "IL": 1.10,
    "PA": 1.05, "OH": 1.00, "GA": 1.05, "NC": 0.95, "MI": 1.15,
    "NJ": 1.20, "VA": 0.95, "WA": 1.10, "AZ": 1.05, "MA": 1.15,
    "CO": 1.05, "TN": 0.95, "IN": 0.95, "MO": 1.00, "MD": 1.10,
}

# Experience modification by loss ratio
def _experience_mod(loss_ratio: float) -> float:
    if loss_ratio <= 0:
        return 0.85  # No losses = credit
    elif loss_ratio <= 0.3:
        return 0.90
    elif loss_ratio <= 0.5:
        return 1.00
    elif loss_ratio <= 0.7:
        return 1.15
    else:
        return 1.30  # Bad loss history = surcharge


# Years in business factor
def _experience_factor(years: int) -> float:
    if years >= 10:
        return 0.85
    elif years >= 5:
        return 0.90
    elif years >= 3:
        return 0.95
    elif years >= 1:
        return 1.00
    else:
        return 1.20  # New business surcharge


# Fleet size factor (commercial auto)
def _fleet_factor(fleet_size: int) -> float:
    if fleet_size >= 50:
        return 0.80  # Large fleet discount
    elif fleet_size >= 20:
        return 0.85
    elif fleet_size >= 10:
        return 0.90
    elif fleet_size >= 5:
        return 0.95
    else:
        return 1.00


# Carrier pricing variation (some carriers are cheaper for certain LOBs)
CARRIER_LOB_FACTORS = {
    "progressive_commercial": {"commercial_auto": 0.90},
    "hartford": {"general_liability": 0.92, "workers_compensation": 0.95},
    "travelers": {"umbrella": 0.85, "commercial_auto": 0.95},
    "employers_mutual": {"workers_compensation": 0.88},
    "national_general": {"commercial_auto": 1.10},
    "berkshire_hathaway": {"general_liability": 0.90, "bop": 0.88},
}


def _estimate_lob_premium(
    lob: str,
    risk_profile: dict,
    carrier_id: str,
) -> tuple[float, list[str]]:
    """Estimate annual premium for a single LOB.

    Returns (premium, list_of_factors_applied).
    """
    base_rate = BASE_RATES.get(lob, 2000)
    factors = []

    # Unit multiplier
    fleet_size = risk_profile.get("fleet_size", 1) or 1
    employees = risk_profile.get("employee_count", 5) or 5
    revenue = risk_profile.get("annual_revenue", 500000) or 500000
    payroll = risk_profile.get("annual_payroll", 200000) or 200000
    state = risk_profile.get("state", "TX")
    years = risk_profile.get("years_in_business", 1) or 1
    total_loss = risk_profile.get("total_loss_amount", 0)
    prior_premium = risk_profile.get("prior_premium", 0)
    loss_ratio = (total_loss / prior_premium) if prior_premium > 0 else 0.0

    if lob == "commercial_auto":
        premium = base_rate * max(fleet_size, 1)
        factors.append(f"Base: ${base_rate}/vehicle x {fleet_size} vehicles")
        ff = _fleet_factor(fleet_size)
        if ff != 1.0:
            premium *= ff
            factors.append(f"Fleet discount: {ff:.2f}")
    elif lob == "general_liability":
        units = revenue / 100000
        premium = base_rate * max(units, 1)
        factors.append(f"Base: ${base_rate}/per $100K revenue x {units:.1f} units")
    elif lob == "workers_compensation":
        units = payroll / 100
        premium = base_rate * units
        factors.append(f"Base: ${base_rate}/$100 payroll x {units:.0f} units")
    elif lob == "commercial_property":
        locations = max(risk_profile.get("location_count", 1), 1)
        premium = base_rate * locations
        factors.append(f"Base: ${base_rate}/location x {locations}")
    elif lob == "umbrella":
        premium = base_rate
        factors.append(f"Base: ${base_rate} ($1M umbrella)")
    else:
        premium = base_rate
        factors.append(f"Base: ${base_rate}")

    # Territory
    tf = TERRITORY_FACTORS.get(state, 1.00)
    if tf != 1.00:
        premium *= tf
        factors.append(f"Territory ({state}): {tf:.2f}")

    # Experience mod
    em = _experience_mod(loss_ratio)
    if em != 1.00:
        premium *= em
        label = "credit" if em < 1.0 else "surcharge"
        factors.append(f"Experience mod ({label}): {em:.2f}")

    # Business maturity
    ef = _experience_factor(years)
    if ef != 1.00:
        premium *= ef
        label = "discount" if ef < 1.0 else "surcharge"
        factors.append(f"Years in business ({label}): {ef:.2f}")

    # Carrier-specific factor
    cf = CARRIER_LOB_FACTORS.get(carrier_id, {}).get(lob, 1.00)
    if cf != 1.00:
        premium *= cf
        factors.append(f"Carrier adjustment: {cf:.2f}")

    return round(premium, 2), factors


def _build_payment_options(total_premium: float) -> list[dict]:
    """Generate payment plan options for a total premium."""
    options = []

    options.append(asdict(PaymentOption(
        plan="annual",
        installment_amount=round(total_premium, 2),
        installment_count=1,
        total_cost=round(total_premium, 2),
        fee_pct=0.0,
    )))

    semi = total_premium * 1.02  # 2% fee
    options.append(asdict(PaymentOption(
        plan="semi_annual",
        installment_amount=round(semi / 2, 2),
        installment_count=2,
        total_cost=round(semi, 2),
        fee_pct=2.0,
    )))

    quarterly = total_premium * 1.04  # 4% fee
    options.append(asdict(PaymentOption(
        plan="quarterly",
        installment_amount=round(quarterly / 4, 2),
        installment_count=4,
        total_cost=round(quarterly, 2),
        fee_pct=4.0,
    )))

    monthly = total_premium * 1.08  # 8% fee
    options.append(asdict(PaymentOption(
        plan="monthly",
        installment_amount=round(monthly / 12, 2),
        installment_count=12,
        total_cost=round(monthly, 2),
        fee_pct=8.0,
    )))

    return options


def generate_quote(
    carrier_id: str,
    carrier_name: str,
    lobs: list,
    risk_profile: dict,
    quote_id: str = "",
) -> Quote:
    """Generate a premium estimate for one carrier.

    Args:
        carrier_id: Carrier identifier.
        carrier_name: Carrier display name.
        lobs: LOBs this carrier is quoting.
        risk_profile: RiskProfile dict.
        quote_id: Optional ID (auto-generated if empty).

    Returns:
        Quote with per-LOB premiums and payment options.
    """
    if not quote_id:
        from datetime import datetime
        quote_id = f"Q-{carrier_id[:8].upper()}-{datetime.now().strftime('%H%M%S')}"

    coverage_premiums = []
    total = 0.0

    for lob in lobs:
        premium, factors = _estimate_lob_premium(lob, risk_profile, carrier_id)
        display = LOB_DISPLAY_NAMES.get(lob, lob)
        coverage_premiums.append(asdict(CoveragePremium(
            lob=lob,
            lob_display=display,
            annual_premium=premium,
            monthly_premium=round(premium / 12, 2),
            factors_applied=factors,
        )))
        total += premium

    payment_options = _build_payment_options(total)

    quote = Quote(
        quote_id=quote_id,
        carrier_id=carrier_id,
        carrier_name=carrier_name,
        coverage_premiums=coverage_premiums,
        total_annual_premium=round(total, 2),
        payment_options=payment_options,
        disclaimer=(
            "ESTIMATE ONLY. This is a preliminary indication based on the information provided. "
            "Final premium will be determined by the carrier's underwriting review and may differ "
            "significantly. Actual quotes require carrier submission and are subject to approval."
        ),
        confidence_level="estimate",
    )

    logger.info(
        "Generated quote %s from %s: $%.2f/yr for %s",
        quote.quote_id, carrier_name, total, lobs,
    )
    return quote


def generate_quotes_for_matches(
    carrier_matches: list[dict],
    lobs: list,
    risk_profile: dict,
) -> list[Quote]:
    """Generate quotes for all eligible carriers.

    Args:
        carrier_matches: List of CarrierMatch dicts.
        lobs: All requested LOBs.
        risk_profile: RiskProfile dict.

    Returns:
        List of Quote objects for eligible carriers.
    """
    quotes = []
    for match in carrier_matches:
        if not match.get("eligible"):
            continue

        # Quote only the LOBs this carrier supports
        carrier_lobs = set(match.get("supported_lobs", []))
        quotable_lobs = [l for l in lobs if l in carrier_lobs]
        if not quotable_lobs:
            continue

        quote = generate_quote(
            carrier_id=match["carrier_id"],
            carrier_name=match["carrier_name"],
            lobs=quotable_lobs,
            risk_profile=risk_profile,
        )
        quotes.append(quote)

    # Sort by total premium ascending (cheapest first)
    quotes.sort(key=lambda q: q.total_annual_premium)
    return quotes

"""Build structured quote requests from collected intake data."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskProfile:
    """Summarized risk characteristics for carrier matching and rating."""
    industry: str = ""
    naics_code: str = ""
    sic_code: str = ""
    years_in_business: int = 0
    employee_count: int = 0
    annual_revenue: float = 0.0
    annual_payroll: float = 0.0
    entity_type: str = ""
    state: str = ""
    fleet_size: int = 0
    driver_count: int = 0
    total_loss_amount: float = 0.0
    loss_count: int = 0
    prior_carrier: str = ""
    prior_premium: float = 0.0


@dataclass
class QuoteRequest:
    """Structured payload for requesting insurance quotes."""
    request_id: str = ""
    timestamp: str = ""
    business_name: str = ""
    business_dba: str = ""
    mailing_address: dict = field(default_factory=dict)
    fein: str = ""
    lobs: list = field(default_factory=list)  # Lines of business requested
    risk_profile: dict = field(default_factory=dict)
    effective_date: str = ""
    expiration_date: str = ""
    vehicles: list = field(default_factory=list)
    drivers: list = field(default_factory=list)
    coverages: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    loss_history: list = field(default_factory=list)
    prior_insurance: list = field(default_factory=list)
    assigned_forms: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_int(val, default=0) -> int:
    if val is None:
        return default
    try:
        return int(str(val).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(str(val).replace(",", "").replace("$", "").replace("M", "000000").strip())
    except (ValueError, TypeError):
        return default


def build_quote_request(
    entities: dict,
    lobs: list,
    assigned_forms: list,
    form_state: Optional[dict] = None,
) -> QuoteRequest:
    """Assemble a QuoteRequest from collected intake data.

    Args:
        entities: CustomerSubmission.to_dict() output.
        lobs: List of LOB ID strings.
        assigned_forms: List of form number strings.
        form_state: Optional flat form_state dict for supplemental data.

    Returns:
        A fully populated QuoteRequest.
    """
    biz = entities.get("business", {}) or {}
    policy = entities.get("policy", {}) or {}
    vehicles = entities.get("vehicles", []) or []
    drivers = entities.get("drivers", []) or []
    coverages = entities.get("coverages", []) or []
    locations = entities.get("locations", []) or []
    losses = entities.get("loss_history", []) or []
    priors = entities.get("prior_insurance", []) or []

    # Build risk profile
    total_loss = sum(_safe_float(l.get("amount")) for l in losses)
    prior_premium = 0.0
    prior_carrier = ""
    if priors:
        prior_premium = _safe_float(priors[0].get("premium"))
        prior_carrier = priors[0].get("carrier_name", "")

    risk = RiskProfile(
        industry=biz.get("nature_of_business") or biz.get("operations_description", ""),
        naics_code=biz.get("naics", "") or biz.get("naics_code", ""),
        sic_code=biz.get("sic", "") or biz.get("sic_code", ""),
        years_in_business=_safe_int(biz.get("years_in_business")),
        employee_count=_safe_int(biz.get("employee_count")),
        annual_revenue=_safe_float(biz.get("annual_revenue")),
        annual_payroll=_safe_float(biz.get("annual_payroll")),
        entity_type=biz.get("entity_type", ""),
        state=(biz.get("mailing_address", {}) or {}).get("state", ""),
        fleet_size=len(vehicles),
        driver_count=len(drivers),
        total_loss_amount=total_loss,
        loss_count=len(losses),
        prior_carrier=prior_carrier,
        prior_premium=prior_premium,
    )

    # Supplement from form_state if entities are sparse
    fs = form_state or {}
    if not risk.state and "mailing_state" in fs:
        risk.state = fs["mailing_state"].get("value", "")
    if not risk.employee_count and "employee_count" in fs:
        risk.employee_count = _safe_int(fs["employee_count"].get("value"))

    qr = QuoteRequest(
        request_id=f"QR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        timestamp=datetime.now().isoformat(),
        business_name=biz.get("business_name", ""),
        business_dba=biz.get("dba", ""),
        mailing_address=(biz.get("mailing_address") or {}),
        fein=biz.get("tax_id", ""),
        lobs=list(lobs),
        risk_profile=asdict(risk),
        effective_date=policy.get("effective_date", ""),
        expiration_date=policy.get("expiration_date", ""),
        vehicles=vehicles,
        drivers=drivers,
        coverages=coverages,
        locations=locations,
        loss_history=losses,
        prior_insurance=priors,
        assigned_forms=list(assigned_forms),
    )

    logger.info(
        "Built quote request %s: %s, %d LOBs, %d vehicles, %d drivers",
        qr.request_id, qr.business_name, len(lobs), len(vehicles), len(drivers),
    )
    return qr

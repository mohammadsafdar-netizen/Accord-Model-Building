"""Data models for structured entities extracted from customer emails."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Valid entity_type values for normalization
_ENTITY_TYPE_MAP = {
    "corporation": "corporation",
    "corp": "corporation",
    "partnership": "partnership",
    "llc": "llc",
    "limited liability": "llc",
    "limited liability company": "llc",
    "individual": "individual",
    "sole proprietor": "individual",
    "subchapter s": "subchapter_s",
    "subchapter_s": "subchapter_s",
    "s corporation": "subchapter_s",
    "s-corporation": "subchapter_s",
    "s corp": "subchapter_s",
    "joint venture": "joint_venture",
    "joint_venture": "joint_venture",
}


def _normalize_entity_type(val: Optional[str]) -> Optional[str]:
    """Normalize LLM entity_type to our canonical values."""
    if not val:
        return None
    key = val.strip().lower().replace("-", " ").replace("_", " ")
    return _ENTITY_TYPE_MAP.get(key, val.strip().lower())


def _str_or_none(val) -> Optional[str]:
    """Convert a value to string, returning None for None/empty."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


@dataclass
class Address:
    line_one: Optional[str] = None
    line_two: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data) -> Optional["Address"]:
        if not data:
            return None
        # Handle LLM returning a plain string instead of a dict
        if isinstance(data, str):
            return cls(line_one=data)
        if not isinstance(data, dict):
            return None
        return cls(
            line_one=data.get("line_one"),
            line_two=data.get("line_two"),
            city=data.get("city"),
            state=data.get("state"),
            zip_code=data.get("zip_code"),
        )


@dataclass
class Contact:
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["Contact"]:
        if not data:
            return None
        return cls(
            full_name=data.get("full_name"),
            phone=data.get("phone"),
            email=data.get("email"),
            role=data.get("role"),
        )


@dataclass
class BusinessInfo:
    business_name: Optional[str] = None
    dba: Optional[str] = None
    mailing_address: Optional[Address] = None
    tax_id: Optional[str] = None
    naics: Optional[str] = None
    sic: Optional[str] = None
    entity_type: Optional[str] = None  # corporation, partnership, llc, individual, subchapter_s, joint_venture
    operations_description: Optional[str] = None
    annual_revenue: Optional[str] = None
    employee_count: Optional[str] = None
    years_in_business: Optional[str] = None
    website: Optional[str] = None
    business_start_date: Optional[str] = None  # MM/DD/YYYY
    contacts: List[Contact] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if k == "mailing_address" and v:
                d[k] = v.to_dict()
            elif k == "contacts":
                d[k] = [c.to_dict() for c in v]
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["BusinessInfo"]:
        if not data:
            return None
        contacts = [Contact.from_dict(c) for c in (data.get("contacts") or []) if c]
        return cls(
            business_name=data.get("business_name"),
            dba=data.get("dba"),
            mailing_address=Address.from_dict(data.get("mailing_address")),
            tax_id=data.get("tax_id"),
            naics=data.get("naics"),
            sic=data.get("sic"),
            entity_type=_normalize_entity_type(data.get("entity_type")),
            operations_description=data.get("operations_description"),
            annual_revenue=_str_or_none(data.get("annual_revenue")),
            employee_count=_str_or_none(data.get("employee_count")),
            years_in_business=_str_or_none(data.get("years_in_business")),
            website=data.get("website"),
            business_start_date=data.get("business_start_date"),
            contacts=[c for c in contacts if c],
        )


@dataclass
class ProducerInfo:
    agency_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    mailing_address: Optional[Address] = None
    producer_code: Optional[str] = None
    license_number: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if k == "mailing_address" and v:
                d[k] = v.to_dict()
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["ProducerInfo"]:
        if not data:
            return None
        return cls(
            agency_name=data.get("agency_name"),
            contact_name=data.get("contact_name"),
            phone=data.get("phone"),
            fax=data.get("fax"),
            email=data.get("email"),
            mailing_address=Address.from_dict(data.get("mailing_address")),
            producer_code=data.get("producer_code"),
            license_number=data.get("license_number"),
        )


@dataclass
class PolicyInfo:
    policy_number: Optional[str] = None
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    status: Optional[str] = None  # new, renewal, rewrite
    billing_plan: Optional[str] = None  # direct, agency
    payment_plan: Optional[str] = None  # monthly, quarterly, annual
    deposit_amount: Optional[str] = None
    estimated_premium: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["PolicyInfo"]:
        if not data:
            return None
        return cls(
            policy_number=data.get("policy_number"),
            effective_date=data.get("effective_date"),
            expiration_date=data.get("expiration_date"),
            status=data.get("status"),
            billing_plan=data.get("billing_plan"),
            payment_plan=data.get("payment_plan"),
            deposit_amount=_str_or_none(data.get("deposit_amount")),
            estimated_premium=_str_or_none(data.get("estimated_premium")),
        )


@dataclass
class VehicleInfo:
    vin: Optional[str] = None
    year: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    body_type: Optional[str] = None
    gvw: Optional[str] = None
    cost_new: Optional[str] = None
    garaging_address: Optional[Address] = None
    use_type: Optional[str] = None  # service, commercial, retail, pleasure
    radius_of_travel: Optional[str] = None  # miles
    farthest_zone: Optional[str] = None  # zone code

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if k == "garaging_address" and v:
                d[k] = v.to_dict()
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["VehicleInfo"]:
        if not data:
            return None
        return cls(
            vin=data.get("vin"),
            year=data.get("year"),
            make=data.get("make"),
            model=data.get("model"),
            body_type=data.get("body_type"),
            gvw=data.get("gvw"),
            cost_new=data.get("cost_new"),
            garaging_address=Address.from_dict(data.get("garaging_address")),
            use_type=data.get("use_type"),
            radius_of_travel=data.get("radius_of_travel"),
            farthest_zone=data.get("farthest_zone"),
        )


@dataclass
class DriverInfo:
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_initial: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None  # M, F
    marital_status: Optional[str] = None  # S, M, W, D, P
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    years_experience: Optional[str] = None
    hire_date: Optional[str] = None
    mailing_address: Optional[Address] = None
    licensed_year: Optional[str] = None  # 4-digit year first licensed

    def get_first_name(self) -> Optional[str]:
        """Return first_name, falling back to splitting full_name."""
        if self.first_name:
            return self.first_name
        if self.full_name:
            parts = self.full_name.strip().split()
            return parts[0] if parts else None
        return None

    def get_last_name(self) -> Optional[str]:
        """Return last_name, falling back to splitting full_name."""
        if self.last_name:
            return self.last_name
        if self.full_name:
            parts = self.full_name.strip().split()
            return parts[-1] if len(parts) > 1 else None
        return None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if k == "mailing_address" and v:
                d[k] = v.to_dict()
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["DriverInfo"]:
        if not data:
            return None
        return cls(
            full_name=data.get("full_name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            middle_initial=data.get("middle_initial"),
            dob=data.get("dob"),
            sex=data.get("sex"),
            marital_status=data.get("marital_status"),
            license_number=data.get("license_number"),
            license_state=data.get("license_state"),
            years_experience=data.get("years_experience"),
            hire_date=data.get("hire_date"),
            mailing_address=Address.from_dict(data.get("mailing_address")),
            licensed_year=data.get("licensed_year"),
        )


@dataclass
class CoverageRequest:
    lob: Optional[str] = None
    coverage_type: Optional[str] = None
    limit: Optional[str] = None
    deductible: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["CoverageRequest"]:
        if not data:
            return None
        return cls(
            lob=data.get("lob"),
            coverage_type=data.get("coverage_type"),
            limit=data.get("limit"),
            deductible=data.get("deductible"),
        )


@dataclass
class LocationInfo:
    address: Optional[Address] = None
    building_area: Optional[str] = None
    construction_type: Optional[str] = None
    year_built: Optional[str] = None
    occupancy: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if k == "address" and v:
                d[k] = v.to_dict()
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["LocationInfo"]:
        if not data:
            return None
        return cls(
            address=Address.from_dict(data.get("address")),
            building_area=data.get("building_area"),
            construction_type=data.get("construction_type"),
            year_built=data.get("year_built"),
            occupancy=data.get("occupancy"),
        )


@dataclass
class LossHistoryEntry:
    date: Optional[str] = None
    lob: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[str] = None
    claim_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["LossHistoryEntry"]:
        if not data:
            return None
        return cls(
            date=data.get("date"),
            lob=data.get("lob"),
            description=data.get("description"),
            amount=data.get("amount"),
            claim_status=data.get("claim_status"),
        )


@dataclass
class AdditionalInterest:
    """Additional interest / lienholder / mortgagee on a policy."""
    name: Optional[str] = None
    address: Optional[Address] = None
    interest_type: Optional[str] = None  # additional_insured, mortgagee, lienholder, loss_payee, lenders_loss_payable
    account_number: Optional[str] = None
    certificate_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is None or v is False:
                continue
            if k == "address" and v:
                d[k] = v.to_dict()
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["AdditionalInterest"]:
        if not data:
            return None
        return cls(
            name=data.get("name"),
            address=Address.from_dict(data.get("address")),
            interest_type=data.get("interest_type"),
            account_number=data.get("account_number"),
            certificate_required=bool(data.get("certificate_required", False)),
        )


@dataclass
class PriorInsurance:
    """Prior insurance carrier information."""
    carrier_name: Optional[str] = None
    policy_number: Optional[str] = None
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    premium: Optional[str] = None
    lob: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["PriorInsurance"]:
        if not data:
            return None
        return cls(
            carrier_name=data.get("carrier_name"),
            policy_number=data.get("policy_number"),
            effective_date=data.get("effective_date"),
            expiration_date=data.get("expiration_date"),
            premium=_str_or_none(data.get("premium")),
            lob=data.get("lob"),
        )


@dataclass
class CyberInfo:
    """Cyber / privacy liability specific information."""
    annual_revenue: Optional[str] = None
    records_count: Optional[str] = None  # Number of PII/PHI records
    has_encryption: Optional[bool] = None
    has_mfa: Optional[bool] = None
    has_incident_response_plan: Optional[bool] = None
    prior_breaches: Optional[str] = None
    data_types: List[str] = field(default_factory=list)  # PII, PHI, PCI, etc.

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            if isinstance(v, list) and not v:
                continue
            d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["CyberInfo"]:
        if not data:
            return None
        return cls(
            annual_revenue=_str_or_none(data.get("annual_revenue")),
            records_count=_str_or_none(data.get("records_count")),
            has_encryption=data.get("has_encryption"),
            has_mfa=data.get("has_mfa"),
            has_incident_response_plan=data.get("has_incident_response_plan"),
            prior_breaches=_str_or_none(data.get("prior_breaches")),
            data_types=data.get("data_types", []),
        )


@dataclass
class CustomerSubmission:
    """Top-level container for all extracted entities from a customer email."""

    business: Optional[BusinessInfo] = None
    producer: Optional[ProducerInfo] = None
    policy: Optional[PolicyInfo] = None
    vehicles: List[VehicleInfo] = field(default_factory=list)
    drivers: List[DriverInfo] = field(default_factory=list)
    coverages: List[CoverageRequest] = field(default_factory=list)
    locations: List[LocationInfo] = field(default_factory=list)
    loss_history: List[LossHistoryEntry] = field(default_factory=list)
    additional_interests: List[AdditionalInterest] = field(default_factory=list)
    prior_insurance: List[PriorInsurance] = field(default_factory=list)
    cyber_info: Optional[CyberInfo] = None
    raw_email: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.business:
            d["business"] = self.business.to_dict()
        if self.producer:
            d["producer"] = self.producer.to_dict()
        if self.policy:
            d["policy"] = self.policy.to_dict()
        if self.vehicles:
            d["vehicles"] = [v.to_dict() for v in self.vehicles]
        if self.drivers:
            d["drivers"] = [dr.to_dict() for dr in self.drivers]
        if self.coverages:
            d["coverages"] = [c.to_dict() for c in self.coverages]
        if self.locations:
            d["locations"] = [loc.to_dict() for loc in self.locations]
        if self.loss_history:
            d["loss_history"] = [lh.to_dict() for lh in self.loss_history]
        if self.additional_interests:
            d["additional_interests"] = [ai.to_dict() for ai in self.additional_interests]
        if self.prior_insurance:
            d["prior_insurance"] = [pi.to_dict() for pi in self.prior_insurance]
        if self.cyber_info:
            d["cyber_info"] = self.cyber_info.to_dict()
        return d

    @classmethod
    def from_llm_json(cls, data: Dict[str, Any]) -> "CustomerSubmission":
        """Parse LLM JSON output into a CustomerSubmission."""
        # LLM may return null instead of [] for list fields — default to empty list
        vehicles = [VehicleInfo.from_dict(v) for v in (data.get("vehicles") or []) if v]
        drivers = [DriverInfo.from_dict(d) for d in (data.get("drivers") or []) if d]
        coverages = [CoverageRequest.from_dict(c) for c in (data.get("coverages") or []) if c]
        locations = [LocationInfo.from_dict(loc) for loc in (data.get("locations") or []) if loc]
        loss_history = [LossHistoryEntry.from_dict(lh) for lh in (data.get("loss_history") or []) if lh]
        additional_interests = [AdditionalInterest.from_dict(ai) for ai in (data.get("additional_interests") or []) if ai]
        prior_insurance = [PriorInsurance.from_dict(pi) for pi in (data.get("prior_insurance") or []) if pi]

        return cls(
            business=BusinessInfo.from_dict(data.get("business")),
            producer=ProducerInfo.from_dict(data.get("producer")),
            policy=PolicyInfo.from_dict(data.get("policy")),
            vehicles=[v for v in vehicles if v],
            drivers=[d for d in drivers if d],
            coverages=[c for c in coverages if c],
            locations=[loc for loc in locations if loc],
            loss_history=[lh for lh in loss_history if lh],
            additional_interests=[ai for ai in additional_interests if ai],
            prior_insurance=[pi for pi in prior_insurance if pi],
            cyber_info=CyberInfo.from_dict(data.get("cyber_info")),
        )

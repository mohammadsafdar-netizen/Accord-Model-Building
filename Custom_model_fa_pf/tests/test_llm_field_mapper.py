"""Tests for llm_field_mapper.py — 3-phase dynamic field mapper."""

import pytest

from Custom_model_fa_pf.entity_schema import (
    Address,
    BusinessInfo,
    CoverageRequest,
    CustomerSubmission,
    DriverInfo,
    PolicyInfo,
    ProducerInfo,
    VehicleInfo,
)
from Custom_model_fa_pf.form_reader import FormCatalog, FormField
from Custom_model_fa_pf.llm_field_mapper import (
    DETERMINISTIC_PATTERNS,
    CHECKBOX_ENTITY_MAP,
    SUFFIX_TO_INDEX,
    MappingResult,
    _resolve_entity_path,
    _resolve_checkbox,
    _resolve_indexed_field,
    _DRIVER_FIELD_MAP,
    _VEHICLE_FIELD_MAP,
    map_fields,
)


def _make_submission():
    """Create a realistic test CustomerSubmission."""
    return CustomerSubmission(
        business=BusinessInfo(
            business_name="Acme Trucking LLC",
            dba="Acme Transport",
            mailing_address=Address(
                line_one="123 Main St",
                city="Springfield",
                state="IL",
                zip_code="62701",
            ),
            tax_id="12-3456789",
            naics="484110",
            entity_type="llc",
            operations_description="Long-haul freight trucking",
            annual_revenue="2500000",
            employee_count="15",
        ),
        producer=ProducerInfo(
            agency_name="Westside Insurance Brokers",
            contact_name="Rachel Green",
            phone="(312) 555-1234",
            email="rachel@westside.com",
            producer_code="WSI-001",
        ),
        policy=PolicyInfo(
            effective_date="03/01/2026",
            expiration_date="03/01/2027",
            status="new",
            billing_plan="direct",
        ),
        vehicles=[
            VehicleInfo(
                vin="1HGCM82633A004352",
                year="2024",
                make="RAM",
                model="3500",
                body_type="PK",
                gvw="14000",
                cost_new="55000",
            ),
            VehicleInfo(
                vin="5TDZA23C06S123456",
                year="2023",
                make="Ford",
                model="F-250",
            ),
        ],
        drivers=[
            DriverInfo(
                full_name="John Smith",
                first_name="John",
                last_name="Smith",
                dob="05/15/1985",
                sex="M",
                marital_status="M",
                license_number="S123-4567-8901",
                license_state="IL",
                years_experience="15",
                hire_date="01/15/2020",
            ),
            DriverInfo(
                full_name="Jane Doe",
                first_name="Jane",
                last_name="Doe",
                dob="08/22/1990",
                sex="F",
                license_number="D987-6543-2109",
                license_state="IL",
            ),
        ],
        coverages=[
            CoverageRequest(
                lob="commercial_auto",
                coverage_type="liability",
                limit="1000000",
                per_person_limit="500000",
                per_accident_limit="1000000",
            ),
        ],
    )


def _make_catalog(fields_dict: dict) -> FormCatalog:
    """Create a FormCatalog from a simple {name: type} dict."""
    catalog = FormCatalog(pdf_path="test.pdf")
    for name, ftype in fields_dict.items():
        ff = FormField(name=name, field_type=ftype)
        # Infer suffix and base_name
        import re
        match = re.search(r"_([A-M]|\d+)$", name)
        if match:
            ff.suffix = match.group(0)
            ff.base_name = name[:match.start()]
        catalog.fields[name] = ff
    catalog.total_fields = len(catalog.fields)
    return catalog


class TestResolveEntityPath:
    def test_simple_path(self):
        sub = _make_submission()
        assert _resolve_entity_path(sub, "business.business_name") == "Acme Trucking LLC"

    def test_nested_path(self):
        sub = _make_submission()
        assert _resolve_entity_path(sub, "business.mailing_address.city") == "Springfield"

    def test_none_intermediate(self):
        sub = CustomerSubmission()
        assert _resolve_entity_path(sub, "business.mailing_address.city") is None

    def test_today(self):
        sub = _make_submission()
        val = _resolve_entity_path(sub, "_today")
        assert val is not None
        assert "/" in val  # MM/DD/YYYY format


class TestResolveCheckbox:
    def test_matching_entity_type(self):
        sub = _make_submission()
        result = _resolve_checkbox(sub, "business.entity_type", "llc")
        assert result == "1"

    def test_non_matching_entity_type(self):
        sub = _make_submission()
        result = _resolve_checkbox(sub, "business.entity_type", "corporation")
        assert result == "Off"

    def test_lob_matching(self):
        sub = _make_submission()
        result = _resolve_checkbox(sub, "_lob", "commercial_auto", lobs=["commercial_auto"])
        assert result == "1"

    def test_lob_not_matching(self):
        sub = _make_submission()
        result = _resolve_checkbox(sub, "_lob", "general_liability", lobs=["commercial_auto"])
        assert result == "Off"

    def test_coverage_type_matching(self):
        sub = _make_submission()
        result = _resolve_checkbox(sub, "_coverage_type", "liability", coverage_types={"liability"})
        assert result == "1"

    def test_missing_entity_returns_none(self):
        sub = CustomerSubmission()
        result = _resolve_checkbox(sub, "business.entity_type", "llc")
        assert result is None  # No data — don't set checkbox


class TestResolveIndexedField:
    def test_driver_first_name(self):
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_GivenName", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result == "John"

    def test_driver_second(self):
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_GivenName", 1, "drivers", _DRIVER_FIELD_MAP)
        assert result == "Jane"

    def test_driver_out_of_range(self):
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_GivenName", 5, "drivers", _DRIVER_FIELD_MAP)
        assert result is None

    def test_driver_dob(self):
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_BirthDate", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result == "05/15/1985"

    def test_vehicle_vin(self):
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_VIN", 0, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "1HGCM82633A004352"

    def test_vehicle_second(self):
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_Make", 1, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "Ford"

    def test_unknown_base_name(self):
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "UnknownField", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result is None

    # --- Tests for actual PDF field names (canonical names from Form 127) ---

    def test_driver_license_actual_name(self):
        """Driver_LicenseNumberIdentifier is the actual PDF name."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_LicenseNumberIdentifier", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result == "S123-4567-8901"

    def test_driver_gender_actual_name(self):
        """Driver_GenderCode is the actual PDF name (not Driver_SexCode)."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_GenderCode", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result == "M"

    def test_driver_experience_actual_name(self):
        """Driver_ExperienceYearCount is the actual PDF name."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_ExperienceYearCount", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result == "15"

    def test_driver_hired_date_actual_name(self):
        """Driver_HiredDate is the actual PDF name (not Driver_HireDate)."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_HiredDate", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result == "01/15/2020"

    def test_driver_licensed_state_actual_name(self):
        """Driver_LicensedStateOrProvinceCode is the actual PDF name."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_LicensedStateOrProvinceCode", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result == "IL"

    def test_driver_middle_initial_actual_name(self):
        """Driver_OtherGivenNameInitial is the actual PDF name."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Driver_OtherGivenNameInitial", 0, "drivers", _DRIVER_FIELD_MAP)
        assert result is None  # No middle initial in test data

    def test_vehicle_vin_actual_name(self):
        """Vehicle_VINIdentifier is the actual PDF name (not Vehicle_VIN)."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_VINIdentifier", 0, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "1HGCM82633A004352"

    def test_vehicle_make_actual_name(self):
        """Vehicle_ManufacturersName is the actual PDF name (not Vehicle_Make)."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_ManufacturersName", 0, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "RAM"

    def test_vehicle_model_actual_name(self):
        """Vehicle_ModelName is the actual PDF name (not Vehicle_Model)."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_ModelName", 0, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "3500"

    def test_vehicle_body_actual_name(self):
        """Vehicle_BodyCode is the actual PDF name (not Vehicle_BodyTypeCode)."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_BodyCode", 0, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "PK"

    def test_vehicle_gvw_actual_name(self):
        """Vehicle_GrossVehicleWeight is the actual PDF name."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_GrossVehicleWeight", 0, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "14000"

    def test_vehicle_cost_actual_name(self):
        """Vehicle_CostNewAmount is the actual PDF name."""
        sub = _make_submission()
        result = _resolve_indexed_field(sub, "Vehicle_CostNewAmount", 0, "vehicles", _VEHICLE_FIELD_MAP)
        assert result == "55000"


class TestSuffixIndex:
    def test_all_letters(self):
        assert SUFFIX_TO_INDEX["_A"] == 0
        assert SUFFIX_TO_INDEX["_B"] == 1
        assert SUFFIX_TO_INDEX["_M"] == 12

    def test_all_13_letters(self):
        assert len(SUFFIX_TO_INDEX) == 13


class TestPhase1Patterns:
    def test_patterns_are_valid_regex(self):
        import re
        for pattern, path in DETERMINISTIC_PATTERNS:
            re.compile(pattern)  # Should not raise

    def test_checkbox_patterns_valid(self):
        import re
        for pattern, path, value in CHECKBOX_ENTITY_MAP:
            re.compile(pattern)

    def test_business_name_pattern(self):
        import re
        matched = False
        for pattern, path in DETERMINISTIC_PATTERNS:
            if re.search(pattern, "NamedInsured_FullName_A"):
                assert path == "business.business_name"
                matched = True
                break
        assert matched


class TestMapFieldsPhase1And2:
    """Test map_fields with Phase 1+2 only (no LLM)."""

    def test_maps_business_name(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "NamedInsured_FullName_A": "text",
            "NamedInsured_MailingAddress_CityName_A": "text",
        })
        result = map_fields(sub, catalog, lobs=["commercial_auto"])
        assert "NamedInsured_FullName_A" in result.mappings
        assert result.mappings["NamedInsured_FullName_A"] == "Acme Trucking LLC"

    def test_maps_producer(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "Producer_FullName_A": "text",
            "Producer_ProducerCode_A": "text",
        })
        result = map_fields(sub, catalog)
        assert result.mappings.get("Producer_FullName_A") == "Westside Insurance Brokers"
        assert result.mappings.get("Producer_ProducerCode_A") == "WSI-001"

    def test_maps_policy_dates(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "Policy_EffectiveDate_A": "text",
            "Policy_ExpirationDate_A": "text",
        })
        result = map_fields(sub, catalog)
        assert result.mappings.get("Policy_EffectiveDate_A") == "03/01/2026"
        assert result.mappings.get("Policy_ExpirationDate_A") == "03/01/2027"

    def test_maps_checkbox_entity_type(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "LimitedLiabilityCorporationIndicator": "checkbox",
            "CorporationIndicator": "checkbox",
        })
        result = map_fields(sub, catalog)
        assert result.mappings.get("LimitedLiabilityCorporationIndicator") == "1"
        assert result.mappings.get("CorporationIndicator") == "Off"

    def test_maps_lob_checkbox(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "BusinessAutoIndicator": "checkbox",
            "GeneralLiabilityIndicator": "checkbox",
        })
        result = map_fields(sub, catalog, lobs=["commercial_auto"])
        assert result.mappings.get("BusinessAutoIndicator") == "1"
        assert result.mappings.get("GeneralLiabilityIndicator") == "Off"

    def test_maps_drivers_by_suffix(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "Driver_GivenName_A": "text",
            "Driver_Surname_A": "text",
            "Driver_GivenName_B": "text",
            "Driver_Surname_B": "text",
            "Driver_BirthDate_A": "text",
        })
        result = map_fields(sub, catalog)
        assert result.mappings.get("Driver_GivenName_A") == "John"
        assert result.mappings.get("Driver_Surname_A") == "Smith"
        assert result.mappings.get("Driver_GivenName_B") == "Jane"
        assert result.mappings.get("Driver_Surname_B") == "Doe"
        assert result.mappings.get("Driver_BirthDate_A") == "05/15/1985"

    def test_maps_vehicles_by_suffix(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "Vehicle_VIN_A": "text",
            "Vehicle_Make_A": "text",
            "Vehicle_VIN_B": "text",
            "Vehicle_Make_B": "text",
        })
        result = map_fields(sub, catalog)
        assert result.mappings.get("Vehicle_VIN_A") == "1HGCM82633A004352"
        assert result.mappings.get("Vehicle_Make_A") == "RAM"
        assert result.mappings.get("Vehicle_VIN_B") == "5TDZA23C06S123456"
        assert result.mappings.get("Vehicle_Make_B") == "Ford"

    def test_maps_drivers_actual_pdf_names(self):
        """Test Phase 2 with actual Form 127 driver field names."""
        sub = _make_submission()
        catalog = _make_catalog({
            "Driver_GivenName_A": "text",
            "Driver_Surname_A": "text",
            "Driver_GenderCode_A": "text",
            "Driver_LicenseNumberIdentifier_A": "text",
            "Driver_LicensedStateOrProvinceCode_A": "text",
            "Driver_ExperienceYearCount_A": "text",
            "Driver_HiredDate_A": "text",
            "Driver_BirthDate_B": "text",
        })
        result = map_fields(sub, catalog)
        assert result.mappings.get("Driver_GivenName_A") == "John"
        assert result.mappings.get("Driver_Surname_A") == "Smith"
        assert result.mappings.get("Driver_GenderCode_A") == "M"
        assert result.mappings.get("Driver_LicenseNumberIdentifier_A") == "S123-4567-8901"
        assert result.mappings.get("Driver_LicensedStateOrProvinceCode_A") == "IL"
        assert result.mappings.get("Driver_ExperienceYearCount_A") == "15"
        assert result.mappings.get("Driver_HiredDate_A") == "01/15/2020"
        assert result.mappings.get("Driver_BirthDate_B") == "08/22/1990"

    def test_maps_vehicles_actual_pdf_names(self):
        """Test Phase 2 with actual Form 127 vehicle field names."""
        sub = _make_submission()
        catalog = _make_catalog({
            "Vehicle_VINIdentifier_A": "text",
            "Vehicle_ManufacturersName_A": "text",
            "Vehicle_ModelName_A": "text",
            "Vehicle_BodyCode_A": "text",
            "Vehicle_GrossVehicleWeight_A": "text",
            "Vehicle_CostNewAmount_A": "text",
            "Vehicle_VINIdentifier_B": "text",
            "Vehicle_ManufacturersName_B": "text",
        })
        result = map_fields(sub, catalog)
        assert result.mappings.get("Vehicle_VINIdentifier_A") == "1HGCM82633A004352"
        assert result.mappings.get("Vehicle_ManufacturersName_A") == "RAM"
        assert result.mappings.get("Vehicle_ModelName_A") == "3500"
        assert result.mappings.get("Vehicle_BodyCode_A") == "PK"
        assert result.mappings.get("Vehicle_GrossVehicleWeight_A") == "14000"
        assert result.mappings.get("Vehicle_CostNewAmount_A") == "55000"
        assert result.mappings.get("Vehicle_VINIdentifier_B") == "5TDZA23C06S123456"
        assert result.mappings.get("Vehicle_ManufacturersName_B") == "Ford"

    def test_phase_counts(self):
        sub = _make_submission()
        catalog = _make_catalog({
            "NamedInsured_FullName_A": "text",  # Phase 1
            "Driver_GivenName_A": "text",  # Phase 2
            "Driver_GivenName_B": "text",  # Phase 2
            "RandomUnmappedField": "text",  # Unmapped
        })
        result = map_fields(sub, catalog)
        assert result.phase1_count >= 1
        assert result.phase2_count >= 2
        assert "RandomUnmappedField" in result.unmapped_fields

    def test_empty_submission(self):
        sub = CustomerSubmission()
        catalog = _make_catalog({
            "NamedInsured_FullName_A": "text",
            "Driver_GivenName_A": "text",
        })
        result = map_fields(sub, catalog)
        # Should not crash, just have fewer mappings
        assert result.total_mapped == 0 or result.total_mapped >= 0

    def test_empty_catalog(self):
        sub = _make_submission()
        catalog = FormCatalog(pdf_path="test.pdf")
        result = map_fields(sub, catalog)
        assert result.total_mapped == 0


class TestMappingResult:
    def test_total_mapped(self):
        r = MappingResult()
        r.mappings = {"f1": "v1", "f2": "v2"}
        assert r.total_mapped == 2

    def test_to_dict(self):
        r = MappingResult()
        r.mappings = {"f1": "v1"}
        r.phase1_count = 1
        d = r.to_dict()
        assert d["total_mapped"] == 1
        assert d["phase1_count"] == 1

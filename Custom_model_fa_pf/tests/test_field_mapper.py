"""Unit tests for field_mapper — mapping correctness, no LLM needed."""

import pytest
from Custom_model_fa_pf.entity_schema import (
    CustomerSubmission, BusinessInfo, Address, ProducerInfo,
    PolicyInfo, VehicleInfo, DriverInfo, CoverageRequest, Contact,
)
from Custom_model_fa_pf.form_assigner import FormAssignment
from Custom_model_fa_pf.field_mapper import map_all


def _make_submission() -> CustomerSubmission:
    """Create a fully populated test submission."""
    return CustomerSubmission(
        business=BusinessInfo(
            business_name="Test Corp",
            dba="Test Co",
            mailing_address=Address(
                line_one="123 Main St",
                city="Springfield",
                state="IL",
                zip_code="62701",
            ),
            tax_id="12-3456789",
            naics="484110",
            entity_type="corporation",
            operations_description="Trucking",
            annual_revenue="1000000",
            employee_count="10",
            years_in_business="5",
            website="www.testcorp.com",
            business_start_date="01/15/2020",
            contacts=[
                Contact(full_name="John Doe", phone="555-1234", email="john@test.com"),
                Contact(full_name="Jane Doe", phone="555-5678", email="jane@test.com"),
            ],
        ),
        producer=ProducerInfo(
            agency_name="Best Insurance Agency",
            contact_name="Jane Agent",
            phone="555-9999",
            email="jane@agency.com",
        ),
        policy=PolicyInfo(
            effective_date="03/01/2026",
            expiration_date="03/01/2027",
            status="new",
            billing_plan="direct",
            payment_plan="annual",
            deposit_amount="500",
            estimated_premium="5000",
        ),
        vehicles=[
            VehicleInfo(vin="1HGCM82633A004352", year="2024", make="Ford", model="F-350", body_type="PK", gvw="14000", cost_new="55000"),
        ],
        drivers=[
            DriverInfo(full_name="John Doe", dob="01/15/1985", sex="M", marital_status="M", license_number="D123456", license_state="IL", years_experience="15"),
        ],
        coverages=[
            CoverageRequest(lob="commercial_auto", coverage_type="liability", limit="1000000"),
            CoverageRequest(lob="commercial_auto", coverage_type="collision", deductible="1000"),
        ],
    )


def _make_assignments(form_numbers: list[str]) -> list[FormAssignment]:
    return [
        FormAssignment(
            form_number=fn,
            purpose=f"Form {fn}",
            schema_available=fn in {"125", "127", "137", "163"},
            lobs=["commercial_auto"],
        )
        for fn in form_numbers
    ]


class TestFieldMapper:
    def test_form_125_business_fields(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert f125["NamedInsured_FullName_A"] == "Test Corp"
        assert f125["NamedInsured_MailingAddress_CityName_A"] == "Springfield"
        assert f125["NamedInsured_MailingAddress_StateOrProvinceCode_A"] == "IL"
        assert f125["NamedInsured_TaxIdentifier_A"] == "12-3456789"

    def test_form_125_entity_type_checkbox(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert f125["NamedInsured_LegalEntity_CorporationIndicator_A"] == "1"

    def test_form_125_producer_fields(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert f125["Producer_FullName_A"] == "Best Insurance Agency"

    def test_form_125_policy_dates(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert f125["Policy_EffectiveDate_A"] == "03/01/2026"
        assert f125["Policy_ExpirationDate_A"] == "03/01/2027"

    def test_form_125_completion_date(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert "Form_CompletionDate_A" in f125

    def test_form_125_contact_fields(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        # Primary contact
        assert f125["NamedInsured_Primary_PhoneNumber_A"] == "555-1234"
        assert f125["NamedInsured_Contact_PrimaryEmailAddress_A"] == "john@test.com"
        # Secondary contact
        assert f125["NamedInsured_Contact_FullName_B"] == "Jane Doe"
        assert f125["NamedInsured_Contact_PrimaryPhoneNumber_B"] == "555-5678"

    def test_form_125_policy_status_and_billing(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert f125["Policy_Status_QuoteIndicator_A"] == "1"
        assert f125["Policy_Payment_DirectBillIndicator_A"] == "1"
        assert f125["Policy_Payment_PaymentScheduleCode_A"] == "annual"
        assert f125["Policy_Payment_DepositAmount_A"] == "500"
        assert f125["Policy_Payment_EstimatedTotalAmount_A"] == "5000"

    def test_form_125_business_start_date(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert f125["NamedInsured_BusinessStartDate_A"] == "01/15/2020"

    def test_form_125_website(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        assert f125["NamedInsured_Primary_WebsiteAddress_A"] == "www.testcorp.com"

    def test_form_127_driver_fields(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["127"]))
        f127 = mappings["127"]
        # Driver name is now split into first/last
        assert f127["Driver_GivenName_A"] == "John"
        assert f127["Driver_Surname_A"] == "Doe"
        assert f127["Driver_BirthDate_A"] == "01/15/1985"
        assert f127["Driver_GenderCode_A"] == "M"
        assert f127["Driver_LicenseNumberIdentifier_A"] == "D123456"

    def test_form_127_vehicle_fields(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["127"]))
        f127 = mappings["127"]
        assert f127["Vehicle_VINIdentifier_A"] == "1HGCM82633A004352"
        assert f127["Vehicle_ModelYear_A"] == "2024"
        assert f127["Vehicle_ManufacturersName_A"] == "Ford"
        assert f127["Vehicle_ModelName_A"] == "F-350"

    def test_form_137_header_fields(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["137"]))
        f137 = mappings["137"]
        assert f137["NamedInsured_FullName_A"] == "Test Corp"

    def test_form_137_no_vehicle_details(self):
        """Form 137 is coverage-only — vehicle details belong on Form 127."""
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["137"]))
        f137 = mappings["137"]
        # Vehicle physical details should NOT be on Form 137
        assert "Vehicle_VINIdentifier_A" not in f137
        assert "Vehicle_ModelYear_A" not in f137
        assert "Vehicle_ManufacturersName_A" not in f137
        assert "Vehicle_ModelName_A" not in f137
        # Business Auto Symbol should use correct schema name
        assert f137["Vehicle_BusinessAutoSymbol_OneIndicator_A"] == "1"

    def test_form_137_coverage_fields(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["137"]))
        f137 = mappings["137"]
        # CSL is an indicator (checkbox), not an amount field
        assert f137["Vehicle_CombinedSingleLimit_LimitIndicator_A"] == "1"
        assert f137["Vehicle_Collision_DeductibleAmount_A"] == "1000"

    def test_form_163_named_insured(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["163"]))
        f163 = mappings["163"]
        assert f163["Text13[0]"] == "Test Corp"

    def test_form_163_driver_rows(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["163"]))
        f163 = mappings["163"]
        # Driver 1: row starts at Text15[0]
        assert f163["Text15[0]"] == "1"  # driver_num
        assert f163["Text16[0]"] == "John"  # first_name
        assert f163["Text18[0]"] == "Doe"  # last_name
        assert f163["Text23[0]"] == "M"  # sex
        assert f163["Text24[0]"] == "01/15/1985"  # dob
        assert f163["Text27[0]"] == "D123456"  # license_number
        assert f163["marital[0]"] == "M"  # marital_status

    def test_form_163_multiple_drivers(self):
        sub = _make_submission()
        sub.drivers.append(
            DriverInfo(
                first_name="Jane", last_name="Smith",
                dob="06/20/1990", sex="F", marital_status="S",
                license_number="S654321", license_state="WI",
            )
        )
        mappings = map_all(sub, _make_assignments(["163"]))
        f163 = mappings["163"]
        # Driver 2: row starts at Text35[0]
        assert f163["Text35[0]"] == "2"  # driver_num
        assert f163["Text36[0]"] == "Jane"  # first_name
        assert f163["Text38[0]"] == "Smith"  # last_name
        assert f163["Text44[0]"] == "06/20/1990"  # dob
        assert f163["maritalstatus1[0]"] == "S"  # marital_status

    def test_multiple_forms_mapped(self):
        sub = _make_submission()
        mappings = map_all(sub, _make_assignments(["125", "127", "137"]))
        assert "125" in mappings
        assert "127" in mappings
        assert "137" in mappings

    def test_unavailable_schema_skipped(self):
        sub = _make_submission()
        assignments = [
            FormAssignment(form_number="126", purpose="GL", schema_available=False, lobs=["general_liability"]),
        ]
        mappings = map_all(sub, assignments)
        assert "126" not in mappings

    def test_empty_values_excluded(self):
        sub = CustomerSubmission(
            business=BusinessInfo(business_name="Test", mailing_address=Address()),
        )
        mappings = map_all(sub, _make_assignments(["125"]))
        f125 = mappings["125"]
        # Should not have empty address fields
        assert "NamedInsured_MailingAddress_CityName_A" not in f125


class TestDriverNameHelpers:
    """Test DriverInfo.get_first_name() and get_last_name() helpers."""

    def test_split_full_name(self):
        d = DriverInfo(full_name="John Doe")
        assert d.get_first_name() == "John"
        assert d.get_last_name() == "Doe"

    def test_explicit_names_override(self):
        d = DriverInfo(full_name="Johnny D", first_name="John", last_name="Doe")
        assert d.get_first_name() == "John"
        assert d.get_last_name() == "Doe"

    def test_single_name_no_last(self):
        d = DriverInfo(full_name="Cher")
        assert d.get_first_name() == "Cher"
        assert d.get_last_name() is None

    def test_three_part_name(self):
        d = DriverInfo(full_name="Mary Jane Watson")
        assert d.get_first_name() == "Mary"
        assert d.get_last_name() == "Watson"

    def test_no_name_at_all(self):
        d = DriverInfo()
        assert d.get_first_name() is None
        assert d.get_last_name() is None

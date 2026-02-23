#!/usr/bin/env python3
"""End-to-end accuracy test for Custom_model_fa_pf across all 5 LOBs.

Runs realistic emails through the full pipeline (LLM classification → extraction
→ form assignment → field mapping) and compares extracted fields against
hand-crafted ground truth.

Requires: Ollama running with qwen2.5:7b (or specify --model).

Usage:
    .venv/bin/python Custom_model_fa_pf/tests/test_accuracy_e2e.py
    .venv/bin/python Custom_model_fa_pf/tests/test_accuracy_e2e.py --model qwen2.5:7b
"""

import json
import sys
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Setup project path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from Custom_model_fa_pf.entity_schema import CustomerSubmission
from Custom_model_fa_pf.lob_classifier import LOBClassification

# ────────────────────────────────────────────────────────────
# TEST EMAILS — one per LOB, packed with extractable data
# ────────────────────────────────────────────────────────────

EMAILS = {
    "commercial_auto": """
Subject: New Commercial Auto Insurance Application

Dear Agent,

Please quote commercial auto insurance for our company:

Business: Pacific Coast Logistics LLC
DBA: PCL Transport
Address: 4500 Harbor Drive, Suite 310, Long Beach, CA 90802
FEIN: 95-4821367
NAICS Code: 484110
SIC Code: 4213
Entity Type: LLC
Operations: Regional freight and last-mile delivery services
Started business: 03/15/2018
Annual Revenue: $4,800,000
Number of employees: 28
Website: www.pcllogistics.com

Primary Contact: David Park, Operations Manager
Phone: (562) 555-7734
Email: david.park@pcllogistics.com

Second Contact: Susan Lee, Controller
Phone: (562) 555-7740
Email: susan.lee@pcllogistics.com

Insurance Producer: Westside Insurance Brokers
Agent: Rachel Green
Phone: (310) 555-2200
Email: rgreen@westsideins.com
Fax: (310) 555-2201
License: 0K88432
Producer Code: WSB-4401
Address: 1200 Wilshire Blvd, Suite 400, Los Angeles, CA 90017

Policy effective 06/01/2026 through 06/01/2027. This is a new policy.
We want direct billing, annual payment, deposit of $2,500, estimated premium $18,000.

Vehicles:
1. 2024 Freightliner Cascadia, VIN: 3AKJHHDR7PSMA9821, GVW: 80,000, Cost new: $172,000, body type: TT, garaged at 4500 Harbor Dr, Long Beach, CA 90802
2. 2023 Kenworth T680, VIN: 1XKYD49X2NJ439876, GVW: 80,000, Cost new: $165,000, body type: TT, garaged at 4500 Harbor Dr, Long Beach, CA 90802
3. 2025 Ford F-450, VIN: 1FD0W4HT5REA55123, GVW: 16,500, Cost new: $68,000, body type: PK, garaged at 780 E Main St, Riverside, CA 92501
4. 2024 RAM 3500, VIN: 3C63RRGL2RG112233, GVW: 14,000, Cost new: $62,000, body type: PK, garaged at 780 E Main St, Riverside, CA 92501

Drivers:
1. David Park, DOB: 08/22/1980, Male, Married, CDL# D880-2241-9900, CA, 18 years experience, first licensed 2008, hired 03/15/2018
2. Maria Santos, DOB: 04/10/1987, Female, Single, CDL# S337-6612-4455, CA, 11 years experience, first licensed 2015, hired 01/10/2020
3. James Chen, DOB: 12/03/1975, Male, Married, CDL# C225-1198-7733, CA, 24 years experience, first licensed 2002, hired 06/01/2021
4. Angela Brooks, DOB: 09/15/1992, Female, Divorced, DL# B991-4456-1100, CA, 8 years experience, first licensed 2018, hired 09/01/2023

Coverage requested:
- $1,000,000 Combined Single Limit liability
- Bodily injury: $500,000/$1,000,000
- Property damage: $500,000
- Collision deductible: $1,000
- Comprehensive deductible: $500
- Medical payments: $5,000
- Uninsured motorists: $1,000,000
- Underinsured motorists: $1,000,000

Loss history:
1. 10/15/2024, commercial auto, Rear-end collision on I-405, $12,500, closed
2. 03/22/2025, commercial auto, Cargo shift damage, $4,200, closed

Thank you,
David Park
""",

    "general_liability": """
Subject: General Liability Insurance Quote

Hello,

I need general liability coverage for my restaurant business.

Business Name: Bella Cucina Italian Kitchen
DBA: Bella Cucina
Mailing Address: 215 Restaurant Row, San Diego, CA 92101
FEIN: 95-7723456
NAICS: 722511
Entity Type: Corporation
Description: Full-service Italian restaurant with bar, catering services, and outdoor patio dining
Annual Revenue: $1,850,000
Employees: 24 full-time
In business since 2019

Primary Contact: Antonio Rossi, Owner
Phone: (619) 555-3344
Email: antonio@bellacucina.com

Second Contact: Lisa Rossi, Manager
Phone: (619) 555-3345
Email: lisa@bellacucina.com

Website: www.bellacucina.com

Producer: Pacific Shield Insurance Agency
Agent: Mark Thompson
Phone: (619) 555-8800
Fax: (619) 555-8801
Email: mthompson@pacificshield.com
License #: 0H71234
Producer Code: PSA-2201
Address: 500 Broadway, Suite 200, San Diego, CA 92101

Coverage needed effective 07/01/2026 to 07/01/2027.
This is a renewal policy, policy number GL-2025-44891.
$1,000,000 per occurrence / $2,000,000 general aggregate.
Agency billing, quarterly payments.

Location: 215 Restaurant Row, San Diego, CA 92101
Building: 4,500 sq ft, masonry construction, built 2005
Occupancy: restaurant

Loss history:
1. 01/20/2025, general liability, Customer slip and fall, $8,000, open
2. 08/15/2024, general liability, Food poisoning claim, $3,500, closed

Thank you,
Antonio Rossi
""",

    "commercial_property": """
Subject: Commercial Property Insurance Quote Request

Hi,

We need commercial property insurance for our manufacturing facility.

Business: Summit Steel Fabricators Inc
Address: 8800 Industrial Parkway, Cleveland, OH 44125
Tax ID: 34-6789012
Entity: S-Corporation (Subchapter S)
NAICS: 332312
Operations: Custom steel fabrication and welding services
Revenue: $6,200,000
Employees: 52
In business: 15 years
Business start date: 06/01/2011

Contact: Robert Wagner, President
Phone: (216) 555-4400
Email: rwagner@summitsteel.com

Contact 2: Patricia Holmes, CFO
Phone: (216) 555-4401
Email: pholmes@summitsteel.com

Producer: Great Lakes Insurance Group
Agent: Jennifer Walsh
Phone: (216) 555-9900
Email: jwalsh@greatlakesins.com
Fax: (216) 555-9901
Address: 1500 Euclid Ave, Cleveland, OH 44115
License: AG-445521
Code: GLIG-1102

We need coverage starting 08/01/2026 through 08/01/2027. New policy.
Direct billing, monthly payment plan, deposit $3,000, estimated premium $28,500.

Property Locations:
1. Main Plant: 8800 Industrial Parkway, Cleveland, OH 44125
   Building: 45,000 sq ft, steel frame construction, built 1998
   Occupancy: manufacturing/fabrication

2. Warehouse: 8820 Industrial Parkway, Cleveland, OH 44125
   Building: 20,000 sq ft, masonry, built 2008
   Occupancy: warehouse/storage

Equipment and contents value: $3,500,000

Thank you,
Robert Wagner
""",

    "workers_compensation": """
Subject: Workers Comp Insurance Application

Dear Agent,

We need workers compensation insurance.

Company: Mountain View Healthcare Services Corp
Address: 1200 Medical Center Drive, Denver, CO 80204
FEIN: 84-5567890
Corporation
NAICS: 621111
Operations: Home health care and assisted living staffing services
Revenue: $3,400,000
Employees: 95
Years in business: 12
Business started: 01/10/2014

Contact: Karen Mitchell, HR Director
Phone: (303) 555-6677
Email: kmitchell@mvhealthcare.com

Contact: Tom Bradley, CEO
Phone: (303) 555-6600
Email: tbradley@mvhealthcare.com

Producer: Rocky Mountain Insurance Partners
Agent Name: Steve Collins
Phone: (303) 555-1100
Email: scollins@rmip.com
Fax: (303) 555-1101
Address: 750 17th Street, Suite 800, Denver, CO 80202
License: 334521
Code: RMIP-5501

Coverage effective 09/01/2026 to 09/01/2027.
This is a new policy.
Agency billing, annual payment.
Estimated premium: $42,000

Annual payroll: $5,800,000

Thank you,
Karen Mitchell
""",

    "commercial_umbrella": """
Subject: Commercial Umbrella Policy Quote

Hi,

We need a commercial umbrella/excess liability policy for our construction firm.

Business: Iron Bridge Builders LLC
DBA: Iron Bridge Construction
Address: 3300 Construction Way, Phoenix, AZ 85009
FEIN: 86-2233445
Entity Type: LLC
NAICS: 236220
Operations: Commercial and industrial construction, heavy equipment operations
Revenue: $12,000,000
Employees: 68
In business: 20 years
Website: www.ironbridgebuilders.com
Business start date: 02/01/2006

Contact: Frank Morrison, Owner
Phone: (602) 555-8800
Email: fmorrison@ironbridge.com

Contact: Diana Cruz, Risk Manager
Phone: (602) 555-8810
Email: dcruz@ironbridge.com

Producer: Desert Sun Insurance
Agent: Amy Nguyen
Phone: (480) 555-3300
Fax: (480) 555-3301
Email: anguyen@desertsunins.com
License: 0M66778
Code: DSI-7701
Address: 2200 E Camelback Rd, Suite 100, Scottsdale, AZ 85251

Policy effective 10/01/2026 through 10/01/2027. New policy.
Direct billing, quarterly payments, deposit $5,000, estimated premium $35,000.

We want a $5,000,000 umbrella over the following underlying:
- Commercial auto: $1M CSL
- General liability: $1M/$2M
- Employer's liability: $1M

Vehicles (underlying auto):
1. 2024 Ford F-550, VIN: 1FDUF5HT6REA77001, GVW: 19,500, Cost: $74,000, body: CC, garaged at 3300 Construction Way, Phoenix, AZ 85009
2. 2023 Chevrolet Silverado 3500HD, VIN: 1GC4YVEK9PF223344, GVW: 14,000, Cost: $59,000, body: PK, garaged at 3300 Construction Way, Phoenix, AZ 85009

Drivers:
1. Frank Morrison, DOB: 05/18/1972, Male, Married, DL# M882-5500-3311, AZ, 30 years, first licensed 1996, hired 02/01/2006, 3300 Construction Way, Phoenix, AZ 85009
2. Tony Reyes, DOB: 11/30/1988, Male, Single, DL# R445-2211-8844, AZ, 12 years, first licensed 2014, hired 04/15/2019, 1500 W Van Buren, Phoenix, AZ 85007
3. Sarah Kim, DOB: 03/25/1995, Female, Married, middle initial J, DL# K112-9988-5566, AZ, 7 years, first licensed 2019, hired 08/01/2022, 900 N Central Ave, Phoenix, AZ 85004

Loss history:
1. 05/10/2025, commercial auto, Equipment trailer rollover, $22,000, open
2. 11/03/2024, general liability, Worker fall at job site, $15,000, closed

Thank you,
Frank Morrison
""",
}

# ────────────────────────────────────────────────────────────
# GROUND TRUTH — expected entity values per LOB test email
# ────────────────────────────────────────────────────────────

GROUND_TRUTH = {
    "commercial_auto": {
        "expected_lobs": ["commercial_auto"],
        "expected_forms": ["125", "127", "137"],
        "entities": {
            "business.business_name": "Pacific Coast Logistics LLC",
            "business.dba": "PCL Transport",
            "business.mailing_address.line_one": "4500 Harbor Drive, Suite 310",
            "business.mailing_address.city": "Long Beach",
            "business.mailing_address.state": "CA",
            "business.mailing_address.zip_code": "90802",
            "business.tax_id": "95-4821367",
            "business.naics": "484110",
            "business.sic": "4213",
            "business.entity_type": "llc",
            "business.operations_description": ["Regional freight", "last-mile delivery", "freight"],
            "business.annual_revenue": "4800000",
            "business.employee_count": "28",
            "business.business_start_date": "03/15/2018",
            "business.website": "www.pcllogistics.com",
            "business.contacts[0].full_name": ["David Park"],
            "business.contacts[0].phone": "(562) 555-7734",
            "business.contacts[0].email": "david.park@pcllogistics.com",
            "business.contacts[1].full_name": ["Susan Lee"],
            "business.contacts[1].phone": "(562) 555-7740",
            "business.contacts[1].email": "susan.lee@pcllogistics.com",
            "producer.agency_name": "Westside Insurance Brokers",
            "producer.contact_name": "Rachel Green",
            "producer.phone": "(310) 555-2200",
            "producer.email": "rgreen@westsideins.com",
            "producer.fax": "(310) 555-2201",
            "producer.license_number": "0K88432",
            "producer.producer_code": "WSB-4401",
            "producer.mailing_address.line_one": "1200 Wilshire Blvd, Suite 400",
            "producer.mailing_address.city": "Los Angeles",
            "producer.mailing_address.state": "CA",
            "producer.mailing_address.zip_code": "90017",
            "policy.effective_date": "06/01/2026",
            "policy.expiration_date": "06/01/2027",
            "policy.status": "new",
            "policy.billing_plan": "direct",
            "policy.payment_plan": "annual",
            "policy.deposit_amount": "2500",
            "policy.estimated_premium": "18000",
            "vehicles_count": 4,
            "vehicles[0].vin": "3AKJHHDR7PSMA9821",
            "vehicles[0].year": "2024",
            "vehicles[0].make": ["Freightliner"],
            "vehicles[0].model": ["Cascadia"],
            "vehicles[0].gvw": "80000",
            "vehicles[0].cost_new": "172000",
            "vehicles[0].body_type": "TT",
            "vehicles[1].vin": "1XKYD49X2NJ439876",
            "vehicles[1].year": "2023",
            "vehicles[1].make": ["Kenworth"],
            "vehicles[1].model": ["T680"],
            "vehicles[2].vin": "1FD0W4HT5REA55123",
            "vehicles[2].year": "2025",
            "vehicles[2].make": ["Ford"],
            "vehicles[2].model": ["F-450"],
            "vehicles[3].vin": "3C63RRGL2RG112233",
            "vehicles[3].year": "2024",
            "vehicles[3].make": ["RAM"],
            "vehicles[3].model": ["3500"],
            "drivers_count": 4,
            "drivers[0].full_name": ["David Park"],
            "drivers[0].dob": "08/22/1980",
            "drivers[0].sex": "M",
            "drivers[0].marital_status": "M",
            "drivers[0].license_number": "D880-2241-9900",
            "drivers[0].license_state": "CA",
            "drivers[0].years_experience": "18",
            "drivers[0].licensed_year": "2008",
            "drivers[1].full_name": ["Maria Santos"],
            "drivers[1].dob": "04/10/1987",
            "drivers[1].sex": "F",
            "drivers[1].marital_status": "S",
            "drivers[1].license_number": "S337-6612-4455",
            "drivers[1].license_state": "CA",
            "drivers[2].full_name": ["James Chen"],
            "drivers[2].dob": "12/03/1975",
            "drivers[2].sex": "M",
            "drivers[2].marital_status": "M",
            "drivers[3].full_name": ["Angela Brooks"],
            "drivers[3].dob": "09/15/1992",
            "drivers[3].sex": "F",
            "drivers[3].marital_status": "D",
            "coverages_count_min": 4,
            "loss_history_count": 2,
            "loss_history[0].date": "10/15/2024",
            "loss_history[0].amount": "12500",
            "loss_history[1].date": "03/22/2025",
        },
        # Expected field mappings on actual PDF forms
        "form_fields": {
            "125": {
                "NamedInsured_FullName_A": "Pacific Coast Logistics LLC",
                "NamedInsured_FullName_B": "PCL Transport",
                "NamedInsured_MailingAddress_CityName_A": "Long Beach",
                "NamedInsured_MailingAddress_StateOrProvinceCode_A": "CA",
                "NamedInsured_MailingAddress_PostalCode_A": "90802",
                "NamedInsured_TaxIdentifier_A": "95-4821367",
                "NamedInsured_NAICSCode_A": "484110",
                "NamedInsured_SICCode_A": "4213",
                "NamedInsured_LegalEntity_LimitedLiabilityCorporationIndicator_A": "1",
                "NamedInsured_BusinessStartDate_A": "03/15/2018",
                "NamedInsured_Primary_WebsiteAddress_A": "www.pcllogistics.com",
                "Policy_EffectiveDate_A": "06/01/2026",
                "Policy_ExpirationDate_A": "06/01/2027",
                "Policy_Status_QuoteIndicator_A": "1",
                "Policy_Payment_DirectBillIndicator_A": "1",
                "Policy_Payment_PaymentScheduleCode_A": "annual",
                "Policy_Payment_DepositAmount_A": "2500",
                "Policy_Payment_EstimatedTotalAmount_A": "18000",
                "Producer_FullName_A": "Westside Insurance Brokers",
                "Producer_ContactPerson_FullName_A": "Rachel Green",
                "Producer_ContactPerson_PhoneNumber_A": "(310) 555-2200",
                "Producer_ContactPerson_EmailAddress_A": "rgreen@westsideins.com",
                "Producer_FaxNumber_A": "(310) 555-2201",
                "Producer_MailingAddress_CityName_A": "Los Angeles",
                "Producer_MailingAddress_StateOrProvinceCode_A": "CA",
                "Producer_MailingAddress_PostalCode_A": "90017",
            },
            "127": {
                "NamedInsured_FullName_A": "Pacific Coast Logistics LLC",
                "Driver_GivenName_A": "David",
                "Driver_Surname_A": "Park",
                "Driver_BirthDate_A": "08/22/1980",
                "Driver_GenderCode_A": "M",
                "Driver_MaritalStatusCode_A": "M",
                "Driver_LicenseNumber_A": "D880-2241-9900",
                "Driver_LicensedStateOrProvinceCode_A": "CA",
                "Vehicle_VINIdentifier_A": "3AKJHHDR7PSMA9821",
                "Vehicle_ModelYear_A": "2024",
                "Vehicle_Manufacturer_A": "Freightliner",
                "Vehicle_ModelName_A": "Cascadia",
            },
            "137": {
                "NamedInsured_FullName_A": "Pacific Coast Logistics LLC",
                "Vehicle_VINIdentifier_A": "3AKJHHDR7PSMA9821",
                "Vehicle_ModelYear_A": "2024",
                "Vehicle_Manufacturer_A": "Freightliner",
                "Vehicle_BusinessAutoDesignatedSymbol_1_A": "1",
            },
        },
    },
    "general_liability": {
        "expected_lobs": ["general_liability"],
        "expected_forms": ["125"],
        "entities": {
            "business.business_name": ["Bella Cucina Italian Kitchen", "Bella Cucina"],
            "business.dba": ["Bella Cucina"],
            "business.mailing_address.city": "San Diego",
            "business.mailing_address.state": "CA",
            "business.mailing_address.zip_code": "92101",
            "business.tax_id": "95-7723456",
            "business.naics": "722511",
            "business.entity_type": "corporation",
            "business.annual_revenue": "1850000",
            "business.employee_count": "24",
            "business.website": "www.bellacucina.com",
            "business.contacts[0].full_name": ["Antonio Rossi"],
            "business.contacts[0].phone": "(619) 555-3344",
            "business.contacts[0].email": "antonio@bellacucina.com",
            "producer.agency_name": "Pacific Shield Insurance Agency",
            "producer.contact_name": "Mark Thompson",
            "producer.phone": "(619) 555-8800",
            "producer.email": "mthompson@pacificshield.com",
            "policy.effective_date": "07/01/2026",
            "policy.expiration_date": "07/01/2027",
            "policy.status": "renewal",
            "policy.policy_number": "GL-2025-44891",
            "policy.billing_plan": "agency",
            "policy.payment_plan": "quarterly",
            "locations_count_min": 1,
            "loss_history_count": 2,
        },
        "form_fields": {
            "125": {
                "NamedInsured_MailingAddress_CityName_A": "San Diego",
                "NamedInsured_MailingAddress_StateOrProvinceCode_A": "CA",
                "NamedInsured_TaxIdentifier_A": "95-7723456",
                "NamedInsured_LegalEntity_CorporationIndicator_A": "1",
                "Policy_EffectiveDate_A": "07/01/2026",
                "Policy_ExpirationDate_A": "07/01/2027",
                "Producer_FullName_A": "Pacific Shield Insurance Agency",
            },
        },
    },
    "commercial_property": {
        "expected_lobs": ["commercial_property"],
        "expected_forms": ["125"],
        "entities": {
            "business.business_name": "Summit Steel Fabricators Inc",
            "business.mailing_address.city": "Cleveland",
            "business.mailing_address.state": "OH",
            "business.mailing_address.zip_code": "44125",
            "business.tax_id": "34-6789012",
            "business.entity_type": "subchapter_s",
            "business.naics": "332312",
            "business.annual_revenue": "6200000",
            "business.employee_count": "52",
            "business.business_start_date": "06/01/2011",
            "business.contacts[0].full_name": ["Robert Wagner"],
            "business.contacts[0].phone": "(216) 555-4400",
            "business.contacts[0].email": "rwagner@summitsteel.com",
            "producer.agency_name": "Great Lakes Insurance Group",
            "producer.contact_name": "Jennifer Walsh",
            "producer.phone": "(216) 555-9900",
            "producer.email": "jwalsh@greatlakesins.com",
            "policy.effective_date": "08/01/2026",
            "policy.expiration_date": "08/01/2027",
            "policy.status": "new",
            "policy.billing_plan": "direct",
            "policy.payment_plan": "monthly",
            "policy.deposit_amount": "3000",
            "policy.estimated_premium": "28500",
            "locations_count_min": 1,
        },
        "form_fields": {
            "125": {
                "NamedInsured_MailingAddress_CityName_A": "Cleveland",
                "NamedInsured_MailingAddress_StateOrProvinceCode_A": "OH",
                "NamedInsured_TaxIdentifier_A": "34-6789012",
                "Policy_EffectiveDate_A": "08/01/2026",
                "Policy_ExpirationDate_A": "08/01/2027",
                "Policy_Status_QuoteIndicator_A": "1",
                "Policy_Payment_DirectBillIndicator_A": "1",
                "Producer_FullName_A": "Great Lakes Insurance Group",
            },
        },
    },
    "workers_compensation": {
        "expected_lobs": ["workers_compensation"],
        "expected_forms": ["125"],
        "entities": {
            "business.business_name": "Mountain View Healthcare Services Corp",
            "business.mailing_address.city": "Denver",
            "business.mailing_address.state": "CO",
            "business.mailing_address.zip_code": "80204",
            "business.tax_id": "84-5567890",
            "business.entity_type": "corporation",
            "business.naics": "621111",
            "business.annual_revenue": "3400000",
            "business.employee_count": "95",
            "business.business_start_date": "01/10/2014",
            "business.contacts[0].full_name": ["Karen Mitchell"],
            "business.contacts[0].phone": "(303) 555-6677",
            "business.contacts[0].email": "kmitchell@mvhealthcare.com",
            "producer.agency_name": "Rocky Mountain Insurance Partners",
            "producer.contact_name": "Steve Collins",
            "producer.phone": "(303) 555-1100",
            "producer.email": "scollins@rmip.com",
            "policy.effective_date": "09/01/2026",
            "policy.expiration_date": "09/01/2027",
            "policy.status": "new",
            "policy.billing_plan": "agency",
            "policy.payment_plan": "annual",
            "policy.estimated_premium": "42000",
        },
        "form_fields": {
            "125": {
                "NamedInsured_MailingAddress_CityName_A": "Denver",
                "NamedInsured_MailingAddress_StateOrProvinceCode_A": "CO",
                "NamedInsured_TaxIdentifier_A": "84-5567890",
                "NamedInsured_LegalEntity_CorporationIndicator_A": "1",
                "Policy_EffectiveDate_A": "09/01/2026",
                "Producer_FullName_A": "Rocky Mountain Insurance Partners",
            },
        },
    },
    "commercial_umbrella": {
        "expected_lobs": ["commercial_umbrella"],
        "expected_forms": ["125", "163"],
        "entities": {
            "business.business_name": "Iron Bridge Builders LLC",
            "business.dba": ["Iron Bridge Construction"],
            "business.mailing_address.city": "Phoenix",
            "business.mailing_address.state": "AZ",
            "business.mailing_address.zip_code": "85009",
            "business.tax_id": "86-2233445",
            "business.entity_type": "llc",
            "business.naics": "236220",
            "business.annual_revenue": "12000000",
            "business.employee_count": "68",
            "business.website": "www.ironbridgebuilders.com",
            "business.business_start_date": "02/01/2006",
            "business.contacts[0].full_name": ["Frank Morrison"],
            "business.contacts[0].phone": "(602) 555-8800",
            "business.contacts[0].email": "fmorrison@ironbridge.com",
            "producer.agency_name": "Desert Sun Insurance",
            "producer.contact_name": "Amy Nguyen",
            "producer.phone": "(480) 555-3300",
            "producer.email": "anguyen@desertsunins.com",
            "policy.effective_date": "10/01/2026",
            "policy.expiration_date": "10/01/2027",
            "policy.status": "new",
            "policy.billing_plan": "direct",
            "policy.payment_plan": "quarterly",
            "policy.deposit_amount": "5000",
            "policy.estimated_premium": "35000",
            "drivers_count": 3,
            "drivers[0].full_name": ["Frank Morrison"],
            "drivers[0].dob": "05/18/1972",
            "drivers[0].sex": "M",
            "drivers[0].marital_status": "M",
            "drivers[0].license_number": "M882-5500-3311",
            "drivers[0].license_state": "AZ",
            "drivers[0].licensed_year": "1996",
            "drivers[1].full_name": ["Tony Reyes"],
            "drivers[1].dob": "11/30/1988",
            "drivers[1].sex": "M",
            "drivers[2].full_name": ["Sarah Kim"],
            "drivers[2].dob": "03/25/1995",
            "drivers[2].sex": "F",
            "drivers[2].middle_initial": "J",
            "vehicles_count": 2,
            "vehicles[0].vin": "1FDUF5HT6REA77001",
            "vehicles[0].year": "2024",
            "vehicles[0].make": ["Ford"],
            "vehicles[0].model": ["F-550"],
            "vehicles[1].vin": "1GC4YVEK9PF223344",
            "loss_history_count": 2,
        },
        "form_fields": {
            "125": {
                "NamedInsured_MailingAddress_CityName_A": "Phoenix",
                "NamedInsured_MailingAddress_StateOrProvinceCode_A": "AZ",
                "NamedInsured_TaxIdentifier_A": "86-2233445",
                "NamedInsured_LegalEntity_LimitedLiabilityCorporationIndicator_A": "1",
                "Policy_EffectiveDate_A": "10/01/2026",
                "Policy_ExpirationDate_A": "10/01/2027",
                "Producer_FullName_A": "Desert Sun Insurance",
            },
            "163": {
                "Text13[0]": "Iron Bridge Builders LLC",
                "Text1[0]": "10/01/2026",
                "Text8[0]": "Desert Sun Insurance",
            },
        },
    },
}


# ────────────────────────────────────────────────────────────
# COMPARISON ENGINE
# ────────────────────────────────────────────────────────────

def _normalize(val: Any) -> str:
    """Normalize a value for comparison."""
    if val is None:
        return ""
    s = str(val).strip().lower()
    # Normalize currency/numbers: remove $, commas
    s = s.replace("$", "").replace(",", "")
    return s


def _values_match(expected: Any, actual: Any) -> bool:
    """Check if actual matches expected. Supports list-of-acceptable-values."""
    if actual is None:
        return False
    norm_actual = _normalize(actual)
    if not norm_actual:
        return False

    if isinstance(expected, list):
        # Any of the expected values is acceptable (substring match)
        return any(_normalize(e) in norm_actual or norm_actual in _normalize(e) for e in expected)
    else:
        norm_exp = _normalize(expected)
        return norm_exp == norm_actual or norm_exp in norm_actual or norm_actual in norm_exp


def _get_nested(obj: Any, path: str) -> Any:
    """Get a value from a nested object using dot.notation with [N] indexing."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        # Handle array indexing like "vehicles[0]"
        if "[" in part:
            name, idx_str = part.split("[", 1)
            idx = int(idx_str.rstrip("]"))
            if hasattr(current, name):
                arr = getattr(current, name)
            elif isinstance(current, dict):
                arr = current.get(name, [])
            else:
                return None
            if isinstance(arr, list) and idx < len(arr):
                current = arr[idx]
            else:
                return None
        elif hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


@dataclass
class FieldResult:
    field_path: str
    expected: Any
    actual: Any
    match: bool
    category: str = ""  # e.g. "business", "producer", "vehicle", "driver"


@dataclass
class LOBResult:
    lob_id: str
    lob_classified: bool = False
    forms_correct: bool = False
    expected_forms: List[str] = field(default_factory=list)
    actual_forms: List[str] = field(default_factory=list)
    entity_results: List[FieldResult] = field(default_factory=list)
    form_field_results: Dict[str, List[FieldResult]] = field(default_factory=dict)
    pipeline_time_s: float = 0.0
    error: Optional[str] = None

    @property
    def entity_correct(self) -> int:
        return sum(1 for r in self.entity_results if r.match)

    @property
    def entity_total(self) -> int:
        return len(self.entity_results)

    @property
    def entity_accuracy(self) -> float:
        return self.entity_correct / self.entity_total if self.entity_total > 0 else 0.0

    def form_accuracy(self, form_num: str) -> float:
        results = self.form_field_results.get(form_num, [])
        if not results:
            return 0.0
        return sum(1 for r in results if r.match) / len(results)


# ────────────────────────────────────────────────────────────
# PIPELINE RUNNER
# ────────────────────────────────────────────────────────────

def run_single_test(lob_id: str, email_text: str, gt: dict, model: str) -> LOBResult:
    """Run one email through the pipeline and compare to ground truth."""
    from Custom_model_fa_pf import pipeline

    result = LOBResult(lob_id=lob_id)

    try:
        t0 = time.time()
        pr = pipeline.run(
            email_text=email_text,
            json_only=True,
            model=model,
            confidence_threshold=0.5,  # Lower to catch edge cases
        )
        result.pipeline_time_s = time.time() - t0

        # --- Check LOB classification ---
        classified_lobs = [l.lob_id for l in pr.lobs]
        result.lob_classified = all(l in classified_lobs for l in gt["expected_lobs"])

        # --- Check form assignment ---
        assigned_forms = sorted(pr.field_values.keys())
        result.expected_forms = sorted(gt["expected_forms"])
        result.actual_forms = assigned_forms
        result.forms_correct = all(f in assigned_forms for f in gt["expected_forms"])

        # --- Check entity extraction ---
        entities = pr.entities
        if entities:
            for path, expected in gt["entities"].items():
                # Special array count checks (top-level only, e.g. "vehicles_count")
                # Do NOT match nested fields like "business.employee_count"
                if "." not in path and path.endswith("_count"):
                    arr_name = path.replace("_count", "")
                    arr = getattr(entities, arr_name, []) or []
                    actual_count = len(arr) if isinstance(arr, list) else 0
                    exp_count = int(expected)
                    result.entity_results.append(FieldResult(
                        field_path=path, expected=exp_count, actual=actual_count,
                        match=(actual_count == exp_count),
                        category=arr_name,
                    ))
                    continue
                if "." not in path and path.endswith("_count_min"):
                    arr_name = path.replace("_count_min", "")
                    arr = getattr(entities, arr_name, []) or []
                    actual_count = len(arr) if isinstance(arr, list) else 0
                    min_count = int(expected)
                    result.entity_results.append(FieldResult(
                        field_path=path, expected=f">={min_count}", actual=actual_count,
                        match=(actual_count >= min_count),
                        category=arr_name,
                    ))
                    continue

                actual = _get_nested(entities, path)
                match = _values_match(expected, actual)
                # Determine category
                cat = path.split(".")[0].split("[")[0]
                result.entity_results.append(FieldResult(
                    field_path=path, expected=expected, actual=actual,
                    match=match, category=cat,
                ))

        # --- Check form field mappings ---
        for form_num, expected_fields in gt.get("form_fields", {}).items():
            field_results = []
            actual_fields = pr.field_values.get(form_num, {})
            for field_name, expected_val in expected_fields.items():
                actual_val = actual_fields.get(field_name)
                match = _values_match(expected_val, actual_val)
                field_results.append(FieldResult(
                    field_path=field_name, expected=expected_val, actual=actual_val,
                    match=match, category=f"Form {form_num}",
                ))
            result.form_field_results[form_num] = field_results

    except Exception as e:
        result.error = str(e)
        import traceback
        traceback.print_exc()

    return result


# ────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ────────────────────────────────────────────────────────────

def print_report(results: Dict[str, LOBResult]):
    """Print a detailed accuracy report."""
    W = 90
    print("\n" + "=" * W)
    print("  CUSTOM_MODEL_FA_PF — END-TO-END ACCURACY REPORT")
    print("=" * W)

    total_entity_correct = 0
    total_entity_total = 0
    total_form_correct = 0
    total_form_total = 0

    for lob_id, r in results.items():
        print(f"\n{'─' * W}")
        lob_display = lob_id.upper().replace("_", " ")
        status = "PASS" if r.lob_classified else "FAIL"
        print(f"  LOB: {lob_display}")
        print(f"{'─' * W}")

        if r.error:
            print(f"  ERROR: {r.error}")
            continue

        print(f"  Pipeline time: {r.pipeline_time_s:.1f}s")
        print(f"  LOB classified correctly: {'YES' if r.lob_classified else 'NO'}")
        forms_status = "YES" if r.forms_correct else "NO"
        print(f"  Forms assigned correctly: {forms_status}  (expected: {r.expected_forms}, got: {r.actual_forms})")

        # --- Entity extraction detail ---
        print(f"\n  ENTITY EXTRACTION: {r.entity_correct}/{r.entity_total} ({r.entity_accuracy:.0%})")
        total_entity_correct += r.entity_correct
        total_entity_total += r.entity_total

        # Group by category
        categories = {}
        for fr in r.entity_results:
            categories.setdefault(fr.category, []).append(fr)

        for cat, fields in sorted(categories.items()):
            cat_correct = sum(1 for f in fields if f.match)
            cat_total = len(fields)
            cat_pct = cat_correct / cat_total if cat_total > 0 else 0
            print(f"\n    {cat} ({cat_correct}/{cat_total} = {cat_pct:.0%}):")
            for fr in fields:
                icon = "OK" if fr.match else "MISS"
                actual_display = repr(fr.actual) if fr.actual is not None else "None"
                if len(str(actual_display)) > 40:
                    actual_display = str(actual_display)[:40] + "..."
                expected_display = repr(fr.expected)
                if len(str(expected_display)) > 35:
                    expected_display = str(expected_display)[:35] + "..."
                short_path = fr.field_path.split(".")[-1] if "." in fr.field_path else fr.field_path
                print(f"      [{icon:4s}] {short_path:30s} expected={expected_display:35s} got={actual_display}")

        # --- Form field mapping detail ---
        for form_num, field_results in sorted(r.form_field_results.items()):
            fc = sum(1 for f in field_results if f.match)
            ft = len(field_results)
            fp = fc / ft if ft > 0 else 0
            total_form_correct += fc
            total_form_total += ft
            print(f"\n  FORM {form_num} FIELD MAPPING: {fc}/{ft} ({fp:.0%})")
            for fr in field_results:
                icon = "OK" if fr.match else "MISS"
                actual_display = repr(fr.actual) if fr.actual is not None else "None"
                if len(str(actual_display)) > 40:
                    actual_display = str(actual_display)[:40] + "..."
                short_name = fr.field_path
                if len(short_name) > 45:
                    short_name = "..." + short_name[-42:]
                print(f"      [{icon:4s}] {short_name:45s} = {actual_display}")

    # --- Summary ---
    print(f"\n{'=' * W}")
    print(f"  SUMMARY")
    print(f"{'=' * W}")

    # LOB classification
    lob_ok = sum(1 for r in results.values() if r.lob_classified)
    print(f"\n  LOB Classification:   {lob_ok}/{len(results)} LOBs correctly classified")

    # Forms
    form_ok = sum(1 for r in results.values() if r.forms_correct)
    print(f"  Form Assignment:      {form_ok}/{len(results)} test cases with correct forms")

    # Entity accuracy
    ent_pct = total_entity_correct / total_entity_total if total_entity_total > 0 else 0
    print(f"  Entity Extraction:    {total_entity_correct}/{total_entity_total} fields correct ({ent_pct:.1%})")

    # Form field accuracy
    ff_pct = total_form_correct / total_form_total if total_form_total > 0 else 0
    print(f"  Form Field Mapping:   {total_form_correct}/{total_form_total} fields correct ({ff_pct:.1%})")

    # Per-LOB summary table
    print(f"\n  {'LOB':<25s} {'Entity':>12s} {'Form Fields':>12s} {'Time':>8s}")
    print(f"  {'─' * 60}")
    for lob_id, r in results.items():
        ent_s = f"{r.entity_correct}/{r.entity_total}" if not r.error else "ERROR"
        ff_correct = sum(sum(1 for f in frs if f.match) for frs in r.form_field_results.values())
        ff_total = sum(len(frs) for frs in r.form_field_results.values())
        ff_s = f"{ff_correct}/{ff_total}" if not r.error else "ERROR"
        time_s = f"{r.pipeline_time_s:.1f}s" if not r.error else "N/A"
        print(f"  {lob_id:<25s} {ent_s:>12s} {ff_s:>12s} {time_s:>8s}")

    overall_correct = total_entity_correct + total_form_correct
    overall_total = total_entity_total + total_form_total
    overall_pct = overall_correct / overall_total if overall_total > 0 else 0
    print(f"\n  OVERALL ACCURACY: {overall_correct}/{overall_total} = {overall_pct:.1%}")
    total_time = sum(r.pipeline_time_s for r in results.values())
    print(f"  TOTAL TIME: {total_time:.1f}s")
    print(f"{'=' * W}\n")

    return {
        "entity_accuracy": ent_pct,
        "form_field_accuracy": ff_pct,
        "overall_accuracy": overall_pct,
        "lob_classification": lob_ok,
        "details": {lob_id: {
            "entity": r.entity_accuracy,
            "forms": {fn: r.form_accuracy(fn) for fn in r.form_field_results},
        } for lob_id, r in results.items()},
    }


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="E2E accuracy test for Custom_model_fa_pf")
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model name")
    parser.add_argument("--lob", default=None, help="Test single LOB only (e.g. commercial_auto)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    print(f"Model: {args.model}")
    print(f"Testing {len(EMAILS) if not args.lob else 1} LOBs...")

    test_lobs = [args.lob] if args.lob else list(EMAILS.keys())
    results = {}

    for lob_id in test_lobs:
        if lob_id not in EMAILS:
            print(f"Unknown LOB: {lob_id}")
            continue

        print(f"\n>>> Running: {lob_id}...")
        r = run_single_test(lob_id, EMAILS[lob_id], GROUND_TRUTH[lob_id], args.model)
        results[lob_id] = r

        if r.error:
            print(f"  ERROR: {r.error}")
        else:
            print(f"  Entity: {r.entity_correct}/{r.entity_total} ({r.entity_accuracy:.0%}) in {r.pipeline_time_s:.1f}s")

    summary = print_report(results)

    # Save JSON report
    report_path = ROOT / "Custom_model_fa_pf" / "output" / "accuracy_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        # Build serializable version
        serial = {}
        for lob_id, r in results.items():
            serial[lob_id] = {
                "lob_classified": r.lob_classified,
                "forms_correct": r.forms_correct,
                "entity_accuracy": r.entity_accuracy,
                "entity_correct": r.entity_correct,
                "entity_total": r.entity_total,
                "pipeline_time_s": r.pipeline_time_s,
                "error": r.error,
                "entity_details": [
                    {"field": fr.field_path, "expected": str(fr.expected), "actual": str(fr.actual), "match": fr.match}
                    for fr in r.entity_results
                ],
                "form_field_details": {
                    fn: [
                        {"field": fr.field_path, "expected": str(fr.expected), "actual": str(fr.actual), "match": fr.match}
                        for fr in frs
                    ]
                    for fn, frs in r.form_field_results.items()
                },
            }
        json.dump({"summary": summary, "details": serial}, f, indent=2, default=str)
    print(f"JSON report saved to: {report_path}")


if __name__ == "__main__":
    main()

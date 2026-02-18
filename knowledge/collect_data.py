#!/usr/bin/env python3
"""
Collect free insurance knowledge data for the RAG system.

Sources:
  1. Schema tooltips (local — schemas/*.json)
  2. NAICS codes (census.gov or embedded fallback)
  3. Insurance glossary (NAIC website or embedded fallback)
  4. State insurance info (embedded)
  5. ACORD form structure (local — schemas + prompts.py)
  6. Common insurance abbreviations (embedded)

Usage:
    .venv/bin/python knowledge/collect_data.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from knowledge.constants import DATA_DIR, SCHEMAS_DIR


def collect_schema_knowledge() -> list[dict]:
    """Extract field definitions from ACORD schemas."""
    docs = []
    form_map = {"125": "Commercial Insurance Application",
                "127": "Business Auto Section",
                "137": "Commercial Auto Section"}

    for schema_file in sorted(SCHEMAS_DIR.glob("*.json")):
        form_num = schema_file.stem
        form_name = form_map.get(form_num, f"ACORD {form_num}")
        data = json.loads(schema_file.read_text())
        fields = data.get("fields", data)

        for field_name, field_def in fields.items():
            if not isinstance(field_def, dict):
                continue
            docs.append({
                "field_name": field_name,
                "form_type": form_num,
                "form_name": form_name,
                "type": field_def.get("type", "text"),
                "tooltip": field_def.get("tooltip", ""),
                "category": field_def.get("category", "general"),
                "page": field_def.get("page", 0),
                "suffix": field_def.get("suffix", ""),
            })

    print(f"  Schema knowledge: {len(docs)} field definitions")
    return docs


def collect_naics_codes() -> list[dict]:
    """Collect NAICS codes. Try download, fall back to embedded core set."""
    codes = []

    # Try downloading from census.gov
    try:
        import requests
        url = "https://www.census.gov/naics/2022NAICS/2-6%20digit_2022_Codes.xlsx"
        print(f"  Downloading NAICS codes from census.gov...")
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            import openpyxl
            import io
            wb = openpyxl.load_workbook(io.BytesIO(resp.content))
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 3 and row[1] is not None and row[2] is not None:
                    # Census XLSX columns: 0=sequence number, 1=NAICS code, 2=description
                    naics_code = str(row[1]).strip().rstrip("-")
                    description = str(row[2]).strip()
                    # Valid NAICS codes are 2-6 digit numbers
                    if naics_code.isdigit() and 2 <= len(naics_code) <= 6 and description:
                        codes.append({"code": naics_code, "description": description})
            print(f"  NAICS codes downloaded: {len(codes)} entries")
            return codes
    except Exception as e:
        print(f"  NAICS download failed ({e}), using embedded fallback")

    # Embedded fallback — essential codes for insurance
    codes = [
        {"code": "236220", "description": "Commercial and Institutional Building Construction"},
        {"code": "238110", "description": "Poured Concrete Foundation and Structure Contractors"},
        {"code": "238210", "description": "Electrical Contractors and Other Wiring Installation Contractors"},
        {"code": "238220", "description": "Plumbing, Heating, and Air-Conditioning Contractors"},
        {"code": "238910", "description": "Site Preparation Contractors"},
        {"code": "311811", "description": "Retail Bakeries"},
        {"code": "312111", "description": "Soft Drink Manufacturing"},
        {"code": "332710", "description": "Machine Shops"},
        {"code": "336111", "description": "Automobile Manufacturing"},
        {"code": "423110", "description": "Automobile and Other Motor Vehicle Merchant Wholesalers"},
        {"code": "441110", "description": "New Car Dealers"},
        {"code": "441120", "description": "Used Car Dealers"},
        {"code": "444110", "description": "Home Centers"},
        {"code": "445110", "description": "Supermarkets and Other Grocery Stores"},
        {"code": "448140", "description": "Family Clothing Stores"},
        {"code": "452210", "description": "Department Stores"},
        {"code": "484110", "description": "General Freight Trucking, Local"},
        {"code": "484121", "description": "General Freight Trucking, Long-Distance, Truckload"},
        {"code": "484122", "description": "General Freight Trucking, Long-Distance, Less Than Truckload"},
        {"code": "485110", "description": "Urban Transit Systems"},
        {"code": "485310", "description": "Taxi and Ridesharing Services"},
        {"code": "524113", "description": "Direct Life Insurance Carriers"},
        {"code": "524114", "description": "Direct Health and Medical Insurance Carriers"},
        {"code": "524126", "description": "Direct Property and Casualty Insurance Carriers"},
        {"code": "524210", "description": "Insurance Agencies and Brokerages"},
        {"code": "531110", "description": "Lessors of Residential Buildings and Dwellings"},
        {"code": "531120", "description": "Lessors of Nonresidential Buildings"},
        {"code": "531210", "description": "Offices of Real Estate Agents and Brokers"},
        {"code": "541110", "description": "Offices of Lawyers"},
        {"code": "541211", "description": "Offices of Certified Public Accountants"},
        {"code": "541330", "description": "Engineering Services"},
        {"code": "541511", "description": "Custom Computer Programming Services"},
        {"code": "541512", "description": "Computer Systems Design Services"},
        {"code": "561612", "description": "Security Guards and Patrol Services"},
        {"code": "621111", "description": "Offices of Physicians (except Mental Health Specialists)"},
        {"code": "621210", "description": "Offices of Dentists"},
        {"code": "621310", "description": "Offices of Chiropractors"},
        {"code": "722511", "description": "Full-Service Restaurants"},
        {"code": "722513", "description": "Limited-Service Restaurants"},
        {"code": "722514", "description": "Cafeterias, Grill Buffets, and Buffets"},
        {"code": "811111", "description": "General Automotive Repair"},
        {"code": "811121", "description": "Automotive Body, Paint, and Interior Repair and Maintenance"},
        {"code": "812111", "description": "Barber Shops"},
        {"code": "812112", "description": "Beauty Salons"},
        {"code": "812310", "description": "Coin-Operated Laundries and Drycleaners"},
    ]
    print(f"  NAICS codes (embedded fallback): {len(codes)} entries")
    return codes


def collect_insurance_glossary() -> list[dict]:
    """Collect insurance glossary terms. Try NAIC scrape, fall back to embedded."""
    terms = []

    # Try scraping NAIC glossary
    try:
        import requests
        from html.parser import HTMLParser

        print(f"  Scraping NAIC insurance glossary...")
        resp = requests.get("https://content.naic.org/glossary-insurance-terms", timeout=30)
        if resp.status_code == 200:
            # Simple HTML parsing for glossary terms
            class GlossaryParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.terms = []
                    self.in_term = False
                    self.in_def = False
                    self.current_term = ""
                    self.current_def = ""
                    self.tag_stack = []

                def handle_starttag(self, tag, attrs):
                    self.tag_stack.append(tag)
                    attrs_dict = dict(attrs)
                    cls = attrs_dict.get("class", "")
                    if "glossary-term" in cls or "views-field-name" in cls:
                        self.in_term = True
                        self.current_term = ""
                    elif "glossary-definition" in cls or "views-field-body" in cls:
                        self.in_def = True
                        self.current_def = ""

                def handle_endtag(self, tag):
                    if self.tag_stack:
                        self.tag_stack.pop()
                    if self.in_term and tag in ("h3", "h4", "div", "span", "dt"):
                        self.in_term = False
                    elif self.in_def and tag in ("div", "p", "dd"):
                        self.in_def = False
                        if self.current_term.strip() and self.current_def.strip():
                            self.terms.append({
                                "term": self.current_term.strip(),
                                "definition": self.current_def.strip(),
                            })

                def handle_data(self, data):
                    if self.in_term:
                        self.current_term += data
                    elif self.in_def:
                        self.current_def += data

            parser = GlossaryParser()
            parser.feed(resp.text)
            if parser.terms:
                terms = parser.terms
                print(f"  NAIC glossary scraped: {len(terms)} terms")
                return terms
    except Exception as e:
        print(f"  NAIC scrape failed ({e}), using embedded fallback")

    # Embedded fallback — comprehensive insurance glossary
    terms = [
        {"term": "Actual Cash Value (ACV)", "definition": "The replacement cost of damaged or stolen property minus depreciation. ACV accounts for the age, condition, and useful life of the item."},
        {"term": "Additional Insured", "definition": "A person or organization added to an insurance policy who is not the named insured. They receive coverage under the policy, often required by contracts."},
        {"term": "Adjuster", "definition": "A person who investigates and settles insurance claims on behalf of the insurance company. May be a staff adjuster, independent adjuster, or public adjuster."},
        {"term": "Agent", "definition": "A licensed individual or firm authorized to sell insurance policies on behalf of one or more insurance companies. Also known as a producer."},
        {"term": "Aggregate Limit", "definition": "The maximum amount an insurer will pay for all covered losses during a policy period, regardless of the number of claims."},
        {"term": "Binder", "definition": "A temporary agreement that provides insurance coverage until a formal policy is issued. A binder is legally enforceable."},
        {"term": "Bodily Injury (BI)", "definition": "Physical harm, sickness, or disease sustained by a person, including resulting death. A key coverage in liability insurance."},
        {"term": "Broker", "definition": "An insurance professional who represents the buyer (not the insurer) in finding and placing insurance coverage."},
        {"term": "Business Auto Policy (BAP)", "definition": "A commercial auto insurance policy covering vehicles used for business purposes. Provides liability, physical damage, and other auto coverages."},
        {"term": "Business Owners Policy (BOP)", "definition": "A package policy combining property and general liability coverage for small to mid-sized businesses at a reduced premium."},
        {"term": "Cancellation", "definition": "The termination of an insurance policy before its expiration date, initiated by either the insured or the insurer."},
        {"term": "Certificate of Insurance (COI)", "definition": "A document issued by an insurer confirming that a policy exists, the types and amounts of coverage, and the named insured. Does not confer rights."},
        {"term": "Claim", "definition": "A formal request by the insured to the insurance company for payment or coverage under the terms of the policy."},
        {"term": "Coinsurance", "definition": "A provision requiring the insured to carry insurance equal to a specified percentage of the property value. Failure to meet the requirement results in a penalty."},
        {"term": "Collision Coverage", "definition": "Auto insurance coverage that pays for damage to the insured vehicle resulting from a collision with another vehicle or object, regardless of fault."},
        {"term": "Combined Single Limit (CSL)", "definition": "A single liability limit that applies to both bodily injury and property damage combined per occurrence, rather than separate limits."},
        {"term": "Commercial General Liability (CGL)", "definition": "A standard liability insurance policy for businesses covering bodily injury, property damage, personal injury, and advertising injury claims."},
        {"term": "Comprehensive Coverage", "definition": "Auto insurance covering loss or damage from causes other than collision, including theft, vandalism, fire, hail, flood, and animal strikes."},
        {"term": "Covered Auto", "definition": "A vehicle described in the declarations or meeting the definition in the policy for which coverage applies. Identified by coverage symbols 1-9 in BAP."},
        {"term": "Declarations Page", "definition": "The section of an insurance policy listing key information: named insured, policy period, coverages, limits, premiums, and endorsements. Also called the dec page."},
        {"term": "Deductible", "definition": "The amount the insured must pay out of pocket before the insurance company pays a claim. Higher deductibles typically result in lower premiums."},
        {"term": "Endorsement", "definition": "An amendment or addition to an existing insurance policy that changes the terms or coverage. Also called a rider."},
        {"term": "Errors and Omissions (E&O)", "definition": "Professional liability insurance covering claims of negligent acts, errors, or omissions in professional services."},
        {"term": "Exclusion", "definition": "A provision in an insurance policy that eliminates coverage for certain risks, hazards, perils, or types of property."},
        {"term": "Experience Modification Rate (EMR)", "definition": "A multiplier applied to workers compensation premiums based on a business's actual loss history compared to similar businesses. Also called experience mod or e-mod."},
        {"term": "Garage Liability", "definition": "Insurance for businesses involved in the automobile industry (dealers, repair shops, service stations) covering liability arising from garage operations."},
        {"term": "General Aggregate", "definition": "The maximum total amount the insurer will pay for all claims (except products-completed operations) during the policy period under a CGL policy."},
        {"term": "Hired Auto", "definition": "A vehicle leased, hired, rented, or borrowed for use in the named insured's business. Coverage symbol 8 in BAP."},
        {"term": "Indemnity", "definition": "The principle of restoring the insured to the same financial position they were in before the loss, without profit or loss."},
        {"term": "Inland Marine", "definition": "Insurance covering goods in transit over land, mobile equipment, and certain types of personal and commercial property."},
        {"term": "Insurable Interest", "definition": "A financial interest in the subject of insurance such that loss or destruction would cause financial harm to the policyholder."},
        {"term": "Lapse", "definition": "The termination of an insurance policy due to non-payment of premium within the grace period."},
        {"term": "Liability Insurance", "definition": "Coverage that protects the insured against claims of negligence or harm to third parties, including legal defense costs and damages awarded."},
        {"term": "Limit of Insurance", "definition": "The maximum amount an insurer will pay for a single claim or occurrence under the policy."},
        {"term": "Loss Payee", "definition": "A person or entity entitled to receive insurance proceeds for a covered loss, typically a lender or lienholder with a financial interest in the property."},
        {"term": "Loss Ratio", "definition": "The ratio of claims paid (losses incurred) to premiums earned, expressed as a percentage. A key measure of underwriting profitability."},
        {"term": "Medical Payments Coverage", "definition": "Coverage that pays medical expenses for persons injured in an accident involving the insured vehicle, regardless of fault."},
        {"term": "Moral Hazard", "definition": "The risk that an insured may be dishonest or careless because they know insurance will cover their losses."},
        {"term": "Mortgagee", "definition": "A lender (bank or financial institution) named on a property insurance policy that holds a mortgage on the insured property."},
        {"term": "NAIC Code", "definition": "A unique identification number assigned to insurance companies by the National Association of Insurance Commissioners. Used for regulatory tracking and reporting."},
        {"term": "Named Insured", "definition": "The person or entity specifically named in the declarations page of an insurance policy as the policyholder."},
        {"term": "Non-Owned Auto", "definition": "A vehicle not owned, leased, hired, rented, or borrowed by the named insured but used in connection with the named insured's business. Coverage symbol 9 in BAP."},
        {"term": "Occurrence", "definition": "An accident or event, including continuous or repeated exposure to conditions, that results in bodily injury or property damage during the policy period."},
        {"term": "Per Occurrence Limit", "definition": "The maximum amount the insurer will pay for all damages arising from a single occurrence or accident."},
        {"term": "Personal Injury", "definition": "In CGL context: injury other than bodily injury, including false arrest, malicious prosecution, wrongful eviction, slander, libel, and invasion of privacy."},
        {"term": "Policy Period", "definition": "The time span during which an insurance policy provides coverage, from the effective date to the expiration date."},
        {"term": "Premium", "definition": "The amount paid by the insured to the insurance company for coverage, usually on an annual, semi-annual, quarterly, or monthly basis."},
        {"term": "Products-Completed Operations", "definition": "CGL coverage for bodily injury and property damage arising from the insured's products or completed work after it has been delivered or completed."},
        {"term": "Property Damage (PD)", "definition": "Physical injury to tangible property, including loss of use. A key coverage in liability insurance."},
        {"term": "Replacement Cost", "definition": "The cost to replace damaged or destroyed property with new property of similar kind and quality, without deduction for depreciation."},
        {"term": "Reservation of Rights", "definition": "A notice from the insurer to the insured stating that certain rights under the policy are being reserved while a claim is investigated."},
        {"term": "Rider", "definition": "An amendment to an insurance policy that adds, removes, or modifies coverage. Also called an endorsement."},
        {"term": "Self-Insured Retention (SIR)", "definition": "The amount of loss that the insured retains (pays) before excess or umbrella coverage applies. Similar to a deductible but with different legal implications."},
        {"term": "Subrogation", "definition": "The right of an insurer, after paying a claim, to pursue recovery from the party that caused the loss. Allows the insurer to 'step into the shoes' of the insured."},
        {"term": "Surety Bond", "definition": "A three-party agreement guaranteeing that a principal will fulfill obligations to an obligee, with the surety providing the guarantee."},
        {"term": "Umbrella Policy", "definition": "Excess liability insurance providing coverage above the limits of underlying policies (auto, CGL, employer's liability). May also drop down to cover excluded claims."},
        {"term": "Underwriter", "definition": "An insurance company employee who evaluates risks, determines premiums, and decides whether to accept or reject applications for insurance."},
        {"term": "Underwriting", "definition": "The process of evaluating, selecting, classifying, and pricing risks to determine if and under what terms an insurance company will provide coverage."},
        {"term": "Uninsured Motorist (UM)", "definition": "Auto insurance coverage that pays for injuries caused by a driver who has no insurance or by a hit-and-run driver."},
        {"term": "Underinsured Motorist (UIM)", "definition": "Auto insurance coverage that pays for injuries when the at-fault driver's liability limits are insufficient to cover the insured's damages."},
        {"term": "Vehicle Identification Number (VIN)", "definition": "A unique 17-character code assigned to every motor vehicle for identification purposes. Used in auto insurance for vehicle identification."},
        {"term": "Waiver of Subrogation", "definition": "An endorsement whereby the insured gives up the right to recover from a third party. Often required in construction and lease contracts."},
        {"term": "Workers Compensation", "definition": "Insurance providing wage replacement and medical benefits to employees injured in the course of employment, regardless of fault."},
        {"term": "Written Premium", "definition": "The total premium charged for all policies written (issued) during a specific period, before deductions for reinsurance."},
        {"term": "Earned Premium", "definition": "The portion of the written premium that applies to the expired portion of the policy period. If a 12-month policy is 6 months in, 50% is earned."},
        {"term": "Loss Reserve", "definition": "An estimate of the amount an insurer expects to pay for reported but unsettled claims. A key component of an insurer's financial statements."},
        {"term": "Tail Coverage", "definition": "Extended reporting period coverage that allows claims to be reported after a claims-made policy has expired or been cancelled."},
        {"term": "Retroactive Date", "definition": "The date specified in a claims-made policy before which occurrences are not covered, even if the claim is reported during the policy period."},
        {"term": "Garage Keepers Coverage", "definition": "Insurance covering physical damage to customers' vehicles while in the care, custody, or control of an auto service business."},
        {"term": "Motor Carrier", "definition": "A business engaged in transporting goods or passengers by motor vehicle for hire. Subject to federal and state motor carrier regulations."},
        {"term": "Hired and Non-Owned Auto", "definition": "Combined coverage for vehicles the business hires/rents and for employee-owned vehicles used for business purposes."},
        {"term": "Symbol", "definition": "In a Business Auto Policy, a number (1-9) that defines which vehicles are covered: 1=Any Auto, 2=Owned Only, 7=Specifically Described, 8=Hired, 9=Non-Owned."},
        {"term": "Inland Marine Floater", "definition": "A policy covering movable property that travels from location to location, such as contractor's equipment, fine arts, or musical instruments."},
        {"term": "Liquor Liability", "definition": "Insurance covering bodily injury or property damage caused by serving or selling alcoholic beverages. Required for bars, restaurants, and event venues."},
        {"term": "Fiduciary Liability", "definition": "Insurance protecting fiduciaries from claims of mismanagement of employee benefit plans governed by ERISA."},
        {"term": "Directors and Officers (D&O)", "definition": "Liability insurance covering directors and officers of a company against claims of wrongful acts in their capacity as corporate leaders."},
        {"term": "Cyber Liability", "definition": "Insurance covering losses from data breaches, cyberattacks, ransomware, privacy violations, and related cyber incidents."},
        {"term": "Professional Liability", "definition": "Insurance protecting professionals against claims of negligence, errors, or omissions in the performance of professional services. Also called E&O."},
        {"term": "Commercial Property", "definition": "Insurance covering a business's buildings, equipment, inventory, furniture, and other business personal property against covered perils."},
        {"term": "Business Income Coverage", "definition": "Insurance that replaces lost income and pays continuing expenses when a business cannot operate due to a covered property loss."},
        {"term": "Extra Expense Coverage", "definition": "Insurance covering additional costs a business incurs to continue operations after a covered property loss."},
        {"term": "Equipment Breakdown", "definition": "Insurance covering loss from the sudden breakdown of boilers, pressure vessels, electrical equipment, and mechanical equipment. Formerly called boiler and machinery."},
        {"term": "Crime Insurance", "definition": "Coverage protecting a business against losses from employee dishonesty, forgery, robbery, burglary, computer fraud, and other criminal acts."},
        {"term": "Employment Practices Liability (EPLI)", "definition": "Insurance covering claims by employees alleging discrimination, wrongful termination, sexual harassment, or other employment-related issues."},
        {"term": "ACORD", "definition": "Association for Cooperative Operations Research and Development. A nonprofit standards organization for the insurance industry. Develops standardized forms, data standards, and electronic interchange formats used across the industry."},
        {"term": "ACORD 125", "definition": "The Commercial Insurance Application form. A standardized multi-page form used to apply for commercial insurance lines including CGL, property, auto, umbrella, and specialty coverages."},
        {"term": "ACORD 127", "definition": "The Business Auto Section form. Used in conjunction with ACORD 125 to provide detailed information about commercial auto coverage including driver schedules, vehicle information, and coverage details."},
        {"term": "ACORD 137", "definition": "The Commercial Auto Section form. Details the vehicle schedule, coverage symbols, limits, and deductibles for commercial auto policies."},
        {"term": "ACORD 163", "definition": "The Driver Information Schedule form. Provides detailed driver information including MVR records, accidents, and violations for commercial auto policies."},
        {"term": "Producer", "definition": "An insurance agent or broker licensed to sell insurance. In ACORD forms, the 'Producer' section refers to the agent/broker submitting the application, not the insurance company."},
        {"term": "Carrier", "definition": "An insurance company that underwrites and issues insurance policies. In ACORD forms, the 'Company' or 'Insurer' section refers to the carrier."},
        {"term": "Surplus Lines", "definition": "Insurance placed with non-admitted insurers when coverage is not available from admitted (licensed) carriers in the state. Subject to surplus lines regulations."},
        {"term": "Admitted Carrier", "definition": "An insurance company licensed and regulated by the state department of insurance. Policyholders are protected by the state guaranty fund."},
        {"term": "Non-Admitted Carrier", "definition": "An insurance company not licensed in a particular state. May write surplus lines business. Not protected by state guaranty fund."},
    ]
    print(f"  Insurance glossary (embedded): {len(terms)} terms")
    return terms


def collect_state_info() -> list[dict]:
    """Collect US state insurance information."""
    states = [
        {"code": "AL", "name": "Alabama", "doi_url": "https://www.aldoi.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "AK", "name": "Alaska", "doi_url": "https://www.commerce.alaska.gov/web/ins", "auto_min_bi": "50/100", "auto_min_pd": "25000"},
        {"code": "AZ", "name": "Arizona", "doi_url": "https://insurance.az.gov", "auto_min_bi": "25/50", "auto_min_pd": "15000"},
        {"code": "AR", "name": "Arkansas", "doi_url": "https://insurance.arkansas.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "CA", "name": "California", "doi_url": "https://www.insurance.ca.gov", "auto_min_bi": "15/30", "auto_min_pd": "5000"},
        {"code": "CO", "name": "Colorado", "doi_url": "https://doi.colorado.gov", "auto_min_bi": "25/50", "auto_min_pd": "15000"},
        {"code": "CT", "name": "Connecticut", "doi_url": "https://portal.ct.gov/cid", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "DE", "name": "Delaware", "doi_url": "https://insurance.delaware.gov", "auto_min_bi": "25/50", "auto_min_pd": "10000"},
        {"code": "DC", "name": "District of Columbia", "doi_url": "https://disb.dc.gov", "auto_min_bi": "25/50", "auto_min_pd": "10000"},
        {"code": "FL", "name": "Florida", "doi_url": "https://www.myfloridacfo.com/division/insurance", "auto_min_bi": "10/20", "auto_min_pd": "10000"},
        {"code": "GA", "name": "Georgia", "doi_url": "https://oci.georgia.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "HI", "name": "Hawaii", "doi_url": "https://cca.hawaii.gov/ins", "auto_min_bi": "20/40", "auto_min_pd": "10000"},
        {"code": "ID", "name": "Idaho", "doi_url": "https://doi.idaho.gov", "auto_min_bi": "25/50", "auto_min_pd": "15000"},
        {"code": "IL", "name": "Illinois", "doi_url": "https://insurance.illinois.gov", "auto_min_bi": "25/50", "auto_min_pd": "20000"},
        {"code": "IN", "name": "Indiana", "doi_url": "https://www.in.gov/idoi", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "IA", "name": "Iowa", "doi_url": "https://iid.iowa.gov", "auto_min_bi": "20/40", "auto_min_pd": "15000"},
        {"code": "KS", "name": "Kansas", "doi_url": "https://insurance.kansas.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "KY", "name": "Kentucky", "doi_url": "https://insurance.ky.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "LA", "name": "Louisiana", "doi_url": "https://www.ldi.la.gov", "auto_min_bi": "15/30", "auto_min_pd": "25000"},
        {"code": "ME", "name": "Maine", "doi_url": "https://www.maine.gov/pfr/insurance", "auto_min_bi": "50/100", "auto_min_pd": "25000"},
        {"code": "MD", "name": "Maryland", "doi_url": "https://insurance.maryland.gov", "auto_min_bi": "30/60", "auto_min_pd": "15000"},
        {"code": "MA", "name": "Massachusetts", "doi_url": "https://www.mass.gov/orgs/division-of-insurance", "auto_min_bi": "20/40", "auto_min_pd": "5000"},
        {"code": "MI", "name": "Michigan", "doi_url": "https://www.michigan.gov/difs", "auto_min_bi": "50/100", "auto_min_pd": "10000"},
        {"code": "MN", "name": "Minnesota", "doi_url": "https://mn.gov/commerce/insurance", "auto_min_bi": "30/60", "auto_min_pd": "10000"},
        {"code": "MS", "name": "Mississippi", "doi_url": "https://www.mid.ms.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "MO", "name": "Missouri", "doi_url": "https://insurance.mo.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "MT", "name": "Montana", "doi_url": "https://csimt.gov", "auto_min_bi": "25/50", "auto_min_pd": "20000"},
        {"code": "NE", "name": "Nebraska", "doi_url": "https://doi.nebraska.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "NV", "name": "Nevada", "doi_url": "https://doi.nv.gov", "auto_min_bi": "25/50", "auto_min_pd": "20000"},
        {"code": "NH", "name": "New Hampshire", "doi_url": "https://www.nh.gov/insurance", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "NJ", "name": "New Jersey", "doi_url": "https://www.state.nj.us/dobi", "auto_min_bi": "15/30", "auto_min_pd": "5000"},
        {"code": "NM", "name": "New Mexico", "doi_url": "https://www.osi.state.nm.us", "auto_min_bi": "25/50", "auto_min_pd": "10000"},
        {"code": "NY", "name": "New York", "doi_url": "https://www.dfs.ny.gov", "auto_min_bi": "25/50", "auto_min_pd": "10000"},
        {"code": "NC", "name": "North Carolina", "doi_url": "https://www.ncdoi.gov", "auto_min_bi": "30/60", "auto_min_pd": "25000"},
        {"code": "ND", "name": "North Dakota", "doi_url": "https://www.insurance.nd.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "OH", "name": "Ohio", "doi_url": "https://insurance.ohio.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "OK", "name": "Oklahoma", "doi_url": "https://www.oid.ok.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "OR", "name": "Oregon", "doi_url": "https://dfr.oregon.gov", "auto_min_bi": "25/50", "auto_min_pd": "20000"},
        {"code": "PA", "name": "Pennsylvania", "doi_url": "https://www.insurance.pa.gov", "auto_min_bi": "15/30", "auto_min_pd": "5000"},
        {"code": "RI", "name": "Rhode Island", "doi_url": "https://dbr.ri.gov/insurance", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "SC", "name": "South Carolina", "doi_url": "https://doi.sc.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "SD", "name": "South Dakota", "doi_url": "https://dlr.sd.gov/insurance", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "TN", "name": "Tennessee", "doi_url": "https://www.tn.gov/commerce/insurance", "auto_min_bi": "25/50", "auto_min_pd": "15000"},
        {"code": "TX", "name": "Texas", "doi_url": "https://www.tdi.texas.gov", "auto_min_bi": "30/60", "auto_min_pd": "25000"},
        {"code": "UT", "name": "Utah", "doi_url": "https://insurance.utah.gov", "auto_min_bi": "25/65", "auto_min_pd": "15000"},
        {"code": "VT", "name": "Vermont", "doi_url": "https://dfr.vermont.gov/insurance", "auto_min_bi": "25/50", "auto_min_pd": "10000"},
        {"code": "VA", "name": "Virginia", "doi_url": "https://scc.virginia.gov/pages/Insurance", "auto_min_bi": "30/60", "auto_min_pd": "20000"},
        {"code": "WA", "name": "Washington", "doi_url": "https://www.insurance.wa.gov", "auto_min_bi": "25/50", "auto_min_pd": "10000"},
        {"code": "WV", "name": "West Virginia", "doi_url": "https://www.wvinsurance.gov", "auto_min_bi": "25/50", "auto_min_pd": "25000"},
        {"code": "WI", "name": "Wisconsin", "doi_url": "https://oci.wi.gov", "auto_min_bi": "25/50", "auto_min_pd": "10000"},
        {"code": "WY", "name": "Wyoming", "doi_url": "https://doi.wyo.gov", "auto_min_bi": "25/50", "auto_min_pd": "20000"},
    ]
    print(f"  State insurance info: {len(states)} states/territories")
    return states


def collect_form_structure() -> list[dict]:
    """Collect ACORD form structure and layout descriptions."""
    docs = []

    # Form descriptions
    form_info = {
        "125": {
            "name": "Commercial Insurance Application",
            "pages": 4,
            "description": "The primary application form for commercial insurance. Used to apply for multiple lines of business including CGL, commercial property, business auto, umbrella, inland marine, crime, cyber, and more.",
            "page_descriptions": {
                1: "Header (date, agency/producer, company/insurer), Named Insured info, Policy details (number, dates, status), Lines of Business with premiums, Section attachments",
                2: "Premises/location details, Building occupancy, Nature of business, Legal entity type, Business operations description, Annual revenue, Employee counts",
                3: "Additional interests, Prior coverage history, Loss history, Questions about foreclosure/judgments/fire code violations, Safety programs",
                4: "Signatures, Remarks, Prior coverage continuation, Additional loss history rows",
            },
        },
        "127": {
            "name": "Business Auto Section",
            "pages": 4,
            "description": "Used with ACORD 125 for business auto coverage details. Contains driver schedules (up to 13 drivers) and vehicle information with coverage details.",
            "page_descriptions": {
                1: "Header, Insurer/NAIC, Named Insured, Policy Number, Driver schedule table (13 rows: name, DOB, license, city, state, zip, sex, marital status)",
                2: "Driver accident/violation history, Vehicle schedule (VIN, year, make, model, body type, GVW, mileage)",
                3: "Vehicle coverage details, Symbols, Limits, Deductibles, Premium amounts per vehicle",
                4: "Additional vehicle/coverage rows, State-specific endorsements",
            },
        },
        "137": {
            "name": "Commercial Auto Section",
            "pages": 3,
            "description": "Vehicle schedule form for commercial auto policies. Details coverage symbols (1-9), limits, and deductibles for each scheduled vehicle.",
            "page_descriptions": {
                1: "Header, Named Insured, Policy dates, Business Auto coverage symbols table, Vehicle schedule A-F",
                2: "Truckers section, Motor Carrier section, Additional coverage details",
                3: "Continuation of vehicle schedule, Additional endorsements",
            },
        },
    }

    for form_num, info in form_info.items():
        # Overall form description
        docs.append({
            "form_type": form_num,
            "section": "overview",
            "title": f"ACORD {form_num} - {info['name']}",
            "content": info["description"],
        })
        # Per-page descriptions
        for page_num, page_desc in info["page_descriptions"].items():
            docs.append({
                "form_type": form_num,
                "section": f"page_{page_num}",
                "title": f"ACORD {form_num} Page {page_num}",
                "content": page_desc,
            })

    # Category explanations
    categories = {
        "header": "Form header fields: completion date, form edition identifier. Located at the very top of the form.",
        "insurer": "Insurance carrier (company) information: full name, NAIC code (5-digit), product code, underwriter name. The INSURER is the insurance COMPANY providing coverage, NOT the agent.",
        "producer": "Insurance agent/broker information: agency name, contact person, phone, fax, email, mailing address, license numbers. The PRODUCER sells/submits the policy.",
        "named_insured": "The customer/business buying insurance: company name, mailing address, phone, website, tax ID, NAICS/SIC codes, legal entity type, contacts.",
        "policy": "Policy details: policy number, effective/expiration dates, status (quote/bound/issue/cancel/renew), payment method, premium amounts.",
        "coverage": "Coverage details: lines of business, premium amounts, limits, deductibles, coverage symbols.",
        "vehicle": "Vehicle information: VIN, year, make, model, body type, GVW, mileage, radius of operation, garaging address.",
        "driver": "Driver information: name, date of birth, license number, state, sex, marital status, years licensed, accident/violation history.",
        "location": "Physical location details: address, city, state, zip, county, inside/outside city limits, building occupancy.",
        "loss_history": "Prior loss/claims history: occurrence dates, claim descriptions, amounts paid, reserved amounts, claim status.",
        "checkbox": "Checkbox fields: return true if checked, false if unchecked. Common in lines of business, legal entity type, and policy status sections.",
        "general": "General/miscellaneous fields that don't fit into specific categories.",
    }

    for cat, desc in categories.items():
        docs.append({
            "form_type": "all",
            "section": "category",
            "title": f"Category: {cat}",
            "content": desc,
        })

    # Field naming conventions
    docs.append({
        "form_type": "all",
        "section": "conventions",
        "title": "ACORD Field Naming Conventions",
        "content": (
            "Field names follow the pattern: Entity_Property_Suffix. "
            "Suffixes _A through _M indicate row/instance number (e.g., Driver 1 = _A, Driver 2 = _B). "
            "Common entities: Producer (agent), Insurer (carrier), NamedInsured (customer), Policy, "
            "CommercialStructure (location/building), LossHistory, PriorCoverage, AdditionalInterest. "
            "Indicator suffix means a checkbox (true/false). "
            "Date fields use MM/DD/YYYY format. "
            "NAIC codes are always 5-digit numbers."
        ),
    })

    print(f"  Form structure: {len(docs)} entries")
    return docs


def collect_abbreviations() -> list[dict]:
    """Collect common insurance abbreviations."""
    abbrevs = [
        {"abbr": "ACV", "full": "Actual Cash Value", "context": "Property valuation method accounting for depreciation"},
        {"abbr": "AI", "full": "Additional Insured", "context": "Third party added to a policy for coverage"},
        {"abbr": "BAP", "full": "Business Auto Policy", "context": "Commercial auto insurance policy"},
        {"abbr": "BI", "full": "Bodily Injury", "context": "Physical harm to a person; key liability coverage component"},
        {"abbr": "BOP", "full": "Business Owners Policy", "context": "Package policy combining property and liability for small businesses"},
        {"abbr": "CGL", "full": "Commercial General Liability", "context": "Standard business liability insurance covering BI, PD, personal injury"},
        {"abbr": "COI", "full": "Certificate of Insurance", "context": "Document proving insurance coverage exists"},
        {"abbr": "COPE", "full": "Construction, Occupancy, Protection, Exposure", "context": "Four factors used in commercial property underwriting"},
        {"abbr": "CSL", "full": "Combined Single Limit", "context": "Single limit for both BI and PD per occurrence"},
        {"abbr": "D&O", "full": "Directors and Officers", "context": "Liability insurance for corporate directors and officers"},
        {"abbr": "DOI", "full": "Department of Insurance", "context": "State regulatory agency overseeing insurance"},
        {"abbr": "E&O", "full": "Errors and Omissions", "context": "Professional liability insurance"},
        {"abbr": "EMR", "full": "Experience Modification Rate", "context": "Workers comp premium multiplier based on loss history"},
        {"abbr": "EPLI", "full": "Employment Practices Liability Insurance", "context": "Coverage for employment-related claims"},
        {"abbr": "GL", "full": "General Liability", "context": "Liability insurance covering third-party claims"},
        {"abbr": "GVW", "full": "Gross Vehicle Weight", "context": "Maximum weight of a vehicle including cargo; used in auto classification"},
        {"abbr": "IBNR", "full": "Incurred But Not Reported", "context": "Reserve for claims that have occurred but not yet been reported"},
        {"abbr": "ISO", "full": "Insurance Services Office", "context": "Organization providing standardized forms, rates, and data for P&C insurance"},
        {"abbr": "LOB", "full": "Line of Business", "context": "Type of insurance coverage (e.g., auto, property, liability)"},
        {"abbr": "MOD", "full": "Experience Modification", "context": "Shorthand for EMR; workers comp rating factor"},
        {"abbr": "MVR", "full": "Motor Vehicle Report", "context": "Driving record report used in auto underwriting"},
        {"abbr": "NAIC", "full": "National Association of Insurance Commissioners", "context": "Regulatory body; assigns 5-digit codes to insurers"},
        {"abbr": "NAICS", "full": "North American Industry Classification System", "context": "6-digit industry codes used for business classification"},
        {"abbr": "NCCI", "full": "National Council on Compensation Insurance", "context": "Organization managing workers comp data and rates"},
        {"abbr": "NI", "full": "Named Insured", "context": "The policyholder specifically named on the declarations page"},
        {"abbr": "P&C", "full": "Property and Casualty", "context": "Insurance covering property damage and liability"},
        {"abbr": "PD", "full": "Property Damage", "context": "Physical damage to tangible property; key liability coverage"},
        {"abbr": "PIP", "full": "Personal Injury Protection", "context": "No-fault auto coverage for medical expenses regardless of fault"},
        {"abbr": "RC", "full": "Replacement Cost", "context": "Property valuation at new replacement price without depreciation"},
        {"abbr": "SIC", "full": "Standard Industrial Classification", "context": "4-digit industry codes (predecessor to NAICS)"},
        {"abbr": "SIR", "full": "Self-Insured Retention", "context": "Amount insured pays before excess coverage kicks in"},
        {"abbr": "TIV", "full": "Total Insurable Value", "context": "Total value of all insured property"},
        {"abbr": "UM", "full": "Uninsured Motorist", "context": "Coverage for injuries caused by uninsured drivers"},
        {"abbr": "UIM", "full": "Underinsured Motorist", "context": "Coverage when at-fault driver's limits are insufficient"},
        {"abbr": "VIN", "full": "Vehicle Identification Number", "context": "Unique 17-character vehicle identifier"},
        {"abbr": "WC", "full": "Workers Compensation", "context": "Insurance for employee workplace injuries"},
        {"abbr": "XS", "full": "Excess", "context": "Coverage that sits above primary policy limits (e.g., excess/umbrella)"},
        {"abbr": "ACORD", "full": "Association for Cooperative Operations Research and Development", "context": "Insurance industry standards organization; develops standardized forms"},
    ]
    print(f"  Insurance abbreviations: {len(abbrevs)} entries")
    return abbrevs


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Collecting insurance knowledge data...\n")

    # 1. Schema knowledge
    schema_data = collect_schema_knowledge()
    (DATA_DIR / "schema_knowledge.json").write_text(
        json.dumps(schema_data, indent=2, ensure_ascii=False) + "\n"
    )

    # 2. NAICS codes
    naics_data = collect_naics_codes()
    (DATA_DIR / "naics_codes.json").write_text(
        json.dumps(naics_data, indent=2, ensure_ascii=False) + "\n"
    )

    # 3. Insurance glossary
    glossary_data = collect_insurance_glossary()
    (DATA_DIR / "insurance_glossary.json").write_text(
        json.dumps(glossary_data, indent=2, ensure_ascii=False) + "\n"
    )

    # 4. State info
    state_data = collect_state_info()
    (DATA_DIR / "state_info.json").write_text(
        json.dumps(state_data, indent=2, ensure_ascii=False) + "\n"
    )

    # 5. Form structure
    form_data = collect_form_structure()
    (DATA_DIR / "form_structure.json").write_text(
        json.dumps(form_data, indent=2, ensure_ascii=False) + "\n"
    )

    # 6. Abbreviations
    abbrev_data = collect_abbreviations()
    (DATA_DIR / "abbreviations.json").write_text(
        json.dumps(abbrev_data, indent=2, ensure_ascii=False) + "\n"
    )

    # Summary
    total = len(schema_data) + len(naics_data) + len(glossary_data) + len(state_data) + len(form_data) + len(abbrev_data)
    print(f"\nTotal: {total} knowledge entries collected")
    print(f"Data saved to: {DATA_DIR}")


if __name__ == "__main__":
    main()

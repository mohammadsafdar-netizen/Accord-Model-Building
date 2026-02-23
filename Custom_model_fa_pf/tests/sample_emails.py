"""Sample email fixtures for testing the Form Assignment & Pre-Filling pipeline."""

COMMERCIAL_AUTO_FULL = """
Subject: New Commercial Auto Insurance Needed

Hi,

We need commercial auto insurance for our trucking company. Here are our details:

Business: Midwest Freight Solutions LLC
DBA: MFS Trucking
Address: 1425 Industrial Blvd, Suite 200, Springfield, IL 62704
FEIN: 37-4528901
NAICS: 484110
Business type: LLC
Operations: Long-haul and regional freight transportation
Annual Revenue: $3,200,000
Employees: 22
Years in business: 8

Contact: Mike Johnson, Owner
Phone: (217) 555-3847
Email: mike@midwestfreight.com

We need coverage effective 04/01/2026 through 04/01/2027.

Vehicles:
1. 2023 Freightliner Cascadia, VIN: 3AKJHHDR5NSLA4521, GVW: 80,000 lbs, Cost: $165,000
2. 2022 Peterbilt 579, VIN: 1XPWD49X4ND628845, GVW: 80,000 lbs, Cost: $155,000
3. 2024 Ford F-350, VIN: 1FT8W3BT2REA73215, Body: PK, GVW: 14,000 lbs, Cost: $62,000

Drivers:
1. Mike Johnson, DOB: 03/15/1978, Male, Married, CDL# S530-4821-5567, IL, 20 years experience, hired 01/01/2016
2. Sarah Williams, DOB: 11/22/1985, Female, Single, CDL# W290-6734-2211, IL, 12 years experience, hired 06/15/2019
3. Carlos Rodriguez, DOB: 07/08/1990, Male, Married, CDL# R445-3318-7790, WI, 8 years experience, hired 03/01/2022

We'd like $1,000,000 CSL liability and $500 collision deductible.

Previous loss: Minor fender bender on 06/15/2024, $8,500 claim, closed.

Thanks,
Mike Johnson
"""

COMMERCIAL_AUTO_MINIMAL = """
Hi, we need auto insurance for our delivery van. Business name is Quick Deliveries Inc
at 500 Main Street, Chicago, IL 60601. One 2023 Ford Transit, used for local deliveries.
Policy to start March 1, 2026. FEIN 36-7891234. Contact me at joe@quickdeliveries.com.
Thanks, Joe Martinez
"""

MULTI_LOB_AUTO_UMBRELLA = """
Subject: Commercial Auto + Umbrella Quote Request

Dear Agent,

We are looking for a commercial auto policy AND an umbrella policy for our construction company.

Company: Apex Construction Group Inc.
Address: 789 Builder's Way, Madison, WI 53703
Tax ID: 39-8127456
Entity: Corporation
Operations: Commercial and residential construction
Revenue: $8,500,000
Employees: 45

Contact: Lisa Chen, CFO
Phone: 608-555-9012
Email: lisa.chen@apexconstruction.com

Effective: 05/01/2026 to 05/01/2027

Vehicles:
1. 2024 Chevrolet Silverado 3500HD, VIN: 1GC4YVEK1RF234567, GVW: 14,000, Cost: $58,000
2. 2023 RAM 5500 Chassis Cab, VIN: 3C7WRSBL2NG345678, GVW: 19,500, Cost: $72,000

Drivers:
1. Robert Chen, DOB: 09/20/1975, Male, Married, DL# C388-5521-0092, WI, 25 yrs exp
2. James Peters, DOB: 02/14/1988, Male, Single, DL# P291-3347-8856, WI, 10 yrs exp

We want $1M CSL auto liability and a $2M umbrella policy.

Thank you,
Lisa Chen
"""

GENERAL_LIABILITY_ONLY = """
Subject: GL Quote for Restaurant

Hi, I need general liability insurance for my restaurant.

Business: The Golden Spoon Restaurant
Address: 321 Culinary Ave, Milwaukee, WI 53202
FEIN: 39-5544321
Type: LLC
We're a full-service restaurant with 30 seats, been open 5 years.
Revenue last year was about $750,000 with 12 employees.

Need coverage starting June 1, 2026.
Looking for $1M per occurrence / $2M aggregate.

Contact: Maria Santos, 414-555-7788, maria@goldenspoon.com
"""

WORKERS_COMP_PROPERTY = """
Subject: WC and Property Insurance

We need workers compensation and commercial property insurance.

Business: Heartland Manufacturing Corp
Address: 1000 Factory Lane, Des Moines, IA 50301
FEIN: 42-1234567
Corporation with 85 employees
Annual payroll: $4,200,000

Property location: Same as above
Building: 25,000 sq ft masonry warehouse built in 2005
Equipment value: $2,000,000

Contact: David Kim, HR Director
Phone: 515-555-4433
Email: dkim@heartlandmfg.com

Effective 07/01/2026.
"""

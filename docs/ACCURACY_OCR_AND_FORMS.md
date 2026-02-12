# Accuracy: OCR Outputs and Form Layouts (125, 127, 137)

This document summarizes how **Docling**, **BBox (EasyOCR)**, and **label-value pairs** are used for extraction, and how each form’s **visual layout** drives spatial rules and prompts. Use it to improve full accuracy across all three forms.

---

## 1. OCR pipeline

| Stage | Output | Role in extraction |
|-------|--------|--------------------|
| **Docling** | Per-page markdown (tables, headings) | Structure and table cells; good for LOB table (125), policy info, applicant blocks. Can merge label+value in one cell. |
| **EasyOCR (BBox)** | Text blocks with `x`, `y`, `confidence` | **Spatial pre-extract** (labels → value regions); **layout disambiguation** (columns, rows). Primary source for “value to the right of label”. |
| **Spatial index** | Rows, columns, **label-value pairs** | Pairs like `CANCEL -> 01/16/2024`; some mispairs (e.g. LOB name → `$`). Fed to LLM as additional context. |
| **Section detection** | Header-based clusters of bbox blocks | Section-scoped **Docling** and **BBox** text per category; section crops for VLM when enabled. |

**Bbox OCR backend:** You can use **EasyOCR** (default) or **Surya** (Marker’s engine). Surya often gives better accuracy and speed on documents; benchmarks (e.g. Marker vs Docling) favor Surya. Use `--ocr-backend surya` (and `pip install surya-ocr`) to try it. Docling is always used for structure; only the bbox+text stage (spatial index, label-value pairs) switches between EasyOCR and Surya.

**Rule of thumb:** When the same text appears in both Docling and BBox, **prefer BBox positions** to assign values to fields (e.g. status row, driver columns, LOB checkboxes).

---

## 2. Form 125 – Commercial Insurance Application

### Layout (page 1, top → bottom)

- **Top:** DATE (right), AGENCY (left) | CARRIER | NAIC CODE  
- **Next:** Company/Program name, POLICY NUMBER, UNDERWRITER (person), UNDERWRITER OFFICE (address)  
- **Status row:** STATUS OF / TRANSACTION; QUOTE, BOUND, ISSUE, CANCEL, RENEW, CHANGE; date and time  
- **LOB table:** INDICATE LINES OF BUSINESS; three columns of LOB names + premium; checkbox = `$`/S in checkbox column  
- **Policy info:** PROPOSED EFF DATE, EXP DATE, BILLING PLAN, PAYMENT PLAN, METHOD OF PAYMENT  
- **Applicant:** NAME (First Named Insured), mailing address, GL/SIC/NAICS/FEIN  

### OCR behaviour

- **Docling:** Tables often have repeated columns; “CARRIER Zurich North America…” in one cell. Use for LOB names + amounts, policy dates.  
- **BBox:** `y≈` and `[x=]` are reliable for: date below DATE, carrier/NAIC below labels, underwriter name below UNDERWRITER (not OFFICE), status row (y≈640–850), LOB rows (y≈900–1270).  
- **Label-value:** Pairs like `CANCEL -> 01/16/2024`, `COMMERCIAL GENERAL LIABILITY -> 600000`; sometimes `LIQUOR LIABILITY -> S` (S = checkbox).  

### Accuracy levers

1. **Spatial pre-extract (done):** Status row (Quote/Bound/Issue/Cancel/Renew/Change), status date/time, underwriter name, LOB indicators + premiums, header/insurer/producer/named insured.  
2. **Prompts:** Underwriter = person; status date vs proposed effective date; LOB/status checkboxes = 1/Off.  
3. **Section-scoped text:** Policy category uses status_transaction + policy_info sections; applicant uses applicant_info.  
4. **VLM (optional):** Section crops for status + LOB reduce checkbox confusion.  

---

## 3. Form 127 – Business Auto Section

### Layout (page 1)

- **Top:** DATE, COMPANY/CARRIER, NAIC, NAMED INSURED, POLICY NUMBER, PRODUCER  
- **Driver table:** 13 rows, columns (by X): **#** (<180), **First Name** (~200–280), **City** (~285–500), **Last Name** (~560–700), **State** (~560–700), **Zip** (~700–780), **Sex** (~850–930), **Marital** (~935–975), **DOB** (~1080–1160), **Years exp** (~1270–1310), **Year licensed** (~1360–1400), **License#** (~1500–1620), **License State** (~1830–1920), **Tax ID** (~1520–1610).  
- **Vehicle blocks:** Often in GT as nested “Vehicle 1”, “Vehicle 2”; schema uses flat keys Vehicle_*_A, _B.  

### OCR behaviour

- **Docling:** Driver table can merge first name + city or state + zip in one cell; order may not match row order.  
- **BBox:** **Row order = driver number:** row 1 → _A, row 2 → _B, … **X ranges** in `_parse_driver_row` assign blocks to columns (first name vs city, state vs surname).  
- **Spatial pre-extract:** `extract_127_header` (date, carrier, NAIC, policy, insured, producer) + `extract_127_drivers` (driver rows by Y, then column by X).  

### Accuracy levers

1. **Driver table:** Use **BBox only** for driver extraction when available; prompt must state “columns by X” and “row order = _A, _B, …”.  
2. **Column disambiguation:** First name vs city (x≈200–280 vs 285–500); state vs surname (both 560–700); use `_is_person_name_or_multi` and `_is_city_name`.  
3. **GT flatten:** 127 GT flattened to Vehicle_*_A, Driver_*_A, etc.; comparison and schema aligned.  
4. **Section-scoped:** Driver category uses driver_table section only.  

---

## 4. Form 137 – Commercial Auto Section (Vehicle Schedule)

### Layout

- **Page 1:** NAMED INSURED, POLICY effective date, INSURER, NAIC; **vehicle/coverage table:** Business Auto Symbols (1–9), liability limits, deductibles, other coverages. Suffixes _A–_F for vehicle/coverage rows.  
- **Pages 2–3:** Same structure for Truckers (_B) and Motor Carrier (_C) sections.  

### OCR behaviour

- **Docling:** Coverage tables; symbol columns may be hard to interpret (which column = which symbol).  
- **BBox:** `extract_137_header` (date, agency, insured, policy, effective, carrier, NAIC); `extract_137_coverage` does left-side liability amounts, right-side deductibles, hired/non-owned by label Y and value X.  
- **Symbol checkboxes:** Business Auto Symbol 1–9 = checkboxes; need BBox to see which column is marked.  

### Accuracy levers

1. **Spatial pre-extract:** Header + coverage amounts and deductibles already extracted by Y/X regions.  
2. **Prompts:** “Business Auto Symbols 1–9 are checkboxes; use BBox to see which symbol column is marked; return 1 or Off.”  
3. **Vehicle schedule:** Suffixes _A–_F; coverage fields (limits, deductibles) tied to same suffix by page/section.  
4. **Section-scoped:** vehicle_schedule section for vehicle/coverage categories.  

---

## 5. Cross-form recommendations

1. **Dual-OCR rule in prompts:** “Use BOTH Docling and BBox; when the same information appears in both, **BBox positions (X,Y) decide which field a value belongs to** (e.g. status row, driver columns, LOB columns).”  
2. **Section-scoped note:** When extraction uses section-scoped text, add: “The text below is limited to the relevant form section(s); use it with BBox positions for correct field assignment.”  
3. **Checkbox consistency:** All forms: Indicator/checkbox fields = “1” or “Off” only; never text or amounts.  
4. **Comparison:** Checkbox and numeric normalisation (e.g. 0/1 → false/true, dates to YYYY-MM-DD, times to HHMM) applied in `compare.py`.  

---

## 6. File reference

| Component | Path |
|-----------|------|
| OCR engine (Docling + EasyOCR + spatial index) | `ocr_engine.py` |
| Spatial pre-extract (125/127/137) | `spatial_extract.py` |
| Section config (headers, category→sections) | `section_config.py` |
| Section detection and scoped text | `form_sections.py` |
| Prompts (layout, category hints) | `prompts.py` |
| Extractor (category loop, section-scoped, gap-fill, vision) | `extractor.py` |
| Comparison and normalisation | `compare.py` |

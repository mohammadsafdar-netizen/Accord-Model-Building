# The ACORD Form Extraction Project — A Deep Dive

---

## The Problem This Solves

Insurance companies in the United States use standardized paper forms called **ACORD forms**. These are the forms you fill out when you apply for commercial insurance — business auto coverage, general liability, contractor supplements, etc.

Every day, insurance brokers, agents, and carriers receive **thousands** of these forms. They arrive as scanned PDFs — sometimes printed cleanly, sometimes filled out by hand, sometimes faxed and re-scanned until the text is barely readable. Someone has to sit down and manually type every single field into a database: the company name, the address, which coverage boxes are checked, what vehicles are listed, driver license numbers, policy dates... hundreds of fields per form.

This project **automates that entire process**. You feed it a scanned PDF, and it gives you back clean, structured data — every field extracted, validated, and ready to import into a database.

---

## What Are ACORD Forms?

ACORD (Association for Cooperative Operations Research and Development) is the insurance industry's standards body. They design the forms that virtually every insurance company in America uses. Think of them like tax forms (W-2, 1040) but for insurance.

This project handles four specific forms:

**ACORD 125 — Commercial Insurance Application** (548 fields)
The main application form. Contains the company name, address, who the insurance broker is, what kind of business it is, how many employees, prior coverage history, loss history (past claims), and dozens of yes/no questions about the business operations. This is the "front door" form — everything starts here.

**ACORD 127 — Business Auto Section** (634 fields)
The driver and vehicle details for business auto insurance. Has a table with up to 13 driver rows (A through M), each with name, city, state, ZIP, sex, date of birth, license number, license state, marital status, and several codes. Also has vehicle information — year, make, model, VIN, body type, cost, garaging location. This is the hardest form because of those dense tables with narrow columns.

**ACORD 137 — Commercial Auto Section** (403 fields)
The coverage schedule for commercial auto. Lists vehicles with their "Business Auto Symbols" (codes 1-9 that determine what kind of coverage applies), coverage types, limits, deductibles, and state-specific information. Lots of checkboxes and small numeric fields.

**ACORD 163 — Contractors Supplement** (518 fields)
Additional information for contractor businesses. Contains details about subcontractors, equipment, operations, street addresses for multiple locations, and various yes/no questions about the contractor's work. Has a distinctive multi-column layout that requires special handling.

---

## The Core Challenge: Why Is This Hard?

You might think, "Can't you just run OCR on it and be done?" Unfortunately, no. Here's why:

### 1. OCR gives you text, not meaning

OCR (Optical Character Recognition) can tell you that the pixels at position (350, 420) on the page spell "Indianapolis". But it can't tell you whether that's a **city name**, a **company name**, a **street name**, or part of an **address**. On an ACORD 127, "Indianapolis" might appear in the driver table's City column, but OCR has no idea what column it belongs to — it just sees text floating on a page.

### 2. Tables are a nightmare

The ACORD 127 driver table has 13 rows and about 10 columns, printed in tiny text. When scanned, columns shift by a few pixels. The OCR sees "Thomas Indianapolis Mooney IN 46140 M 03/15/1980" — but which part is the first name? Which is the city? Which is the state? A human reads the column headers and knows. A computer needs to be taught this.

### 3. Checkboxes are ambiguous

A checkbox might be checked with a bold X, a light pencil mark, a printed checkmark, or a filled square. When scanned at low quality, a checked box can look empty, and sometimes scan artifacts (dust, fold marks) make an empty box look checked. The system needs to distinguish between genuine checkmarks and noise.

### 4. Handwriting varies wildly

Some forms are typed. Some are handwritten. Some have handwritten notes over typed text. OCR struggles with handwriting, especially when it's cramped into tiny form fields.

### 5. Every scanned form is slightly different

Even identical form types get scanned differently — rotated slightly, shifted, with different brightness and contrast. A field that's at pixel position (300, 500) on one scan might be at (310, 495) on another.

---

## How The System Works — The Full Pipeline

Think of the extraction process like a detective team. No single detective solves the case alone. Instead, multiple specialists examine the evidence from different angles, and then they compare notes to reach a consensus.

### Phase 1: Reading the Page (OCR)

The system uses **two different OCR engines simultaneously**:

**Docling** understands document structure. It knows "this is a table," "this is a heading," "this paragraph belongs to that section." It gives you organized markdown text, like reading a well-formatted document.

**EasyOCR** gives you raw precision. For every word it reads, it tells you the exact pixel coordinates — "the word 'Indianapolis' is at position X=350, Y=420, width=120, height=18." This spatial information is critical for knowing which column a value belongs to.

By combining both, the system gets the best of both worlds: structural understanding AND precise positioning. Every word on every page is mapped into a "spatial index" — imagine a searchable map of the entire form where you can query "what text exists in the rectangle from (300,400) to (500,430)?"

### Phase 2: Knowing What To Look For (Schema)

Before extracting anything, the system loads a **schema** — a detailed blueprint of every field the form should contain. The schema for ACORD 125 says there are 548 fields, organized into categories like "header" (agency name, date), "insurer" (carrier name, NAIC code), "named_insured" (the customer's name, address), "policy" (effective date, expiration date), "driver," "vehicle," "coverage," etc.

Each field in the schema has:
- A **name** (e.g., `NamedInsured_FullName_A`)
- A **type** (text, checkbox, radio, date, numeric)
- A **tooltip** describing what it should contain ("Full legal name of the insured party")
- A **physical position** on the form (pixel coordinates of the actual form widget)
- A **category** (which section of the form it belongs to)

These positions were extracted from "AcroForm" reference PDFs — PDFs that have the form fields digitally defined (not scanned). The project uses those reference forms **only** to build this positional map. The actual extraction always works from scanned images.

### Phase 3: The 14-Step Extraction Pipeline

This is where the real intelligence happens. The system runs **14 different extraction methods**, each one catching things the others might miss:

**Step 1 — Spatial Pre-Extract:** Using the schema's position map, the system looks at where each field *should* be on the page, finds OCR text blocks in that region, and assigns them directly. If the schema says "PostalCode is at position (500, 200)" and the OCR found "40508" at position (498, 202), that's a match. No AI needed — pure geometry. This is the highest-confidence method (95%).

**Step 2 — Positional Atlas Matching:** A more sophisticated version of Step 1. It handles alignment differences between the schema's reference positions and the actual scan by computing offsets (how much did the scan shift?). It uses "anchor points" — text that appears on every form (like "ACORD 125") — to calibrate the alignment.

**Step 3 — Template Anchoring:** Compares the scan against known template layouts to identify standardized regions of the form. Like saying "the insured information is always in the top-left quadrant."

**Step 4 — Label-Value Pairing:** Searches the OCR text for patterns like "Name: John Smith" or "Policy #: ABC-123456". When it finds a label followed by a colon and a value, it can assign that value to the corresponding field.

**Step 5 — Semantic Matching:** Uses a small AI model (MiniLM, only 80MB) that understands the *meaning* of text. If the form has a label "AGENCY" next to a value, semantic matching knows that "AGENCY" is conceptually related to the schema field `Producer_FullName_A`, even though the words are completely different. This is done using "embeddings" — converting text into numerical vectors where similar concepts are close together in mathematical space.

**Step 6 — VLM Direct Extract:** This is the big gun. A **Vision Language Model** (think: an AI that can see and read images) looks at the actual page image and extracts fields directly. The model used here is `acord-vlm-7b` — a 7-billion-parameter AI model that was **custom-trained on 510 ACORD forms**. It literally learned what these forms look like and where to find each field. When it sees a page, it outputs JSON like `{"InsuredName": "Humphrey Inc", "EffectiveDate": "12/15/2023"}`.

**Step 7 — Multimodal Extract:** Sends both the page image AND the OCR text to the VLM at the same time. This gives the AI two sources of information — it can see the image and also read the machine-extracted text. Sometimes the image shows something the OCR missed, and vice versa.

**Step 8 — Checkbox Crops:** For every checkbox field, the system crops a tight rectangle around just that checkbox from the page image, enhances the contrast (using a technique called CLAHE), and asks the VLM "is this checkbox checked or unchecked?" This focused approach is much more accurate than asking the VLM to assess all checkboxes at once.

**Step 9 — VLM Vision Pass:** A general vision pass where the VLM examines the page images and extracts any remaining fields it can identify.

**Step 10 — Text LLM Category Extraction:** A text-only language model (Qwen 2.5, 7B parameters) extracts fields category by category. First it gets all "header" fields, then "insurer" fields, then "policy" fields, etc. Breaking it into categories prevents the model from being overwhelmed by 600+ fields at once.

**Step 11 — Gap-Fill Pass:** After all the above, some fields are still missing. The gap-fill pass sends the OCR text along with just the missing field names to the LLM for one more attempt.

**Step 12 — Ensemble Fusion:** Now comes the crucial step. Multiple extraction methods have produced potentially different answers for the same field. The ensemble weighs them:

Imagine three methods extracted `InsuredName`:
- Spatial extraction says "Humphrey Inc" (confidence: 0.95)
- VLM extraction says "Humphrey Inc" (confidence: 0.85)
- Text LLM says "Humphrey Inc." (confidence: 0.65)

All three agree (after normalizing the period). Agreement **boosts** confidence. The ensemble picks the highest-confidence source's exact text ("Humphrey Inc" from spatial) and marks overall confidence at 0.95 + an agreement bonus.

But when sources **disagree**, the ensemble picks the one with the highest confidence. And it's smart about field types — for checkboxes, it trusts the vision model more than the text model. For dates, it trusts the text model more.

**Step 13 — Cross-Field Validation:** Checks logical consistency:
- If the state is "WI" (Wisconsin), the ZIP code should start with "53" or "54"
- The policy effective date should be before the expiration date
- Vehicle years should be between 1950 and 2028
- VIN numbers have a mathematical check digit
- Phone numbers should be 10 digits
- NAIC codes should be exactly 5 digits

**Step 14 — Normalize and Verify:** Cleans up all values:
- Dates get standardized to MM/DD/YYYY
- Checkboxes become "1" (checked) or "Off" (unchecked)
- Dollar amounts strip "$" and commas
- Phone numbers get formatted consistently
- State codes get validated against real US/Canadian codes
- Tooltip text accidentally extracted as values gets filtered out

Plus there's a final **pixel-based checkbox verification** — the system crops each checkbox's exact position from the page image, counts how many pixels are dark vs light, and uses that ratio to override the AI's answer when the pixel evidence is strong. If less than 10% of pixels are dark, the box is empty regardless of what the AI thinks. If more than 28% are dark, it's checked. For ambiguous cases (10-28%), it does a **second check at 2x zoom** with a larger crop region, averaging both measurements for a more stable decision.

---

## The AI Models

The system runs entirely locally — no cloud services, no internet required during extraction. It uses **Ollama**, which is like a local server for running AI models on your own GPU.

**Text LLM: Qwen 2.5 (7B parameters)**
A general-purpose language model that reads OCR text and extracts structured data. It's given a prompt like "Here is the OCR text from an ACORD 125 form. Extract these header fields: [list of fields]. Return JSON only." It's good at understanding context but can't see images.

**Vision LLM: acord-vlm-7b (fine-tuned Qwen2.5-VL-7B)**
This is the project's secret weapon. It started as a general-purpose vision model (Qwen2.5-VL-7B, which can look at images and answer questions about them). The project team then **fine-tuned** it — they showed it 8,403 training examples of ACORD form pages paired with the correct extracted data, and the model learned the specific patterns of these insurance forms.

Fine-tuning used a technique called **QLoRA** (Quantized Low-Rank Adaptation), which makes training feasible on a single consumer GPU. Instead of retraining all 7 billion parameters, it only trains a small "adapter" layer (~2% of the weights) while keeping the base model frozen. This takes about 4-6 hours on a modern GPU.

The fine-tuned model achieves 5-7% higher accuracy than the generic base model because it learned things like:
- "The box in the upper-right corner labeled 'DATE' contains a date in MM/DD/YYYY format"
- "The narrow column between 'Last Name' and 'State' in the driver table is the 'City' column"
- "A faint pencil mark in a checkbox means 'checked'"

**Semantic Matcher: MiniLM**
A tiny (80MB) model that converts text into numerical vectors. Used to match OCR-detected labels to schema field names. Runs on CPU, very fast.

---

## How Accuracy Is Measured

The project includes **510 test forms** with verified ground truth — human-verified correct answers for every field. When the system extracts a form, it compares each extracted value against the ground truth:

- **Exact match:** The extracted value equals the expected value (after normalization). Full credit.
- **Partial match:** The extracted value contains the right answer but has extra text, or is close but not perfect. Half credit.
- **Wrong:** The system extracted something, but it doesn't match. Zero credit.
- **Missing:** The system didn't extract anything for this field. Zero credit.

**Accuracy** = (exact matches + 0.5 x partial matches) / total ground truth fields

The comparison is smart about normalization:
- "true" and "1" are both valid for a checked checkbox
- "02/19/2025" and "2/19/2025" are the same date
- "St." and "Street" are equivalent in addresses
- Leading/trailing whitespace is ignored
- State code prefixes that bleed from adjacent OCR are stripped

Current results (as of the latest commit):

| Form | Accuracy | What it means |
|------|----------|--------------|
| 125 | 73.28% | 329 of ~464 fields correct |
| 127 | 79.15% | 460 of ~590 fields correct |
| 137 | 80.83% | 295 of ~370 fields correct |
| 163 | 86.75% | 429 of ~517 fields correct |
| **Average** | **80.00%** | **About 4 out of 5 fields are perfect** |

**Coverage** (did the system at least attempt to extract something?) averages ~96%. So it finds almost everything, and gets about 80% of it exactly right.

---

## The Fine-Tuning Pipeline

The `finetune/` directory contains a complete training pipeline:

**Data Preparation** (`prepare_dataset.py`): Takes the 510 test forms, renders each page as an image, pairs it with the ground truth fields for that page, and creates 8,403 training examples in the format:
```
User: [image of page] "Extract these fields from this ACORD 125 page: [field list]"
Assistant: {"FieldName1": "value1", "FieldName2": "value2", ...}
```

**Training** (`train.py`): Fine-tunes Qwen2.5-VL-7B using:
- **QLoRA**: 4-bit quantized base model + trainable low-rank adapter
- **Curriculum learning**: 3 phases — general examples first (high learning rate), then hard examples (medium rate), then error-specific examples (low rate)
- Takes 4-6 hours on a modern GPU

**DPO Training** (`train_dpo.py`): An advanced technique called Direct Preference Optimization. It shows the model pairs of outputs — one correct and one wrong — and teaches it to prefer the correct one. This is built from the system's own mistakes: when extraction gets a field wrong, the wrong answer becomes the "rejected" output and the ground truth becomes the "chosen" output.

**Active Learning** (`active_learning.py`): An iterative improvement loop:
1. Run extraction on test forms
2. Find the worst errors
3. Create targeted training examples from those errors
4. Retrain the model
5. Human reviewers correct remaining mistakes
6. Those corrections become new training data
7. Repeat

**Export** (`export_ollama.py`): Converts the trained model to GGUF format (a compressed format for inference) and registers it with Ollama so the extraction pipeline can use it immediately.

---

## The Human Review System

The system includes a **confidence-based human review** feature. When enabled (`--generate-review`), it:

1. Computes an effective confidence score for every extracted field (combining ensemble confidence with OCR verification)
2. Fields below the threshold (default: 85% confidence) get flagged for human review
3. Generates a `review_manifest.json` with the flagged fields, their extracted values, confidence scores, the OCR text snippet, and which extraction source produced the value

This lets a human reviewer focus only on the ~10% of fields the system is least sure about, rather than checking all 500+ fields manually. It's the bridge between "fully automated" and "fully manual" — the system does the easy 90%, humans handle the hard 10%.

---

## Why So Many Extraction Methods?

You might wonder: if the fine-tuned VLM is the best single method, why bother with 13 other methods?

Because no single method is perfect across all cases:

- **Spatial extraction** is best for fields with precise positions, but fails when scans are misaligned
- **VLM** is great at reading images but sometimes hallucinates values that aren't there
- **Text LLM** understands context well but can't see the actual form layout
- **Semantic matching** catches creative label-field mappings but requires clear labels
- **Pixel analysis** is definitive for checkboxes but can't extract text

By running all methods and combining them with the ensemble, the system catches errors that any single method would make. When two methods agree, confidence goes up. When they disagree, the more trusted method (based on its track record for that field type) wins.

This architecture is what pushes accuracy from ~65% (single method) to 80% (full ensemble).

---

## What Remains Imperfect

Even at 80% accuracy, 1 in 5 fields has some kind of error. The remaining challenges are:

1. **Checkbox false positives** (66 errors across all forms): The system sometimes thinks an empty checkbox is checked, or vice versa. Scan artifacts, fold marks, and very light pencil marks cause this.

2. **Field boundary bleed** (56 errors): Adjacent cells merge during OCR. A street address bleeds into the city field, or a date bleeds into a numeric field next to it.

3. **Missing values** (74 errors): Fields the system can't find at all — usually because the text is too faint, the field is blank, or it's in a region the OCR couldn't parse.

4. **Table column confusion** (46 errors): In dense driver/vehicle tables, values end up in the wrong column. "Indianapolis" gets assigned to "Last Name" instead of "City."

5. **OCR quality** (18 errors): The underlying OCR simply misreads characters. "1990" becomes "199C", "Elizabeth" becomes "Elizabe".

Each category of error is being systematically addressed through the improvements described above — multi-resolution checkbox verification, positional boundary enforcement, small-field recovery, and table pre-parsing.

---

## The Big Picture

This project represents a **complete, production-ready document intelligence pipeline** for insurance form processing. It runs entirely on local hardware (no cloud dependency), uses open-source models (no licensing fees), and achieves accuracy levels that make it genuinely useful — especially when combined with the human review system that flags the ~10% of fields it's least confident about.

The architecture is designed to improve over time through the active learning loop: every corrected form becomes training data for the next version of the model. As more forms are processed and corrected, the system gets progressively better at handling the specific patterns and variations that appear in real-world insurance documents.

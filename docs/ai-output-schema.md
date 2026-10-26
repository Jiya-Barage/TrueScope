# TrueScope AI Output Schema Specification

**Document Version:** 1.0.0  
**Target Audience:** 
- **Teammate A (Frontend / React):** Invoice visualization, confidence indicators, explainability panels, and correction UI.
- **Teammate B (Backend / FastAPI):** Orchestration, pipeline execution, persistence, and schema validation.
- **Teammate C (AI / Extraction & Classification):** Pipeline producer contract.
- **Teammate D (Emission Engine):** Activity key matching, emission factor lookups, and CO2e calculation.

---

## 1. Purpose & Pipeline Context

TrueScope converts business invoices (PDFs and scanned images) into auditable greenhouse gas (GHG) emission records for SMEs. The end-to-end flow is:

$$\text{Invoice Upload} \longrightarrow \mathbf{AI\ (OCR\ +\ Extraction\ +\ Classification)} \longrightarrow \text{Emission Engine} \longrightarrow \text{Dashboard\ \&\ Report}$$

The AI pipeline is responsible for:
1. Extracting raw text and word-level optical character recognition (OCR) confidence.
2. Parsing metadata (vendor, dates, invoice numbers) and itemized line items.
3. Classifying each line item into a standardized activity category and GHG Scope (1, 2, or 3).
4. Generating composite confidence scores and human-readable explanation strings per line item.

The JSON schema defined below serves as the **strict interface contract** consumed downstream by Teammate B (FastAPI pipeline orchestration), Teammate D (emission engine rule matching), and Teammate A (React UI).

---

## 2. JSON Schema Definition

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TrueScopeAIOutput",
  "type": "object",
  "required": [
    "invoice_id",
    "source_file",
    "vendor",
    "invoice_date",
    "invoice_number",
    "currency",
    "line_items",
    "overall_confidence",
    "warnings"
  ],
  "properties": {
    "invoice_id": {
      "type": "string",
      "description": "Unique identifier for the invoice execution."
    },
    "source_file": {
      "type": "string",
      "description": "Original file name or path of the uploaded invoice."
    },
    "vendor": {
      "type": ["string", "null"],
      "description": "Detected supplier or vendor name."
    },
    "invoice_date": {
      "type": ["string", "null"],
      "format": "date",
      "description": "Invoice date formatted as YYYY-MM-DD, or null if unresolvable."
    },
    "invoice_number": {
      "type": ["string", "null"],
      "description": "Invoice or reference number identifier."
    },
    "currency": {
      "type": ["string", "null"],
      "description": "Three-letter ISO currency code (e.g. GBP, EUR, USD) or symbol."
    },
    "line_items": {
      "type": "array",
      "description": "Extracted itemized billable rows mapped to emission activities.",
      "items": {
        "type": "object",
        "required": [
          "description",
          "quantity",
          "unit",
          "amount",
          "category",
          "scope",
          "confidence",
          "confidence_flag",
          "reasons"
        ],
        "properties": {
          "description": {
            "type": "string",
            "description": "Raw description text extracted for the item."
          },
          "quantity": {
            "type": ["number", "null"],
            "description": "Numerical quantity or activity volume."
          },
          "unit": {
            "type": ["string", "null"],
            "description": "Standardized or raw unit of measurement (e.g. litres, kWh, km)."
          },
          "amount": {
            "type": ["number", "null"],
            "description": "Monetary charge or line item total."
          },
          "category": {
            "type": "string",
            "enum": [
              "stationary_fuel_diesel",
              "mobile_fuel_petrol",
              "mobile_fuel_diesel",
              "natural_gas",
              "electricity_grid",
              "freight_transport",
              "business_travel",
              "purchased_goods",
              "waste_disposal",
              "water_effluent",
              "non_emission",
              "unknown"
            ],
            "description": "Standardized activity key matching the Emission Engine lookup."
          },
          "scope": {
            "type": ["integer", "null"],
            "enum": [1, 2, 3, null],
            "description": "GHG Protocol Scope (1, 2, 3) or null if unknown or non-emission."
          },
          "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Heuristic confidence score between 0.0 and 1.0."
          },
          "confidence_flag": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Categorical confidence level driving UI display."
          },
          "reasons": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Short human-readable strings explaining classification & confidence."
          },
          "expected_unit": {
            "type": ["string", "null"],
            "description": "Optional canonical unit expected by the Emission Engine for activity calculation."
          }
        }
      }
    },
    "overall_confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Aggregate confidence score for the entire invoice extraction."
    },
    "warnings": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Pipeline alerts, low-confidence notices, or missing field warnings."
    }
  }
}
```

---

## 3. Example JSON Output

```json
{
  "invoice_id": "inv_8f7b2c9e-5612-4d2a",
  "source_file": "sample_fuel_invoice.pdf",
  "vendor": "Apex Logistics Fuel Corp",
  "invoice_date": "2024-03-15",
  "invoice_number": "INV-2024-00892",
  "currency": "GBP",
  "line_items": [
    {
      "description": "Ultra Low Sulphur Diesel Bulk Delivery - Fleet Fuel",
      "quantity": 1250.0,
      "unit": "litres",
      "amount": 1875.0,
      "category": "mobile_fuel_diesel",
      "scope": 1,
      "confidence": 0.88,
      "confidence_flag": "high",
      "reasons": [
        "Matched keyword 'diesel' with fleet context -> mobile_fuel_diesel (Scope 1)",
        "High OCR word confidence (0.94)",
        "Quantity and unit 'litres' are present and physically plausible"
      ]
    },
    {
      "description": "Environmental Waste Compliance Fee",
      "quantity": null,
      "unit": null,
      "amount": 45.0,
      "category": "waste_disposal",
      "scope": 3,
      "confidence": 0.62,
      "confidence_flag": "medium",
      "reasons": [
        "Matched keyword 'waste' -> waste_disposal (Scope 3)",
        "Physical quantity or unit missing; requires review"
      ]
    }
  ],
  "overall_confidence": 0.75,
  "warnings": [
    "Line 2: Missing physical activity quantity/unit; emission calculation is skipped for review."
  ]
}
```

---

## 4. Field-by-Field Reference

| Field | Type | Description | Producer Rules | Consumer Guidance |
| :--- | :--- | :--- | :--- | :--- |
| `invoice_id` | `string` | Unique identifier. | Generated by UUID4 or passed by caller. | Used by B to track DB entity. |
| `source_file` | `string` | File name. | Preserved from upload metadata. | Displayed in UI header. |
| `vendor` | `string \| null` | Vendor name. | Extracted from header lines; `null` if unreadable. | Displayed on invoice summary card. |
| `invoice_date` | `string \| null` | Date in `YYYY-MM-DD`. | Normalised from various date formats; `null` if absent. | Display and manual date review; the current report preview does not filter by date. |
| `invoice_number`| `string \| null`| Invoice identifier. | Regex-matched reference code; `null` if unconfirmed. | Audit trail cross-referencing. |
| `currency` | `string \| null` | 3-letter currency code.| Detected symbol/code ($ -> USD, £ -> GBP, € -> EUR). | Invoice metadata only; not used to infer physical activity or calculate emissions. |
| `line_items` | `array` | Parsed items list. | Empty array if no line items parsed. | Iterated by D for emission calculation and A for UI table. |
| `line_items[].description` | `string` | Raw line text. | Retains original wording. | Shown in invoice results; backend-upload values are read-only. |
| `line_items[].quantity` | `number \| null`| Activity quantity. | Float or integer parsed from line. | Primary activity data for physical emission factors. |
| `line_items[].unit` | `string \| null` | Unit of measure. | Standardized lower-case token (e.g. `litres`, `kwh`). | Crucial for unit matching in D. |
| `line_items[].amount` | `number \| null`| Total cost. | Parsed line item total price. | Display and review only; never a substitute for physical activity data. |
| `line_items[].category` | `string` | Activity key. | Must match category taxonomy below. | Key in D's emission factor table. |
| `line_items[].scope` | `integer \| null`| GHG Scope (`1`, `2`, `3`). | Fixed mapping derived from category. | Used in Scope summaries; only compatible kg CO2e values contribute to CO2e totals. |
| `line_items[].confidence` | `number` | Heuristic score [0, 1]. | Weighted average of OCR, completeness, match. | Powers sorting, flagging, and color bars. |
| `line_items[].confidence_flag` | `string` | `high`, `medium`, `low`. | Discretized via defined thresholds. | Visual badge in UI (Green, Amber, Red). |
| `line_items[].reasons` | `array[string]`| Explanations. | List of human-readable rule rationale strings. | Displayed in UI explainability drawer/tooltip. |
| `line_items[].expected_unit` | `string \| null` | Expected unit token. | Canonical unit expected by Emission Engine; `null` if `non_emission` or `unknown`. | Optional hint for Teammate D to flag unit deviations. |
| `overall_confidence` | `number` | Aggregate invoice confidence. | Mean line confidence scaled by non-low line ratio (0.0 if no items). | Summary badge on invoice list. |
| `warnings` | `array[string]` | Alert messages. | Explicit issues during extraction. | Rendered in UI banner if non-empty. |

---

## 5. Category Taxonomy & GHG Protocol Mapping

> **Coverage notice:** These are classifier taxonomy keys, not a promise that a
> matching factor exists. The engine only calculates exact category/unit
> matches and does not convert incompatible units or estimate emissions from
> spend. See [`emission-engine/README.md`](../emission-engine/README.md) for
> actual library coverage.

| Category Key (`category`) | GHG Scope (`scope`) | Expected Unit (`expected_unit`) | Typical Extracted Units (not necessarily supported by a factor) | Description / Example Activities |
| :--- | :---: | :---: | :--- | :--- |
| `stationary_fuel_diesel` | **1** | `litre` | `litre`, `litres`, `gallons` | Diesel consumed in stationary generators, boilers, site plant. |
| `mobile_fuel_petrol` | **1** | `litre` | `litre`, `litres`, `gallons` | Gasoline / petrol used in company-owned or operated road vehicles. |
| `mobile_fuel_diesel` | **1** | `litre` | `litre`, `litres`, `gallons` | Diesel used in company-owned or operated road fleet / vehicles / transport. |
| `natural_gas` | **1** | `kWh` | `kWh`, `m3`, `therms` | Piped utility natural gas for heating or industrial use. |
| `electricity_grid` | **2** | `kWh` | `kWh`, `mwh`, `units` | Purchased grid electricity from power utilities. |
| `freight_transport` | **3** | `tonne-km` | `tonne-km`, `km`, `trip`, `nos` | Upstream/downstream third-party shipping, courier, logistics. |
| `business_travel` | **3** | `passenger-km` | `passenger-km`, `km`, `trip` | Employee flights, train journeys, hotels, taxi rides. |
| `purchased_goods` | **3** | `kg` | `kg`, `units`, `nos` | Raw materials, equipment, consumable office goods. |
| `waste_disposal` | **3** | `tonne` | `tonne`, `tonnes`, `kg`, `month` | Commercial waste, landfill, recycling disposal. |
| `water_effluent` | **3** | `m3` | `m3`, `litres`, `kl` | Water supply, effluent treatment, sewage, STP. |
| `non_emission` | **null** | `null` | `null`, `month`, `nos` | Known non-emission lines: fixed/demand/service/meter charges, GST/tax/cess, late fees, rounding, discounts, deposits. |
| `unknown` | **null** | `null` | `null` | Unclassified items requiring human intervention. |

### Differentiating `unknown` vs `non_emission`

Both `unknown` and `non_emission` carry a GHG Scope of `null`, but serve fundamentally different roles in TrueScope:
- **`non_emission` (Scope null):** The classifier *confidently* determined that the line item represents a financial fee, tax, surcharge, discount, or non-combustion utility charge carrying zero direct greenhouse gas emissions (e.g. fixed demand charges, meter rent, GST/VAT/cess, late fees). No emission factor applies and no emission calculation is performed.
- **`unknown` (Scope null):** The classifier could *not* match the line item to any known emission activity or non-emission rule. It represents unclassified data requiring human review and intervention in the UI.

---

## 6. Confidence Scoring Rules & Heuristics

The confidence score is a **heuristic index** $\in [0.0, 1.0]$, **NOT** a calibrated statistical probability. It is engineered to give SME users and auditors immediate insight into data reliability.

### Scoring Factors and Weights

Each line item confidence $C$ is a heuristic score and is not an estimate of
emission-factor validity. A missing physical quantity or unsupported
category/unit pair is skipped for review; monetary amounts do not trigger a
spend-based fallback.

The pipeline confidence score $C$ is computed from four weighted sub-scores:

$$C = w_{\text{ocr}} \cdot S_{\text{ocr}} + w_{\text{comp}} \cdot S_{\text{comp}} + w_{\text{match}} \cdot S_{\text{match}} + w_{\text{sanity}} \cdot S_{\text{sanity}}$$

Default pipeline weights:
- $w_{\text{ocr}} = 0.25$: Mean OCR word confidence for the tokens making up the line item.
- $w_{\text{comp}} = 0.30$: Field completeness score (credit awarded for description, quantity, unit, and monetary amount).
- $w_{\text{match}} = 0.30$: Classification rule match strength (1.0 for specific multi-word/exact token match, 0.7 for partial match, 0.0 for unknown).
- $w_{\text{sanity}} = 0.15$: Physical sanity check (verification that unit is compatible with the detected category, e.g. `litres` for diesel, `kwh` for electricity).

The final score is clamped to $[0.0, 1.0]$ and rounded to 2 decimal places.

### Confidence Flag Thresholds

| Flag (`confidence_flag`) | Score Range | UI Treatment (Teammate A) | Engine Behavior (Teammate D) |
| :--- | :---: | :--- | :--- |
| `high` | $\ge 0.80$ | **Green badge**: Higher extraction/classification confidence. | Still requires an exact supported factor/unit match and factor review. |
| `medium` | $0.50 \le C < 0.80$ | **Amber badge**: Highlighted for human review. | Does not enable a spend-based or benchmark calculation. |
| `low` | $< 0.50$ | **Red badge**: Review is recommended. | Does not hold or confirm a calculation; review status is reported separately. |

### Aggregate Overall Confidence

To ensure erroneous rows (such as mathematical quantity $\times$ rate mismatches) cannot be hidden behind high scores on clean rows, `overall_confidence` is calculated as the mean of line item confidences scaled by the fraction of lines that are not flagged `low`:

$$\text{Overall Confidence} = \left(\frac{1}{N} \sum_{i=1}^N C_i\right) \times \left(\frac{N_{\text{non-low}}}{N}\right)$$

where $N$ is the total number of line items and $N_{\text{non-low}}$ is the count of line items whose `confidence_flag` is not `low`. If $N = 0$, `overall_confidence` is 0.0.

---

## 7. Explainability & UI Guidelines (Teammate A)

To foster trust among SME clients and non-expert sustainability managers:
1. **Explainability:** Display the strings in `reasons` as bullet points when the user inspects a line item.
2. **Missing Field Prompting:** The current upload flow flags missing quantity/unit and skips the calculation. Editing extracted backend-upload values is not currently supported.
3. **Audit Trail:** Preserve the original OCR description, extraction result, calculation result, and review reasons in the stored invoice record.

---

## 8. Changelog

### 2026-10-26 (Keyword Priority Update)
- **Non-emission Keyword Priority:** `non_emission` now uses strong vs weak keyword priority; emission keywords beat generic charge wording.

### 2026-10-19 (Additive Schema Update)
- **New Category `non_emission` (Scope null):** Added dedicated activity key for known zero-emission invoice items (fixed/demand/service/meter charges, GST, tax, cess, late fees, rounding, discounts, deposits) where no emission factor applies.
- **New Category `water_effluent` (Scope 3):** Added activity key for water supply, effluent treatment, sewage, and STP items with canonical expected unit `m3`.
- **Diesel Split:** Formally established the mobile vs stationary diesel split (`mobile_fuel_diesel` for vehicles/truck/fleet/transport/tanker delivery; `stationary_fuel_diesel` for generators/DG/boiler/stationary use or when vehicle context is absent).
- **Canonical Expected Units:** Standardized expected unit mappings for the Emission Engine and documented the optional `expected_unit` field on line items.
- **Taxonomy Clarification:** Defined operational distinction between `non_emission` (known zero-emission lines) and `unknown` (unrecognized lines needing human review).

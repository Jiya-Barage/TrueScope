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
              "unknown"
            ],
            "description": "Standardized activity key matching the Emission Engine lookup."
          },
          "scope": {
            "type": ["integer", "null"],
            "enum": [1, 2, 3, null],
            "description": "GHG Protocol Scope (1, 2, 3) or null if unknown."
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
        "Quantity or physical unit missing; financial spend available"
      ]
    }
  ],
  "overall_confidence": 0.75,
  "warnings": [
    "Line 2: Missing physical activity quantity; Emission Engine may require spend-based estimation."
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
| `invoice_date` | `string \| null` | Date in `YYYY-MM-DD`. | Normalised from various date formats; `null` if absent. | Used for emission accounting reporting periods. |
| `invoice_number`| `string \| null`| Invoice identifier. | Regex-matched reference code; `null` if unconfirmed. | Audit trail cross-referencing. |
| `currency` | `string \| null` | 3-letter currency code.| Detected symbol/code ($ -> USD, £ -> GBP, € -> EUR). | Required if spend-based emission factors are used. |
| `line_items` | `array` | Parsed items list. | Empty array if no line items parsed. | Iterated by D for emission calculation and A for UI table. |
| `line_items[].description` | `string` | Raw line text. | Retains original wording. | Shown in editable UI table. |
| `line_items[].quantity` | `number \| null`| Activity quantity. | Float or integer parsed from line. | Primary activity data for physical emission factors. |
| `line_items[].unit` | `string \| null` | Unit of measure. | Standardized lower-case token (e.g. `litres`, `kwh`). | Crucial for unit matching in D. |
| `line_items[].amount` | `number \| null`| Total cost. | Parsed line item total price. | Used as fallback for spend-based emission factors. |
| `line_items[].category` | `string` | Activity key. | Must match category taxonomy below. | Key in D's emission factor table. |
| `line_items[].scope` | `integer \| null`| GHG Scope (`1`, `2`, `3`). | Fixed mapping derived from category. | Aggregated into Scope 1/2/3 dashboard totals. |
| `line_items[].confidence` | `number` | Heuristic score [0, 1]. | Weighted average of OCR, completeness, match. | Powers sorting, flagging, and color bars. |
| `line_items[].confidence_flag` | `string` | `high`, `medium`, `low`. | Discretized via defined thresholds. | Visual badge in UI (Green, Amber, Red). |
| `line_items[].reasons` | `array[string]`| Explanations. | List of human-readable rule rationale strings. | Displayed in UI explainability drawer/tooltip. |
| `overall_confidence` | `number` | Aggregate invoice confidence. | Mean line confidence scaled by non-low line ratio (0.0 if no items). | Summary badge on invoice list. |
| `warnings` | `array[string]` | Alert messages. | Explicit issues during extraction. | Rendered in UI banner if non-empty. |

---

## 5. Category Taxonomy & GHG Protocol Mapping

> [!IMPORTANT]
> **Strict Contract with Teammate D (Emission Engine):**  
> Teammate D must ensure that emission-factor database keys match these exact string tokens.  
> These keys can **only** be extended or modified by mutual agreement between AI (Teammate C) and Emission Engine (Teammate D).

| Category Key (`category`) | GHG Scope (`scope`) | Typical Units | Description / Example Activities |
| :--- | :---: | :--- | :--- |
| `stationary_fuel_diesel` | **1** | `litres`, `gallons` | Diesel consumed in stationary generators, boilers, site plant. |
| `mobile_fuel_petrol` | **1** | `litres`, `gallons` | Gasoline / petrol used in company-owned or operated road vehicles. |
| `mobile_fuel_diesel` | **1** | `litres`, `gallons` | Diesel used in company-owned or operated road fleet. |
| `natural_gas` | **1** | `kwh`, `m3`, `therms` | Piped utility natural gas for heating or industrial use. |
| `electricity_grid` | **2** | `kwh`, `mwh` | Purchased grid electricity from power utilities. |
| `freight_transport` | **3** | `tonne.km`, `km`, `miles` | Upstream/downstream third-party shipping, courier, logistics. |
| `business_travel` | **3** | `km`, `miles`, `passenger.km`| Employee flights, train journeys, hotels, taxi rides. |
| `purchased_goods` | **3** | `kg`, `units`, `spend` | Raw materials, equipment, consumable office goods. |
| `waste_disposal` | **3** | `tonnes`, `kg`, `litres` | Commercial waste, landfill, recycling, wastewater processing. |
| `unknown` | **null** | `null` | Unclassified items requiring user intervention. |

---

## 6. Confidence Scoring Rules & Heuristics

The confidence score is a **heuristic index** $\in [0.0, 1.0]$, **NOT** a calibrated statistical probability. It is engineered to give SME users and auditors immediate insight into data reliability.

### Scoring Factors and Weights

Each line item confidence $C$ is computed from four weighted sub-scores:

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
| `high` | $\ge 0.80$ | **Green badge**: Ready for automatic aggregation. | Full auto-calculation using primary activity factor. |
| `medium` | $0.50 \le C < 0.80$ | **Amber badge**: Highlighted for optional human review. | Fallback to spend-based or benchmark factor if unit is missing. |
| `low` | $< 0.50$ | **Red badge**: "Review Required" button triggers edit modal. | Held in pending state until user confirms category & values. |

### Aggregate Overall Confidence

To ensure erroneous rows (such as mathematical quantity $\times$ rate mismatches) cannot be hidden behind high scores on clean rows, `overall_confidence` is calculated as the mean of line item confidences scaled by the fraction of lines that are not flagged `low`:

$$\text{Overall Confidence} = \left(\frac{1}{N} \sum_{i=1}^N C_i\right) \times \left(\frac{N_{\text{non-low}}}{N}\right)$$

where $N$ is the total number of line items and $N_{\text{non-low}}$ is the count of line items whose `confidence_flag` is not `low`. If $N = 0$, `overall_confidence` is 0.0.

---

## 7. Explainability & UI Guidelines (Teammate A)

To foster trust among SME clients and non-expert sustainability managers:
1. **Explainability Drawer / Popover:** When clicking `confidence_flag`, display the strings in `reasons` as bullet points.
2. **Missing Field Prompting:** If a reason indicates missing quantity or unit, provide inline edit cells in the React table allowing the user to type in the values directly from the invoice image view.
3. **Audit Trail:** Maintain the original OCR description alongside any user-edited values to ensure compliance auditability.

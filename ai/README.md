# TrueScope AI Extraction & Classification Pipeline

## Overview

The `ai` module forms the ingestion and understanding layer of **TrueScope**. It converts unstructured SME invoice files (PDF documents, scanned PNG/JPG images) into structured, auditable greenhouse gas (GHG) activity records.

The pipeline executes a deterministic, multi-stage workflow:
1. **OCR Extraction (`ai.ocr.extractor`)**: Extracts document text, bounding page count, and word-level recognition confidence scores via Tesseract OCR and `pdf2image`.
2. **Metadata & Line Item Parsing (`ai.parsing.parser`)**: Parses vendor headers, invoice numbers, billing dates (normalized to `YYYY-MM-DD`), currency codes, and candidate itemized billable rows. Never hallucinates or fabricates missing values.
3. **Activity Classification (`ai.classification.classifier`)**: Maps line item descriptions and context keywords to standardized emission activity keys and GHG Protocol Scopes (Scope 1, Scope 2, Scope 3).
4. **Confidence Scoring (`ai.confidence.scorer`)**: Computes a heuristic confidence score ($0.0 \le C \le 1.0$), assigns categorical flags (`high`, `medium`, `low`), and generates human-readable audit reasons explaining data completeness, OCR quality, and domain sanity checks.

The output conforms strictly to the contract documented in [`docs/ai-output-schema.md`](../docs/ai-output-schema.md).

---

## Folder Structure

```
ai/
├── README.md               # Architecture, setup guide, and execution commands
├── requirements.txt        # Pinned Python package dependencies
├── .env.example            # Environment template for local binaries
├── pipeline.py             # End-to-end pipeline runner & CLI entrypoint
├── ocr/
│   ├── __init__.py
│   └── extractor.py        # OCR text & word confidence extraction
├── parsing/
│   ├── __init__.py
│   └── parser.py           # Metadata and line item extraction
├── classification/
│   ├── __init__.py
│   └── classifier.py       # GHG Scope 1/2/3 activity classifier
├── confidence/
│   ├── __init__.py
│   └── scorer.py           # Composite confidence scoring & explanations
└── tests/
    ├── __init__.py
    └── test_pipeline.py    # Offline unit test suite (no external binaries required)
```

---

## Installation & Setup

### 1. Python Virtual Environment

From the project root:

```bash
# Create local virtual environment
python -m venv ai/.venv

# Activate environment (Windows PowerShell)
.\ai\.venv\Scripts\Activate.ps1

# Activate environment (Linux / macOS)
source ai/.venv/bin/activate

# Install dependencies
pip install -r ai/requirements.txt
```

### 2. OCR & PDF Dependencies (Windows Setup)

The pipeline requires two native external binary tools when running OCR on real PDFs and images:

#### A. Tesseract OCR (Windows)
1. Download and run the **UB Mannheim** 64-bit installer from GitHub:  
   [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)  
   (Default installation directory: `C:\Program Files\Tesseract-OCR\tesseract.exe`).
2. Add `C:\Program Files\Tesseract-OCR` to your system `PATH`, **OR** set `TESSERACT_CMD` in `ai/.env`:
   ```env
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

#### B. Poppler for Windows (`pdf2image` requirement)
1. Download the latest Poppler binary release zip (e.g. from `@oschwartz10612` on GitHub):  
   [https://github.com/oschwartz10612/poppler-windows/releases/](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extract the archive (e.g., to `C:\Program Files\poppler` or `C:\poppler`).
3. Add the `Library\bin` or `bin` directory to your system `PATH`, **OR** set `POPPLER_PATH` in `ai/.env`:
   ```env
   POPPLER_PATH=C:\Program Files\poppler\Library\bin
   ```

#### C. Environment Configuration
Copy `ai/.env.example` to `ai/.env`:
```powershell
Copy-Item ai\.env.example ai\.env
```
Populate `TESSERACT_CMD` and `POPPLER_PATH` if binaries are not placed on the system PATH.

---

## Running the Pipeline

Execute the pipeline on an invoice from the project root using the module flag:

```powershell
# From project root:
.\ai\.venv\Scripts\python.exe -m ai.pipeline path/to/invoice.pdf

# Or if the virtual environment is already activated:
python -m ai.pipeline sample-invoices/fuel_delivery.pdf
```

The CLI prints the formatted JSON payload matching `docs/ai-output-schema.md` to standard output.

---

## Running Tests

All unit tests are isolated and do not require Tesseract or Poppler to be installed on the machine:

```powershell
# Run the test suite with verbose output
.\ai\.venv\Scripts\python.exe -m pytest ai/tests/test_pipeline.py -v
```

---

## Category Taxonomy & Emission Engine Synchronization

The classifier keys strictly mirror the database keys maintained by Teammate D (Emission Engine):

| Activity Key | GHG Scope | Target Emission Factor Data |
| :--- | :---: | :--- |
| `stationary_fuel_diesel` | Scope 1 | DEFRA / EPA Stationary Combustion (litres, gallons) |
| `mobile_fuel_petrol` | Scope 1 | DEFRA / EPA Passenger Cars / Vans (litres) |
| `mobile_fuel_diesel` | Scope 1 | DEFRA / EPA Road Fleet / Commercial (litres) |
| `natural_gas` | Scope 1 | Utility Gas Factors (kWh, m3, therms) |
| `electricity_grid` | Scope 2 | Location-based Grid Mix (kWh, MWh) |
| `freight_transport` | Scope 3 | Third-Party Logistics / Freight (tonne.km, kg) |
| `business_travel` | Scope 3 | Air, Rail, Hotel (passenger.km, spend) |
| `purchased_goods` | Scope 3 | Upstream Goods & Consumables (kg, spend) |
| `waste_disposal` | Scope 3 | Commercial Waste Processing (tonnes) |
| `unknown` | null | Requires manual review in UI |

---

## Known Limitations & Roadmap

- **Rule-Based Parsing Baseline**: The current parser extracts standard tabular invoice formats and single-page utility/fuel bills using regex and heuristic layout anchors. Multi-line wrapped tables or unusual column orderings should be reviewed using the confidence score.
- **Spend-Based Fallback**: If invoices lack physical units (e.g. general freight fee or consulting), the pipeline extracts monetary amounts; downstream calculation requires spend-based emission factors (EEIO).
- **Future AWS Textract Adapter**: The extractor architecture is modular (`ai.ocr.extractor.extract`), allowing a drop-in AWS Textract adapter in Phase 2 without changing downstream parser or classifier contracts.

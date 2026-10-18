# TrueScope Backend

FastAPI API for invoice uploads, synchronous AI processing, and in-memory invoice status/results. Uploaded files are limited to 10 MiB and temporarily stored with their original supported extension while processing.

## Setup

From the repository root, create and activate a virtual environment, then install the backend requirements:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements.txt
```

## Start the API

From the repository root:

```powershell
python -m uvicorn backend.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`.

## Run tests

From the repository root:

```powershell
python -m pytest backend/tests -q
```

Invoice records are process-local and are lost when the server restarts. OCR requires the AI dependencies plus working Tesseract and, for PDFs, Poppler binaries as described in `ai/README.md`.

## Deterministic demo records

`POST /api/invoices/demo` accepts a JSON `demo_id`. The fixed IDs are `INV-2024-001` (mock electricity) and `INV-2024-003` (mock natural gas), copied from `frontend/src/data/mockData.js`. They return stable `demo_INV-2024-001` and `demo_INV-2024-003` invoice IDs, are labeled `synthetic_demo`, and do not invoke OCR, the AI pipeline, or the emission engine. Their factor and emission values are predefined frontend mock values, not verified engine calculations.

## Invoice report endpoint

`GET /api/invoices/{invoice_id}/report` returns JSON from the stored invoice result and does not rerun processing. The response contains `invoice_id`, `processing_status`, `source`, invoice metadata, `line_items`, `warnings`, `review_warnings`, and `totals`.

For uploaded invoices, `totals.successful_calculations_by_emissions_unit` groups valid engine emissions by their exact `emissions_basis` and `emissions_unit`; `successful_calculations_by_category` additionally keeps categories separate. `successful_calculation_total.value` is populated only when successful calculations share one basis/unit, and is a subtotal when some lines were skipped. Otherwise it is `null` with a reason. Activity quantities are never combined. Demo reports keep predefined mock emissions separate from engine totals; their successful calculation total is `null`. Missing invoice IDs return 404, while failed or incomplete records return 409 with processing status and any stored error.
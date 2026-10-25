# TrueScope

TrueScope is a demonstration prototype for extracting invoice activity data,
classifying emissions categories, and estimating emissions with a small
emission-factor library.

## Local demonstration setup (Windows PowerShell)

Install the Python dependencies from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt -r ai\requirements.txt
```

Install Node.js, then install the frontend dependencies:

```powershell
Set-Location frontend
npm.cmd ci
```

Real invoice uploads also require Tesseract OCR and Poppler for Windows. Follow
the setup instructions in [ai/README.md](./ai/README.md), and configure
`ai/.env` from [ai/.env.example](./ai/.env.example) when those binaries are
not available on `PATH`.

Open two PowerShell terminals at the repository root. Start the API in the
first:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in the second:

```powershell
Set-Location frontend
npm.cmd run dev
```

Open the frontend URL printed by Vite (normally `http://localhost:5173`).
The API allows the Vite development origins `localhost` and `127.0.0.1` on
ports 5173–5179, so it continues to work if Vite selects an available fallback
port.
The backend health check and interactive API documentation are available at
`http://127.0.0.1:8000/api/health` and `http://127.0.0.1:8000/docs`.
`VITE_API_BASE_URL` can be set in `frontend/.env` to change the API base URL.

## Synthetic upload smoke test

Upload [synthetic-electricity-invoice.png](./sample-invoices/synthetic-electricity-invoice.png)
through the frontend to exercise OCR, extraction, classification, calculation,
review flags, report totals, and CSV export. It is explicitly synthetic, not a
real bill. With the current unverified demo factor it produces 71 kg CO2 (not
CO2e); the CO2e overview excludes that result and the detailed report/export
retains its basis.

## Data and calculation limitations

- The dashboard starts with synthetic frontend mock data. Uploaded invoice
  extraction results and predefined API demo records are stored in
  `database\truescope.sqlite3` and restored by the frontend after reload. Raw
  uploaded files are temporary and deleted after processing. Frontend company
  settings and edits to mock rows remain in memory only.
- Set `TRUESCOPE_DATABASE_PATH` before starting the API to use a different
  SQLite database file. Keep the database local and protected; it may contain
  invoice metadata and extracted line descriptions.
- Uploaded invoice processing is synchronous. Supported formats are PDF, PNG,
  JPG, and JPEG, with a 10 MiB upload limit.
- Emission factors are a limited demonstration library. Its factors are
  unverified and must not be treated as authoritative reporting values. See
  [the factor inventory and evidence audit](./emission-engine/README.md) for
  recorded values, provenance gaps, and evidence required before verification.
  The library's India value is a default only, not a proven geography for each
  factor; an unresolved electricity source-year conflict is not reported as a
  confirmed reference year.
- No paper or stationery factor is provided. Rows with unsupported category and
  unit combinations are left uncalculated and flagged for review; quantities
  such as packs or individual units are not converted to mass.
- A partial emission calculation does not mean invoice extraction failed.
  Review skipped line items and warnings before using calculated subtotals.
- Reports are labeled draft/demo outputs and are not certified regulatory
  disclosures. Dashboard, invoice-summary, and report totals include eligible
  uploaded values labeled as kg CO₂e only; CO₂-only, skipped, failed, or invalid
  rows are retained for review but excluded. Synthetic demo values are displayed
  separately and never added to uploaded totals. The monthly trend chart is
  static synthetic data and does not include uploaded invoices.

## Validation commands

From the repository root:

```powershell
python -m pytest -q
python -m unittest discover -s emission-engine -p "test_engine.py" -v
```

From `frontend`:

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

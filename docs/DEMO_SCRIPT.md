# TrueScope – 3-minute demo script

**Before you start (2 min):** run backend + frontend (see README.md). Open http://localhost:5173. Keep `sample-invoices/` folder open in a file window. Do one dry run, then record a backup video.

**0:00 Hook (20s)** – "Every Indian SME selling to a big buyer now gets asked for a carbon number. They have invoices, not ESG teams. TrueScope turns an invoice into a Scope 1–3 report in seconds."

**0:20 Sample company (30s)** – Overview of *Apex Logistics* (top-right says "Sample company"). Point to Scope 1/2/3 cards, donut, trend. "Everything here is built from invoice line items."

**0:50 Works for any SME (30s)** – Click the company pill → **+ Add your company** → type a name (e.g. "Sahyadri Textiles"), employees, location → **Create & upload invoice**. "Each company gets its own workspace, invoices and report."

**1:20 Live upload (50s)** – Upload `synthetic-electricity-invoice.png`, then `synthetic-messy-invoice.png`. Say: "OCR reads it, the classifier assigns the GHG scope, the engine multiplies activity × factor." Open one row → show factor, unit, confidence.

**2:10 Trust (30s)** – Re-upload the same invoice: "Duplicates are caught, so totals can't be double-counted." Show a flagged line (freight per trip): "We never guess from price; it goes to review."

**2:40 Output (20s)** – Reports → Print/PDF and CSV. "Buyer-ready summary with method and data-quality notes."

**2:55 Close** – "Next: verified CEA/DESNZ factor libraries, ERP/GST integration, supplier portals."

## Likely judge questions
- **Where do factors come from?** GHG Protocol activity×factor method with a pluggable India default library; every line shows factor and source; next step is loading CEA (grid) and DESNZ/IPCC datasets with verification status.
- **Why not a spreadsheet?** Extraction + scope classification + duplicate control + audit trail per line.
- **Accuracy?** Confidence score per line; unsupported units are flagged, never estimated from spend.
- **Multiple businesses?** Company switcher; each has isolated invoices and reports.

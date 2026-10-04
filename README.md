# 🌱 TrueScope

### AI-Powered Carbon Emission Estimation & Reporting for SMEs

TrueScope transforms ordinary business invoices into **structured carbon-emission insights** using OCR, AI-based activity classification, and emission-factor mapping.

Our goal is to make carbon reporting **faster, more accessible, and affordable for SMEs** without requiring dedicated ESG expertise.

---

## 👥 Team

| Member | Role |
|---|---|
| **Jiya Barage** | 🎨 Frontend |
| **Nikhil Bhandarkawathekar** | ⚙️ Backend & Orchestration |
| **Shivvani Bankar** | 🤖 OCR + AI / Classification |
| **Aditya Baviskar** | 🌱 Emission Engine & Validation |

---

## 🔄 Workflow

```text
📄 Invoice Upload
        ↓
🔍 OCR & Data Extraction
        ↓
🤖 Activity Classification
        ↓
🌱 Emission Factor Mapping
        ↓
🧮 CO₂e Calculation
        ↓
📊 Carbon Dashboard
        ↓
📑 Carbon Report


---

## ✨ Key Features

- 📄 **Invoice-to-Carbon Pipeline** — Convert existing invoices into structured emission data.
- 🔍 **AI-Assisted Extraction** — Extract vendor, item, quantity, and unit information from invoices.
- 🧠 **Activity Classification** — Classify activities into relevant Scope 1, Scope 2, or Scope 3 categories.
- 🌱 **Emission Factor Mapping** — Map activities to appropriate emission factors.
- 🧮 **Automated CO₂e Calculation** — Calculate estimated carbon emissions from activity data.
- 🔎 **Explainable Results** — Show how each emission estimate was derived.
- 📊 **Carbon Dashboard** — Visualize total emissions, scope-wise breakdowns, categories, and trends.
- 📑 **Carbon Report** — Generate a structured, shareable carbon report.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 🎨 Frontend | **React** |
| ⚙️ Backend | **FastAPI** |
| 🤖 AI / OCR | **Python + Tesseract / AWS Textract** |
| 🗄️ Database | **PostgreSQL** |
| 📑 PDF Reports | **WeasyPrint** |
| 🌱 Emission Factors | **DEFRA / EPA / GHG Protocol** |

---

## 🏗️ System Architecture

```text
                    ┌──────────────────┐
                    │  Invoice Upload  │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │    OCR + AI      │
                    │    Extraction    │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │    Activity      │
                    │  Classification  │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │ Emission Factor  │
                    │     Mapping      │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │  Carbon Engine   │
                    │ CO₂e Calculation │
                    └────────┬─────────┘
                             ↓
              ┌──────────────┴──────────────┐
              ↓                             ↓
      ┌─────────────────┐           ┌─────────────────┐
      │ Carbon Dashboard│           │  Carbon Report  │
      └─────────────────┘           └─────────────────┘

"""Unit tests for TrueScope AI pipeline.

These tests run without requiring Tesseract OCR binary or Poppler to be installed,
allowing automated CI/CD and offline verification.
"""

from __future__ import annotations

from unittest.mock import patch
import pytest

from ai.classification.classifier import classify
from ai.confidence.scorer import score
from ai.parsing.parser import parse
from ai.pipeline import run


# ---------------------------------------------------------------------------
# Task 5.1: Classifier Tests
# ---------------------------------------------------------------------------

def test_classify_stationary_fuel_diesel():
    item = {"description": "Generator backup red diesel fuel delivery", "unit": "litres"}
    result = classify(item)
    assert result["category"] == "stationary_fuel_diesel"
    assert result["scope"] == 1
    assert result["match_strength"] > 0.7
    assert "diesel" in result["reason"].lower()


def test_classify_mobile_fuel_diesel():
    item = {"description": "Fleet diesel fuel bulk purchase", "unit": "litres"}
    result = classify(item)
    assert result["category"] == "mobile_fuel_diesel"
    assert result["scope"] == 1
    assert result["match_strength"] >= 0.8


def test_classify_mobile_fuel_petrol():
    item = {"description": "Unleaded petrol for company car", "unit": "litres"}
    result = classify(item)
    assert result["category"] == "mobile_fuel_petrol"
    assert result["scope"] == 1
    assert result["match_strength"] > 0.7


def test_classify_natural_gas():
    item = {"description": "Mains natural gas meter consumption", "unit": "kWh"}
    result = classify(item)
    assert result["category"] == "natural_gas"
    assert result["scope"] == 1
    assert result["match_strength"] > 0.7


def test_classify_electricity_grid():
    item = {"description": "Electricity grid power supply charges", "unit": "kWh"}
    result = classify(item)
    assert result["category"] == "electricity_grid"
    assert result["scope"] == 2
    assert result["match_strength"] > 0.7


def test_classify_freight_transport():
    item = {"description": "Overnight courier shipping haulage service", "unit": "kg"}
    result = classify(item)
    assert result["category"] == "freight_transport"
    assert result["scope"] == 3
    assert result["match_strength"] > 0.7


def test_classify_business_travel():
    item = {"description": "London to Manchester business flight ticket", "unit": None}
    result = classify(item)
    assert result["category"] == "business_travel"
    assert result["scope"] == 3
    assert result["match_strength"] > 0.7


def test_classify_waste_disposal():
    item = {"description": "Commercial refuse collection and waste disposal fee", "unit": "tonnes"}
    result = classify(item)
    assert result["category"] == "waste_disposal"
    assert result["scope"] == 3
    assert result["match_strength"] > 0.7


def test_classify_purchased_goods():
    item = {"description": "A4 print paper stationery supplies", "unit": "units"}
    result = classify(item)
    assert result["category"] == "purchased_goods"
    assert result["scope"] == 3
    assert result["match_strength"] > 0.7


def test_classify_unknown():
    item = {"description": "Random miscellaneous consultancy consulting advisory", "unit": "hours"}
    result = classify(item)
    assert result["category"] == "unknown"
    assert result["scope"] is None
    assert result["match_strength"] == 0.0


# ---------------------------------------------------------------------------
# Task 5.2: Scorer Tests (Range, Weights & Flag Thresholds)
# ---------------------------------------------------------------------------

def test_scorer_high_confidence():
    """Complete line item, matching plausible unit, high OCR and strong classification."""
    line_item = {
        "description": "Electricity consumption",
        "quantity": 1500.0,
        "unit": "kWh",
        "amount": 420.50,
    }
    ocr_result = {
        "words": [
            {"text": "electricity", "conf": 0.95},
            {"text": "consumption", "conf": 0.92},
        ]
    }
    classification = {
        "category": "electricity_grid",
        "scope": 2,
        "match_strength": 0.95,
        "reason": "Matched keyword 'electricity'",
    }

    res = score(line_item, ocr_result, classification)
    assert 0.80 <= res["confidence"] <= 1.0
    assert res["confidence_flag"] == "high"
    assert len(res["reasons"]) >= 3


def test_scorer_medium_confidence():
    """Missing physical unit, but spend present with matched category."""
    line_item = {
        "description": "Courier parcel delivery",
        "quantity": None,
        "unit": None,
        "amount": 45.00,
    }
    ocr_result = {
        "words": [
            {"text": "courier", "conf": 0.80},
            {"text": "parcel", "conf": 0.80},
        ]
    }
    classification = {
        "category": "freight_transport",
        "scope": 3,
        "match_strength": 0.80,
        "reason": "Matched courier",
    }

    res = score(line_item, ocr_result, classification)
    assert 0.50 <= res["confidence"] < 0.80
    assert res["confidence_flag"] == "medium"


def test_scorer_low_confidence():
    """Unclassified category with missing fields and poor OCR."""
    line_item = {
        "description": "Misc items",
        "quantity": None,
        "unit": None,
        "amount": None,
    }
    ocr_result = {
        "words": [
            {"text": "misc", "conf": 0.20},
        ]
    }
    classification = {
        "category": "unknown",
        "scope": None,
        "match_strength": 0.0,
        "reason": "Unrecognized activity",
    }

    res = score(line_item, ocr_result, classification)
    assert 0.0 <= res["confidence"] < 0.50
    assert res["confidence_flag"] == "low"


def test_scorer_boundary_clamping():
    """Ensures confidence never exceeds 1.0 or drops below 0.0."""
    line_item = {
        "description": "Test item",
        "quantity": 10.0,
        "unit": "litres",
        "amount": 100.0,
    }
    ocr_result = {"words": [{"text": "test", "conf": 1.0}]}
    classification = {
        "category": "stationary_fuel_diesel",
        "scope": 1,
        "match_strength": 1.0,
        "reason": "Perfect match",
    }
    res = score(line_item, ocr_result, classification)
    assert 0.0 <= res["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Task 5.3: Parser Tests on Hard-Coded OCR Sample Text
# ---------------------------------------------------------------------------

SAMPLE_INVOICE_TEXT = """
Energy Direct UK Ltd
Invoice Date: 2024-04-12
Invoice Number: INV-98231
Currency: GBP

Description                          Quantity   Unit    Amount
Mains Electricity Standard Meter     2500       kWh     625.00
Natural gas heating utility          1200       kWh     180.00
Subtotal:                                               805.00
Total Due:                                              805.00
"""


def test_parser_extracts_metadata_and_line_items():
    ocr_result = {
        "text": SAMPLE_INVOICE_TEXT,
        "words": [],
        "pages": 1,
    }
    parsed = parse(ocr_result)

    assert parsed["vendor"] == "Energy Direct UK Ltd"
    assert parsed["invoice_date"] == "2024-04-12"
    assert parsed["invoice_number"] == "INV-98231"
    assert parsed["currency"] == "GBP"

    items = parsed["line_items"]
    assert len(items) >= 2

    # Verify first item
    first_item = items[0]
    assert "electricity" in first_item["description"].lower()
    assert first_item["quantity"] == 2500.0
    assert first_item["unit"] == "kWh"
    assert first_item["amount"] == 625.00

    # Verify second item
    second_item = items[1]
    assert "natural gas" in second_item["description"].lower()
    assert second_item["quantity"] == 1200.0
    assert second_item["unit"] == "kWh"
    assert second_item["amount"] == 180.00


def test_parser_never_fabricates_missing_fields():
    incomplete_text = "Acme Supplies\nSome unformatted text without any date or reference numbers."
    ocr_result = {"text": incomplete_text, "words": [], "pages": 1}
    parsed = parse(ocr_result)

    assert parsed["vendor"] == "Acme Supplies"
    assert parsed["invoice_date"] is None
    assert parsed["invoice_number"] is None
    assert parsed["currency"] is None


# ---------------------------------------------------------------------------
# Task 5.4: Pipeline Schema Contract Verification (Mocked OCR)
# ---------------------------------------------------------------------------

def test_pipeline_matches_contract_schema(tmp_path):
    # Create a dummy invoice file so path verification succeeds
    dummy_invoice = tmp_path / "test_invoice.png"
    dummy_invoice.write_bytes(b"\x89PNG\r\n\x1a\n")

    mock_ocr = {
        "text": (
            "Apex Logistics Fuel\n"
            "Invoice No: INV-7721\n"
            "Date: 2024-02-20\n"
            "Currency: GBP\n"
            "Ultra Low Sulphur Diesel 1000 litres 1500.00\n"
        ),
        "words": [
            {"text": "diesel", "conf": 0.95},
            {"text": "1000", "conf": 0.90},
            {"text": "litres", "conf": 0.92},
        ],
        "pages": 1,
    }

    with patch("ai.pipeline.extract", return_value=mock_ocr):
        result = run(str(dummy_invoice))

    # Required top-level schema keys
    required_keys = {
        "invoice_id",
        "source_file",
        "vendor",
        "invoice_date",
        "invoice_number",
        "currency",
        "line_items",
        "overall_confidence",
        "warnings",
    }
    assert set(result.keys()) == required_keys

    assert result["source_file"] == "test_invoice.png"
    assert result["vendor"] == "Apex Logistics Fuel"
    assert result["invoice_date"] == "2024-02-20"
    assert result["invoice_number"] == "INV-7721"
    assert result["currency"] == "GBP"
    assert isinstance(result["overall_confidence"], float)
    assert isinstance(result["warnings"], list)
    assert len(result["line_items"]) == 1

    # Verify line item schema keys
    item = result["line_items"][0]
    required_item_keys = {
        "description",
        "quantity",
        "unit",
        "amount",
        "category",
        "scope",
        "confidence",
        "confidence_flag",
        "reasons",
    }
    assert set(item.keys()) == required_item_keys

    assert item["quantity"] == 1000.0
    assert item["unit"] == "litres"
    assert item["amount"] == 1500.00
    assert item["category"] == "stationary_fuel_diesel"
    assert item["scope"] == 1
    assert item["confidence_flag"] in {"high", "medium", "low"}
    assert isinstance(item["reasons"], list)


def test_extractor_file_not_found():
    from ai.ocr.extractor import extract
    with pytest.raises(FileNotFoundError):
        extract("non_existent_file_path_xyz.pdf")


def test_extractor_unsupported_format(tmp_path):
    dummy_txt = tmp_path / "invoice.docx"
    dummy_txt.write_text("dummy text")
    from ai.ocr.extractor import extract
    with pytest.raises(ValueError, match="Unsupported file format"):
        extract(str(dummy_txt))


def test_scorer_unit_mismatch_sanity_penalty():
    line_item = {
        "description": "Diesel fuel",
        "quantity": 100.0,
        "unit": "kWh",  # Inappropriate unit for diesel fuel
        "amount": 250.0,
    }
    ocr_result = {"words": []}
    classification = {
        "category": "stationary_fuel_diesel",
        "scope": 1,
        "match_strength": 0.85,
        "reason": "Matched diesel",
    }
    res = score(line_item, ocr_result, classification)
    assert any("unexpected" in r.lower() or "warning" in r.lower() for r in res["reasons"])


def test_parser_various_date_formats():
    from ai.parsing.parser import extract_date
    assert extract_date("Issued on 2024/05/18 by vendor") == "2024-05-18"
    assert extract_date("Date of invoice: 25/12/2023") == "2023-12-25"
    assert extract_date("Billing date: 14 Oct 2024") == "2024-10-14"
    assert extract_date("No dates here") is None

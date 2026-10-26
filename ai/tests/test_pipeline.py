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
    assert required_item_keys.issubset(set(item.keys()))
    assert set(item.keys()) - required_item_keys <= {"expected_unit"}
    assert item.get("expected_unit") == "litre"

    assert item["quantity"] == 1000.0
    assert item["unit"] in {"litre", "litres"}
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


def test_parser_with_lines_and_rate_mismatch():
    """Verify parsing with structured 'lines' input and qty x rate mismatch detection."""
    mock_lines = [
        {"text": "Mis Patil Enterprises TAX INVOICE", "conf": 0.92},
        {"text": "Shop 3, Market Yard Invoice No: PE-118", "conf": 0.90},
        {"text": "Pune 411037 Date: 07-10-2026", "conf": 0.90},
        {"text": "GSTIN: 27AAAPP999901Z2", "conf": 0.85},
        {"text": "Bill To: Greenleaf Packaging Pvt Ltd", "conf": 0.91},
        {"text": "Description Qty Unit Rate Amount (INR)", "conf": 0.88},
        {"text": "Diesel (bulk) tanker refill 400 Lr 91.80 36,720.00", "conf": 0.85},
        {"text": "Courier / parcel charges 12 Nos 145.00 4,740.00", "conf": 0.89},
        {"text": "Ad paper reams office supplies 40 Nos 235.00 9,400.00", "conf": 0.85},
        {"text": "Waste disposal service « monthly 1 Month 2,800.00 2,800.00", "conf": 0.84},
        {"text": "Taxi hire for client visit 2 Trip 4,350.00. 2,700.00", "conf": 0.92},
        {"text": "Subtotal: 53,360.00", "conf": 0.92},
        {"text": "GST (18%): 9,604.80", "conf": 0.90},
        {"text": "Total: 62,964.80", "conf": 0.91},
    ]
    ocr_result = {
        "text": "\n".join(l["text"] for l in mock_lines),
        "lines": mock_lines,
        "words": [],
        "pages": 1,
    }

    parsed = parse(ocr_result)

    # 1. Vendor is "Patil Enterprises" style (not the whole document)
    assert parsed["vendor"] == "Patil Enterprises"
    assert parsed["invoice_number"] == "PE-118"
    assert parsed["invoice_date"] == "2026-10-07"

    # 2. Assert exactly 5 line items
    items = parsed["line_items"]
    assert len(items) == 5

    # 3. Assert correct quantities, units, and amounts
    # Item 0: Diesel
    assert items[0]["description"] == "Diesel (bulk) tanker refill"
    assert items[0]["quantity"] == 400.0
    assert items[0]["unit"] == "litre"
    assert items[0]["rate"] == 91.80
    assert items[0]["amount"] == 36720.00

    # Item 1: Courier
    assert items[1]["quantity"] == 12.0
    assert items[1]["unit"] == "nos"
    assert items[1]["amount"] == 4740.00

    # Item 2: Ad paper
    assert items[2]["quantity"] == 40.0
    assert items[2]["unit"] == "nos"
    assert items[2]["amount"] == 9400.00

    # Item 3: Waste disposal
    assert items[3]["quantity"] == 1.0
    assert items[3]["unit"] in {"month", "Month"}
    assert items[3]["amount"] == 2800.00

    # Item 4: Taxi hire
    assert items[4]["description"] == "Taxi hire for client visit"
    assert items[4]["quantity"] == 2.0
    assert items[4]["unit"] in {"trip", "Trip"}
    assert items[4]["rate"] == 4350.00
    assert items[4]["amount"] == 2700.00

    # 4. Taxi line triggers mismatch reason (2 * 4,350 != 2,700)
    assert "qty x rate does not match amount" in items[4]["reasons"]

    # 5. Check scorer on the Taxi line lowers score to low (< 0.50) and retains mismatch reason
    class_res = classify(items[4])
    scored = score(items[4], ocr_result, class_res)
    assert "qty x rate does not match amount" in scored["reasons"]
    assert scored["confidence"] < 0.50
    assert scored["confidence_flag"] == "low"

    # Verify Fix 2 description cleanup stripped '«'
    assert items[3]["description"] == "Waste disposal service monthly"


# ---------------------------------------------------------------------------
# Task: Tests for Fix 1, Fix 2, Fix 3
# ---------------------------------------------------------------------------

def test_group_words_into_lines_different_blocks_same_row():
    """Unit-test _group_words_into_lines with words having same vertical position but different order."""
    from ai.ocr.extractor import _group_words_into_lines

    # Mimic Tesseract multi-block output where columns appear in different blocks/order
    # Row 1 (top=100, height=20): Diesel 250 Litre 92.40 23,100.00
    words = [
        {"text": "23,100.00", "conf": 0.95, "top": 102, "left": 450, "height": 20},  # Amount (block 14)
        {"text": "Diesel", "conf": 0.90, "top": 100, "left": 50, "height": 20},       # Desc (block 7)
        {"text": "92.40", "conf": 0.92, "top": 101, "left": 350, "height": 20},       # Rate (block 11)
        {"text": "250", "conf": 0.88, "top": 100, "left": 150, "height": 20},         # Qty (block 7)
        {"text": "Litre", "conf": 0.91, "top": 101, "left": 230, "height": 20},       # Unit (block 9)
        # Row 2 (top=140, height=20): Petrol 60 Litre 104.10 6,246.00
        {"text": "Petrol", "conf": 0.94, "top": 140, "left": 50, "height": 20},
        {"text": "60", "conf": 0.90, "top": 140, "left": 150, "height": 20},
        {"text": "Litre", "conf": 0.92, "top": 141, "left": 230, "height": 20},
        {"text": "104.10", "conf": 0.89, "top": 140, "left": 350, "height": 20},
        {"text": "6,246.00", "conf": 0.93, "top": 141, "left": 450, "height": 20},
    ]

    lines = _group_words_into_lines(words)
    assert len(lines) == 2

    # Row 1 must be correctly sorted horizontally
    assert lines[0]["text"] == "Diesel 250 Litre 92.40 23,100.00"
    assert 0.0 <= lines[0]["conf"] <= 1.0

    # Row 2 must be correctly grouped and ordered
    assert lines[1]["text"] == "Petrol 60 Litre 104.10 6,246.00"


def test_clean_description_strips_junk_preserves_numbers():
    """Unit-test _clean_description for junk symbol stripping and number preservation."""
    from ai.parsing.parser import _clean_description

    assert _clean_description("Waste disposal service « monthly") == "Waste disposal service monthly"
    assert _clean_description(". High Speed Diesel (HSD) for generator 250 ,") == "High Speed Diesel (HSD) for generator 250"
    assert _clean_description("Courier delivery | urgent ~ overnight _") == "Courier delivery urgent overnight"
    assert _clean_description("Freight transport 3.5 tonne truck") == "Freight transport 3.5 tonne truck"


def test_mismatch_penalty_forces_low_confidence():
    """Unit-test that rate mismatch forces confidence < 0.50 ('low') and preserves reason."""
    from ai.confidence.scorer import RATE_MISMATCH_PENALTY

    assert RATE_MISMATCH_PENALTY > 0.0

    line_item = {
        "description": "Taxi hire for client visit",
        "quantity": 2.0,
        "unit": "Trip",
        "rate": 4350.00,
        "amount": 2700.00,  # 2 * 4350 = 8700 != 2700
    }
    ocr_result = {"words": []}
    classification = {
        "category": "business_travel",
        "scope": 3,
        "match_strength": 0.90,
        "reason": "Matched taxi",
    }

    scored = score(line_item, ocr_result, classification)
    assert scored["confidence"] < 0.50
    assert scored["confidence_flag"] == "low"
    assert "qty x rate does not match amount" in scored["reasons"]


def test_overall_confidence_penalizes_low_lines(tmp_path):
    """Test that overall_confidence drops when a line is low due to rate mismatch."""
    dummy_invoice = tmp_path / "invoice.png"
    dummy_invoice.write_bytes(b"\x89PNG\r\n\x1a\n")

    # Mock OCR with 2 items: 1 valid match, 1 arithmetic mismatch
    mock_ocr = {
        "text": (
            "Test Vendor\n"
            "Invoice No: INV-101\n"
            "Date: 2024-03-01\n"
            "Currency: INR\n"
            "Description Qty Unit Rate Amount\n"
            "Diesel fuel 100 Litre 90.00 9000.00\n"
            "Taxi ride 2 Trip 1000.00 500.00\n"
            "Total: 9500.00\n"
        ),
        "lines": [
            {"text": "Test Vendor", "conf": 0.95},
            {"text": "Invoice No: INV-101", "conf": 0.95},
            {"text": "Date: 2024-03-01", "conf": 0.95},
            {"text": "Currency: INR", "conf": 0.95},
            {"text": "Description Qty Unit Rate Amount", "conf": 0.95},
            {"text": "Diesel fuel 100 Litre 90.00 9000.00", "conf": 0.95},
            {"text": "Taxi ride 2 Trip 1000.00 500.00", "conf": 0.95},
            {"text": "Total: 9500.00", "conf": 0.95},
        ],
        "words": [],
        "pages": 1,
    }

    with patch("ai.pipeline.extract", return_value=mock_ocr):
        result = run(str(dummy_invoice))

    assert len(result["line_items"]) == 2
    # Item 1 should be high/medium
    assert result["line_items"][0]["confidence_flag"] in {"high", "medium"}
    # Item 2 has rate mismatch (2 * 1000 != 500), should be low
    assert result["line_items"][1]["confidence_flag"] == "low"

    # overall_confidence should be mean * (1 / 2), significantly lower than clean mean
    item_confs = [it["confidence"] for it in result["line_items"]]
    expected_overall = round((sum(item_confs) / 2) * (1 / 2), 2)
    assert result["overall_confidence"] == expected_overall
    assert result["overall_confidence"] < 0.50


# ---------------------------------------------------------------------------
# Task: Non-emission, Water & Effluent, and Diesel Split Tests
# ---------------------------------------------------------------------------

def test_classify_non_emission_fixed_demand_charges():
    item = {"description": "Fixed demand charges", "unit": "month"}
    res = classify(item)
    assert res["category"] == "non_emission"
    assert res["scope"] is None
    assert "non-emission" in res["reason"].lower()
    assert "no emission factor" in res["reason"].lower()


def test_classify_non_emission_gst():
    item = {"description": "GST (18%)", "unit": None}
    res = classify(item)
    assert res["category"] == "non_emission"
    assert res["scope"] is None
    assert "non-emission" in res["reason"].lower()


def test_classify_diesel_for_company_truck():
    item = {"description": "Diesel for company truck", "unit": "litre"}
    res = classify(item)
    assert res["category"] == "mobile_fuel_diesel"
    assert res["scope"] == 1
    assert res["match_strength"] >= 0.8


def test_classify_diesel_for_generator():
    item = {"description": "Diesel for generator", "unit": "litre"}
    res = classify(item)
    assert res["category"] == "stationary_fuel_diesel"
    assert res["scope"] == 1
    assert res["match_strength"] >= 0.8


def test_classify_water_supply_charges_m3():
    item = {"description": "Water supply charges m3", "unit": "m3"}
    res = classify(item)
    assert res["category"] == "water_effluent"
    assert res["scope"] == 3
    assert res["match_strength"] >= 0.8


def test_classify_unclassifiable_description_returns_unknown():
    item = {"description": "Xyzzy unclassifiable quantum widget consulting", "unit": "nos"}
    res = classify(item)
    assert res["category"] == "unknown"
    assert res["scope"] is None
    assert res["match_strength"] == 0.0


def test_scorer_non_emission_high_confidence():
    line_item = {
        "description": "Fixed demand charges",
        "quantity": 1.0,
        "unit": "month",
        "amount": 3200.0,
    }
    ocr_result = {
        "words": [
            {"text": "Fixed", "conf": 0.95},
            {"text": "demand", "conf": 0.95},
            {"text": "charges", "conf": 0.95},
        ]
    }
    classification = classify(line_item)
    scored = score(line_item, ocr_result, classification)
    assert scored["confidence"] >= 0.80
    assert scored["confidence_flag"] == "high"
    assert any("no emission calculation" in r.lower() for r in scored["reasons"])


def test_scorer_emission_category_differing_unit_warning_not_heavily_penalized():
    line_item = {
        "description": "Freight transport Pune to Mumbai",
        "quantity": 1.0,
        "unit": "trip",
        "amount": 8500.0,
    }
    ocr_result = {"words": [{"text": "freight", "conf": 0.95}]}
    classification = classify(line_item)
    scored = score(line_item, ocr_result, classification)
    # Freight transport expects tonne-km, line has trip: should not penalize heavily (remains high)
    assert scored["confidence"] >= 0.80
    assert scored["confidence_flag"] == "high"
    assert any("differs from the emission engine's expected unit 'tonne-km'" in r for r in scored["reasons"])

def test_parser_label_based_invoice_format():
    invoice_text = """
TAX INVOICE

Invoice Number: TEST-001
Invoice Date: 22 October 2026

Seller: Demo Supplies Pvt. Ltd.
Buyer: TrustScope Demo Company

Item 1: Office paper
Quantity: 10 packs
Unit Price: Rs. 100
Amount: Rs. 1,000

Item 2: Purchased electricity
Quantity: 100 kWh
Unit Price: Rs. 8
Amount: Rs. 800

Item 3: Office stationery
Quantity: 5 units
Unit Price: Rs. 50
Amount: Rs. 250

Subtotal: Rs. 2,050
GST (18%): Rs. 369
Total Amount: Rs. 2,419
"""

    parsed = parse({
        "text": invoice_text,
        "words": [],
        "pages": 1,
    })

    assert parsed["invoice_number"] == "TEST-001"
    assert parsed["invoice_date"] == "2026-10-22"
    assert len(parsed["line_items"]) == 3

    items = parsed["line_items"]

    assert "Office paper" in items[0]["description"]
    assert items[0]["quantity"] == 10.0
    assert items[0]["unit"] == "packs"
    assert items[0]["amount"] == 1000.0

    assert "Purchased electricity" in items[1]["description"]
    assert items[1]["quantity"] == 100.0
    assert items[1]["unit"] == "kWh"
    assert items[1]["amount"] == 800.0

    assert "Office stationery" in items[2]["description"]
    assert items[2]["quantity"] == 5.0
    assert items[2]["unit"] == "units"
    assert items[2]["amount"] == 250.0


def test_parser_extracts_vendor_without_seller_label():
    from ai.parsing.parser import extract_vendor

    lines = [
        "TAX INVOICE",
        "Seller: Demo Supplies Pvt. Ltd.",
        "Buyer: TrustScope Demo Company",
    ]

    assert extract_vendor(lines) == "Demo Supplies Pvt. Ltd."


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Total: Rs. 2,419", "INR"),
        ("Currency: INR", "INR"),
        ("Total: ₹2,419", "INR"),
        ("Total: Rs 500", "INR"),
        ("Total: 500 GBP", "GBP"),
        ("Total: $500", "USD"),
    ],
)
def test_parser_extracts_currency_formats(text, expected):
    from ai.parsing.parser import extract_currency

    assert extract_currency(text) == expected


def test_parser_does_not_invent_missing_currency():
    from ai.parsing.parser import extract_currency

    assert extract_currency("Invoice total: 2419") is None


# ---------------------------------------------------------------------------
# Task: Non-Emission Priority & Emission Category Preservation Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("desc", "expected_category"),
    [
        ("Courier service charges", "freight_transport"),
        ("Waste disposal service charges", "waste_disposal"),
        ("Taxi service charges", "business_travel"),
        ("Freight service charges", "freight_transport"),
        ("Freight charges Pune to Mumbai", "freight_transport"),
        ("Electricity consumption charges", "electricity_grid"),
    ],
)
def test_emission_keywords_beat_generic_charges(desc, expected_category):
    """Test 1: Emission lines with generic charge phrasing classify as emission categories."""
    res = classify({"description": desc})
    assert res["category"] == expected_category
    assert res["scope"] is not None
    # Weak non-emission word was ignored, so reason must state priority
    reasons_pool = (res.get("reasons", []) or []) + [res.get("reason", "")]
    assert any("Emission keyword takes priority over generic charge wording" in r for r in reasons_pool)


@pytest.mark.parametrize(
    "desc",
    [
        "Fixed demand charges",
        "Electricity fixed charges",
        "GST 18%",
        "Late payment fee",
        "Rounding off",
        "Service charges",
        "Processing fee",
    ],
)
def test_strong_and_uncontested_weak_non_emission(desc):
    """Test 2: Strong non-emission keywords and generic charges without emission keywords -> non_emission."""
    res = classify({"description": desc})
    assert res["category"] == "non_emission"
    assert res["scope"] is None
    assert "non-emission" in res["reason"].lower()


def test_unrecognized_description_stays_unknown():
    """Test 3: 'Blorp zint widget' -> unknown and never non_emission."""
    res = classify({"description": "Blorp zint widget"})
    assert res["category"] == "unknown"
    assert res["category"] != "non_emission"
    assert res["scope"] is None
    assert res["match_strength"] == 0.0


DOCUMENTED_TAXONOMY = {
    "natural_gas",
    "stationary_fuel_diesel",
    "mobile_fuel_diesel",
    "mobile_fuel_petrol",
    "electricity_grid",
    "freight_transport",
    "business_travel",
    "purchased_goods",
    "waste_disposal",
    "water_effluent",
    "non_emission",
    "unknown",
}

DOCUMENTED_SCOPES = {
    "natural_gas": 1,
    "stationary_fuel_diesel": 1,
    "mobile_fuel_diesel": 1,
    "mobile_fuel_petrol": 1,
    "electricity_grid": 2,
    "freight_transport": 3,
    "business_travel": 3,
    "purchased_goods": 3,
    "waste_disposal": 3,
    "water_effluent": 3,
    "non_emission": None,
    "unknown": None,
}


def test_scope_invariants_for_all_emittable_categories():
    """Test 4: Scope invariants match docs/ai-output-schema.md for every emittable category."""
    from ai.classification.classifier import CLASSIFICATION_RULES

    for cat, config in CLASSIFICATION_RULES.items():
        assert cat in DOCUMENTED_SCOPES, f"Category {cat} missing in DOCUMENTED_SCOPES"
        assert config["scope"] == DOCUMENTED_SCOPES[cat], f"Scope mismatch for {cat}: {config['scope']} != {DOCUMENTED_SCOPES[cat]}"

    # Also check unknown
    res_unknown = classify({"description": "Unrecognized random text xyz 123"})
    assert res_unknown["category"] == "unknown"
    assert res_unknown["scope"] == DOCUMENTED_SCOPES["unknown"]


def test_every_emittable_category_in_documented_taxonomy():
    """Test 5: Every category the classifier can emit is in the documented taxonomy."""
    from ai.classification.classifier import CLASSIFICATION_RULES

    emittable_categories = set(CLASSIFICATION_RULES.keys()) | {"unknown"}
    assert emittable_categories == DOCUMENTED_TAXONOMY


def test_expected_unit_present_on_every_line_item(tmp_path):
    """Test 6: expected_unit is always present (explicit null for non_emission and unknown) and separate from unit."""
    dummy_invoice = tmp_path / "invoice.pdf"
    dummy_invoice.write_bytes(b"%PDF-1.4 dummy")

    mock_ocr = {
        "text": (
            "Test Supplier\n"
            "Invoice No: INV-001\n"
            "Date: 2026-10-01\n"
            "Currency: INR\n"
            "Electricity consumption 500 kWh 10.00 5000.00\n"
            "Fixed demand charges 1 Month 1000.00 1000.00\n"
            "Freight transport Pune to Mumbai 1 Trip 2000.00 2000.00\n"
            "Blorp zint widget 5 Nos 100.00 500.00\n"
        ),
        "lines": [
            {"text": "Test Supplier", "conf": 0.95},
            {"text": "Invoice No: INV-001", "conf": 0.95},
            {"text": "Date: 2026-10-01", "conf": 0.95},
            {"text": "Currency: INR", "conf": 0.95},
            {"text": "Electricity consumption 500 kWh 10.00 5000.00", "conf": 0.95},
            {"text": "Fixed demand charges 1 Month 1000.00 1000.00", "conf": 0.95},
            {"text": "Freight transport Pune to Mumbai 1 Trip 2000.00 2000.00", "conf": 0.95},
            {"text": "Blorp zint widget 5 Nos 100.00 500.00", "conf": 0.95},
        ],
        "words": [],
        "pages": 1,
    }

    with patch("ai.pipeline.extract", return_value=mock_ocr):
        result = run(str(dummy_invoice))

    assert len(result["line_items"]) == 4

    # 1. electricity_grid -> expected_unit is "kWh", unit is "kwh"
    item0 = result["line_items"][0]
    assert item0["category"] == "electricity_grid"
    assert "expected_unit" in item0
    assert item0["expected_unit"] == "kWh"
    assert item0["unit"].lower() == "kwh"

    # 2. non_emission -> expected_unit is None, unit is "month"
    item1 = result["line_items"][1]
    assert item1["category"] == "non_emission"
    assert "expected_unit" in item1
    assert item1["expected_unit"] is None
    assert item1["unit"].lower() == "month"

    # 3. freight_transport -> expected_unit is "tonne-km", unit is "trip" (separate)
    item2 = result["line_items"][2]
    assert item2["category"] == "freight_transport"
    assert "expected_unit" in item2
    assert item2["expected_unit"] == "tonne-km"
    assert item2["unit"].lower() == "trip"
    assert item2["expected_unit"] != item2["unit"]

    # 4. unknown -> expected_unit is None, unit is "nos"
    item3 = result["line_items"][3]
    assert item3["category"] == "unknown"
    assert "expected_unit" in item3
    assert item3["expected_unit"] is None
    assert item3["unit"].lower() == "nos"


def validate_output(output: dict) -> None:
    """Test helper to validate pipeline output schema and domain invariants."""
    # Top-level required keys and types
    required_top = {
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
    assert required_top.issubset(set(output.keys())), f"Missing keys: {required_top - set(output.keys())}"
    assert isinstance(output["invoice_id"], str)
    assert isinstance(output["source_file"], str)
    assert output["vendor"] is None or isinstance(output["vendor"], str)
    assert output["invoice_date"] is None or isinstance(output["invoice_date"], str)
    assert output["invoice_number"] is None or isinstance(output["invoice_number"], str)
    assert output["currency"] is None or isinstance(output["currency"], str)
    assert isinstance(output["line_items"], list)
    assert isinstance(output["overall_confidence"], (int, float))
    assert 0.0 <= output["overall_confidence"] <= 1.0
    assert isinstance(output["warnings"], list)
    assert all(isinstance(w, str) for w in output["warnings"])

    # Line item required keys and invariants
    required_line_keys = {
        "description",
        "quantity",
        "unit",
        "amount",
        "category",
        "scope",
        "confidence",
        "confidence_flag",
        "reasons",
        "expected_unit",
    }
    for idx, item in enumerate(output["line_items"]):
        assert required_line_keys.issubset(set(item.keys())), f"Line {idx} missing: {required_line_keys - set(item.keys())}"
        assert isinstance(item["description"], str)
        assert item["quantity"] is None or isinstance(item["quantity"], (int, float))
        assert item["unit"] is None or isinstance(item["unit"], str)
        assert item["amount"] is None or isinstance(item["amount"], (int, float))
        assert item["category"] in DOCUMENTED_TAXONOMY, f"Line {idx} invalid category: {item['category']}"
        assert item["scope"] in {1, 2, 3, None}, f"Line {idx} invalid scope: {item['scope']}"
        assert item["scope"] == DOCUMENTED_SCOPES[item["category"]]
        assert isinstance(item["confidence"], (int, float))
        assert 0.0 <= item["confidence"] <= 1.0, f"Line {idx} confidence out of range: {item['confidence']}"
        assert item["confidence_flag"] in {"high", "medium", "low"}

        # confidence_flag thresholds: high >= 0.80, medium 0.50-0.79, low < 0.50
        conf = item["confidence"]
        flag = item["confidence_flag"]
        if conf >= 0.80:
            assert flag == "high", f"Expected high for {conf}, got {flag}"
        elif conf >= 0.50:
            assert flag == "medium", f"Expected medium for {conf}, got {flag}"
        else:
            assert flag == "low", f"Expected low for {conf}, got {flag}"

        assert isinstance(item["reasons"], list)
        assert all(isinstance(r, str) for r in item["reasons"])
        assert "expected_unit" in item
        if item["category"] in {"non_emission", "unknown"}:
            assert item["expected_unit"] is None
        else:
            from ai.confidence.scorer import EXPECTED_UNITS_BY_CATEGORY
            assert item["expected_unit"] == EXPECTED_UNITS_BY_CATEGORY[item["category"]]


def test_validate_output_on_mocked_sample_invoices(tmp_path):
    """Test 7: Run validate_output() on pipeline output built from mocked OCR text for the 3 sample invoices."""
    mock_ocr_01 = {
        "text": (
            "Shree Ganesh Fuels & Logistics TAX INVOICE\n"
            "Plot 14, MIDC Bhosari Invoice No: SGF/2026/0457\n"
            "Pune, Maharashtra 411026 Date: 03-10-2026\n"
            "GSTIN: 27ABCDE1234F1Z5\n"
            "Bill To:\n"
            "Greenleaf Packaging Pvt Ltd\n"
            "Sector 7, Chakan, Pune 410501\n"
            "Description Qty Unit Rate Amount (INR)\n"
            "High Speed Diesel (HSD) for generator 250 Litre 92.40 23,100.00\n"
            "Petrol - company vehicle 60 Litre 104.10 6,246.00\n"
            "Freight transport Pune to Mumbai 1 Trip 8,500.00 8,500.00\n"
            "Subtotal: 37,846.00\n"
            "GST (18%): 6,812.28\n"
            "Total: 44,658.28\n"
        ),
        "lines": [
            {"text": "Shree Ganesh Fuels & Logistics TAX INVOICE", "conf": 0.95},
            {"text": "Plot 14, MIDC Bhosari Invoice No: SGF/2026/0457", "conf": 0.93},
            {"text": "Pune, Maharashtra 411026 Date: 03-10-2026", "conf": 0.96},
            {"text": "GSTIN: 27ABCDE1234F1Z5", "conf": 0.84},
            {"text": "Bill To:", "conf": 0.96},
            {"text": "Greenleaf Packaging Pvt Ltd", "conf": 0.96},
            {"text": "Sector 7, Chakan, Pune 410501", "conf": 0.94},
            {"text": "Description Qty Unit Rate Amount (INR)", "conf": 0.96},
            {"text": "High Speed Diesel (HSD) for generator 250 Litre 92.40 23,100.00", "conf": 0.95},
            {"text": "Petrol - company vehicle 60 Litre 104.10 6,246.00", "conf": 0.95},
            {"text": "Freight transport Pune to Mumbai 1 Trip 8,500.00 8,500.00", "conf": 0.96},
            {"text": "Subtotal: 37,846.00", "conf": 0.96},
            {"text": "GST (18%): 6,812.28", "conf": 0.96},
            {"text": "Total: 44,658.28", "conf": 0.96},
        ],
        "words": [],
        "pages": 1,
    }

    mock_ocr_02 = {
        "text": (
            "Western Maharashtra Power Distribution Co. TAX INVOICE\n"
            "Rasta Peth Division Office Invoice No: ELEC/PN/10/883921\n"
            "Pune, Maharashtra 411011 Date: 05-10-2026\n"
            "GSTIN: 27PQRSX5678L1ZK\n"
            "Bill To:\n"
            "Greenleaf Packaging Pvt Ltd\n"
            "Sector 7, Chakan, Pune 410501\n"
            "Description Qty Unit Rate Amount (INR)\n"
            "Electricity consumption - industrial LT 4820 kWh 9.35 45,067.00\n"
            "Fixed demand charges 1 Month 3,200.00 3,200.00\n"
            "Subtotal: 48,267.00\n"
            "GST (18%): 8,688.06\n"
            "Total: 56,955.06\n"
        ),
        "lines": [
            {"text": "Western Maharashtra Power Distribution Co. TAX INVOICE", "conf": 0.96},
            {"text": "Rasta Peth Division Office Invoice No: ELEC/PN/10/883921", "conf": 0.94},
            {"text": "Pune, Maharashtra 411011 Date: 05-10-2026", "conf": 0.96},
            {"text": "GSTIN: 27PQRSX5678L1ZK", "conf": 0.91},
            {"text": "Bill To:", "conf": 0.96},
            {"text": "Greenleaf Packaging Pvt Ltd", "conf": 0.96},
            {"text": "Sector 7, Chakan, Pune 410501", "conf": 0.94},
            {"text": "Description Qty Unit Rate Amount (INR)", "conf": 0.96},
            {"text": "Electricity consumption - industrial LT 4820 kWh 9.35 45,067.00", "conf": 0.95},
            {"text": "Fixed demand charges 1 Month 3,200.00 3,200.00", "conf": 0.95},
            {"text": "Subtotal: 48,267.00", "conf": 0.96},
            {"text": "GST (18%): 8,688.06", "conf": 0.95},
            {"text": "Total: 56,955.06", "conf": 0.96},
        ],
        "words": [],
        "pages": 1,
    }

    mock_ocr_03 = {
        "text": (
            "Ms Patil Enterprises TAX INVOICE\n"
            "Shop 3, Market Yard Invoice No: PE-118\n"
            "Pune 411037 Date: 07-10-2026\n"
            "GSTIN: 27AAAPP99990122\n"
            "Bill To:\n"
            "Greenleaf Packaging Pvt ud\n"
            "Chakan, Pune\n"
            "Description Qty Unit Rate Amount (INR)\n"
            "Diesel (bulk) tanker refill 400 Lr 91.80 36,720.00\n"
            "Courier / parcel charges 12 Nos 145.00 4,740.00\n"
            "Ad paper reams office supplies 40 Nos 235.00 9,400.00\n"
            "Waste disposal service monthly 1 Month 2,800.00 2,800.00\n"
            "Taxi hire for client visit 2 Trip 4,350.00. 2,700.00\n"
            "Subtotal: 53,360.00\n"
            "GST (18%): 9,604.80\n"
            "Total: 62,964.80\n"
        ),
        "lines": [
            {"text": "Ms Patil Enterprises TAX INVOICE", "conf": 0.92},
            {"text": "Shop 3, Market Yard Invoice No: PE-118", "conf": 0.89},
            {"text": "Pune 411037 Date: 07-10-2026", "conf": 0.90},
            {"text": "GSTIN: 27AAAPP99990122", "conf": 0.59},
            {"text": "Bill To:", "conf": 0.88},
            {"text": "Greenleaf Packaging Pvt ud", "conf": 0.82},
            {"text": "Chakan, Pune", "conf": 0.94},
            {"text": "Description Qty Unit Rate Amount (INR)", "conf": 0.83},
            {"text": "Diesel (bulk) tanker refill 400 Lr 91.80 36,720.00", "conf": 0.85},
            {"text": "Courier / parcel charges 12 Nos 145.00 4,740.00", "conf": 0.89},
            {"text": "Ad paper reams office supplies 40 Nos 235.00 9,400.00", "conf": 0.85},
            {"text": "Waste disposal service monthly 1 Month 2,800.00 2,800.00", "conf": 0.84},
            {"text": "Taxi hire for client visit 2 Trip 4,350.00. 2,700.00", "conf": 0.83},
            {"text": "Subtotal: 53,360.00", "conf": 0.92},
            {"text": "GST (18%): 9,604.80", "conf": 0.94},
            {"text": "Total: 62,964.80", "conf": 0.95},
        ],
        "words": [],
        "pages": 1,
    }

    dummy_f1 = tmp_path / "invoice_01.pdf"
    dummy_f1.write_bytes(b"%PDF-1.4 dummy")
    dummy_f2 = tmp_path / "invoice_02.pdf"
    dummy_f2.write_bytes(b"%PDF-1.4 dummy")
    dummy_f3 = tmp_path / "invoice_03.jpg"
    dummy_f3.write_bytes(b"\xff\xd8\xff dummy")

    with patch("ai.pipeline.extract", return_value=mock_ocr_01):
        res1 = run(str(dummy_f1))
        validate_output(res1)
        assert len(res1["line_items"]) == 3

    with patch("ai.pipeline.extract", return_value=mock_ocr_02):
        res2 = run(str(dummy_f2))
        validate_output(res2)
        assert len(res2["line_items"]) == 2

    with patch("ai.pipeline.extract", return_value=mock_ocr_03):
        res3 = run(str(dummy_f3))
        validate_output(res3)
        assert len(res3["line_items"]) == 5

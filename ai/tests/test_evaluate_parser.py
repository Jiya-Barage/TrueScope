import json

from ai import evaluate_parser


def test_evaluation_reports_missing_and_extra_items_without_inflating_metrics(
    monkeypatch, tmp_path
):
    labels = {
        "labeling_note": "Synthetic test labels only.",
        "invoices": [
            {
                "file": "demo.png",
                "vendor": "Demo Vendor",
                "invoice_date": "2026-10-01",
                "invoice_number": "DEMO-1",
                "currency": "INR",
                "line_items": [
                    {
                        "description": "Expected item",
                        "quantity": 1,
                        "unit": "kg",
                        "rate": 2,
                        "amount": 2,
                    },
                    {
                        "description": "Missing item",
                        "quantity": 3,
                        "unit": "litre",
                        "rate": 4,
                        "amount": 12,
                    },
                ],
            }
        ],
    }
    labels_path = tmp_path / "ground_truth.json"
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    monkeypatch.setattr(evaluate_parser, "GROUND_TRUTH_PATH", labels_path)
    monkeypatch.setattr(
        evaluate_parser,
        "REPOSITORY_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(evaluate_parser, "extract", lambda path: {"text": ""})
    monkeypatch.setattr(
        evaluate_parser,
        "parse",
        lambda ocr: {
            "vendor": "Demo Vendor",
            "invoice_date": "2026-10-01",
            "invoice_number": "DEMO-1",
            "currency": "INR",
            "line_items": [
                {
                    "description": "Expected item",
                    "quantity": 1,
                    "unit": "kg",
                    "rate": 2,
                    "amount": 2,
                },
                {
                    "description": "Extra item",
                    "quantity": 9,
                    "unit": "each",
                    "rate": 8,
                    "amount": 72,
                },
            ],
        },
    )

    result = evaluate_parser.evaluate_parser()

    assert "1 synthetic invoice and 2 labelled line items" in result[
        "evaluation_warning"
    ]
    assert "not a real-world accuracy estimate" in result["evaluation_warning"]
    assert result["field_exact_match"]["matched"] == 9
    assert result["field_exact_match"]["total"] == 19
    assert result["line_item_exact_match_recall"] == {
        "matched": 1,
        "expected": 2,
        "rate": 0.5,
    }
    assert result["missing_line_items"] == [
        {"file": "demo.png", "index": 1, "description": "Missing item"}
    ]
    assert result["extra_extracted_items"] == {
        "count": 1,
        "items": [{"file": "demo.png", "index": 1, "description": "Extra item"}],
    }


def test_missing_parsed_fields_count_as_field_misses(monkeypatch, tmp_path):
    labels = {
        "labeling_note": "Synthetic test labels only.",
        "invoices": [
            {
                "file": "demo.png",
                "vendor": "Demo Vendor",
                "invoice_date": "2026-10-01",
                "invoice_number": "DEMO-1",
                "currency": "INR",
                "line_items": [],
            }
        ],
    }
    labels_path = tmp_path / "ground_truth.json"
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    monkeypatch.setattr(evaluate_parser, "GROUND_TRUTH_PATH", labels_path)
    monkeypatch.setattr(evaluate_parser, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(evaluate_parser, "extract", lambda path: {"text": ""})
    monkeypatch.setattr(
        evaluate_parser,
        "parse",
        lambda ocr: {
            "invoice_date": "2026-10-01",
            "invoice_number": "DEMO-1",
            "currency": "INR",
            "line_items": [],
        },
    )

    result = evaluate_parser.evaluate_parser()

    assert result["field_exact_match"]["matched"] == 3
    assert result["field_exact_match"]["total"] == 4

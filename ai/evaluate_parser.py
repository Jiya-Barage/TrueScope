"""Measure parser extraction against labels for the synthetic demo invoices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai.ocr.extractor import extract
from ai.parsing.parser import parse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = REPOSITORY_ROOT / "sample-invoices" / "ground_truth.json"
INVOICE_FIELDS = ("vendor", "invoice_date", "invoice_number", "currency")
ITEM_FIELDS = ("description", "quantity", "unit", "rate", "amount")


def evaluate_parser() -> dict[str, Any]:
    labels = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    records = labels.get("invoices")
    if not isinstance(records, list) or not records:
        raise ValueError("Ground-truth labels must contain a non-empty invoices list.")

    expected_item_count = 0
    matched_fields = 0
    total_fields = 0
    exact_items = 0
    missing_items = []
    extra_items = []
    per_invoice = []

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each ground-truth invoice must be an object.")
        for field in (*INVOICE_FIELDS, "line_items", "file"):
            if field not in record:
                raise ValueError(
                    f"Ground-truth invoice is missing required field '{field}'."
                )

        invoice_path = REPOSITORY_ROOT / "sample-invoices" / record["file"]
        parsed = parse(extract(str(invoice_path)))
        if not isinstance(parsed, dict):
            raise ValueError("Parser output must be an object.")
        invoice_field_matches = sum(
            field in parsed and parsed[field] == record[field]
            for field in INVOICE_FIELDS
        )
        matched_fields += invoice_field_matches
        total_fields += len(INVOICE_FIELDS)

        expected = record["line_items"]
        actual = parsed.get("line_items", [])
        if not isinstance(expected, list) or not isinstance(actual, list):
            raise ValueError("Ground-truth and parsed line items must be lists.")
        expected_item_count += len(expected)
        unmatched_actual = list(enumerate(actual))
        invoice_exact_items = 0
        invoice_missing_items = []

        for index, expected_item in enumerate(expected):
            if not isinstance(expected_item, dict):
                raise ValueError("Each ground-truth line item must be an object.")
            actual_item = actual[index] if index < len(actual) else {}
            for field in ITEM_FIELDS:
                if field not in expected_item:
                    raise ValueError(
                        "Ground-truth line item is missing required field "
                        f"'{field}'."
                    )

            matched_fields += sum(
                isinstance(actual_item, dict)
                and field in actual_item
                and actual_item[field] == expected_item[field]
                for field in ITEM_FIELDS
            )
            total_fields += len(ITEM_FIELDS)

            matching_actual = next(
                (
                    actual_index
                    for actual_index, candidate in unmatched_actual
                    if isinstance(candidate, dict)
                    and all(
                        field in candidate
                        and candidate[field] == expected_item[field]
                        for field in ITEM_FIELDS
                    )
                ),
                None,
            )
            if matching_actual is None:
                missing_item = {
                    "file": record["file"],
                    "index": index,
                    "description": expected_item["description"],
                }
                missing_items.append(missing_item)
                invoice_missing_items.append(missing_item)
            else:
                invoice_exact_items += 1
                unmatched_actual = [
                    (actual_index, candidate)
                    for actual_index, candidate in unmatched_actual
                    if actual_index != matching_actual
                ]

        invoice_extra_items = [
            {
                "file": record["file"],
                "index": index,
                "description": (
                    item.get("description")
                    if isinstance(item, dict)
                    else None
                ),
            }
            for index, item in unmatched_actual
        ]
        extra_items.extend(invoice_extra_items)
        total_fields += len(ITEM_FIELDS) * len(invoice_extra_items)
        exact_items += invoice_exact_items
        per_invoice.append(
            {
                "file": record["file"],
                "metadata_exact_matches": invoice_field_matches,
                "metadata_fields": len(INVOICE_FIELDS),
                "items_exact_matches": invoice_exact_items,
                "expected_items": len(expected),
                "actual_items": len(actual),
                "missing_items": len(invoice_missing_items),
                "extra_items": len(invoice_extra_items),
            }
        )

    labeling_note = labels.get("labeling_note")
    synthetic = (
        isinstance(labeling_note, str)
        and "synthetic" in labeling_note.casefold()
    )
    dataset_kind = "synthetic " if synthetic else ""
    invoice_label = "invoice" if len(records) == 1 else "invoices"

    return {
        "dataset_size": len(records),
        "expected_line_items": expected_item_count,
        "evaluation_warning": (
            f"This evaluation uses only {len(records)} {dataset_kind}{invoice_label} "
            f"and {expected_item_count} labelled line items; results are not a "
            "real-world accuracy estimate."
        ),
        "field_exact_match": {
            "matched": matched_fields,
            "total": total_fields,
            "rate": matched_fields / total_fields if total_fields else 0.0,
            "comparison": (
                "Invoice fields and line-item fields are compared by row "
                "position; missing values and extra item fields count as misses."
            ),
        },
        "line_item_exact_match_recall": {
            "matched": exact_items,
            "expected": expected_item_count,
            "rate": (
                exact_items / expected_item_count
                if expected_item_count
                else 0.0
            ),
        },
        "missing_line_items": missing_items,
        "extra_extracted_items": {
            "count": len(extra_items),
            "items": extra_items,
        },
        "invoices": per_invoice,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_parser(), indent=2))

"""End-to-end AI pipeline for TrueScope.

Orchestrates invoice ingestion, OCR extraction, metadata parsing, activity classification,
and confidence scoring, producing a standardized JSON output conforming to docs/ai-output-schema.md.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai.classification.classifier import classify
from ai.confidence.scorer import score
from ai.ocr.extractor import extract
from ai.parsing.parser import parse


def run(path: str, invoice_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute the end-to-end TrueScope AI pipeline on an invoice document.

    Chains OCR extraction -> metadata/item parsing -> activity classification -> confidence scoring.

    Args:
        path: Path to the invoice document (PDF, PNG, JPG, JPEG).
        invoice_id: Optional custom invoice ID string. If not provided, a UUID is generated.

    Returns:
        Structured dictionary matching the schema contract in docs/ai-output-schema.md.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If file format is unsupported.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Invoice file not found: {path}")

    assigned_id = invoice_id or f"inv_{uuid.uuid4().hex[:12]}"
    source_filename = file_path.name

    # Step 1: Optical Character Recognition
    ocr_result = extract(str(file_path))

    # Step 2: Parsing metadata and candidate line items
    parsed_meta = parse(ocr_result)

    # Step 3 & 4: Classification and Confidence Scoring for each line item
    processed_line_items: List[Dict[str, Any]] = []
    warnings: List[str] = list(parsed_meta.get("warnings", []))

    if parsed_meta.get("vendor") is None:
        warnings.append("Vendor name could not be confidently identified.")

    if parsed_meta.get("invoice_date") is None:
        warnings.append("Invoice date could not be detected; please verify accounting period.")

    for idx, item in enumerate(parsed_meta.get("line_items", []), start=1):
        class_res = classify(item)
        score_res = score(item, ocr_result, class_res)

        processed_item = {
            "description": item["description"],
            "quantity": item["quantity"],
            "unit": item["unit"],
            "amount": item["amount"],
            "category": class_res["category"],
            "scope": class_res["scope"],
            "confidence": score_res["confidence"],
            "confidence_flag": score_res["confidence_flag"],
            "reasons": score_res["reasons"],
        }
        processed_line_items.append(processed_item)

        # Flag specific issues as warnings
        if class_res["category"] == "unknown":
            warnings.append(f"Line {idx} ('{item['description'][:30]}...'): Unclassified activity requiring manual review.")
        elif item["quantity"] is None or item["unit"] is None:
            warnings.append(
                f"Line {idx}: Missing physical quantity/unit; Emission Engine may require spend-based estimation."
            )

    if not processed_line_items:
        warnings.append("No line items could be parsed from the invoice text.")
        overall_conf = 0.0
    else:
        # Compute overall confidence as the mean of line confidences scaled by the
        # fraction of lines that are not 'low'. This prevents low-confidence or
        # erroneous rows (e.g. rate mismatches) from being obscured by high-confidence rows.
        # Formula: round(mean(line_confs) * (non_low_lines / total_lines), 2)
        mean_conf = sum(item["confidence"] for item in processed_line_items) / len(processed_line_items)
        non_low_lines = sum(1 for item in processed_line_items if item["confidence_flag"] != "low")
        overall_conf = round(mean_conf * (non_low_lines / len(processed_line_items)), 2)

    return {
        "invoice_id": assigned_id,
        "source_file": source_filename,
        "vendor": parsed_meta.get("vendor"),
        "invoice_date": parsed_meta.get("invoice_date"),
        "invoice_number": parsed_meta.get("invoice_number"),
        "currency": parsed_meta.get("currency"),
        "line_items": processed_line_items,
        "overall_confidence": overall_conf,
        "warnings": warnings,
    }


def main() -> None:
    """CLI entrypoint for executing pipeline on a local invoice."""
    if len(sys.argv) < 2:
        print("Usage: python -m ai.pipeline <path_to_invoice>", file=sys.stderr)
        print("Supported formats: .pdf, .png, .jpg, .jpeg", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    try:
        result = run(input_file)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"Error executing pipeline: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

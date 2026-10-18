"""Confidence scoring module for TrueScope.

Calculates heuristic data quality confidence scores and human-readable explanation
strings for invoice line items by combining OCR fidelity, field completeness,
classification match strength, and domain-specific sanity checks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

# Weights for composite confidence calculation (Must sum to 1.0)
SCORING_WEIGHTS: Dict[str, float] = {
    "ocr": 0.25,
    "completeness": 0.30,
    "match_strength": 0.30,
    "sanity": 0.15,
}

# Thresholds for categorical flags
FLAG_THRESHOLDS = {
    "high": 0.80,
    "medium": 0.50,
}

# Domain mapping of expected plausible units per category
PLAUSIBLE_UNITS_BY_CATEGORY: Dict[str, Set[str]] = {
    "stationary_fuel_diesel": {"litres", "gallons", "l", "gal"},
    "mobile_fuel_diesel": {"litres", "gallons", "l", "gal"},
    "mobile_fuel_petrol": {"litres", "gallons", "l", "gal"},
    "natural_gas": {"kwh", "m3", "therms"},
    "electricity_grid": {"kwh", "mwh", "units"},
    "freight_transport": {"tonne.km", "km", "miles", "tonnes", "kg"},
    "business_travel": {"km", "miles", "passenger.km"},
    "purchased_goods": {"kg", "units", "tonnes", "items"},
    "waste_disposal": {"tonnes", "kg", "litres", "m3"},
}


def _calculate_ocr_score(
    line_item: Dict[str, Any], ocr_result: Dict[str, Any]
) -> tuple[float, Optional[str]]:
    """Compute average OCR confidence for words in the line item.

    Args:
        line_item: Extracted line item dict.
        ocr_result: Full OCR extraction result containing 'words'.

    Returns:
        Tuple of (ocr_score between 0.0 and 1.0, explanation string).
    """
    words = ocr_result.get("words", [])
    if not words:
        # Default neutral baseline if OCR word data is not present (e.g. mocked input)
        return 0.85, "Baseline OCR word confidence assumed"

    desc = line_item.get("description", "")
    desc_tokens = set(re.findall(r"\w+", desc.lower()))

    matching_confs = [
        w["conf"]
        for w in words
        if w.get("text", "").lower() in desc_tokens and isinstance(w.get("conf"), (int, float))
    ]

    if matching_confs:
        avg_conf = sum(matching_confs) / len(matching_confs)
        score = max(0.0, min(1.0, avg_conf))
        return score, f"OCR word recognition quality is {int(score * 100)}%"

    # Fallback to overall OCR average if individual words were not mapped
    all_confs = [w["conf"] for w in words if isinstance(w.get("conf"), (int, float))]
    if all_confs:
        avg_all = sum(all_confs) / len(all_confs)
        score = max(0.0, min(1.0, avg_all))
        return score, f"Document average OCR confidence is {int(score * 100)}%"

    return 0.70, "OCR confidence not recorded"


def _calculate_completeness(line_item: Dict[str, Any]) -> tuple[float, List[str]]:
    """Check completeness of essential fields (description, quantity, unit, amount).

    Args:
        line_item: Extracted line item dict.

    Returns:
        Tuple of (completeness score 0.0 to 1.0, list of notes).
    """
    points = 0.0
    notes = []

    # 1. Description (0.25)
    desc = line_item.get("description")
    if desc and str(desc).strip():
        points += 0.25
    else:
        notes.append("Missing item description")

    # 2. Quantity (0.25)
    qty = line_item.get("quantity")
    if qty is not None:
        points += 0.25
    else:
        notes.append("Missing activity quantity")

    # 3. Unit (0.25)
    unit = line_item.get("unit")
    if unit is not None and str(unit).strip():
        points += 0.25
    else:
        notes.append("Missing measurement unit")

    # 4. Monetary Amount (0.25)
    amt = line_item.get("amount")
    if amt is not None:
        points += 0.25
    else:
        notes.append("Missing financial amount")

    if points == 1.0:
        notes.append("All line item fields (description, quantity, unit, amount) present")

    return points, notes


def _calculate_sanity(
    line_item: Dict[str, Any], classification: Dict[str, Any]
) -> tuple[float, str]:
    """Verify if the measurement unit is physically plausible for the activity category.

    Args:
        line_item: Extracted line item dict.
        classification: Classification dict with 'category'.

    Returns:
        Tuple of (sanity score 0.0 to 1.0, explanation string).
    """
    category = classification.get("category", "unknown")
    unit = (line_item.get("unit") or "").lower()

    if category == "unknown":
        return 0.30, "Unclassified category; unable to verify physical units"

    plausible = PLAUSIBLE_UNITS_BY_CATEGORY.get(category)
    if not plausible:
        return 0.70, f"No unit restrictions defined for {category}"

    if not unit:
        return 0.50, f"No unit provided; spend-based emission calculation may be needed for {category}"

    if unit in plausible:
        return 1.0, f"Unit '{unit}' is physically plausible for {category}"

    return 0.10, f"Warning: Unit '{unit}' is unexpected for activity category '{category}'"


def score(
    line_item: Dict[str, Any],
    ocr_result: Dict[str, Any],
    classification: Dict[str, Any],
) -> Dict[str, Any]:
    """Calculate composite confidence score, categorical flag, and reasons.

    Args:
        line_item: Line item dictionary (description, quantity, unit, amount).
        ocr_result: Raw OCR output dictionary (text, words, pages).
        classification: Output of classifier (category, scope, match_strength, reason).

    Returns:
        Dictionary with:
            - "confidence" (float): Heuristic score between 0.0 and 1.0.
            - "confidence_flag" (str): "high", "medium", or "low".
            - "reasons" (list[str]): Explanation strings for explainability UI.
    """
    reasons: List[str] = []

    # 1. OCR fidelity sub-score
    ocr_score, ocr_note = _calculate_ocr_score(line_item, ocr_result)
    if ocr_note:
        reasons.append(ocr_note)

    # 2. Completeness sub-score
    comp_score, comp_notes = _calculate_completeness(line_item)
    reasons.extend(comp_notes)

    # 3. Classification match strength
    match_score = float(classification.get("match_strength", 0.0))
    class_reason = classification.get("reason")
    if class_reason:
        reasons.append(class_reason)

    # 4. Domain sanity check
    sanity_score, sanity_note = _calculate_sanity(line_item, classification)
    if sanity_note:
        reasons.append(sanity_note)

    # Weighted calculation
    composite = (
        SCORING_WEIGHTS["ocr"] * ocr_score
        + SCORING_WEIGHTS["completeness"] * comp_score
        + SCORING_WEIGHTS["match_strength"] * match_score
        + SCORING_WEIGHTS["sanity"] * sanity_score
    )

    clamped_score = max(0.0, min(1.0, round(composite, 2)))

    # Determine categorical badge flag
    if clamped_score >= FLAG_THRESHOLDS["high"]:
        flag = "high"
    elif clamped_score >= FLAG_THRESHOLDS["medium"]:
        flag = "medium"
    else:
        flag = "low"

    return {
        "confidence": clamped_score,
        "confidence_flag": flag,
        "reasons": reasons,
    }

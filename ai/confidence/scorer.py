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

# Penalty applied when quantity * rate deviates significantly from amount (> 2%)
RATE_MISMATCH_PENALTY: float = 0.40

# Domain mapping of expected plausible units per category
PLAUSIBLE_UNITS_BY_CATEGORY: Dict[str, Set[str]] = {
    "stationary_fuel_diesel": {"litre", "litres", "liter", "liters", "gallons", "l", "gal"},
    "mobile_fuel_diesel": {"litre", "litres", "liter", "liters", "gallons", "l", "gal"},
    "mobile_fuel_petrol": {"litre", "litres", "liter", "liters", "gallons", "l", "gal"},
    "natural_gas": {"kwh", "m3", "therms"},
    "electricity_grid": {"kwh", "mwh", "units"},
    "freight_transport": {"tonne.km", "km", "miles", "tonnes", "kg", "trip", "nos"},
    "business_travel": {"km", "miles", "passenger.km", "trip", "nos"},
    "purchased_goods": {"kg", "units", "tonnes", "items", "nos", "reams"},
    "waste_disposal": {"tonnes", "kg", "litres", "litre", "m3", "month"},
}


def _calculate_ocr_score(
    line_item: Dict[str, Any], ocr_result: Dict[str, Any]
) -> tuple[float, Optional[str]]:
    """Compute OCR confidence for the line item using lines if available, or words.

    Args:
        line_item: Extracted line item dict.
        ocr_result: Full OCR extraction result containing 'lines' and/or 'words'.

    Returns:
        Tuple of (ocr_score between 0.0 and 1.0, explanation string).
    """
    # 1. Use per-line OCR confidence from line_conf if attached by parser
    if line_item.get("line_conf") is not None:
        try:
            score = float(line_item["line_conf"])
            norm = max(0.0, min(1.0, score))
            return norm, f"OCR line recognition quality is {int(norm * 100)}%"
        except (ValueError, TypeError):
            pass

    # 2. Check ocr_result['lines'] for matching line
    desc = line_item.get("description", "").lower().strip()
    lines = ocr_result.get("lines", [])
    if lines and desc:
        for line_obj in lines:
            line_text = line_obj.get("text", "").lower()
            if desc in line_text or line_text in desc:
                score = float(line_obj.get("conf", 0.85))
                norm = max(0.0, min(1.0, score))
                return norm, f"OCR line recognition quality is {int(norm * 100)}%"

    # 3. Fallback to word-level average for backwards compatibility
    words = ocr_result.get("words", [])
    if not words:
        return 0.85, "Baseline OCR word confidence assumed"

    desc_tokens = set(re.findall(r"\w+", desc))
    matching_confs = [
        w["conf"]
        for w in words
        if w.get("text", "").lower() in desc_tokens and isinstance(w.get("conf"), (int, float))
    ]

    if matching_confs:
        avg_conf = sum(matching_confs) / len(matching_confs)
        score = max(0.0, min(1.0, avg_conf))
        return score, f"OCR word recognition quality is {int(score * 100)}%"

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


def _has_rate_mismatch(line_item: Dict[str, Any]) -> bool:
    """Check if quantity multiplied by rate deviates significantly (> 2%) from amount."""
    if "qty x rate does not match amount" in line_item.get("reasons", []):
        return True
    qty = line_item.get("quantity")
    rate = line_item.get("rate")
    amt = line_item.get("amount")
    if qty is not None and rate is not None and amt is not None and amt > 0:
        diff = abs(qty * rate - amt)
        if (diff / amt) > 0.02:
            return True
    return False


def _calculate_sanity(
    line_item: Dict[str, Any], classification: Dict[str, Any]
) -> tuple[float, str]:
    """Verify if the measurement unit is physically plausible and rate check passes.

    Args:
        line_item: Extracted line item dict.
        classification: Classification dict with 'category'.

    Returns:
        Tuple of (sanity score 0.0 to 1.0, explanation string).
    """
    # Check if qty x rate mismatch was detected by parser or direct calculation
    if _has_rate_mismatch(line_item):
        return 0.10, "qty x rate does not match amount"

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

    # Penalize arithmetic mismatch between quantity, rate, and amount
    if _has_rate_mismatch(line_item):
        composite -= RATE_MISMATCH_PENALTY
        if "qty x rate does not match amount" not in reasons:
            reasons.append("qty x rate does not match amount")

    clamped_score = max(0.0, min(1.0, round(composite, 2)))
    # Guarantee that arithmetic mismatch lands strictly in 'low' (< 0.50)
    if _has_rate_mismatch(line_item) and clamped_score >= FLAG_THRESHOLDS["medium"]:
        clamped_score = 0.49

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

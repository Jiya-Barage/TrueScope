"""Activity classification module for TrueScope.

Classifies extracted invoice line items into standardized GHG Protocol categories
and Scopes (1, 2, or 3) using extensible keyword rules.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Standardized category taxonomy and rule definitions
# Category keys MUST remain synchronized with the Emission Engine
CLASSIFICATION_RULES: Dict[str, Dict[str, Any]] = {
    "mobile_fuel_diesel": {
        "scope": 1,
        "keywords": [
            "fleet diesel",
            "vehicle diesel",
            "truck diesel",
            "road diesel",
            "derv",
            "automotive diesel",
            "fleet fuel diesel",
        ],
        "weight": 1.0,
    },
    "mobile_fuel_petrol": {
        "scope": 1,
        "keywords": [
            "petrol",
            "gasoline",
            "unleaded",
            "fleet petrol",
            "motor spirit",
            "pms",
            "e10",
            "e5",
        ],
        "weight": 0.95,
    },
    "stationary_fuel_diesel": {
        "scope": 1,
        "keywords": [
            "generator diesel",
            "red diesel",
            "gas oil",
            "heating oil",
            "stationary diesel",
            "boiler diesel",
            "diesel fuel",
            "diesel",
        ],
        "weight": 0.85,
    },
    "natural_gas": {
        "scope": 1,
        "keywords": [
            "natural gas",
            "mains gas",
            "piped gas",
            "gas consumption",
            "gas utility",
            "therms gas",
        ],
        "weight": 0.95,
    },
    "electricity_grid": {
        "scope": 2,
        "keywords": [
            "electricity",
            "grid electricity",
            "power consumption",
            "electric supply",
            "kwh consumed",
            "units consumed",
            "metered electricity",
            "power supply",
        ],
        "weight": 0.95,
    },
    "business_travel": {
        "scope": 3,
        "keywords": [
            "flight",
            "airfare",
            "airline",
            "hotel",
            "accommodation",
            "taxi",
            "cab",
            "uber",
            "train",
            "railway",
            "business travel",
            "lodging",
        ],
        "weight": 0.90,
    },
    "freight_transport": {
        "scope": 3,
        "keywords": [
            "freight",
            "courier",
            "haulage",
            "cargo",
            "shipping",
            "delivery fee",
            "logistics transport",
            "trucking",
        ],
        "weight": 0.90,
    },
    "waste_disposal": {
        "scope": 3,
        "keywords": [
            "waste disposal",
            "refuse collection",
            "landfill",
            "recycling",
            "waste management",
            "hazardous waste",
            "effluent",
            "rubbish collection",
            "scrap disposal",
            "waste",
            "disposal",
        ],
        "weight": 0.85,
    },
    "purchased_goods": {
        "scope": 3,
        "keywords": [
            "office supplies",
            "stationery",
            "hardware",
            "equipment",
            "materials",
            "raw material",
            "consumables",
            "packaging material",
            "paper",
            "purchased goods",
        ],
        "weight": 0.80,
    },
}


def classify(line_item: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a line item into a GHG category and Scope based on description & unit.

    Args:
        line_item: Dictionary containing at least "description" (str).
                   Optionally contains "unit" (str).

    Returns:
        Dictionary with:
            - "category" (str): Standardized taxonomy key or "unknown".
            - "scope" (int or None): 1, 2, 3, or None.
            - "match_strength" (float): 0.0 to 1.0 indicating keyword match confidence.
            - "reason" (str): Short human-readable explanation of the classification rule hit.
    """
    desc = line_item.get("description", "")
    unit = line_item.get("unit", "") or ""
    text_to_match = f"{desc} {unit}".lower().strip()

    if not text_to_match:
        return {
            "category": "unknown",
            "scope": None,
            "match_strength": 0.0,
            "reason": "Empty description; unable to classify activity.",
        }

    best_category: Optional[str] = None
    best_scope: Optional[int] = None
    best_match_strength = 0.0
    matched_keyword = ""

    # Check each category rule
    for category, config in CLASSIFICATION_RULES.items():
        scope = config["scope"]
        weight = config["weight"]
        keywords: List[str] = config["keywords"]

        for kw in keywords:
            # Word boundary regex for accurate keyword detection
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text_to_match):
                # Longer keywords have higher specificity
                specificity = min(1.0, weight * (1.0 if len(kw.split()) > 1 else 0.9))
                if specificity > best_match_strength:
                    best_match_strength = specificity
                    best_category = category
                    best_scope = scope
                    matched_keyword = kw

    if best_category and best_match_strength > 0.0:
        return {
            "category": best_category,
            "scope": best_scope,
            "match_strength": round(best_match_strength, 2),
            "reason": f"Matched keyword '{matched_keyword}' -> {best_category} (Scope {best_scope})",
        }

    return {
        "category": "unknown",
        "scope": None,
        "match_strength": 0.0,
        "reason": "No emission activity keywords matched; manual review required.",
    }

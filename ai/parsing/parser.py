"""Parsing module for TrueScope.

Extracts invoice metadata (vendor, date, invoice number, currency) and candidate
line items from raw OCR text using robust pattern matching.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# Standard unit normalization mapping
KNOWN_UNITS = {
    "l": "litres",
    "litre": "litres",
    "litres": "litres",
    "liter": "litres",
    "liters": "litres",
    "ltr": "litres",
    "ltrs": "litres",
    "gal": "gallons",
    "gallon": "gallons",
    "gallons": "gallons",
    "kwh": "kWh",
    "mwh": "MWh",
    "m3": "m3",
    "therms": "therms",
    "therm": "therms",
    "km": "km",
    "mile": "miles",
    "miles": "miles",
    "kg": "kg",
    "kgs": "kg",
    "tonne": "tonnes",
    "tonnes": "tonnes",
    "ton": "tonnes",
    "tons": "tonnes",
    "unit": "units",
    "units": "units",
}

CURRENCY_SYMBOLS = {
    "£": "GBP",
    "€": "EUR",
    "$": "USD",
    "₹": "INR",
    "¥": "JPY",
}

CURRENCY_CODES = {"GBP", "EUR", "USD", "INR", "CAD", "AUD", "CHF"}

# Header/footer keywords to ignore when scanning for line items
IGNORE_HEADER_KEYWORDS = [
    "invoice no",
    "invoice number",
    "invoice #",
    "invoice date",
    "due date",
    "bill to",
    "ship to",
    "subtotal",
    "tax",
    "vat",
    "total",
    "amount due",
    "balance due",
    "payment terms",
    "currency",
    "date:",
    "invoice:",
]


def extract_vendor(lines: List[str]) -> Optional[str]:
    """Extract vendor name from the first non-empty, non-generic header line.

    Args:
        lines: List of text lines.

    Returns:
        Vendor name string or None if unidentifiable.
    """
    generic_words = {"invoice", "tax invoice", "receipt", "bill", "statement"}
    for raw_line in lines[:5]:
        line = raw_line.strip()
        if not line:
            continue
        cleaned = re.sub(r"[^\w\s]", "", line).strip().lower()
        if cleaned in generic_words:
            continue
        # Skip if line looks like an invoice label, date, or metadata
        if re.match(r"^(invoice|date|bill to|ship to|to|from|currency)\b", cleaned):
            continue
        return line
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract and normalize invoice date to YYYY-MM-DD.

    Args:
        text: Raw OCR text.

    Returns:
        Date string in YYYY-MM-DD format, or None.
    """
    # 1. ISO format: YYYY-MM-DD or YYYY/MM/DD
    match_iso = re.search(r"\b(20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b", text)
    if match_iso:
        y, m, d = match_iso.groups()
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"

    # 2. Common DD/MM/YYYY or DD-MM-YYYY
    match_dmy = re.search(r"\b(0[1-9]|[12]\d|3[01])[-/.](0[1-9]|1[0-2])[-/.](20\d{2})\b", text)
    if match_dmy:
        d, m, y = match_dmy.groups()
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"

    # 3. Textual date: 15 Mar 2024 or 15 March 2024 or March 15, 2024
    month_names = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december"
    match_textual = re.search(
        rf"\b(0?[1-9]|[12]\d|3[01])\s+({month_names})\w*\s+(20\d{{2}})\b",
        text,
        re.IGNORECASE,
    )
    if match_textual:
        d_str, m_str, y_str = match_textual.groups()
        try:
            parsed = datetime.strptime(f"{d_str} {m_str[:3]} {y_str}", "%d %b %Y")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice reference number.

    Args:
        text: Raw OCR text.

    Returns:
        Invoice number string or None.
    """
    pattern = (
        r"\b(?:invoice|reference)\s+(?:number|num|no\.?|#)\b\s*[:.\-#]?\s*([a-zA-Z0-9\-_/]+)"
        r"|\binv(?:oice)?\s*#\s*([a-zA-Z0-9\-_/]+)"
        r"|\binv\b\s*[:.\-#]\s*([a-zA-Z0-9\-_/]+)"
    )
    matches = re.findall(pattern, text, re.IGNORECASE)
    for group in matches:
        for match in group:
            if not match:
                continue
            inv_num = match.strip()
            # Ensure it has digits or length >= 3 and is not a keyword like 'date'
            if (
                len(inv_num) >= 3
                and any(ch.isalnum() for ch in inv_num)
                and inv_num.lower() not in {"date", "number", "numbers", "total"}
            ):
                return inv_num
    return None


def extract_currency(text: str) -> Optional[str]:
    """Extract 3-letter currency code from symbol or code in text.

    Args:
        text: Raw OCR text.

    Returns:
        3-letter currency code or None.
    """
    for code in CURRENCY_CODES:
        if re.search(rf"\b{code}\b", text, re.IGNORECASE):
            return code.upper()

    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            return code

    return None


def _parse_line_item(
    line: str,
    vendor: Optional[str] = None,
    invoice_number: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Parse a single text line into description, quantity, unit, and amount.

    Args:
        line: Single text line.
        vendor: Detected vendor to avoid classifying vendor header as an item.
        invoice_number: Detected invoice number.

    Returns:
        Line item dictionary or None if line is not an item.
    """
    stripped = line.strip()
    if not stripped or len(stripped) < 4:
        return None

    # Exclude vendor line or exact invoice number lines
    if vendor and stripped.lower() == vendor.lower():
        return None
    if invoice_number and invoice_number.lower() in stripped.lower():
        return None

    lower_line = stripped.lower()
    # Skip common headers and total lines
    if any(lower_line.startswith(kw) for kw in IGNORE_HEADER_KEYWORDS):
        return None

    # Skip table header lines like "Description Quantity Unit Amount"
    if "description" in lower_line and ("amount" in lower_line or "quantity" in lower_line or "price" in lower_line):
        return None

    # Check for monetary amount at or near the end of line
    # Examples: 1,875.00, £1875.00, 750.50
    amount_match = re.search(r"[$£€₹]?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})|[0-9]+(?:\.[0-9]{1,2}))\s*$", stripped)
    amount: Optional[float] = None
    remaining_text = stripped

    if amount_match:
        raw_amt = amount_match.group(1).replace(",", "")
        try:
            amount = float(raw_amt)
            remaining_text = stripped[: amount_match.start()].strip()
        except ValueError:
            amount = None

    # Find quantity and unit
    # Examples: "1250 litres", "450 kWh", "500.5 L"
    unit_regex = r"\b(" + "|".join(re.escape(k) for k in KNOWN_UNITS.keys()) + r")\b"
    qty_unit_pattern = rf"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*({unit_regex})"

    qty_unit_match = re.search(qty_unit_pattern, remaining_text, re.IGNORECASE)
    quantity: Optional[float] = None
    unit: Optional[str] = None

    if qty_unit_match:
        raw_qty = qty_unit_match.group(1).replace(",", "")
        raw_u = qty_unit_match.group(2).lower()
        try:
            quantity = float(raw_qty)
            unit = KNOWN_UNITS.get(raw_u, raw_u)
            # Remove qty & unit from description
            desc_part1 = remaining_text[: qty_unit_match.start()].strip()
            desc_part2 = remaining_text[qty_unit_match.end() :].strip()
            description = f"{desc_part1} {desc_part2}".strip()
        except ValueError:
            description = remaining_text
    else:
        description = remaining_text

    # Clean description
    description = re.sub(r"^[^\w]+", "", description)
    description = re.sub(r"\s+", " ", description).strip()

    # A valid line item must have either an amount or a quantity/unit
    if amount is None and quantity is None:
        return None

    # If description is too short or empty, reject
    if not description or len(description) < 3:
        return None

    return {
        "description": description,
        "quantity": quantity,
        "unit": unit,
        "amount": amount,
    }


def parse(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse raw OCR result into structured metadata and line items.

    Never fabricates values; returns None for fields that cannot be extracted.

    Args:
        ocr_result: Dictionary containing 'text', 'words', 'pages'.

    Returns:
        Dictionary containing:
            - "vendor": str or None
            - "invoice_date": str (YYYY-MM-DD) or None
            - "invoice_number": str or None
            - "currency": str or None
            - "line_items": list[dict]
    """
    raw_text = ocr_result.get("text", "")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    vendor = extract_vendor(lines)
    invoice_date = extract_date(raw_text)
    invoice_number = extract_invoice_number(raw_text)
    currency = extract_currency(raw_text)

    line_items: List[Dict[str, Any]] = []
    for line in lines:
        parsed_item = _parse_line_item(line, vendor=vendor, invoice_number=invoice_number)
        if parsed_item:
            line_items.append(parsed_item)

    return {
        "vendor": vendor,
        "invoice_date": invoice_date,
        "invoice_number": invoice_number,
        "currency": currency,
        "line_items": line_items,
    }

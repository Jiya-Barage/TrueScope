"""Parsing module for TrueScope.

Extracts invoice metadata (vendor, date, invoice number, currency) and candidate
line items from raw OCR text using robust pattern matching.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# Standard unit normalization mapping and aliases
UNIT_ALIASES = {
    "lr": "litre",
    "ltr": "litre",
    "ltrs": "litre",
    "litre": "litre",
    "litres": "litre",
    "liter": "litre",
    "liters": "litre",
    "kwh": "kWh",
    "mwh": "MWh",
    "nos": "nos",
    "nos.": "nos",
    "no": "nos",
    "month": "Month",
    "trip": "Trip",
    "km": "km",
}

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
    "nos": "nos",
    "month": "Month",
    "trip": "Trip",
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
    """Extract vendor name from lines.

    Finds first non-empty line that is not purely 'TAX INVOICE', removes trailing
    'TAX INVOICE' if on same line, and leniently normalizes OCR'd 'Mis'/'M/s' prefix.

    Args:
        lines: List of text lines.

    Returns:
        Vendor name string or None if unidentifiable.
    """
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        # Remove trailing "TAX INVOICE" or document header if on same line
        v = re.sub(r"\s+tax\s+invoice\s*$", "", line, flags=re.IGNORECASE).strip()
        cleaned_lower = re.sub(r"[^\w\s]", "", v).strip().lower()
        if not cleaned_lower or cleaned_lower in {"tax invoice", "invoice", "receipt", "bill", "statement"}:
            continue
        # Leniently normalize OCR'd "Mis", "M/s", "Ms" prefix
        v = re.sub(r"^(?:m/s|mis|ms|m\s*/\s*s|m\.\s*s\.?)\s+", "", v, flags=re.IGNORECASE).strip()
        # Skip if line looks like an invoice label or metadata
        if re.match(r"^(?:invoice|date|bill to|ship to|to|from|currency)\b", v, re.IGNORECASE):
            continue
        if len(v) >= 2:
            return v
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


def _clean_description(desc: str) -> str:
    """Clean OCR junk symbols from description while preserving numbers and text.

    Strips stray OCR junk symbols (such as «, », |, _, ~) from within and at the
    edges of descriptions, and strips leading/trailing periods, commas, colons,
    hyphens, and whitespace. Leaves numbers, decimals, and words intact.
    """
    if not desc:
        return ""
    # Replace stray OCR symbols with a space so adjacent words don't merge
    cleaned = re.sub(r"[«»|_~]+", " ", desc)
    # Collapse multiple whitespace sequences into a single space
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip leading and trailing punctuation and whitespace
    cleaned = cleaned.strip(" .,:;-_«»|~").strip()
    return cleaned


def _clean_num(val: str) -> Optional[float]:
    """Clean number string by stripping thousands commas and trailing dots."""
    cleaned = val.strip().rstrip(".").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_table_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a tabular invoice line with tolerant regex into items.

    Rules:
      amount = last number on the line
      rate = number before amount (if present)
      unit = token before rate
      quantity = number before unit
      description = everything before quantity

    Args:
        line: Raw text line.

    Returns:
        Parsed line item dict or None if line does not match.
    """
    num_re = r"[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?\.?"
    
    # 5 columns: desc, qty, unit, rate, amount
    pattern_5col = re.compile(
        rf"^(?P<desc>.+?)\s+(?P<qty>{num_re})\s+(?P<unit>[^\s0-9]+)\s+(?P<rate>{num_re})\s+(?P<amount>{num_re})\s*$"
    )
    # 4 columns: desc, qty, unit, amount (fallback when rate column is absent)
    pattern_4col = re.compile(
        rf"^(?P<desc>.+?)\s+(?P<qty>{num_re})\s+(?P<unit>[^\s0-9]+)\s+(?P<amount>{num_re})\s*$"
    )

    stripped = line.strip()
    m5 = pattern_5col.match(stripped)
    if m5:
        d = m5.groupdict()
        qty = _clean_num(d["qty"])
        rate = _clean_num(d["rate"])
        amount = _clean_num(d["amount"])
        raw_unit = d["unit"]
        unit = UNIT_ALIASES.get(raw_unit.lower().strip("."), raw_unit)
        desc = _clean_description(d["desc"])

        reasons = []
        if qty is not None and rate is not None and amount is not None and amount > 0:
            diff = abs(qty * rate - amount)
            if (diff / amount) > 0.02:
                reasons.append("qty x rate does not match amount")

        return {
            "description": desc,
            "quantity": qty,
            "unit": unit,
            "rate": rate,
            "amount": amount,
            "reasons": reasons,
        }

    m4 = pattern_4col.match(stripped)
    if m4:
        d = m4.groupdict()
        qty = _clean_num(d["qty"])
        amount = _clean_num(d["amount"])
        raw_unit = d["unit"]
        unit = UNIT_ALIASES.get(raw_unit.lower().strip("."), raw_unit)
        desc = _clean_description(d["desc"])

        return {
            "description": desc,
            "quantity": qty,
            "unit": unit,
            "rate": None,
            "amount": amount,
            "reasons": [],
        }

    return None


def _parse_line_item(
    line: str,
    vendor: Optional[str] = None,
    invoice_number: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fallback line item parser for non-tabular invoices.

    Args:
        line: Single text line.
        vendor: Detected vendor.
        invoice_number: Detected invoice number.

    Returns:
        Line item dictionary or None.
    """
    stripped = line.strip()
    if not stripped or len(stripped) < 4:
        return None

    if vendor and stripped.lower() == vendor.lower():
        return None
    if invoice_number and invoice_number.lower() in stripped.lower():
        return None

    lower_line = stripped.lower()
    if any(lower_line.startswith(kw) for kw in IGNORE_HEADER_KEYWORDS):
        return None

    if "description" in lower_line and ("amount" in lower_line or "quantity" in lower_line or "price" in lower_line):
        return None

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
            unit = UNIT_ALIASES.get(raw_u, KNOWN_UNITS.get(raw_u, raw_u))
            desc_part1 = remaining_text[: qty_unit_match.start()].strip()
            desc_part2 = remaining_text[qty_unit_match.end() :].strip()
            description = f"{desc_part1} {desc_part2}".strip()
        except ValueError:
            description = remaining_text
    else:
        description = remaining_text

    description = _clean_description(description)

    if amount is None and quantity is None:
        return None

    if not description or len(description) < 3:
        return None

    return {
        "description": description,
        "quantity": quantity,
        "unit": unit,
        "rate": None,
        "amount": amount,
        "reasons": [],
    }


def parse(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse raw OCR result into structured metadata and line items.

    Never fabricates values; returns None for fields that cannot be extracted.

    Args:
        ocr_result: Dictionary containing 'text', 'lines', 'words', 'pages'.

    Returns:
        Dictionary containing:
            - "vendor": str or None
            - "invoice_date": str (YYYY-MM-DD) or None
            - "invoice_number": str or None
            - "currency": str or None
            - "line_items": list[dict]
            - "warnings": list[str]
    """
    raw_text = ocr_result.get("text", "")
    lines_data = ocr_result.get("lines")

    if lines_data:
        line_strings = [l.get("text", "").strip() for l in lines_data if l.get("text", "").strip()]
        line_confs = [l.get("conf", 0.85) for l in lines_data if l.get("text", "").strip()]
    else:
        line_strings = [line.strip() for line in raw_text.splitlines() if line.strip()]
        line_confs = [0.85] * len(line_strings)

    vendor = extract_vendor(line_strings)
    invoice_date = extract_date(raw_text)
    invoice_number = extract_invoice_number(raw_text)
    currency = extract_currency(raw_text)

    line_items: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # Detect table region boundaries
    table_start_idx = -1
    for idx, line in enumerate(line_strings):
        lower = line.lower()
        if "description" in lower and ("qty" in lower or "quantity" in lower):
            table_start_idx = idx
            break

    table_end_idx = len(line_strings)
    if table_start_idx != -1:
        for idx in range(table_start_idx + 1, len(line_strings)):
            lower = line_strings[idx].lower()
            if re.search(r"\b(?:subtotal|total)\b", lower):
                table_end_idx = idx
                break

        # Parse table region rows
        for idx in range(table_start_idx + 1, table_end_idx):
            line = line_strings[idx]
            if not line:
                continue
            parsed_item = _parse_table_line(line)
            if parsed_item:
                parsed_item["line_conf"] = line_confs[idx] if idx < len(line_confs) else 0.85
                line_items.append(parsed_item)
            else:
                warnings.append(f"Skipped unrecognized line inside table region: '{line}'")
    else:
        # Fallback for documents without explicit Description/Qty table header
        for idx, line in enumerate(line_strings):
            parsed_item = _parse_line_item(line, vendor=vendor, invoice_number=invoice_number)
            if parsed_item:
                parsed_item["line_conf"] = line_confs[idx] if idx < len(line_confs) else 0.85
                line_items.append(parsed_item)

    return {
        "vendor": vendor,
        "invoice_date": invoice_date,
        "invoice_number": invoice_number,
        "currency": currency,
        "line_items": line_items,
        "warnings": warnings,
    }

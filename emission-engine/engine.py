from datetime import date
import ipaddress
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
FACTOR_FILE = BASE_DIR / "data" / "emission_factors.json"

APPROVED_LIBRARY_STATUSES = {
    "verification_in_progress",
    "verified",
}

APPROVED_FACTOR_STATUSES = {
    "verified",
    "unverified_demo_value",
}

PROVENANCE_FIELDS = (
    "source_title",
    "source_publisher",
    "dataset_version",
    "publication_year",
    "reporting_year",
    "geography",
    "activity_boundary",
    "method",
    "rationale",
)


def load_emission_library():
    """Load and validate emission factors and trust metadata."""
    with FACTOR_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Emission library must be a JSON object.")

    metadata = data.get("metadata")
    factors = data.get("factors")

    if not isinstance(metadata, dict):
        raise ValueError("Emission library must contain metadata.")

    if not isinstance(factors, list):
        raise ValueError("Emission library must contain a factors list.")

    required_metadata = (
        "project",
        "version",
        "status",
        "default_geography",
    )

    for key in required_metadata:
        value = metadata.get(key)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Metadata field '{key}' must be a non-empty string."
            )

    if (
        not isinstance(metadata["status"], str)
        or metadata["status"] not in APPROVED_LIBRARY_STATUSES
    ):
        raise ValueError(
            f"Invalid library status: '{metadata['status']}'. "
            f"Allowed statuses: "
            f"{', '.join(sorted(APPROVED_LIBRARY_STATUSES))}."
        )

    factor_keys = set()
    for factor in factors:
        if not isinstance(factor, dict):
            raise ValueError(
                "Each emission factor must be a JSON object."
            )

        value = factor.get("factor")

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ValueError("Emission factor must be a valid number.")

        if not math.isfinite(value) or value < 0:
            raise ValueError(
                "Emission factor must be finite and non-negative."
            )

        for key in (
            "category",
            "activity_unit",
            "factor_unit",
            "scope",
        ):
            field_value = factor.get(key)

            if (
                not isinstance(field_value, str)
                or not field_value.strip()
            ):
                raise ValueError(
                    f"Emission factor field '{key}' "
                    "must be a non-empty string."
                )

        factor_unit_parts = factor["factor_unit"].rsplit("/", 1)
        if (
            len(factor_unit_parts) != 2
            or not factor_unit_parts[0].strip()
            or normalize_unit(factor_unit_parts[1])
            != normalize_unit(factor["activity_unit"])
        ):
            raise ValueError(
                "Emission factor denominator must match its activity unit."
            )

        factor_status = factor.get("verification_status")

        if (
            not isinstance(factor_status, str)
            or factor_status not in APPROVED_FACTOR_STATUSES
        ):
            raise ValueError(
                f"Invalid factor verification status: "
                f"'{factor_status}'. Allowed statuses: "
                f"{', '.join(sorted(APPROVED_FACTOR_STATUSES))}."
            )

        provenance = factor.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(
                "Each emission factor must contain provenance metadata."
            )
        for key in PROVENANCE_FIELDS:
            field_value = provenance.get(key)
            if key == "rationale":
                if not isinstance(field_value, str) or not field_value.strip():
                    raise ValueError(
                        "Emission factor provenance rationale must be non-empty."
                    )
            elif field_value is not None and (
                not isinstance(field_value, str) or not field_value.strip()
            ):
                raise ValueError(
                    f"Emission factor provenance field '{key}' "
                    "must be a non-empty string or null."
                )

        factor_key = (
            factor["category"],
            normalize_unit(factor["activity_unit"]),
        )
        if factor_key in factor_keys:
            raise ValueError(
                "Duplicate emission factor for category "
                f"'{factor_key[0]}' and unit '{factor_key[1]}'."
            )
        factor_keys.add(factor_key)

    return metadata, factors


def load_emission_factors():
    """Load and return the emission factor records."""
    _, factors = load_emission_library()
    return factors


def normalize_unit(unit):
    """Normalize supported unit spellings."""
    aliases = {
        "litre": "litres",
        "liter": "litres",
        "liters": "litres",
        "tonne": "tonnes",
        "ton": "tonnes",
        "m3": "m³",
        "m^3": "m³",
        "passenger km": "passenger-km",
        "p-km": "passenger-km",
    }

    cleaned = " ".join(unit.strip().lower().split())
    return aliases.get(cleaned, cleaned)


def has_valid_source(source):
    """Return whether a source is a usable, non-placeholder HTTP reference."""
    if not isinstance(source, str) or not source.strip():
        return False

    try:
        parsed = urlparse(source.strip())
        hostname = parsed.hostname
    except ValueError:
        return False

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False

    try:
        parsed.port
    except ValueError:
        return False

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    if address is not None:
        if not address.is_global:
            return False
    else:
        hostname = hostname.lower()
        if hostname.endswith("."):
            hostname = hostname[:-1]

        try:
            ascii_hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError:
            return False

        labels = ascii_hostname.split(".")
        if (
            len(ascii_hostname) > 253
            or any(
                not re.fullmatch(
                    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?",
                    label,
                )
                for label in labels
            )
            or all(label.isdigit() for label in labels)
        ):
            return False

        hostname = ascii_hostname

    placeholder_hosts = {
        "example.com",
        "example.org",
        "example.net",
        "localhost",
    }

    return not (
        hostname in placeholder_hosts
        or hostname.endswith(".example.com")
        or hostname.endswith(".example.org")
        or hostname.endswith(".example.net")
    )


def has_valid_verification_evidence(evidence, factor):
    """Check that a human review is tied to this factor's full provenance."""
    if not isinstance(evidence, dict) or evidence.get("reviewed") is not True:
        return False

    provenance = factor.get("provenance")
    if not isinstance(provenance, dict):
        return False

    for key in (
        "reviewer",
        "methodology",
        "source_locator",
        "supporting_excerpt",
        "category",
        "factor_unit",
        "activity_unit",
        "source_title",
        "source_publisher",
        "dataset_version",
        "publication_year",
        "reporting_year",
        "geography",
        "activity_boundary",
        "method",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            return False

    reviewed_factor = evidence.get("factor")
    if (
        isinstance(reviewed_factor, bool)
        or not isinstance(reviewed_factor, (int, float))
        or reviewed_factor != factor.get("factor")
    ):
        return False

    if (
        evidence["category"] != factor.get("category")
        or evidence["factor_unit"] != factor.get("factor_unit")
        or normalize_unit(evidence["activity_unit"])
        != normalize_unit(factor.get("activity_unit", ""))
        or evidence["source_title"] != provenance.get("source_title")
        or evidence["source_publisher"] != provenance.get("source_publisher")
        or evidence["dataset_version"] != provenance.get("dataset_version")
        or evidence["publication_year"] != provenance.get("publication_year")
        or evidence["reporting_year"] != provenance.get("reporting_year")
        or evidence["geography"] != provenance.get("geography")
        or evidence["activity_boundary"]
        != provenance.get("activity_boundary")
        or evidence["method"] != provenance.get("method")
        or evidence.get("source") != factor.get("source")
        or evidence.get("source_year") != factor.get("source_year")
    ):
        return False

    review_date = evidence.get("review_date")
    if not isinstance(review_date, str):
        return False

    try:
        parsed_date = date.fromisoformat(review_date)
    except ValueError:
        return False

    return parsed_date.isoformat() == review_date


def calculate_emissions(category, quantity, unit, expected_unit=None):
    """Calculate emissions and return factor trust information.

    ``factor_verified`` reflects structural checks of supplied provenance and
    evidence; it does not establish the source or factor's scientific accuracy.
    Invalid optional provenance leaves calculations available but unverified.
    """

    if not isinstance(category, str) or not category.strip():
        raise ValueError("Category must be a non-empty string.")

    if isinstance(quantity, bool) or not isinstance(
        quantity, (int, float)
    ):
        raise ValueError("Quantity must be a valid number.")

    if not math.isfinite(quantity):
        raise ValueError("Quantity must be a finite number.")

    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("Unit must be a non-empty string.")

    if expected_unit is not None:
        if not isinstance(expected_unit, str) or not expected_unit.strip():
            raise ValueError("Expected unit must be a non-empty string.")
        if normalize_unit(unit) != normalize_unit(expected_unit):
            raise ValueError(
                f"Activity unit '{unit}' does not match expected unit "
                f"'{expected_unit}'."
            )

    metadata, factors = load_emission_library()

    factor_record = next(
        (
            item for item in factors
            if item["category"] == category
            and normalize_unit(item["activity_unit"])
            == normalize_unit(unit)
        ),
        None,
    )

    if factor_record is None:
        raise ValueError(
            f"No emission factor found for category '{category}' "
            f"with unit '{unit}'."
        )

    emissions = quantity * factor_record["factor"]

    if not math.isfinite(emissions):
        raise ValueError(
            "Calculated emissions are outside the supported range."
        )

    verification_status = factor_record["verification_status"]
    factor_unit = factor_record["factor_unit"]
    source = factor_record.get("source")
    source_year = factor_record.get("source_year")
    source_year_valid = (
        isinstance(source_year, int)
        and not isinstance(source_year, bool)
        and source_year > 0
    )

    # This indicates declared verified status and complete evidence metadata.
    # It does not establish scientific validity.
    factor_verified = (
        verification_status == "verified"
        and has_valid_source(source)
        and source_year_valid
        and has_valid_verification_evidence(
            factor_record.get("verification_evidence"),
            factor_record,
        )
    )

    normalized_factor_unit = factor_unit.lower().replace(" ", "")
    if normalized_factor_unit.startswith("kgco2e/"):
        emissions_basis = "CO2e"
    elif normalized_factor_unit.startswith("kgco2/"):
        emissions_basis = "CO2"
    else:
        emissions_basis = "unspecified"

    result = {
        "category": category,
        "scope": factor_record["scope"],
        "activity_data": quantity,
        "activity_unit": unit,
        "emission_factor": factor_record["factor"],
        "factor_unit": factor_unit,
        "emissions": round(emissions, 3),
        "emissions_unit": f"kg {emissions_basis}",
        "emissions_basis": emissions_basis,
        "calculation": (
            f"{quantity} {unit} × "
            f"{factor_record['factor']} {factor_unit}"
        ),
        "factor_source": source,
        "source_year": source_year,
        "factor_provenance": factor_record["provenance"],
        "validation_status": (
            "verified"
            if factor_verified
            else "unverified_demo_value"
            if verification_status == "verified"
            else verification_status
        ),
        "trust_metadata": {
            "project": metadata["project"],
            "library_version": metadata["version"],
            "library_status": metadata["status"],
            "geography": factor_record["provenance"]["geography"],
            "library_default_geography": metadata["default_geography"],
            "verification_required": metadata.get(
                "factor_verification_required", True
            ),
            "factor_verified": factor_verified,
        },
    }

    return result


if __name__ == "__main__":
    result = calculate_emissions(
        category="electricity_grid",
        quantity=100,
        unit="kWh",
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

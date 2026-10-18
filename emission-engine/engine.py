import json
import math
from pathlib import Path


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

    if metadata["status"] not in APPROVED_LIBRARY_STATUSES:
        raise ValueError(
            f"Invalid library status: '{metadata['status']}'. "
            f"Allowed statuses: "
            f"{', '.join(sorted(APPROVED_LIBRARY_STATUSES))}."
        )

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

        factor_status = factor.get("verification_status")

        if factor_status not in APPROVED_FACTOR_STATUSES:
            raise ValueError(
                f"Invalid factor verification status: "
                f"'{factor_status}'. Allowed statuses: "
                f"{', '.join(sorted(APPROVED_FACTOR_STATUSES))}."
            )

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


def calculate_emissions(category, quantity, unit):
    """Calculate emissions and return factor trust information."""

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

    factor_verified = (
        verification_status == "verified"
        and isinstance(factor_record.get("source"), str)
        and bool(factor_record["source"].strip())
        and isinstance(factor_record.get("source_year"), int)
        and not isinstance(factor_record.get("source_year"), bool)
        and factor_record["source_year"] > 0
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
        "factor_source": factor_record.get("source"),
        "source_year": factor_record.get("source_year"),
        "validation_status": verification_status,
        "trust_metadata": {
            "project": metadata["project"],
            "library_version": metadata["version"],
            "library_status": metadata["status"],
            "geography": metadata["default_geography"],
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

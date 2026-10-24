import json
import math
import unittest
from unittest.mock import mock_open, patch

from engine import (
    calculate_emissions,
    load_emission_factors,
    load_emission_library,
)


VALID_EVIDENCE = {
    "reviewed": True,
    "reviewer": "Reviewer",
    "methodology": "Reviewed against the cited methodology",
    "review_date": "2025-04-30",
}


def make_factor(
    verification_status="unverified_demo_value",
    source=None,
    source_year=None,
    factor_unit="kg CO2/kWh",
    verification_evidence=None,
):
    return {
        "category": "electricity_grid",
        "scope": "Scope 2",
        "activity_unit": "kWh",
        "factor": 0.710,
        "factor_unit": factor_unit,
        "source": source,
        "source_year": source_year,
        "verification_status": verification_status,
        "verification_evidence": verification_evidence,
    }


def make_library(factors=None, metadata=None):
    default_metadata = {
        "project": "TrustScope",
        "version": "1.0.0",
        "status": "verification_in_progress",
        "default_geography": "India",
        "factor_verification_required": True,
    }
    if metadata:
        default_metadata.update(metadata)

    return {
        "metadata": default_metadata,
        "factors": factors if factors is not None else [make_factor()],
    }


class TestEmissionEngine(unittest.TestCase):
    def run_with_library(self, data, category="electricity_grid",
                         quantity=100, unit="kWh"):
        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(data)),
        ):
            return calculate_emissions(category, quantity, unit)

    def test_basic_emission_calculation(self):
        result = self.run_with_library(make_library())
        self.assertEqual(result["emissions"], 71.0)

    def test_zero_quantity(self):
        result = self.run_with_library(make_library(), quantity=0)
        self.assertEqual(result["emissions"], 0.0)

    def test_decimal_quantity(self):
        result = self.run_with_library(make_library(), quantity=2.5)
        self.assertEqual(result["emissions"], 1.775)

    def test_result_contains_calculation_and_multiplication_symbol(self):
        result = self.run_with_library(make_library())
        self.assertEqual(
            result["calculation"],
            "100 kWh × 0.71 kg CO2/kWh",
        )

    def test_result_contains_category(self):
        result = self.run_with_library(make_library())
        self.assertEqual(result["category"], "electricity_grid")

    def test_result_contains_scope(self):
        result = self.run_with_library(make_library())
        self.assertEqual(result["scope"], "Scope 2")

    def test_result_contains_activity_data(self):
        result = self.run_with_library(make_library())
        self.assertEqual(result["activity_data"], 100)
        self.assertEqual(result["activity_unit"], "kWh")

    def test_result_contains_factor(self):
        result = self.run_with_library(make_library())
        self.assertEqual(result["emission_factor"], 0.710)
        self.assertEqual(result["factor_unit"], "kg CO2/kWh")

    def test_result_contains_source_and_year(self):
        factor = make_factor(
            source="https://www.gov.uk/environment",
            source_year=2025,
        )
        result = self.run_with_library(make_library([factor]))
        self.assertEqual(result["factor_source"], factor["source"])
        self.assertEqual(result["source_year"], 2025)

    def test_result_contains_trust_metadata(self):
        result = self.run_with_library(make_library())
        self.assertEqual(result["validation_status"], "unverified_demo_value")
        self.assertEqual(result["trust_metadata"]["project"], "TrustScope")
        self.assertEqual(result["trust_metadata"]["library_version"], "1.0.0")
        self.assertEqual(
            result["trust_metadata"]["library_status"],
            "verification_in_progress",
        )
        self.assertEqual(result["trust_metadata"]["geography"], "India")
        self.assertTrue(result["trust_metadata"]["verification_required"])
        self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_demo_library_factors_remain_unverified(self):
        for factor in load_emission_factors():
            with self.subTest(category=factor["category"]):
                result = calculate_emissions(
                    factor["category"], 1, factor["activity_unit"]
                )
                self.assertEqual(
                    result["validation_status"],
                    "unverified_demo_value",
                )
                self.assertFalse(
                    result["trust_metadata"]["factor_verified"]
                )

    def test_category_matching_is_exact(self):
        with self.assertRaisesRegex(ValueError, "No emission factor"):
            self.run_with_library(make_library(), category="Electricity_grid")

    def test_unit_matching_is_case_insensitive(self):
        result = self.run_with_library(make_library(), quantity=10, unit="KWH")
        self.assertEqual(result["emissions"], 7.1)

    def test_supported_unit_aliases(self):
        aliases = (
            ("litres", "litre"),
            ("litres", "liter"),
            ("litres", "liters"),
            ("tonnes", "tonne"),
            ("tonnes", "ton"),
            ("m³", "m3"),
            ("m³", "m^3"),
            ("m³", "m³"),
            ("passenger-km", "passenger km"),
            ("passenger-km", "p-km"),
        )
        for activity_unit, requested_unit in aliases:
            with self.subTest(activity_unit=activity_unit, unit=requested_unit):
                factor = make_factor()
                factor["activity_unit"] = activity_unit
                result = self.run_with_library(
                    make_library([factor]), quantity=1, unit=requested_unit
                )
                self.assertEqual(result["activity_unit"], requested_unit)

    def test_co2_factor_has_co2_label(self):
        result = self.run_with_library(
            make_library([make_factor(factor_unit="kg CO2/kWh")])
        )
        self.assertEqual(result["emissions_basis"], "CO2")
        self.assertEqual(result["emissions_unit"], "kg CO2")

    def test_co2e_factor_has_co2e_label(self):
        result = self.run_with_library(
            make_library([make_factor(factor_unit="kg CO2e/kWh")])
        )
        self.assertEqual(result["emissions_basis"], "CO2e")
        self.assertEqual(result["emissions_unit"], "kg CO2e")

    def test_unknown_factor_basis_is_labelled_unspecified(self):
        result = self.run_with_library(
            make_library([make_factor(factor_unit="units/kWh")])
        )
        self.assertEqual(result["emissions_basis"], "unspecified")
        self.assertEqual(result["emissions_unit"], "kg unspecified")

    def test_boolean_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid number"):
            self.run_with_library(make_library(), quantity=True)

    def test_string_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid number"):
            self.run_with_library(make_library(), quantity="100")

    def test_none_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid number"):
            self.run_with_library(make_library(), quantity=None)

    def test_negative_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            self.run_with_library(make_library(), quantity=-1)

    def test_nan_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite number"):
            self.run_with_library(make_library(), quantity=math.nan)

    def test_infinite_quantities_are_rejected(self):
        for quantity in (math.inf, -math.inf):
            with self.subTest(quantity=quantity):
                with self.assertRaisesRegex(ValueError, "finite number"):
                    self.run_with_library(make_library(), quantity=quantity)

    def test_empty_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Category"):
            self.run_with_library(make_library(), category="")

    def test_invalid_category_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Category"):
            self.run_with_library(make_library(), category=None)

    def test_empty_unit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unit"):
            self.run_with_library(make_library(), unit="")

    def test_invalid_unit_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unit"):
            self.run_with_library(make_library(), unit=None)

    def test_unsupported_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No emission factor"):
            self.run_with_library(
                make_library(), category="Unknown Category"
            )

    def test_unsupported_unit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No emission factor"):
            self.run_with_library(make_library(), unit="MWh")

    def test_unsupported_categories_are_rejected(self):
        unsupported_cases = (
            ("mobile_fuel_petrol", "litres"),
            ("stationary_fuel_diesel", "litres"),
            ("purchased_goods", "kg"),
            ("Water & Effluent", "m3"),
        )
        for category, unit in unsupported_cases:
            with self.subTest(category=category, unit=unit):
                with self.assertRaisesRegex(ValueError, "No emission factor"):
                    self.run_with_library(
                        make_library(), category=category, unit=unit
                    )

    def test_negative_factor_value_is_rejected(self):
        factor = make_factor()
        factor["factor"] = -0.5
        with self.assertRaisesRegex(ValueError, "finite and non-negative"):
            self.run_with_library(make_library([factor]))

    def test_boolean_factor_value_is_rejected(self):
        factor = make_factor()
        factor["factor"] = True
        with self.assertRaisesRegex(ValueError, "valid number"):
            self.run_with_library(make_library([factor]))

    def test_non_finite_factor_values_are_rejected(self):
        for value in (math.nan, math.inf):
            with self.subTest(value=value):
                factor = make_factor()
                factor["factor"] = value
                with self.assertRaisesRegex(
                    ValueError, "finite and non-negative"
                ):
                    self.run_with_library(make_library([factor]))

    def test_invalid_source_or_missing_source_year_is_not_verified(self):
        incomplete_factors = (
            make_factor(
                verification_status="verified",
                source=None,
                source_year=2025,
                verification_evidence=VALID_EVIDENCE,
            ),
            make_factor(
                verification_status="verified",
                source="https://www.gov.uk/environment",
                source_year=None,
                verification_evidence=VALID_EVIDENCE,
            ),
        )
        for factor in incomplete_factors:
            with self.subTest(source=factor["source"],
                              source_year=factor["source_year"]):
                result = self.run_with_library(make_library([factor]))
                self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_missing_source_and_year_are_preserved(self):
        factor = make_factor(verification_status="verified")
        result = self.run_with_library(make_library([factor]))
        self.assertIsNone(result["factor_source"])
        self.assertIsNone(result["source_year"])
        self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_placeholder_or_malformed_source_is_not_verified(self):
        for source in (
            "https://example.com/source",
            "https://docs.example.org/reference",
            "not a source",
            "",
            "https://user:password@www.gov.uk/environment",
            "https://bad host/reference",
            "https://[invalid-host]/reference",
            "https://www.gov.uk:invalid/reference",
            "https://127.0.0.1/reference",
            "https://10.0.0.1/reference",
            "https://[::1]/reference",
        ):
            with self.subTest(source=source):
                factor = make_factor(
                    verification_status="verified",
                    source=source,
                    source_year=2025,
                    verification_evidence=VALID_EVIDENCE,
                )
                result = self.run_with_library(make_library([factor]))
                self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_duplicate_category_and_normalized_unit_are_rejected(self):
        first = make_factor()
        duplicate = make_factor()
        duplicate["activity_unit"] = "KWH"
        with self.assertRaisesRegex(ValueError, "Duplicate emission factor"):
            self.run_with_library(make_library([first, duplicate]))

    def test_verified_status_without_evidence_is_not_verified(self):
        factor = make_factor(
            verification_status="verified",
            source="https://www.gov.uk/environment",
            source_year=2025,
        )
        result = self.run_with_library(make_library([factor]))
        self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_missing_or_incomplete_evidence_is_not_verified(self):
        incomplete_evidence = (
            None,
            [],
            {"reviewed": True},
            {**VALID_EVIDENCE, "reviewed": 1},
            {**VALID_EVIDENCE, "reviewer": ""},
            {**VALID_EVIDENCE, "reviewer": "  "},
            {**VALID_EVIDENCE, "methodology": ""},
            {**VALID_EVIDENCE, "methodology": None},
            {**VALID_EVIDENCE, "review_date": None},
        )
        for evidence in incomplete_evidence:
            with self.subTest(evidence=evidence):
                factor = make_factor(
                    verification_status="verified",
                    source="https://www.gov.uk/environment",
                    source_year=2025,
                    verification_evidence=evidence,
                )
                result = self.run_with_library(make_library([factor]))
                self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_complete_structural_evidence_allows_verified_flag(self):
        factor = make_factor(
            verification_status="verified",
            source="https://www.gov.uk/environment",
            source_year=2025,
            verification_evidence=VALID_EVIDENCE,
        )
        result = self.run_with_library(make_library([factor]))
        self.assertTrue(result["trust_metadata"]["factor_verified"])

    def test_invalid_review_dates_are_not_verified(self):
        for review_date in ("2025-02-30", "2025-2-03", "20250203", " 2025-02-03"):
            with self.subTest(review_date=review_date):
                factor = make_factor(
                    verification_status="verified",
                    source="https://www.gov.uk/environment",
                    source_year=2025,
                    verification_evidence={
                        **VALID_EVIDENCE,
                        "review_date": review_date,
                    },
                )
                result = self.run_with_library(make_library([factor]))
                self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_boolean_or_invalid_source_year_is_not_verified(self):
        for source_year in (True, False, 0, -1, "2025", 2025.0):
            with self.subTest(source_year=source_year):
                factor = make_factor(
                    verification_status="verified",
                    source="https://www.gov.uk/environment",
                    source_year=source_year,
                    verification_evidence=VALID_EVIDENCE,
                )
                result = self.run_with_library(make_library([factor]))
                self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_invalid_library_status_is_rejected(self):
        data = make_library(metadata={"status": "invalid_status"})
        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(data)),
        ):
            with self.assertRaisesRegex(ValueError, "Invalid library status"):
                load_emission_library()

    def test_non_string_library_status_is_rejected(self):
        data = make_library(metadata={"status": []})
        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(data)),
        ):
            with self.assertRaisesRegex(ValueError, "non-empty string"):
                load_emission_library()

    def test_invalid_factor_verification_status_is_rejected(self):
        for status in ("pending_unknown", None, []):
            with self.subTest(status=status):
                factor = make_factor()
                factor["verification_status"] = status
                with self.assertRaisesRegex(
                    ValueError, "Invalid factor verification status"
                ):
                    self.run_with_library(make_library([factor]))

    def test_load_emission_factors_returns_records(self):
        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(make_library())),
        ):
            factors = load_emission_factors()
        self.assertIsInstance(factors, list)
        self.assertEqual(len(factors), 1)

    def test_missing_metadata_is_rejected(self):
        data = {"factors": [make_factor()]}
        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(data)),
        ):
            with self.assertRaisesRegex(ValueError, "metadata"):
                load_emission_library()


if __name__ == "__main__":
    unittest.main()

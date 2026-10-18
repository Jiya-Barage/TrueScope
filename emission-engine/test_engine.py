import json
import math
import unittest
from unittest.mock import mock_open, patch

from engine import (
    calculate_emissions,
    load_emission_factors,
    load_emission_library,
)


def make_factor(
    verification_status="unverified_demo_value",
    source=None,
    source_year=None,
    factor_unit="kg CO2/kWh",
):
    return {
        "category": "Purchased Electricity",
        "scope": "Scope 2",
        "activity_unit": "kWh",
        "factor": 0.710,
        "factor_unit": factor_unit,
        "source": source,
        "source_year": source_year,
        "verification_status": verification_status,
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

    def run_with_library(self, data, category, quantity, unit):
        """Run a calculation using a temporary emission library."""
        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(data)),
        ):
            return calculate_emissions(category, quantity, unit)

    def test_basic_emission_calculation(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(result["emissions"], 71.0)

    def test_zero_quantity(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            0,
            "kWh",
        )
        self.assertEqual(result["emissions"], 0.0)

    def test_decimal_quantity(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            2.5,
            "kWh",
        )
        self.assertEqual(result["emissions"], 1.775)

    def test_result_contains_category(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(result["category"], "Purchased Electricity")

    def test_result_contains_scope(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(result["scope"], "Scope 2")

    def test_result_contains_activity_data(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(result["activity_data"], 100)
        self.assertEqual(result["activity_unit"], "kWh")

    def test_result_contains_factor(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(result["emission_factor"], 0.710)
        self.assertEqual(result["factor_unit"], "kg CO2/kWh")

    def test_result_contains_calculation(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(
            result["calculation"],
            "100 kWh × 0.71 kg CO2/kWh",
        )

    def test_result_contains_trust_metadata(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            100,
            "kWh",
        )
        trust = result["trust_metadata"]
        self.assertEqual(trust["project"], "TrustScope")
        self.assertEqual(trust["library_version"], "1.0.0")
        self.assertEqual(trust["geography"], "India")

    def test_unverified_factor_is_not_verified(self):
        result = self.run_with_library(
            make_library([make_factor()]),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertFalse(
            result["trust_metadata"]["factor_verified"]
        )

    def test_unverified_factor_status_is_preserved(self):
        result = self.run_with_library(
            make_library([make_factor()]),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(
            result["validation_status"],
            "unverified_demo_value",
        )

    def test_missing_source_and_year_are_transparent(self):
        factor = make_factor(
            source=None,
            source_year=None,
        )
        result = self.run_with_library(
            make_library([factor]),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertIsNone(result["factor_source"])
        self.assertIsNone(result["source_year"])
        self.assertFalse(
            result["trust_metadata"]["factor_verified"]
        )

    def test_verified_factor_requires_source_and_year(self):
        factor = make_factor(
            verification_status="verified",
            source="https://example.com/source",
            source_year=2025,
        )
        result = self.run_with_library(
            make_library([factor]),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertTrue(
            result["trust_metadata"]["factor_verified"]
        )

    def test_verified_factor_without_source_is_not_verified(self):
        factor = make_factor(
            verification_status="verified",
            source=None,
            source_year=2025,
        )
        result = self.run_with_library(
            make_library([factor]),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertFalse(
            result["trust_metadata"]["factor_verified"]
        )

    def test_verified_factor_without_year_is_not_verified(self):
        factor = make_factor(
            verification_status="verified",
            source="https://example.com/source",
            source_year=None,
        )
        result = self.run_with_library(
            make_library([factor]),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertFalse(
            result["trust_metadata"]["factor_verified"]
        )

    def test_co2_factor_has_co2_label(self):
        result = self.run_with_library(
            make_library(
                [make_factor(factor_unit="kg CO2/kWh")]
            ),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(result["emissions_basis"], "CO2")
        self.assertEqual(result["emissions_unit"], "kg CO2")

    def test_co2e_factor_has_co2e_label(self):
        result = self.run_with_library(
            make_library(
                [make_factor(factor_unit="kg CO2e/kWh")]
            ),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(result["emissions_basis"], "CO2e")
        self.assertEqual(result["emissions_unit"], "kg CO2e")

    def test_unknown_factor_basis_is_labelled_unspecified(self):
        result = self.run_with_library(
            make_library(
                [make_factor(factor_unit="units/kWh")]
            ),
            "Purchased Electricity",
            100,
            "kWh",
        )
        self.assertEqual(
            result["emissions_basis"],
            "unspecified",
        )
        self.assertEqual(
            result["emissions_unit"],
            "kg unspecified",
        )

    def test_litre_unit_alias(self):
        factor = make_factor()
        factor["activity_unit"] = "litres"
        result = self.run_with_library(
            make_library([factor]),
            "Purchased Electricity",
            10,
            "litre",
        )
        self.assertEqual(result["activity_data"], 10)

    def test_liter_unit_alias(self):
        factor = make_factor()
        factor["activity_unit"] = "litres"
        result = self.run_with_library(
            make_library([factor]),
            "Purchased Electricity",
            10,
            "liter",
        )
        self.assertEqual(result["activity_data"], 10)

    def test_unit_matching_is_case_insensitive(self):
        result = self.run_with_library(
            make_library(),
            "Purchased Electricity",
            10,
            "KWH",
        )
        self.assertEqual(result["emissions"], 7.1)

    def test_negative_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            self.run_with_library(
                make_library(),
                "Purchased Electricity",
                -1,
                "kWh",
            )

    def test_boolean_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid number"):
            self.run_with_library(
                make_library(),
                "Purchased Electricity",
                True,
                "kWh",
            )

    def test_string_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid number"):
            self.run_with_library(
                make_library(),
                "Purchased Electricity",
                "100",
                "kWh",
            )

    def test_nan_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite number"):
            self.run_with_library(
                make_library(),
                "Purchased Electricity",
                math.nan,
                "kWh",
            )

    def test_infinite_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite number"):
            self.run_with_library(
                make_library(),
                "Purchased Electricity",
                math.inf,
                "kWh",
            )

    def test_empty_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Category"):
            self.run_with_library(
                make_library(),
                "",
                100,
                "kWh",
            )

    def test_empty_unit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unit"):
            self.run_with_library(
                make_library(),
                "Purchased Electricity",
                100,
                "",
            )

    def test_unsupported_category_and_unit_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "No emission factor"):
            self.run_with_library(
                make_library(),
                "Unknown Category",
                100,
                "kWh",
            )

    def test_invalid_factor_value_is_rejected(self):
        factor = make_factor()
        factor["factor"] = -0.5

        with self.assertRaisesRegex(
            ValueError,
            "finite and non-negative",
        ):
            self.run_with_library(
                make_library([factor]),
                "Purchased Electricity",
                100,
                "kWh",
            )

    def test_boolean_factor_value_is_rejected(self):
        factor = make_factor()
        factor["factor"] = True

        with self.assertRaisesRegex(
            ValueError,
            "valid number",
        ):
            self.run_with_library(
                make_library([factor]),
                "Purchased Electricity",
                100,
                "kWh",
            )

    def test_invalid_library_status_is_rejected(self):
        data = make_library(
            metadata={"status": "invalid_status"}
        )

        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(data)),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Invalid library status",
            ):
                load_emission_library()

    def test_invalid_factor_verification_status_is_rejected(self):
        factor = make_factor()
        factor["verification_status"] = "pending_unknown"

        with self.assertRaisesRegex(
            ValueError,
            "Invalid factor verification status",
        ):
            self.run_with_library(
                make_library([factor]),
                "Purchased Electricity",
                100,
                "kWh",
            )

    def test_load_emission_factors_returns_list(self):
        data = make_library()

        with patch(
            "pathlib.Path.open",
            mock_open(read_data=json.dumps(data)),
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
            with self.assertRaisesRegex(
                ValueError,
                "metadata",
            ):
                load_emission_library()


if __name__ == "__main__":
    unittest.main()
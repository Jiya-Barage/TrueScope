import json
import math
import unittest
from unittest.mock import mock_open, patch

from engine import (
    calculate_emissions,
    load_emission_factors,
    load_emission_library,
)


REVIEW_METADATA_ONLY = {
    "reviewed": True,
    "reviewer": "Reviewer",
    "methodology": "Review method is described, but no source excerpt is attached.",
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
        "provenance": {
            "source_title": None,
            "source_publisher": None,
            "dataset_version": None,
            "publication_year": None,
            "reporting_year": None,
            "geography": None,
            "activity_boundary": None,
            "method": None,
            "rationale": "Source evidence is unavailable.",
        },
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
            "100 kWh \u00d7 0.71 kg CO2/kWh",
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
        self.assertIsNone(result["trust_metadata"]["geography"])
        self.assertEqual(
            result["trust_metadata"]["library_default_geography"],
            "India",
        )
        self.assertTrue(result["trust_metadata"]["verification_required"])
        self.assertFalse(result["trust_metadata"]["factor_verified"])
        self.assertEqual(
            result["validation_status"],
            "unverified_demo_value",
        )

    def test_demo_library_factors_remain_unverified(self):
        expected_factors = {
            "electricity_grid": (
                0.710, "kWh", "kg CO2/kWh",
                "https://www.niti.gov.in/sites/default/files/2026-02/"
                "Scenarios-Towards-Viksit-Bharat-and-Net-Zero-Sectoral-"
                "Insights-Power.pdf",
                None,
            ),
            "Fleet Diesel": (
                2.687, "Litres", "kg CO2e/Litre", None, None,
            ),
            "natural_gas": (
                0.183, "kWh", "kg CO2e/kWh", None, None,
            ),
            "freight_transport": (
                0.602, "tonne-km", "kg CO2e/tonne-km", None, None,
            ),
            "waste_disposal": (
                412.0, "Tonnes", "kg CO2e/Tonne", None, None,
            ),
            "business_travel": (
                0.158, "passenger-km", "kg CO2e/passenger-km", None, None,
            ),
            "Packaging Materials": (
                0.940, "kg", "kg CO2e/kg", None, None,
            ),
            "Water & Effluent": (
                0.344, "m³", "kg CO2e/m³", None, None,
            ),
        }
        factors = load_emission_factors()
        self.assertEqual(
            len(factors),
            len(expected_factors),
            "Update the factor inventory audit when library records change.",
        )
        provenance_fields = {
            "source_title",
            "source_publisher",
            "dataset_version",
            "publication_year",
            "reporting_year",
            "geography",
            "activity_boundary",
            "method",
            "rationale",
        }

        for factor in factors:
            with self.subTest(category=factor["category"]):
                self.assertEqual(
                    (
                        factor["factor"],
                        factor["activity_unit"],
                        factor["factor_unit"],
                        factor.get("source"),
                        factor.get("source_year"),
                    ),
                    expected_factors[factor["category"]],
                )
                self.assertEqual(
                    factor["verification_status"],
                    "unverified_demo_value",
                )
                provenance = factor["provenance"]
                self.assertEqual(set(provenance), provenance_fields)
                self.assertTrue(provenance["rationale"].strip())
                self.assertIsNone(provenance["geography"])
                self.assertIsNone(provenance["activity_boundary"])
                self.assertIsNone(provenance["method"])
                result = calculate_emissions(
                    factor["category"], 1, factor["activity_unit"]
                )
                self.assertEqual(
                    result["validation_status"],
                    "unverified_demo_value",
                )
                self.assertEqual(
                    result["emissions_basis"],
                    "CO2e"
                    if factor["factor_unit"].startswith("kg CO2e/")
                    else "CO2"
                    if factor["factor_unit"].startswith("kg CO2/")
                    else "unspecified",
                )
                self.assertFalse(
                    result["trust_metadata"]["factor_verified"]
                )
                self.assertEqual(
                    result["factor_provenance"],
                    provenance,
                )
                self.assertEqual(
                    result["trust_metadata"]["library_default_geography"],
                    "India",
                )

    def test_placeholder_source_and_year_are_not_verified(self):
        factor = make_factor(
            verification_status="verified",
            source="https://example.com/source",
            source_year=2025,
        )
        result = self.run_with_library(
            make_library([factor]),
            "electricity_grid",
            100,
            "kWh",
        )
        self.assertFalse(
            result["trust_metadata"]["factor_verified"]
        )

    def test_verified_factor_without_source_is_not_verified(self):
        factor = make_factor(
            verification_status="verified",
            source=None,
            source_year=2025,
            verification_evidence={
                "reviewed": True,
                "reviewer": "Reviewer",
                "methodology": "Methodology reviewed",
                "review_date": "2026-10-24",
            },
        )
        result = self.run_with_library(
            make_library([factor]),
            "electricity_grid",
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
            verification_evidence={
                "reviewed": True,
                "reviewer": "Reviewer",
                "methodology": "Methodology reviewed",
                "review_date": "2026-10-24",
            },
        )
        result = self.run_with_library(
            make_library([factor]),
            "electricity_grid",
            100,
            "kWh",
        )
        self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_factor_provenance_is_required_and_validated(self):
        factor = make_factor()
        factor.pop("provenance")
        with self.assertRaisesRegex(ValueError, "provenance metadata"):
            self.run_with_library(make_library([factor]))

        for provenance in (
            {},
            {"rationale": ""},
            {"rationale": "No source", "geography": ""},
        ):
            with self.subTest(provenance=provenance):
                factor = make_factor()
                factor["provenance"] = provenance
                with self.assertRaisesRegex(ValueError, "provenance"):
                    self.run_with_library(make_library([factor]))

    def test_category_matching_is_exact(self):
        with self.assertRaisesRegex(ValueError, "No emission factor"):
            self.run_with_library(make_library(), category="Electricity_grid")

    def test_unit_matching_is_case_insensitive(self):
        result = self.run_with_library(make_library(), quantity=10, unit="KWH")
        self.assertEqual(result["emissions"], 7.1)

    def test_expected_unit_accepts_normalized_aliases(self):
        result = calculate_emissions(
            "electricity_grid",
            10,
            "kWh",
            expected_unit="KWH",
        )
        self.assertEqual(result["emissions"], 7.1)

    def test_expected_unit_mismatch_is_rejected_before_calculation(self):
        with self.assertRaisesRegex(ValueError, "does not match expected unit"):
            calculate_emissions(
                "electricity_grid",
                10,
                "miles",
                expected_unit="kWh",
            )

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
                factor["factor_unit"] = f"kg CO2/{activity_unit}"
                result = self.run_with_library(
                    make_library([factor]), quantity=1, unit=requested_unit
                )
                self.assertEqual(result["activity_unit"], requested_unit)

    def test_verified_status_and_complete_evidence_mark_metadata_complete(self):
        provenance = {
            "source_title": "Grid electricity factor source",
            "source_publisher": "Public energy agency",
            "dataset_version": "2025 edition",
            "publication_year": "2025",
            "reporting_year": "2025",
            "geography": "India",
            "activity_boundary": "Grid electricity generation",
            "method": "Published grid-average method",
            "rationale": "Factor evidence is recorded for review metadata.",
        }
        evidence = {
            **REVIEW_METADATA_ONLY,
            "source_locator": "Table 1",
            "supporting_excerpt": "Grid electricity factor",
            "category": "electricity_grid",
            "factor": 0.710,
            "factor_unit": "kg CO2/kWh",
            "activity_unit": "kWh",
            "source": "https://www.gov.uk/environment",
            "source_year": 2025,
            **{
                key: value
                for key, value in provenance.items()
                if key != "rationale"
            },
        }
        factor = make_factor(
            verification_status="verified",
            source="https://www.gov.uk/environment",
            source_year=2025,
            verification_evidence=evidence,
        )
        factor["provenance"] = provenance
        result = self.run_with_library(
            make_library([factor]), "electricity_grid", 100, "kWh"
        )
        self.assertTrue(result["trust_metadata"]["factor_verified"])

    def test_unverified_factor_stays_unverified_with_complete_evidence(self):
        factor = make_factor(
            source="https://example.com/source",
            source_year=2025,
            verification_evidence={
                "reviewed": True,
                "reviewer": "Reviewer",
                "methodology": "Methodology reviewed",
                "review_date": "2026-10-24",
            },
        )
        result = self.run_with_library(
            make_library([factor]), "electricity_grid", 100, "kWh"
        )
        self.assertEqual(
            result["validation_status"], "unverified_demo_value"
        )
        self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_incomplete_verification_evidence_is_not_verified(self):
        factor = make_factor(
            verification_status="verified",
            source="https://example.com/source",
            source_year=2025,
            verification_evidence={
                "reviewed": True,
                "reviewer": "Reviewer",
                "methodology": "",
                "review_date": "2026-10-24",
            },
        )
        result = self.run_with_library(
            make_library([factor]),
            "electricity_grid",
            100,
            "kWh",
        )
        self.assertFalse(
            result["trust_metadata"]["factor_verified"]
        )

    def test_each_verification_evidence_field_is_required_and_well_formed(self):
        complete_evidence = {
            "reviewed": True,
            "reviewer": "Reviewer",
            "methodology": "Methodology reviewed",
            "review_date": "2026-10-24",
        }
        missing_reviewed = {
            key: value
            for key, value in complete_evidence.items()
            if key != "reviewed"
        }
        invalid_evidence_cases = [
            ("reviewed missing", missing_reviewed),
            ("reviewed false", {**complete_evidence, "reviewed": False}),
            ("reviewed non-boolean", {**complete_evidence, "reviewed": 1}),
        ]

        for field in ("reviewer", "methodology", "review_date"):
            missing = {
                key: value
                for key, value in complete_evidence.items()
                if key != field
            }
            invalid_evidence_cases.extend(
                (
                    (f"{field} missing", missing),
                    (f"{field} blank", {**complete_evidence, field: "  "}),
                    (f"{field} wrong type", {**complete_evidence, field: 1}),
                )
            )

        for case, verification_evidence in invalid_evidence_cases:
            with self.subTest(case=case):
                factor = make_factor(
                    verification_status="verified",
                    source="https://example.com/source",
                    source_year=2025,
                    verification_evidence=verification_evidence,
                )
                result = self.run_with_library(
                    make_library([factor]), "electricity_grid", 100, "kWh"
                )
                self.assertFalse(result["trust_metadata"]["factor_verified"])

    def test_boolean_and_non_positive_source_years_are_not_verified(self):
        invalid_source_years = [True, False, 0, -1]

        for source_year in invalid_source_years:
            with self.subTest(source_year=source_year):
                factor = make_factor(
                    verification_status="verified",
                    source="https://example.com/source",
                    source_year=source_year,
                    verification_evidence={
                        "reviewed": True,
                        "reviewer": "Reviewer",
                        "methodology": "Methodology reviewed",
                        "review_date": "2026-10-24",
                    },
                )
                result = self.run_with_library(
                    make_library([factor]), "electricity_grid", 100, "kWh"
                )
                self.assertFalse(result["trust_metadata"]["factor_verified"])

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

    def test_factor_denominator_must_match_activity_unit(self):
        factor = make_factor(factor_unit="kg CO2/kWh")
        factor["activity_unit"] = "litres"
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.run_with_library(make_library([factor]))

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

    def test_requested_categories_have_no_matching_library_factors(self):
        unsupported_cases = [
            ("water_effluent", 10, "m³"),
            ("mobile_fuel_diesel", 10, "litres"),
            ("stationary_fuel_diesel", 10, "litres"),
            ("purchased_goods", 10, "kg"),
        ]

        for category, quantity, unit in unsupported_cases:
            with self.subTest(category=category, unit=unit):
                with self.assertRaisesRegex(
                    ValueError, "No emission factor found"
                ):
                    calculate_emissions(category, quantity, unit)

    def test_non_emission_category_has_no_emission_factor(self):
        with self.assertRaisesRegex(ValueError, "No emission factor found"):
            calculate_emissions("non_emission", 10, "kWh")

    def test_incompatible_activity_unit_has_no_matching_factor(self):
        with self.assertRaisesRegex(ValueError, "No emission factor found"):
            calculate_emissions("electricity_grid", 10, "miles")

    def test_invalid_factor_value_is_rejected(self):
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
                verification_evidence=REVIEW_METADATA_ONLY,
            ),
            make_factor(
                verification_status="verified",
                source="https://www.gov.uk/environment",
                source_year=None,
                verification_evidence=REVIEW_METADATA_ONLY,
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
                    verification_evidence=REVIEW_METADATA_ONLY,
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
        self.assertEqual(
            result["validation_status"],
            "unverified_demo_value",
        )

    def test_missing_or_incomplete_evidence_is_not_verified(self):
        incomplete_evidence = (
            None,
            [],
            {"reviewed": True},
            {**REVIEW_METADATA_ONLY, "reviewed": 1},
            {**REVIEW_METADATA_ONLY, "reviewer": ""},
            {**REVIEW_METADATA_ONLY, "reviewer": "  "},
            {**REVIEW_METADATA_ONLY, "methodology": ""},
            {**REVIEW_METADATA_ONLY, "methodology": None},
            {**REVIEW_METADATA_ONLY, "review_date": None},
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

    def test_url_year_and_generic_review_do_not_verify_factor(self):
        factor = make_factor(
            verification_status="verified",
            source="https://www.gov.uk/",
            source_year=2025,
            verification_evidence=REVIEW_METADATA_ONLY,
        )
        result = self.run_with_library(make_library([factor]))
        self.assertFalse(result["trust_metadata"]["factor_verified"])
        self.assertEqual(result["validation_status"], "unverified_demo_value")

    def test_verification_evidence_must_match_factor_and_provenance(self):
        factor = make_factor(
            verification_status="verified",
            source="https://www.gov.uk/",
            source_year=2025,
            verification_evidence={
                **REVIEW_METADATA_ONLY,
                "source_locator": "Table not actually reviewed",
            },
        )
        result = self.run_with_library(make_library([factor]))
        self.assertFalse(result["trust_metadata"]["factor_verified"])
        self.assertEqual(
            result["validation_status"],
            "unverified_demo_value",
        )

    def test_invalid_review_dates_are_not_verified(self):
        for review_date in ("2025-02-30", "2025-2-03", "20250203", " 2025-02-03"):
            with self.subTest(review_date=review_date):
                factor = make_factor(
                    verification_status="verified",
                    source="https://www.gov.uk/environment",
                    source_year=2025,
                    verification_evidence={
                        **REVIEW_METADATA_ONLY,
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
                    verification_evidence=REVIEW_METADATA_ONLY,
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


import importlib.util
import math
import sys
import tempfile
import uuid
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, TypedDict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend import storage


InvoiceStatus = Literal["queued", "processing", "completed", "failed"]


class InvoiceRecord(TypedDict):
    status: InvoiceStatus
    result: dict[str, Any] | None
    error: dict[str, str] | None
    source: dict[str, str]


class DemoRequest(BaseModel):
    demo_id: str


INVOICE_RECORDS: dict[str, InvoiceRecord] = {}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


DEMO_RECORDS: dict[str, dict[str, Any]] = {
    "INV-2024-001": {
        "id": "INV-2024-001",
        "invoiceNumber": "INV-CONED-8821",
        "supplier": "ConEdison Energy Co.",
        "date": "2024-09-14",
        "billingPeriod": "01 Aug 2024 - 31 Aug 2024",
        "totalAmount": 3840.50,
        "currency": "USD",
        "itemDescription": "Grid Electricity Consumption (Facility Meter #402)",
        "quantity": 14200,
        "unit": "kWh",
        "activityCategory": "Purchased Electricity",
        "scope": "Scope 2",
        "emissionFactor": 0.385,
        "emissionFactorUnit": "kg CO₂e / kWh",
        "emissionFactorNote": "Demo Mock Factor - Unverified (Regional Grid Avg)",
        "calculatedEmissionsKg": 5467,
        "confidence": 98,
        "confidenceLevel": "high",
        "status": "Processed",
        "extractedFields": {
            "accountNumber": "CE-9402-991",
            "invoicePeriod": "Aug 2024",
            "taxAmount": 245.00,
            "meterReadType": "Smart Meter Actual",
        },
    },
    "INV-2024-003": {
        "id": "INV-2024-003",
        "invoiceNumber": "NG-HEAT-77314",
        "supplier": "National Grid Utilities",
        "date": "2024-09-28",
        "billingPeriod": "01 Sep 2024 - 25 Sep 2024",
        "totalAmount": 1845.20,
        "currency": "USD",
        "itemDescription": "Natural Gas Space & Warehouse Heating",
        "quantity": 9400,
        "unit": "kWh",
        "activityCategory": "Natural Gas Heating",
        "scope": "Scope 1",
        "emissionFactor": 0.183,
        "emissionFactorUnit": "kg CO₂e / kWh",
        "emissionFactorNote": "Demo Mock Factor - Unverified (Stationary Combustion)",
        "calculatedEmissionsKg": 1720,
        "confidence": 94,
        "confidenceLevel": "high",
        "status": "Processed",
        "extractedFields": {
            "accountNumber": "NG-002-7119",
            "thermalUnits": "320 Therms",
            "taxAmount": 110.00,
            "meterReadType": "Gas Meter Actual",
        },
    },
}


app = FastAPI(title="TrueScope API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"^http://(?:localhost|127\.0\.0\.1):517[3-9]$",
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Accept", "Content-Type"],
    allow_credentials=False,
)


def _invoice_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "invoice_not_found",
            "message": "Invoice not found.",
        },
    )


def _save_invoice_record(
    invoice_id: str,
    record: InvoiceRecord,
) -> None:
    storage.save_invoice(invoice_id, record)
    INVOICE_RECORDS[invoice_id] = record


def _get_invoice_record(invoice_id: str) -> InvoiceRecord | None:
    record = INVOICE_RECORDS.get(invoice_id)
    if record is None:
        record = storage.get_invoice(invoice_id)
        if record is not None:
            INVOICE_RECORDS[invoice_id] = record
    return record


def _run_ai_pipeline(path: str, invoice_id: str) -> dict[str, Any]:
    from ai.pipeline import run

    return run(path, invoice_id=invoice_id)


def _is_invalid_document_error(error: Exception) -> bool:
    if isinstance(error, OSError):
        message = str(error)
        if (
            message.startswith("image file is truncated")
            or message == "Truncated File Read"
        ):
            return True

    invalid_document_types: list[type[BaseException]] = []

    try:
        from PIL import Image, UnidentifiedImageError

        invalid_document_types.extend(
            (UnidentifiedImageError, Image.DecompressionBombError)
        )
    except ImportError:
        pass

    try:
        from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError

        invalid_document_types.extend(
            (PDFPageCountError, PDFSyntaxError)
        )
    except ImportError:
        pass

    return bool(invalid_document_types) and isinstance(
        error,
        tuple(invalid_document_types),
    )


@lru_cache(maxsize=1)
def _load_emission_engine() -> Any:
    engine_path = (
        Path(__file__).resolve().parent.parent
        / "emission-engine"
        / "engine.py"
    )

    spec = importlib.util.spec_from_file_location(
        "truescope_emission_engine",
        engine_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the emission engine.")

    engine = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = engine
    spec.loader.exec_module(engine)

    return engine


def _calculate_emissions(
    category: str,
    quantity: int | float,
    unit: str,
    expected_unit: str | None = None,
) -> dict[str, Any]:
    engine = _load_emission_engine()
    return engine.calculate_emissions(
        category,
        quantity,
        unit,
        expected_unit=expected_unit,
    )


def _validate_ai_result(result: Any) -> None:
    if not isinstance(result, dict):
        raise TypeError("AI pipeline result must be an object.")

    line_items = result.get("line_items")

    if not isinstance(line_items, list):
        raise TypeError(
            "AI pipeline result must contain a line_items list."
        )

    if any(not isinstance(item, dict) for item in line_items):
        raise TypeError(
            "Each AI pipeline line item must be an object."
        )

    warnings = result.get("warnings", [])
    if warnings is None:
        result["warnings"] = []
    elif not isinstance(warnings, list):
        result["warnings"] = [] if warnings == "" else [warnings]
    else:
        result["warnings"] = warnings

    warnings = [
        warning if isinstance(warning, str) else str(warning)
        for warning in result["warnings"]
    ]
    result["warnings"] = warnings
    for index, item in enumerate(line_items, start=1):
        category = item.get("category")
        if not isinstance(category, str) or not category.strip():
            item["category"] = "unknown"
            warnings.append(
                f"Line {index}: Invalid or missing activity category requires review."
            )

        unit = item.get("unit")
        if unit is not None and (
            not isinstance(unit, str) or not unit.strip()
        ):
            item["unit"] = None
            warnings.append(
                f"Line {index}: Invalid activity unit was omitted."
            )

        scope = item.get("scope")
        if scope is not None and (
            isinstance(scope, bool)
            or not isinstance(scope, int)
            or scope not in {1, 2, 3}
        ):
            item["scope"] = None
            warnings.append(
                f"Line {index}: Invalid scope value was omitted."
            )

        quantity = item.get("quantity")
        if isinstance(quantity, bool) or (
            quantity is not None
            and not isinstance(quantity, (int, float))
        ):
            item["quantity"] = None
            warnings.append(
                f"Line {index}: Invalid activity quantity was omitted."
            )
            quantity = None

        if isinstance(quantity, float) and not math.isfinite(quantity):
            item["quantity"] = None
            warnings.append(
                f"Line {index}: Non-finite activity quantity was omitted."
            )

        for field in ("amount", "confidence"):
            value = item.get(field)
            if isinstance(value, float) and not math.isfinite(value):
                item[field] = None
                warnings.append(
                    f"Line {index}: Non-finite {field} value was omitted."
                )

        confidence = item.get("confidence")
        if (
            confidence is not None
            and (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1
            )
        ):
            item["confidence"] = None
            item["confidence_flag"] = "low"
            warnings.append(
                f"Line {index}: Invalid confidence value requires review."
            )


def _enrich_emission_calculations(result: dict[str, Any]) -> None:
    line_items = result.get("line_items", [])
    warnings = result.get("warnings", [])
    if warnings is None:
        warnings = []
    elif not isinstance(warnings, list):
        warnings = [] if warnings == "" else [warnings]
    result["warnings"] = warnings

    emission_items = [
        item
        for item in line_items
        if item.get("category") != "non_emission"
    ]

    all_calculated = bool(emission_items)

    for index, item in enumerate(line_items, start=1):
        category = item.get("category")
        quantity = item.get("quantity")
        unit = item.get("unit")

        existing_reasons = item.get("review_reasons", [])
        if category == "non_emission" and isinstance(existing_reasons, (list, tuple)):
            review_reasons = list(existing_reasons)
        elif category == "non_emission" and isinstance(existing_reasons, str):
            review_reasons = [existing_reasons]
        else:
            review_reasons = []

        original_review_required = (
            category == "non_emission"
            and item.get("review_required") is True
        )

        description = item.get("description")
        if not isinstance(description, str) or not description.strip():
            item["description"] = "Description unavailable"
            review_reasons.append("Line-item description is missing or invalid.")
            warnings.append(
                f"Line {index}: Description is missing or invalid; review required."
            )

        calculation: dict[str, Any] | None = None
        calculation_reason: str | None = None

        if category == "non_emission":
            calculation_reason = (
                "Emission calculation is not applicable to this line item."
            )
        elif (
            not isinstance(category, str)
            or not category.strip()
            or category == "unknown"
        ):
            calculation_reason = (
                "Activity category is unknown or missing."
            )
        elif (
            quantity is None
            or not isinstance(unit, str)
            or not unit.strip()
        ):
            calculation_reason = (
                "Activity quantity and unit are required for emission calculation."
            )
        elif isinstance(quantity, bool) or not isinstance(
            quantity, (int, float)
        ):
            calculation_reason = "Activity quantity is not numeric."
        elif not math.isfinite(quantity):
            calculation_reason = "Activity quantity must be finite."
        else:
            try:
                expected_unit = item.get("expected_unit")
                if expected_unit is None:
                    calculation = _calculate_emissions(
                        category,
                        quantity,
                        unit,
                    )
                else:
                    calculation = _calculate_emissions(
                        category,
                        quantity,
                        unit,
                        expected_unit,
                    )

                emission_value = (
                    calculation.get("emissions")
                    if isinstance(calculation, dict)
                    else None
                )
                emissions_basis = (
                    calculation.get("emissions_basis")
                    if isinstance(calculation, dict)
                    else None
                )
                emissions_unit = (
                    calculation.get("emissions_unit")
                    if isinstance(calculation, dict)
                    else None
                )

                if (
                    not isinstance(calculation, dict)
                    or isinstance(emission_value, bool)
                    or not isinstance(emission_value, (int, float))
                    or not math.isfinite(emission_value)
                    or emission_value < 0
                    or emissions_basis not in {"CO2", "CO2e", "unspecified"}
                    or emissions_unit != f"kg {emissions_basis}"
                ):
                    calculation = None
                    calculation_reason = (
                        "The emission engine returned an invalid result."
                    )

            except ValueError as exc:
                if str(exc).startswith(
                    "Activity unit '"
                ) and "does not match expected unit" in str(exc):
                    calculation_reason = (
                        "Activity unit is incompatible with the expected "
                        "unit for this category."
                    )
                elif str(exc).startswith("No emission factor found"):
                    calculation_reason = (
                        "No emission factor matches this category and unit."
                    )
                else:
                    calculation_reason = (
                        "The emission engine rejected this activity quantity or unit."
                    )
            except Exception:
                calculation_reason = "Emission calculation failed."

        if calculation is None:
            if category != "non_emission":
                all_calculated = False
                review_reasons.append(
                    calculation_reason
                    or "Emission calculation was skipped."
                )
                warnings.append(
                    f"Line {index}: {review_reasons[-1]}"
                )
        else:
            trust_metadata = calculation.get("trust_metadata", {})

            if not isinstance(trust_metadata, dict):
                trust_metadata = {}

            if (
                trust_metadata.get("verification_required")
                and not trust_metadata.get("factor_verified", False)
            ):
                review_reasons.append(
                    "Emission factor verification is required."
                )
                warnings.append(
                    f"Line {index}: Emission factor is unverified and requires review."
                )

        confidence = item.get("confidence")

        if item.get("confidence_flag") == "low" or (
            isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and confidence < 0.5
        ):
            review_reasons.append("AI confidence is low.")

        item["emission_calculation"] = calculation
        item["calculation_status"] = (
            "not_applicable"
            if category == "non_emission"
            else "calculated"
            if calculation is not None
            else "skipped"
        )
        item["calculation_reason"] = calculation_reason
        item["review_required"] = (
            original_review_required or bool(review_reasons)
        )
        item["review_reasons"] = review_reasons

    result["processing_status"] = "completed"
    result["emission_calculation_status"] = (
        "not_applicable"
        if not emission_items
        else "complete"
        if all_calculated
        else "partial"
    )


def _uploaded_report(record: InvoiceRecord) -> dict[str, Any]:
    result = record["result"] or {}
    line_items = deepcopy(result.get("line_items", []))

    totals_by_unit: dict[tuple[str, str], dict[str, Any]] = {}
    totals_by_category: dict[tuple[str, str, str], dict[str, Any]] = {}

    for item in line_items:
        calculation = item.get("emission_calculation")

        if (
            item.get("category") == "non_emission"
            or item.get("calculation_status") != "calculated"
            or not isinstance(calculation, dict)
        ):
            continue

        emissions = calculation.get("emissions")
        emissions_unit = calculation.get("emissions_unit")
        emissions_basis = calculation.get("emissions_basis")

        if (
            isinstance(emissions, bool)
            or not isinstance(emissions, (int, float))
            or not math.isfinite(emissions)
            or not isinstance(emissions_unit, str)
            or not emissions_unit.strip()
            or not isinstance(emissions_basis, str)
            or not emissions_basis.strip()
        ):
            continue

        unit_key = (emissions_basis, emissions_unit)

        unit_total = totals_by_unit.setdefault(
            unit_key,
            {
                "emissions_basis": emissions_basis,
                "emissions_unit": emissions_unit,
                "total": 0.0,
                "successful_line_items": 0,
            },
        )

        unit_total["total"] += emissions
        unit_total["successful_line_items"] += 1

        category = item.get("category")
        category_label = (
            category if isinstance(category, str) else "unknown"
        )
        category_key = (
            category_label,
            emissions_basis,
            emissions_unit,
        )

        category_total = totals_by_category.setdefault(
            category_key,
            {
                "category": category_label,
                "emissions_basis": emissions_basis,
                "emissions_unit": emissions_unit,
                "total": 0.0,
                "successful_line_items": 0,
            },
        )

        category_total["total"] += emissions
        category_total["successful_line_items"] += 1

    by_unit = list(totals_by_unit.values())
    by_category = list(totals_by_category.values())

    for group in by_unit + by_category:
        group["total"] = round(group["total"], 3)

    valid_calculation_count = sum(
        group["successful_line_items"]
        for group in by_unit
    )

    emission_line_count = sum(
        item.get("category") != "non_emission"
        for item in line_items
    )

    excluded_line_count = max(
        0,
        emission_line_count - valid_calculation_count,
    )

    if len(by_unit) == 1:
        only_total = by_unit[0]
        complete = excluded_line_count == 0

        total_reason = (
            None
            if complete
            else (
                f"Subtotal includes {valid_calculation_count} successful "
                f"calculation(s); {excluded_line_count} line item(s) "
                "were not included."
            )
        )

        total = {
            "value": round(only_total["total"], 3),
            "emissions_basis": only_total["emissions_basis"],
            "emissions_unit": only_total["emissions_unit"],
            "complete": complete,
            "reason": total_reason,
        }
    elif not by_unit:
        total = {
            "value": None,
            "emissions_basis": None,
            "emissions_unit": None,
            "complete": False,
            "reason": (
                "No successful engine calculations are available "
                "for an emissions total."
            ),
        }
    else:
        total = {
            "value": None,
            "emissions_basis": None,
            "emissions_unit": None,
            "complete": False,
            "reason": (
                "Successful calculations use incompatible emissions "
                "bases or units; see grouped totals."
            ),
        }

    review_warnings = [
        {
            "line_number": index,
            "reasons": list(item["review_reasons"]),
        }
        for index, item in enumerate(line_items, start=1)
        if item.get("review_required")
        and item.get("review_reasons")
    ]

    return {
        "invoice_id": result.get("invoice_id"),
        "processing_status": record["status"],
        "emission_calculation_status": result.get(
            "emission_calculation_status"
        ),
        "source": record.get("source", result.get("source")),
        "invoice": {
            key: result.get(key)
            for key in (
                "source_file",
                "vendor",
                "invoice_date",
                "invoice_number",
                "currency",
                "overall_confidence",
            )
        },
        "line_items": line_items,
        "warnings": list(result.get("warnings", [])),
        "review_warnings": review_warnings,
        "totals": {
            "successful_calculations_by_emissions_unit": by_unit,
            "successful_calculations_by_category": by_category,
            "successful_calculation_total": total,
        },
    }


def _demo_report(record: InvoiceRecord) -> dict[str, Any]:
    result = record["result"] or {}

    mock_emissions_note = result.get(
        "emission_calculation_note",
        "Predefined demo emissions are mock values, not engine calculations.",
    )

    line_item = {
        "description": result.get("itemDescription"),
        "quantity": result.get("quantity"),
        "unit": result.get("unit"),
        "activity_category": result.get("activityCategory"),
        "scope": result.get("scope"),
        "confidence_percent": result.get("confidence"),
        "confidence_level": result.get("confidenceLevel"),
        "emission_calculation": None,
        "calculation_status": "predefined_demo_value",
        "predefined_demo_emissions": {
            "value": result.get("calculatedEmissionsKg"),
            "emissions_unit": "kg CO2e",
            "provenance": "synthetic_demo_mock",
            "note": mock_emissions_note,
            "emission_factor": result.get("emissionFactor"),
            "factor_unit": result.get("emissionFactorUnit"),
            "factor_note": result.get("emissionFactorNote"),
        },
        "review_required": False,
        "review_reasons": [],
    }

    return {
        "invoice_id": result.get("invoice_id"),
        "processing_status": record["status"],
        "emission_calculation_status": result.get(
            "emission_calculation_status"
        ),
        "source": record.get("source", result.get("source")),
        "invoice": {
            key: result.get(key)
            for key in (
                "id",
                "invoiceNumber",
                "supplier",
                "date",
                "billingPeriod",
                "totalAmount",
                "currency",
            )
        },
        "line_items": [line_item],
        "warnings": [mock_emissions_note],
        "review_warnings": [],
        "totals": {
            "successful_calculations_by_emissions_unit": [],
            "successful_calculations_by_category": [],
            "successful_calculation_total": {
                "value": None,
                "emissions_basis": None,
                "emissions_unit": None,
                "complete": False,
                "reason": (
                    "Demo emissions are predefined mock values; "
                    "no engine calculation is available to aggregate."
                ),
            },
        },
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/invoices")
def list_invoices() -> dict[str, list[dict[str, Any]]]:
    invoices = []
    for invoice_id, record in storage.list_invoices():
        INVOICE_RECORDS[invoice_id] = record
        invoices.append(
            {
                "invoice_id": invoice_id,
                "status": record["status"],
                "result": record["result"],
                "error": record["error"],
                "source": record["source"],
            }
        )
    return {"invoices": invoices}


@app.post("/api/invoices/demo")
def load_demo_invoice(request: DemoRequest) -> dict[str, Any]:
    demo_record = DEMO_RECORDS.get(request.demo_id)

    if demo_record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "demo_not_found",
                "message": "Demo invoice not found.",
            },
        )

    invoice_id = f"demo_{request.demo_id}"
    result = deepcopy(demo_record)

    result.update(
        {
            "invoice_id": invoice_id,
            "source": {
                "kind": "demo",
                "label": "synthetic_demo",
                "record_id": request.demo_id,
            },
            "data_provenance": "synthetic_demo",
            "processing_status": "completed",
            "emission_calculation_status": "predefined_demo_value",
            "emission_calculation_note": (
                "Emission factor and emissions are predefined frontend demo "
                "values; the emission engine was not invoked and the factor "
                "is unverified."
            ),
        }
    )

    _save_invoice_record(
        invoice_id,
        {
            "status": "completed",
            "result": result,
            "error": None,
            "source": result["source"],
        },
    )

    return {
        "invoice_id": invoice_id,
        "status": "completed",
        "result": result,
    }


@app.delete("/api/invoices/{invoice_id}")
def delete_invoice(invoice_id: str) -> dict[str, str]:
    if _get_invoice_record(invoice_id) is None:
        raise _invoice_not_found()

    storage.delete_invoice(invoice_id)
    INVOICE_RECORDS.pop(invoice_id, None)
    return {"invoice_id": invoice_id, "status": "deleted"}


@app.post("/api/invoices/upload")
async def upload_invoice(request: Request) -> dict[str, Any]:
    form = await request.form()
    uploaded_files = form.getlist("file")

    if (
        len(uploaded_files) != 1
        or not hasattr(uploaded_files[0], "filename")
        or not hasattr(uploaded_files[0], "read")
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "file_required",
                "message": "Exactly one invoice file is required.",
            },
        )

    uploaded_file = uploaded_files[0]

    original_name = (
        (uploaded_file.filename or "")
        .replace("\\", "/")
        .rsplit("/", 1)[-1]
    )

    extension = Path(original_name).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "unsupported_file_type",
                "message": (
                    "Supported invoice formats are PDF, PNG, JPG, and JPEG."
                ),
            },
        )

    temporary_path: str | None = None

    try:
        total_size = 0

        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name

            while chunk := await uploaded_file.read(64 * 1024):
                total_size += len(chunk)

                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "code": "file_too_large",
                            "message": (
                                "Invoice files must be 10 MiB or smaller."
                            ),
                        },
                    )

                temporary_file.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "empty_file",
                    "message": "The uploaded invoice file is empty.",
                },
            )

        invoice_id = f"inv_{uuid.uuid4().hex}"

        source = {
            "kind": "upload",
            "label": "uploaded_invoice",
            "filename": original_name,
        }

        _save_invoice_record(
            invoice_id,
            {
                "status": "processing",
                "result": None,
                "error": None,
                "source": source,
            },
        )

        try:
            result = await run_in_threadpool(
                _run_ai_pipeline,
                temporary_path,
                invoice_id,
            )
        except (FileNotFoundError, ValueError):
            _save_invoice_record(
                invoice_id,
                {
                    "status": "failed",
                    "result": None,
                    "error": {
                        "code": "invalid_invoice_file",
                        "message": (
                            "The invoice file could not be processed. "
                            "Check that it is a valid supported document."
                        ),
                    },
                    "source": source,
                },
            )

            raise HTTPException(
                status_code=422,
                detail=_get_invoice_record(invoice_id)["error"],
            ) from None
        except Exception as exc:
            print("AI PIPELINE ERROR:", repr(exc))
            is_invalid_document = _is_invalid_document_error(exc)

            error = (
                {
                    "code": "invalid_invoice_file",
                    "message": "The invoice file is invalid or corrupt.",
                }
                if is_invalid_document
                else {
                    "code": "processing_failed",
                    "message": "Invoice processing failed.",
                }
            )

            status_code = 422 if is_invalid_document else 500

            _save_invoice_record(
                invoice_id,
                {
                    "status": "failed",
                    "result": None,
                    "error": error,
                    "source": source,
                },
            )

            raise HTTPException(
                status_code=status_code,
                detail=_get_invoice_record(invoice_id)["error"],
            ) from None

        try:
            _validate_ai_result(result)
            result["source_file"] = original_name
            result["source"] = source

            await run_in_threadpool(
                _enrich_emission_calculations,
                result,
            )
        except Exception as exc:
            print("UPLOAD PROCESSING ERROR:", repr(exc))

            _save_invoice_record(
                invoice_id,
                {
                    "status": "failed",
                    "result": None,
                    "error": {
                        "code": "processing_failed",
                        "message": "Invoice processing failed.",
                    },
                    "source": source,
                },
            )

            raise HTTPException(
                status_code=500,
                detail=_get_invoice_record(invoice_id)["error"],
            ) from None

        _save_invoice_record(
            invoice_id,
            {
                "status": "completed",
                "result": result,
                "error": None,
                "source": source,
            },
        )

        return {
            "invoice_id": invoice_id,
            "status": "completed",
            "result": result,
        }

    finally:
        if temporary_path is not None:
            Path(temporary_path).unlink(missing_ok=True)


@app.get("/api/invoices/{invoice_id}/status")
def get_invoice_status(invoice_id: str) -> dict[str, Any]:
    record = _get_invoice_record(invoice_id)

    if record is None:
        raise _invoice_not_found()

    return {
        "invoice_id": invoice_id,
        "status": record["status"],
        "error": record["error"],
        "source": record.get("source"),
    }


@app.get("/api/invoices/{invoice_id}/results")
def get_invoice_results(invoice_id: str) -> dict[str, Any]:
    record = _get_invoice_record(invoice_id)

    if record is None:
        raise _invoice_not_found()

    if record["status"] != "completed" or record["result"] is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invoice_not_complete",
                "message": (
                    "Invoice results are not available until processing is complete."
                ),
            },
        )

    return record["result"]


@app.get("/api/invoices/{invoice_id}/report")
def get_invoice_report(invoice_id: str) -> dict[str, Any]:
    record = _get_invoice_record(invoice_id)

    if record is None:
        raise _invoice_not_found()

    if record["status"] != "completed" or record["result"] is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invoice_report_unavailable",
                "message": (
                    "A report is available only after invoice processing completes."
                ),
                "processing_status": record["status"],
                "error": record["error"],
            },
        )

    if record.get("source", {}).get("kind") == "demo":
        return _demo_report(record)

    return _uploaded_report(record)

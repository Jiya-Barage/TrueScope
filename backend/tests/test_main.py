import importlib.util
import sys
import os
from io import BytesIO
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request

from backend import main
from backend.main import INVOICE_RECORDS, app


client = TestClient(app)


def _post_upload(monkeypatch, filename, content, media_type):
    if importlib.util.find_spec("multipart"):
        return client.post(
            "/api/invoices/upload",
            files={"file": (filename, content, media_type)},
        )

    form = FormData([("file", UploadFile(file=BytesIO(content), filename=filename))])

    class FormContext:
        async def __aenter__(self):
            return form

        async def __aexit__(self, exc_type, exc_value, traceback):
            await form.close()

    monkeypatch.setattr(Request, "form", lambda request: FormContext())
    return client.post("/api/invoices/upload")


def _mock_ai_pipeline(monkeypatch, runner):
    pipeline_module = ModuleType("ai.pipeline")
    pipeline_module.run = runner
    monkeypatch.setitem(sys.modules, "ai.pipeline", pipeline_module)


def _mock_document_exception_types(monkeypatch):
    class UnidentifiedImageError(OSError):
        pass

    class DecompressionBombError(Exception):
        pass

    class PDFPageCountError(Exception):
        pass

    class PDFSyntaxError(Exception):
        pass

    class PDFInfoNotInstalledError(Exception):
        pass

    pil_module = ModuleType("PIL")
    image_module = ModuleType("PIL.Image")
    pil_module.Image = image_module
    pil_module.UnidentifiedImageError = UnidentifiedImageError
    image_module.DecompressionBombError = DecompressionBombError
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", image_module)

    pdf2image_module = ModuleType("pdf2image")
    pdf2image_module.__path__ = []
    pdf_exceptions_module = ModuleType("pdf2image.exceptions")
    pdf_exceptions_module.PDFPageCountError = PDFPageCountError
    pdf_exceptions_module.PDFSyntaxError = PDFSyntaxError
    pdf_exceptions_module.PDFInfoNotInstalledError = PDFInfoNotInstalledError
    monkeypatch.setitem(sys.modules, "pdf2image", pdf2image_module)
    monkeypatch.setitem(sys.modules, "pdf2image.exceptions", pdf_exceptions_module)

    return {
        "UnidentifiedImageError": UnidentifiedImageError,
        "PDFPageCountError": PDFPageCountError,
        "PDFInfoNotInstalledError": PDFInfoNotInstalledError,
    }


def _upload_with_pipeline_error(monkeypatch, filename, error):
    calls = {}

    def failing_pipeline(path, invoice_id):
        calls["path"] = path
        calls["invoice_id"] = invoice_id
        raise error

    _mock_ai_pipeline(monkeypatch, failing_pipeline)
    response = _post_upload(monkeypatch, filename, b"corrupt document bytes", "application/octet-stream")
    return response, calls


def _ai_result(line_items):
    return {
        "invoice_id": "placeholder",
        "source_file": "temporary.pdf",
        "vendor": "Example Energy",
        "invoice_date": "2026-10-18",
        "invoice_number": "EX-1042",
        "currency": "GBP",
        "line_items": line_items,
        "overall_confidence": 0.82,
        "warnings": ["Original AI warning"],
    }


def _line_item(**overrides):
    item = {
        "description": "Grid electricity",
        "quantity": 100,
        "unit": "kWh",
        "amount": 50,
        "category": "electricity_grid",
        "scope": 2,
        "confidence": 0.85,
        "confidence_flag": "high",
        "reasons": ["Matched electricity keyword"],
    }
    item.update(overrides)
    return item


def _upload_ai_result(monkeypatch, result, calculate):
    _mock_ai_pipeline(
        monkeypatch,
        lambda path, invoice_id: {**result, "invoice_id": invoice_id},
    )
    monkeypatch.setattr(main, "_calculate_emissions", calculate)
    return _post_upload(monkeypatch, "utility.pdf", b"invoice bytes", "application/pdf")


@pytest.fixture(autouse=True)
def clear_invoice_records():
    INVOICE_RECORDS.clear()
    yield
    INVOICE_RECORDS.clear()


def test_health():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_allows_vite_origin_for_json_post():
    response = client.options(
        "/api/invoices/demo",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_cors_adds_allow_origin_for_configured_frontend():
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_does_not_allow_unconfigured_origin():
    response = client.get("/api/health", headers={"Origin": "http://localhost:5174"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_unknown_invoice_status():
    response = client.get("/api/invoices/missing/status")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {"code": "invoice_not_found", "message": "Invoice not found."}
    }


def test_unknown_invoice_results():
    response = client.get("/api/invoices/missing/results")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {"code": "invoice_not_found", "message": "Invoice not found."}
    }


def test_results_before_completion():
    INVOICE_RECORDS["inv_processing"] = {
        "status": "processing",
        "result": None,
        "error": None,
    }

    response = client.get("/api/invoices/inv_processing/results")

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "invoice_not_complete",
            "message": "Invoice results are not available until processing is complete.",
        }
    }


def test_results_for_completed_invoice():
    expected_result = {"invoice_id": "inv_completed", "line_items": []}
    INVOICE_RECORDS["inv_completed"] = {
        "status": "completed",
        "result": expected_result,
        "error": None,
    }

    response = client.get("/api/invoices/inv_completed/results")

    assert response.status_code == 200
    assert response.json() == expected_result


def test_successful_upload_invokes_pipeline_and_stores_result(monkeypatch):
    calls = {}
    pipeline_result = {
        "invoice_id": "placeholder",
        "source_file": "temporary.pdf",
        "vendor": "Example Energy",
        "line_items": [],
        "overall_confidence": 0.0,
        "warnings": [],
    }

    def fake_pipeline(path, invoice_id):
        calls["path"] = path
        calls["invoice_id"] = invoice_id
        assert path.endswith(".pdf")
        assert os.path.isfile(path)
        pipeline_result["invoice_id"] = invoice_id
        return dict(pipeline_result)

    _mock_ai_pipeline(monkeypatch, fake_pipeline)
    response = _post_upload(monkeypatch, "utility.pdf", b"invoice bytes", "application/pdf")

    assert response.status_code == 200
    payload = response.json()
    assert payload["invoice_id"] == calls["invoice_id"]
    assert payload["status"] == "completed"
    assert payload["result"]["source_file"] == "utility.pdf"
    assert payload["result"]["vendor"] == "Example Energy"
    assert calls["path"]
    assert not os.path.exists(calls["path"])
    assert INVOICE_RECORDS[calls["invoice_id"]]["result"] == payload["result"]


def test_upload_rejects_unsupported_extension(monkeypatch):
    response = _post_upload(monkeypatch, "invoice.txt", b"data", "text/plain")

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_file_type"


def test_upload_rejects_empty_file(monkeypatch):
    response = _post_upload(monkeypatch, "empty.png", b"", "image/png")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_file"


def test_upload_requires_exactly_one_file(monkeypatch):
    form = FormData(
        [
            ("file", UploadFile(file=BytesIO(b"one"), filename="one.pdf")),
            ("file", UploadFile(file=BytesIO(b"two"), filename="two.pdf")),
        ]
    )

    class FormContext:
        def __await__(self):
            async def resolve():
                return form
            return resolve().__await__()

        async def __aenter__(self):
            return form

        async def __aexit__(self, exc_type, exc_value, traceback):
            await form.close()

    monkeypatch.setattr(Request, "form", lambda request: FormContext())
    response = client.post("/api/invoices/upload")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "file_required"


def test_pipeline_failure_is_safe_and_status_is_failed(monkeypatch):
    calls = {}

    def failing_pipeline(path, invoice_id):
        calls["path"] = path
        calls["invoice_id"] = invoice_id
        raise RuntimeError(f"failure at {path}")

    _mock_ai_pipeline(monkeypatch, failing_pipeline)
    response = _post_upload(monkeypatch, "scan.jpg", b"image bytes", "image/jpeg")

    assert response.status_code == 500
    assert response.json()["detail"] == {
        "code": "processing_failed",
        "message": "Invoice processing failed.",
    }
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.json()["status"] == "failed"
    assert status_response.json()["error"]["message"] == "Invoice processing failed."
    assert calls["path"]
    assert not os.path.exists(calls["path"])


def test_corrupt_image_returns_422_and_marks_invoice_failed(monkeypatch):
    exception_types = _mock_document_exception_types(monkeypatch)
    response, calls = _upload_with_pipeline_error(
        monkeypatch,
        "corrupt.png",
        exception_types["UnidentifiedImageError"]("cannot identify image file"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "invalid_invoice_file",
        "message": "The invoice file is invalid or corrupt.",
    }
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.json()["status"] == "failed"
    assert status_response.json()["error"]["code"] == "invalid_invoice_file"
    assert not os.path.exists(calls["path"])


@pytest.mark.parametrize(
    "message",
    ["image file is truncated (1 bytes not processed)", "Truncated File Read"],
)
def test_truncated_image_oserror_returns_422(monkeypatch, message):
    _mock_document_exception_types(monkeypatch)
    response, calls = _upload_with_pipeline_error(
        monkeypatch,
        "truncated.jpg",
        OSError(message),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_invoice_file"
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.json()["status"] == "failed"
    assert not os.path.exists(calls["path"])


def test_corrupt_pdf_returns_422_and_marks_invoice_failed(monkeypatch):
    exception_types = _mock_document_exception_types(monkeypatch)
    response, calls = _upload_with_pipeline_error(
        monkeypatch,
        "corrupt.pdf",
        exception_types["PDFPageCountError"]("Unable to get page count"),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_invoice_file"
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.json()["status"] == "failed"
    assert not os.path.exists(calls["path"])


def test_missing_poppler_remains_server_error(monkeypatch):
    exception_types = _mock_document_exception_types(monkeypatch)
    response, calls = _upload_with_pipeline_error(
        monkeypatch,
        "invoice.pdf",
        exception_types["PDFInfoNotInstalledError"]("Unable to get page count"),
    )

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "processing_failed"
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.json()["status"] == "failed"
    assert not os.path.exists(calls["path"])


def test_unrelated_oserror_remains_server_error(monkeypatch):
    response, calls = _upload_with_pipeline_error(
        monkeypatch,
        "invoice.jpg",
        OSError("disk I/O failure"),
    )

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "processing_failed"
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.json()["status"] == "failed"
    assert not os.path.exists(calls["path"])


@pytest.mark.parametrize(
    "pipeline_result",
    [
        None,
        {"vendor": "Example Energy", "warnings": []},
        {"vendor": "Example Energy", "line_items": None, "warnings": []},
        {"vendor": "Example Energy", "line_items": ["not an item object"], "warnings": []},
    ],
    ids=["non-dictionary", "missing-line-items", "null-line-items", "malformed-line-entry"],
)
def test_malformed_pipeline_result_returns_safe_error_and_failed_status(
    monkeypatch,
    pipeline_result,
):
    calls = {}

    def malformed_pipeline(path, invoice_id):
        calls["path"] = path
        calls["invoice_id"] = invoice_id
        return pipeline_result

    _mock_ai_pipeline(monkeypatch, malformed_pipeline)
    response = _post_upload(monkeypatch, "malformed.png", b"image bytes", "image/png")

    assert response.status_code == 500
    assert response.json()["detail"] == {
        "code": "processing_failed",
        "message": "Invoice processing failed.",
    }
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "failed"
    assert status_response.json()["error"] == {
        "code": "processing_failed",
        "message": "Invoice processing failed.",
    }
    assert not os.path.exists(calls["path"])


def test_emission_enrichment_failure_marks_invoice_failed(monkeypatch):
    calls = {}

    def valid_pipeline(path, invoice_id):
        calls["path"] = path
        calls["invoice_id"] = invoice_id
        return {
            "invoice_id": invoice_id,
            "line_items": [],
            "warnings": [],
        }

    def failing_enrichment(result):
        raise RuntimeError("unexpected enrichment failure")

    _mock_ai_pipeline(monkeypatch, valid_pipeline)
    monkeypatch.setattr(main, "_enrich_emission_calculations", failing_enrichment)
    response = _post_upload(monkeypatch, "valid.png", b"image bytes", "image/png")

    assert response.status_code == 500
    assert response.json()["detail"] == {
        "code": "processing_failed",
        "message": "Invoice processing failed.",
    }
    status_response = client.get(f"/api/invoices/{calls['invoice_id']}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "failed"
    assert status_response.json()["error"]["code"] == "processing_failed"
    assert not os.path.exists(calls["path"])


def test_successful_upload_result_can_be_retrieved(monkeypatch):
    result = {
        "invoice_id": "placeholder",
        "source_file": "temporary.jpeg",
        "line_items": [{"description": "Grid electricity", "confidence": 0.84}],
    }
    _mock_ai_pipeline(
        monkeypatch,
        lambda path, invoice_id: {**result, "invoice_id": invoice_id},
    )

    upload_response = _post_upload(monkeypatch, "invoice.jpeg", b"image bytes", "image/jpeg")
    invoice_id = upload_response.json()["invoice_id"]
    result_response = client.get(f"/api/invoices/{invoice_id}/results")

    assert upload_response.status_code == 200
    assert result_response.status_code == 200
    assert result_response.json()["source_file"] == "invoice.jpeg"
    assert result_response.json()["line_items"] == result["line_items"]


def test_demo_returns_expected_stable_record_and_provenance():
    response = client.post("/api/invoices/demo", json={"demo_id": "INV-2024-001"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["invoice_id"] == "demo_INV-2024-001"
    assert payload["status"] == "completed"
    assert payload["result"]["id"] == "INV-2024-001"
    assert payload["result"]["invoiceNumber"] == "INV-CONED-8821"
    assert payload["result"]["calculatedEmissionsKg"] == 5467
    assert payload["result"]["source"] == {
        "kind": "demo",
        "label": "synthetic_demo",
        "record_id": "INV-2024-001",
    }
    assert payload["result"]["data_provenance"] == "synthetic_demo"
    assert payload["result"]["emission_calculation_status"] == "predefined_demo_value"


def test_repeated_demo_requests_are_deterministic():
    first = client.post("/api/invoices/demo", json={"demo_id": "INV-2024-003"})
    second = client.post("/api/invoices/demo", json={"demo_id": "INV-2024-003"})

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["invoice_id"] == "demo_INV-2024-003"


def test_unknown_demo_id_returns_not_found():
    response = client.post("/api/invoices/demo", json={"demo_id": "missing"})

    assert response.status_code == 404
    assert response.json() == {
        "detail": {"code": "demo_not_found", "message": "Demo invoice not found."}
    }


def test_demo_does_not_invoke_ai_or_emission_pipeline(monkeypatch):
    def unexpected_call(*args, **kwargs):
        raise AssertionError("Demo mode must not invoke AI or emission processing.")

    monkeypatch.setattr(main, "_run_ai_pipeline", unexpected_call)
    monkeypatch.setattr(main, "_calculate_emissions", unexpected_call)

    response = client.post("/api/invoices/demo", json={"demo_id": "INV-2024-001"})

    assert response.status_code == 200


def test_demo_result_is_retrievable_with_demo_status():
    upload_response = client.post("/api/invoices/demo", json={"demo_id": "INV-2024-001"})
    invoice_id = upload_response.json()["invoice_id"]

    result_response = client.get(f"/api/invoices/{invoice_id}/results")
    status_response = client.get(f"/api/invoices/{invoice_id}/status")

    assert result_response.status_code == 200
    assert result_response.json() == upload_response.json()["result"]
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["source"]["kind"] == "demo"


def test_uploaded_report_aggregates_only_successful_compatible_calculations():
    invoice_id = "inv_report_upload"
    result = _ai_result(
        [
            {
                **_line_item(category="electricity_grid"),
                "emission_calculation": {
                    "emissions": 12.5,
                    "emissions_unit": "kg CO2e",
                    "emissions_basis": "CO2e",
                },
                "calculation_status": "calculated",
                "review_required": False,
                "review_reasons": [],
            },
            {
                **_line_item(category="natural_gas"),
                "emission_calculation": {
                    "emissions": 7.5,
                    "emissions_unit": "kg CO2e",
                    "emissions_basis": "CO2e",
                },
                "calculation_status": "calculated",
                "review_required": True,
                "review_reasons": ["Emission factor verification is required."],
            },
            {
                **_line_item(category="unknown"),
                "emission_calculation": None,
                "calculation_status": "skipped",
                "review_required": True,
                "review_reasons": ["Activity category is unknown or missing."],
            },
        ]
    )
    result["invoice_id"] = invoice_id
    INVOICE_RECORDS[invoice_id] = {
        "status": "completed",
        "result": result,
        "error": None,
        "source": {"kind": "upload", "label": "uploaded_invoice", "filename": "report.pdf"},
    }

    response = client.get(f"/api/invoices/{invoice_id}/report")

    assert response.status_code == 200
    report = response.json()
    total = report["totals"]["successful_calculation_total"]
    assert report["source"]["kind"] == "upload"
    assert len(report["line_items"]) == 3
    assert report["warnings"] == ["Original AI warning"]
    assert report["review_warnings"] == [
        {"line_number": 2, "reasons": ["Emission factor verification is required."]},
        {"line_number": 3, "reasons": ["Activity category is unknown or missing."]},
    ]
    assert total == {
        "value": 20.0,
        "emissions_basis": "CO2e",
        "emissions_unit": "kg CO2e",
        "complete": False,
        "reason": "Subtotal includes 2 successful calculation(s); 1 line item(s) were not included.",
    }
    assert report["totals"]["successful_calculations_by_category"][0]["category"] == "electricity_grid"


def test_uploaded_report_does_not_combine_incompatible_emissions_units():
    invoice_id = "inv_report_mixed_units"
    line_items = []
    for category, basis, unit, value in [
        ("electricity_grid", "CO2", "kg CO2", 10.0),
        ("natural_gas", "CO2e", "kg CO2e", 20.0),
    ]:
        line_items.append(
            {
                **_line_item(category=category),
                "emission_calculation": {
                    "emissions": value,
                    "emissions_basis": basis,
                    "emissions_unit": unit,
                },
                "calculation_status": "calculated",
                "review_required": False,
                "review_reasons": [],
            }
        )
    result = _ai_result(line_items)
    result["invoice_id"] = invoice_id
    INVOICE_RECORDS[invoice_id] = {
        "status": "completed",
        "result": result,
        "error": None,
        "source": {"kind": "upload", "label": "uploaded_invoice", "filename": "mixed.pdf"},
    }

    response = client.get(f"/api/invoices/{invoice_id}/report")

    totals = response.json()["totals"]
    assert totals["successful_calculation_total"]["value"] is None
    assert "incompatible" in totals["successful_calculation_total"]["reason"]
    assert len(totals["successful_calculations_by_emissions_unit"]) == 2


def test_demo_report_marks_predefined_mock_emissions_and_no_engine_total():
    demo_response = client.post("/api/invoices/demo", json={"demo_id": "INV-2024-001"})
    invoice_id = demo_response.json()["invoice_id"]

    response = client.get(f"/api/invoices/{invoice_id}/report")

    assert response.status_code == 200
    report = response.json()
    line = report["line_items"][0]
    assert report["source"]["label"] == "synthetic_demo"
    assert line["emission_calculation"] is None
    assert line["calculation_status"] == "predefined_demo_value"
    assert line["predefined_demo_emissions"]["value"] == 5467
    assert line["predefined_demo_emissions"]["provenance"] == "synthetic_demo_mock"
    assert report["totals"]["successful_calculation_total"]["value"] is None
    assert "predefined mock values" in report["totals"]["successful_calculation_total"]["reason"]


def test_report_missing_invoice_returns_existing_not_found_shape():
    response = client.get("/api/invoices/missing/report")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {"code": "invoice_not_found", "message": "Invoice not found."}
    }


@pytest.mark.parametrize("status", ["processing", "failed"])
def test_report_is_unavailable_for_incomplete_or_failed_invoice(status):
    invoice_id = f"inv_report_{status}"
    INVOICE_RECORDS[invoice_id] = {
        "status": status,
        "result": None,
        "error": {"code": "processing_failed", "message": "Invoice processing failed."}
        if status == "failed"
        else None,
        "source": {"kind": "upload", "label": "uploaded_invoice", "filename": "report.pdf"},
    }

    response = client.get(f"/api/invoices/{invoice_id}/report")

    assert response.status_code == 409
    assert response.json()["detail"]["processing_status"] == status
    if status == "failed":
        assert response.json()["detail"]["error"]["code"] == "processing_failed"


def test_upload_rejects_files_over_size_limit(monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_SIZE_BYTES", 3)

    response = _post_upload(monkeypatch, "large.pdf", b"four", "application/pdf")

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"


def test_upload_calculates_line_and_preserves_ai_and_engine_fields(monkeypatch):
    original_item = _line_item()
    engine_result = {
        "category": "electricity_grid",
        "scope": "Scope 2",
        "activity_data": 100,
        "activity_unit": "kWh",
        "emission_factor": 0.71,
        "factor_unit": "kg CO2/kWh",
        "emissions": 71.0,
        "emissions_unit": "kg CO2",
        "emissions_basis": "CO2",
        "calculation": "100 kWh x 0.71 kg CO2/kWh",
        "factor_source": "factor-source",
        "source_year": 2025,
        "validation_status": "verified",
        "trust_metadata": {
            "verification_required": True,
            "factor_verified": True,
        },
    }
    calls = []

    def calculate(category, quantity, unit):
        calls.append((category, quantity, unit))
        return engine_result

    response = _upload_ai_result(monkeypatch, _ai_result([original_item]), calculate)

    assert response.status_code == 200
    payload = response.json()["result"]
    result_item = payload["line_items"][0]
    for field, value in original_item.items():
        assert result_item[field] == value
    assert result_item["emission_calculation"] == engine_result
    assert result_item["calculation_status"] == "calculated"
    assert result_item["calculation_reason"] is None
    assert result_item["review_required"] is False
    assert result_item["review_reasons"] == []
    assert payload["processing_status"] == "completed"
    assert payload["emission_calculation_status"] == "complete"
    assert payload["warnings"] == ["Original AI warning"]
    assert calls == [("electricity_grid", 100, "kWh")]


@pytest.mark.parametrize(
    ("missing_fields", "expected_reason"),
    [
        ({"quantity": None}, "Activity quantity and unit are required for emission calculation."),
        ({"unit": None}, "Activity quantity and unit are required for emission calculation."),
    ],
)
def test_missing_quantity_or_unit_skips_calculation(monkeypatch, missing_fields, expected_reason):
    calls = []
    response = _upload_ai_result(
        monkeypatch,
        _ai_result([_line_item(**missing_fields)]),
        lambda *args: calls.append(args),
    )

    result_item = response.json()["result"]["line_items"][0]
    assert result_item["calculation_status"] == "skipped"
    assert result_item["calculation_reason"] == expected_reason
    assert result_item["emission_calculation"] is None
    assert result_item["review_required"] is True
    assert calls == []


def test_unknown_category_and_missing_factor_are_skipped(monkeypatch):
    calls = []

    def calculate(category, quantity, unit):
        calls.append(category)
        raise ValueError(f"No emission factor found for category '{category}' with unit '{unit}'.")

    result = _ai_result(
        [
            _line_item(category="unknown", scope=None),
            _line_item(category="electricity_grid", unit="miles"),
        ]
    )
    response = _upload_ai_result(monkeypatch, result, calculate)

    items = response.json()["result"]["line_items"]
    assert [item["calculation_status"] for item in items] == ["skipped", "skipped"]
    assert items[0]["calculation_reason"] == "Activity category is unknown or missing."
    assert items[1]["calculation_reason"] == "No emission factor matches this category and unit."
    assert all(item["review_required"] for item in items)
    assert calls == ["electricity_grid"]


def test_non_emission_lines_are_not_calculated_and_remain_in_report(monkeypatch):
    calls = []
    result = _ai_result(
        [
            _line_item(
                category="non_emission",
                scope=None,
                expected_unit="kWh",
                review_required=True,
                review_reasons=["AI identified an ambiguous service description."],
            ),
            _line_item(
                category="non_emission",
                quantity=None,
                unit=None,
                scope=None,
                expected_unit=None,
            ),
        ]
    )
    response = _upload_ai_result(monkeypatch, result, lambda *args: calls.append(args))

    assert response.status_code == 200
    payload = response.json()["result"]
    assert payload["emission_calculation_status"] == "not_applicable"
    assert payload["warnings"] == ["Original AI warning"]
    assert calls == []
    assert [item["calculation_status"] for item in payload["line_items"]] == [
        "not_applicable",
        "not_applicable",
    ]
    assert [item["scope"] for item in payload["line_items"]] == [None, None]
    assert [item["expected_unit"] for item in payload["line_items"]] == ["kWh", None]
    assert all(item["emission_calculation"] is None for item in payload["line_items"])
    assert [item["review_required"] for item in payload["line_items"]] == [True, False]
    assert [item["review_reasons"] for item in payload["line_items"]] == [
        ["AI identified an ambiguous service description."],
        [],
    ]

    report_response = client.get(f"/api/invoices/{payload['invoice_id']}/report")
    assert report_response.status_code == 200
    report = report_response.json()
    assert [item["scope"] for item in report["line_items"]] == [None, None]
    assert [item["expected_unit"] for item in report["line_items"]] == ["kWh", None]
    assert report["review_warnings"] == [
        {
            "line_number": 1,
            "reasons": ["AI identified an ambiguous service description."],
        }
    ]
    assert report["totals"]["successful_calculations_by_emissions_unit"] == []
    assert report["totals"]["successful_calculations_by_category"] == []
    assert report["totals"]["successful_calculation_total"]["value"] is None


def test_non_emission_does_not_make_successful_emission_total_incomplete(monkeypatch):
    engine_result = {
        "emissions": 5.0,
        "emissions_unit": "kg CO2e",
        "emissions_basis": "CO2e",
    }
    response = _upload_ai_result(
        monkeypatch,
        _ai_result(
            [
                _line_item(category="non_emission", scope=None),
                _line_item(category="electricity_grid"),
            ]
        ),
        lambda category, quantity, unit: engine_result,
    )

    report_response = client.get(
        f"/api/invoices/{response.json()['invoice_id']}/report"
    )
    assert report_response.status_code == 200
    totals = report_response.json()["totals"]
    assert totals["successful_calculation_total"] == {
        "value": 5.0,
        "emissions_basis": "CO2e",
        "emissions_unit": "kg CO2e",
        "complete": True,
        "reason": None,
    }
    assert totals["successful_calculations_by_category"] == [
        {
            "category": "electricity_grid",
            "emissions_basis": "CO2e",
            "emissions_unit": "kg CO2e",
            "total": 5.0,
            "successful_line_items": 1,
        }
    ]


@pytest.mark.parametrize("category", ["water_effluent", "mobile_fuel_diesel", "stationary_fuel_diesel"])
def test_new_emission_categories_skip_missing_factors_without_failing_invoice(monkeypatch, category):
    calls = []

    def missing_factor(category_arg, quantity, unit):
        calls.append((category_arg, quantity, unit))
        raise ValueError(
            f"No emission factor found for category '{category_arg}' with unit '{unit}'."
        )

    response = _upload_ai_result(
        monkeypatch,
        _ai_result([_line_item(category=category, scope=None, expected_unit="litres")]),
        missing_factor,
    )

    assert response.status_code == 200
    payload = response.json()["result"]
    line_item = payload["line_items"][0]
    assert payload["processing_status"] == "completed"
    assert payload["emission_calculation_status"] == "partial"
    assert line_item["category"] == category
    assert line_item["expected_unit"] == "litres"
    assert line_item["calculation_status"] == "skipped"
    assert line_item["calculation_reason"] == "No emission factor matches this category and unit."
    assert line_item["review_required"] is True
    assert calls == [(category, 100, "kWh")]



def test_unverified_factor_requires_review(monkeypatch):
    engine_result = {
        "emissions": 71.0,
        "emissions_unit": "kg CO2",
        "emissions_basis": "CO2",
        "validation_status": "unverified_demo_value",
        "factor_source": None,
        "source_year": None,
        "trust_metadata": {
            "verification_required": True,
            "factor_verified": False,
        },
    }
    response = _upload_ai_result(
        monkeypatch,
        _ai_result([_line_item()]),
        lambda *args: engine_result,
    )

    payload = response.json()["result"]
    result_item = payload["line_items"][0]
    assert result_item["calculation_status"] == "calculated"
    assert result_item["emission_calculation"] == engine_result
    assert result_item["review_required"] is True
    assert result_item["review_reasons"] == ["Emission factor verification is required."]
    assert "Original AI warning" in payload["warnings"]
    assert any("unverified" in warning.lower() for warning in payload["warnings"])


def test_low_confidence_requires_review(monkeypatch):
    response = _upload_ai_result(
        monkeypatch,
        _ai_result([_line_item(confidence=0.42, confidence_flag="low")]),
        lambda *args: {"emissions": 71.0},
    )

    result_item = response.json()["result"]["line_items"][0]
    assert result_item["confidence"] == 0.42
    assert result_item["calculation_status"] == "calculated"
    assert result_item["review_required"] is True
    assert result_item["review_reasons"] == ["AI confidence is low."]


def test_calculation_failure_does_not_fail_other_line_or_invoice(monkeypatch):
    def calculate(category, quantity, unit):
        if category == "electricity_grid":
            raise ValueError("No emission factor found")
        return {"emissions": 12.0, "emissions_unit": "kg CO2e"}

    result = _ai_result(
        [
            _line_item(category="electricity_grid"),
            _line_item(category="natural_gas"),
        ]
    )
    response = _upload_ai_result(monkeypatch, result, calculate)

    payload = response.json()["result"]
    assert response.status_code == 200
    assert payload["processing_status"] == "completed"
    assert payload["emission_calculation_status"] == "partial"
    assert [item["calculation_status"] for item in payload["line_items"]] == [
        "skipped",
        "calculated",
    ]
    assert payload["warnings"][0] == "Original AI warning"
    assert any("No emission factor" in warning for warning in payload["warnings"])

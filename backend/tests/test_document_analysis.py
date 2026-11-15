"""Automated Test Suite for KYC Document Analysis, Parsers, and Field Verification.
Verifies all synthetic fixtures against ground truth definitions without external dependencies.
"""

import json
from pathlib import Path
import pytest

from kyc.document_analysis.comparator import (
    calculate_string_similarity,
    compare_all_fields,
    compare_field,
    normalize_date,
    normalize_nik,
    normalize_text,
)
from kyc.document_analysis.docx_parser import parse_docx
from kyc.document_analysis.pdf_parser import parse_pdf, render_pdf_to_images
from kyc.document_analysis.service import analyze_document


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic_kyc"
GROUND_TRUTH_PATH = FIXTURES_DIR / "ground_truth.json"


@pytest.fixture(scope="session")
def ground_truth() -> dict:
    """Load ground truth synthetic definitions."""
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def puput_applicant() -> dict:
    """Standard applicant payload matching synthetic profile Puput Nugroho."""
    return {
        "full_name": "PUPUT NUGROHO",
        "identity_number": "2912541012827585",
        "date_of_birth": "1950-01-27",
        "birth_date": "1950-01-27",
        "birth_place": "SURABAYA",
        "gender": "PEREMPUAN",
        "address": "GANG PHH. MUSTOFA NO. 2",
        "account_purpose": "TABUNGAN PRIBADI & TRANSAKSI KELUARGA",
        "account_type": "TABUNGAN VELTRIX REGULER",
    }


# ==============================================================================
# 1. Unit Tests: Normalization & Comparison Rules
# ==============================================================================

def test_normalize_text():
    assert normalize_text("  PUPUT   nugroho  ") == "PUPUT NUGROHO"
    assert normalize_text("T. Irwan Yolanda, M.Farm") == "T IRWAN YOLANDA M FARM"


def test_normalize_nik():
    assert normalize_nik(" 2912-5410-1282-7585 ") == "2912541012827585"
    assert normalize_nik("DUMMY-NIK-1234") == "DUMMYNIK1234"


def test_normalize_date():
    assert normalize_date("27-01-1950") == "1950-01-27"
    assert normalize_date("27/01/1950") == "1950-01-27"
    assert normalize_date("1950-01-27") == "1950-01-27"
    assert normalize_date("27 Januari 1950") == "1950-01-27"


def test_compare_field_exact_nik():
    # Exact match
    match = compare_field("identity_number", "2912541012827585", "2912541012827585")
    assert match["result"] == "MATCH"

    # Single digit mismatch must fail
    mismatch = compare_field("identity_number", "2912541012827585", "2912541012827586")
    assert mismatch["result"] == "MISMATCH"


def test_compare_field_whitespace_tolerance():
    # KTP OCR often fuses first/last name or has spaces
    res = compare_field("full_name", "PUPUT NUGROHO", "PUPUTNUGROHO")
    assert res["result"] == "MATCH"


def test_compare_field_not_detected():
    res = compare_field("identity_number", "2912541012827585", None)
    assert res["result"] == "NOT_DETECTED"


# ==============================================================================
# 2. Unit Tests: Digital PDF & DOCX Parsers
# ==============================================================================

def test_digital_pdf_parser(puput_applicant):
    pdf_path = FIXTURES_DIR / "bank_account_form_digital.pdf"
    assert pdf_path.exists(), "Digital PDF fixture missing"

    with open(pdf_path, "rb") as f:
        res = parse_pdf(f.read())

    assert res["status"] == "COMPLETED"
    assert res["is_scanned"] is False
    assert res["document_type"] == "account_opening_form"
    assert res["fields"]["full_name"] == "PUPUT NUGROHO"
    assert res["fields"]["identity_number"] == "2912541012827585"
    assert res["fields"]["account_purpose"] == "TABUNGAN PRIBADI & TRANSAKSI KELUARGA"


def test_scanned_pdf_detection():
    pdf_path = FIXTURES_DIR / "bank_account_form_scanned.pdf"
    assert pdf_path.exists(), "Scanned PDF fixture missing"

    with open(pdf_path, "rb") as f:
        res = parse_pdf(f.read())

    assert res["status"] == "REQUIRES_OCR"
    assert res["is_scanned"] is True
    assert "rendered_images" in res
    assert len(res["rendered_images"]) >= 1


def test_docx_parser(puput_applicant):
    docx_path = FIXTURES_DIR / "bank_account_form_puput.docx"
    assert docx_path.exists(), "DOCX fixture missing"

    with open(docx_path, "rb") as f:
        res = parse_docx(f.read())

    assert res["status"] == "COMPLETED"
    assert res["document_type"] == "account_opening_form"
    assert res["fields"]["full_name"] == "PUPUT NUGROHO"
    assert res["fields"]["identity_number"] == "2912541012827585"
    assert res["fields"]["account_purpose"] == "TABUNGAN PRIBADI & TRANSAKSI KELUARGA"


# ==============================================================================
# 3. Integration Tests: Service on Synthetic KYC Fixtures
# ==============================================================================

def test_service_pdf_digital_flow(puput_applicant):
    pdf_path = FIXTURES_DIR / "bank_account_form_digital.pdf"
    with open(pdf_path, "rb") as f:
        res = analyze_document(
            content_bytes=f.read(),
            mime_type="application/pdf",
            document_type="account_opening_form",
            submitted_form=puput_applicant,
        )

    assert res["status"] == "COMPLETED"
    assert res["overall_status"] == "VERIFIED_MATCH"
    assert res["has_mismatch"] is False
    assert res["manual_review_required"] is False
    assert res["engine"] == "pypdf-digital"


def test_service_docx_flow(puput_applicant):
    docx_path = FIXTURES_DIR / "bank_account_form_puput.docx"
    with open(docx_path, "rb") as f:
        res = analyze_document(
            content_bytes=f.read(),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            document_type="account_opening_form",
            submitted_form=puput_applicant,
        )

    assert res["status"] == "COMPLETED"
    assert res["overall_status"] == "VERIFIED_MATCH"
    assert res["has_mismatch"] is False
    assert res["manual_review_required"] is False
    assert res["engine"] == "python-docx"


def test_service_non_ktp_rejection(puput_applicant):
    """Ensure arbitrary non-KTP images are flagged unknown and routed to manual review."""
    for fn in ("dokumen_sembarang_1.jpeg", "dokumen_sembarang_2.jpeg"):
        img_path = FIXTURES_DIR / fn
        if not img_path.exists():
            continue

        with open(img_path, "rb") as f:
            res = analyze_document(
                content_bytes=f.read(),
                mime_type="image/jpeg",
                document_type="ktp",
                submitted_form=puput_applicant,
            )

        assert res["document_type"] == "unknown"
        assert res["manual_review_required"] is True


def test_service_ktp_clear_puput_match(puput_applicant):
    """Clear KTP 0001 (Puput Nugroho) must match submitted application with high confidence."""
    ktp_path = FIXTURES_DIR / "ktp_0001_clear.png"
    assert ktp_path.exists(), "ktp_0001_clear.png missing"

    with open(ktp_path, "rb") as f:
        res = analyze_document(
            content_bytes=f.read(),
            mime_type="image/png",
            document_type="ktp",
            submitted_form=puput_applicant,
        )

    assert res["document_type"] == "ktp"
    assert res["confidence"] >= 0.90
    assert res["extracted_fields"]["identity_number"] == "2912541012827585"
    assert res["has_mismatch"] is False
    assert res["overall_status"] == "VERIFIED_MATCH"


def test_service_ktp_intentional_mismatch(puput_applicant):
    """KTP 0004 has different identity (Caturangga Yolanda); must flag REJECT_OR_REVISE."""
    ktp_path = FIXTURES_DIR / "ktp_0004_mismatch.png"
    assert ktp_path.exists(), "ktp_0004_mismatch.png missing"

    with open(ktp_path, "rb") as f:
        res = analyze_document(
            content_bytes=f.read(),
            mime_type="image/png",
            document_type="ktp",
            submitted_form=puput_applicant,
        )

    assert res["document_type"] == "ktp"
    assert res["has_mismatch"] is True
    assert res["overall_status"] == "REJECT_OR_REVISE"
    assert res["manual_review_required"] is True


def test_service_empty_input_safe_failure():
    """Empty or corrupted byte payload must safely fail without crash."""
    res = analyze_document(
        content_bytes=b"",
        mime_type="image/png",
        document_type="ktp",
    )
    assert res["status"] == "FAILED"
    assert res["manual_review_required"] is True

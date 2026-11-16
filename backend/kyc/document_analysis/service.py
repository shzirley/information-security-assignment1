"""Unified Document Analysis Service for VELTRIX BankKYC.
Integrates OCR (PaddleOCR local), PDF parsing (digital + scanned fallback via pypdfium2),
DOCX parsing, and field comparison rules against applicant submitted data.
"""

from typing import Any, Optional
from datetime import datetime, timezone

from kyc.document_analysis.comparator import compare_all_fields
from kyc.document_analysis.docx_parser import parse_docx
from kyc.document_analysis.ocr_engine import analyze_image_bytes
from kyc.document_analysis.pdf_parser import parse_bank_account_form, parse_pdf, render_pdf_to_images


def analyze_document(
    content_bytes: bytes,
    mime_type: str,
    document_type: str = "ktp",
    submitted_form: Optional[dict[str, Any]] = None,
    evidence_id: Optional[str] = None,
    evidence_version: Optional[int] = 1,
) -> dict[str, Any]:
    """Unified document analysis pipeline for KYC evidence inspection.

    Args:
        content_bytes: Raw decrypted document bytes.
        mime_type: MIME type of evidence (e.g. image/png, application/pdf).
        document_type: Expected document type ('ktp', 'account_opening_form', etc.).
        submitted_form: Optional dictionary of form values submitted by applicant.
        evidence_id: Identifier of the evidence being analyzed.
        evidence_version: Version number of the evidence file.

    Returns:
        Structured analysis result conforming to reviewer API contract.
    """
    if not content_bytes:
        return {
            "evidence_id": evidence_id,
            "evidence_version": evidence_version,
            "document_type": "unknown",
            "status": "FAILED",
            "engine": "none",
            "model_version": "none",
            "checks": [],
            "extracted_fields": {},
            "manual_review_required": True,
            "overall_status": "MANUAL_REVIEW_REQUIRED",
            "error": "Document content is empty.",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    mime_clean = (mime_type or "").lower().strip()
    engine_name = "unknown"
    model_version = "none"
    extracted_fields: dict[str, Any] = {}
    detected_type = document_type
    overall_confidence: Optional[float] = None
    manual_review_required = False
    status = "COMPLETED"
    raw_text = ""

    # --- 1. IMAGE PROCESSING (KTP & Photos) ---
    if mime_clean in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        engine_name = "paddleocr-local"
        model_version = "PP-OCRv6_medium"

        ocr_result = analyze_image_bytes(content_bytes)
        if ocr_result.get("status") == "FAILED":
            return {
                "evidence_id": evidence_id,
                "evidence_version": evidence_version,
                "document_type": "unknown",
                "status": "FAILED",
                "engine": engine_name,
                "model_version": model_version,
                "checks": [],
                "extracted_fields": {},
                "manual_review_required": True,
                "overall_status": "MANUAL_REVIEW_REQUIRED",
                "error": ocr_result.get("error", "OCR extraction failed"),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

        extracted_fields = ocr_result.get("fields", {})
        detected_type = ocr_result.get("document_type", "unknown")
        overall_confidence = ocr_result.get("confidence")
        manual_review_required = ocr_result.get("manual_review_required", False)
        raw_text = "\n".join(ocr_result.get("raw_lines", []))

    # --- 2. PDF PROCESSING (Digital & Scanned) ---
    elif mime_clean == "application/pdf":
        pdf_res = parse_pdf(content_bytes)

        if pdf_res.get("status") == "REQUIRES_OCR":
            # Scanned PDF: Render first page and invoke OCR
            engine_name = "paddleocr-local"
            model_version = "PP-OCRv6_medium"
            rendered = pdf_res.get("rendered_images") or render_pdf_to_images(content_bytes, max_pages=1)

            if rendered:
                ocr_result = analyze_image_bytes(rendered[0])
                raw_text = "\n".join(ocr_result.get("raw_lines", []))
                # Try parsing as bank form or KTP
                parsed_form = parse_bank_account_form(raw_text)
                if parsed_form.get("is_bank_form"):
                    extracted_fields = parsed_form.get("fields", {})
                    detected_type = "account_opening_form"
                else:
                    extracted_fields = ocr_result.get("fields", {})
                    detected_type = ocr_result.get("document_type", "unknown")

                overall_confidence = ocr_result.get("confidence")
                manual_review_required = ocr_result.get("manual_review_required", False)
            else:
                status = "FAILED"
                manual_review_required = True
        else:
            # Digital PDF with native text layer
            engine_name = "pypdf-digital"
            model_version = "pypdf-native"
            raw_text = pdf_res.get("raw_text", "")
            extracted_fields = pdf_res.get("fields", {})
            detected_type = pdf_res.get("document_type", "account_opening_form")
            overall_confidence = 1.0

    # --- 3. DOCX PROCESSING ---
    elif mime_clean in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        engine_name = "python-docx"
        model_version = "docx-table-parser"

        docx_res = parse_docx(content_bytes)
        if docx_res.get("status") == "COMPLETED":
            raw_text = docx_res.get("raw_text", "")
            extracted_fields = docx_res.get("fields", {})
            detected_type = docx_res.get("document_type", "account_opening_form")
            overall_confidence = 1.0
        else:
            status = "FAILED"
            manual_review_required = True

    # --- 4. UNSUPPORTED MIME TYPE ---
    else:
        return {
            "evidence_id": evidence_id,
            "evidence_version": evidence_version,
            "document_type": "unknown",
            "status": "FAILED",
            "engine": "none",
            "model_version": "none",
            "checks": [],
            "extracted_fields": {},
            "manual_review_required": True,
            "overall_status": "MANUAL_REVIEW_REQUIRED",
            "error": f"Unsupported MIME type for document analysis: {mime_clean}",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    # --- 5. FIELD COMPARISON RULES ---
    checks = []
    has_mismatch = False
    overall_status = "COMPLETED"

    if submitted_form:
        comp_res = compare_all_fields(
            submitted_form=submitted_form,
            extracted_fields=extracted_fields,
            document_type=detected_type,
            overall_confidence=overall_confidence,
        )
        checks = comp_res["checks"]
        has_mismatch = comp_res["has_mismatch"]
        overall_status = comp_res["overall_status"]
        if comp_res["manual_review_required"]:
            manual_review_required = True
    else:
        # No submitted form provided: create informational checks
        for k, v in extracted_fields.items():
            checks.append({
                "field": k,
                "submitted_value": None,
                "extracted_value": str(v),
                "result": "NOT_APPLICABLE",
                "confidence": overall_confidence,
                "reason": "No submission form provided for automated comparison.",
            })
        overall_status = "MANUAL_REVIEW_REQUIRED" if manual_review_required else "COMPLETED"

    return {
        "evidence_id": evidence_id,
        "evidence_version": evidence_version,
        "document_type": detected_type,
        "status": status,
        "engine": engine_name,
        "model_version": model_version,
        "confidence": overall_confidence,
        "checks": checks,
        "extracted_fields": extracted_fields,
        "has_mismatch": has_mismatch,
        "raw_text": raw_text[:32000],
        "manual_review_required": manual_review_required,
        "overall_status": overall_status,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

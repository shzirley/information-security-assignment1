"""Field Normalizer and Consistency Comparator for VELTRIX BankKYC.
Compares applicant submitted form values against extracted document values
according to explicit deterministic rules (NIST & BankKYC requirements).

Status Codes:
- MATCH: Extracted value matches submitted form value after normalization.
- MISMATCH: Extracted value conflicts with submitted form value.
- NOT_DETECTED: Field was expected but could not be extracted from document.
- UNREADABLE: Document image was too blurry or degraded to extract field.
- NOT_APPLICABLE: Field is not applicable or not provided in form.
"""

import re
from datetime import datetime
from typing import Any, Optional


MONTH_MAP = {
    "januari": "01", "january": "01", "jan": "01",
    "februari": "02", "february": "02", "feb": "02",
    "maret": "03", "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "mei": "05", "may": "05",
    "juni": "06", "june": "06", "jun": "06",
    "juli": "07", "july": "07", "jul": "07",
    "agustus": "08", "august": "08", "agu": "08", "aug": "08",
    "september": "09", "sep": "09",
    "oktober": "10", "october": "10", "okt": "10", "oct": "10",
    "november": "11", "nov": "11",
    "desember": "12", "december": "12", "des": "12", "dec": "12",
}


def normalize_text(val: Optional[str]) -> str:
    """Normalize text: strip, uppercase, collapse whitespace, strip punctuation."""
    if not val:
        return ""
    text = str(val).strip().upper()
    # Replace common punctuation with space to handle OCR noise & titles
    text = re.sub(r"[.,;:/\-_]", " ", text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_nik(val: Optional[str]) -> str:
    """Normalize NIK / Identity number: strip dashes, dots, and whitespace."""
    if not val:
        return ""
    text = str(val).strip().upper()
    return re.sub(r"[\s.\-]", "", text)


def normalize_date(val: Optional[str]) -> Optional[str]:
    """Normalize various date formats into standard ISO YYYY-MM-DD.
    Supports:
    - 27-01-1950 or 27/01/1950 (DD-MM-YYYY)
    - 1950-01-27 or 1950/01/27 (YYYY-MM-DD)
    - 27 Januari 1950 or 12 Mei 1995 (DD Month YYYY)
    """
    if not val:
        return None
    raw = str(val).strip()

    # 1. ISO format already (YYYY-MM-DD)
    iso_match = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", raw)
    if iso_match:
        y, m, d = iso_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # 2. Standard Indonesian format (DD-MM-YYYY)
    dmy_match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", raw)
    if dmy_match:
        d, m, y = dmy_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # 3. Textual month format (e.g. 12 Mei 1995 or 27 Januari 1950)
    text_month_match = re.search(
        r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", raw
    )
    if text_month_match:
        d, month_name, y = text_month_match.groups()
        month_num = MONTH_MAP.get(month_name.lower())
        if month_num:
            return f"{int(y):04d}-{int(month_num):02d}-{int(d):02d}"

    return None


def calculate_string_similarity(s1: str, s2: str) -> float:
    """Calculate token-based / character overlap similarity (0.0 to 1.0)."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    # Token overlap (Jaccard similarity on words)
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if tokens1 and tokens2:
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        token_sim = len(intersection) / len(union)
        if token_sim >= 0.8:
            return token_sim

    # Bigram character similarity fallback
    def get_bigrams(s):
        return {s[i:i+2] for i in range(len(s) - 1)}

    b1 = get_bigrams(s1)
    b2 = get_bigrams(s2)
    if not b1 or not b2:
        return 0.0
    return (2.0 * len(b1.intersection(b2))) / (len(b1) + len(b2))


def compare_field(
    field_name: str,
    submitted_val: Any,
    extracted_val: Any,
    extracted_confidence: Optional[float] = None,
) -> dict[str, Any]:
    """Compare a single field pair and return a typed result."""
    sub_raw = str(submitted_val).strip() if submitted_val is not None else ""
    ext_raw = str(extracted_val).strip() if extracted_val is not None else ""

    # Case 1: Submitted value was not provided
    if not sub_raw:
        return {
            "field": field_name,
            "submitted_value": "",
            "extracted_value": ext_raw,
            "result": "NOT_APPLICABLE",
            "confidence": extracted_confidence,
            "reason": "Field was not provided in applicant submission.",
        }

    # Case 2: Extracted value missing / not detected
    if not ext_raw:
        return {
            "field": field_name,
            "submitted_value": sub_raw,
            "extracted_value": None,
            "result": "NOT_DETECTED",
            "confidence": extracted_confidence,
            "reason": f"Field '{field_name}' could not be detected from document.",
        }

    # Case 3: Identity Number (Exact Match Required)
    if field_name == "identity_number":
        norm_sub = normalize_nik(sub_raw)
        norm_ext = normalize_nik(ext_raw)
        is_match = (norm_sub == norm_ext)
        return {
            "field": field_name,
            "submitted_value": sub_raw,
            "extracted_value": ext_raw,
            "result": "MATCH" if is_match else "MISMATCH",
            "confidence": extracted_confidence,
            "reason": "Exact NIK match verified." if is_match else f"NIK mismatch: submitted '{norm_sub}' vs extracted '{norm_ext}'.",
        }

    # Case 4: Date of Birth
    if field_name in ("date_of_birth", "birth_date"):
        iso_sub = normalize_date(sub_raw)
        iso_ext = normalize_date(ext_raw)
        if iso_sub and iso_ext:
            is_match = (iso_sub == iso_ext)
            return {
                "field": field_name,
                "submitted_value": sub_raw,
                "extracted_value": ext_raw,
                "normalized_submitted": iso_sub,
                "normalized_extracted": iso_ext,
                "result": "MATCH" if is_match else "MISMATCH",
                "confidence": extracted_confidence,
                "reason": f"Date match ({iso_sub})" if is_match else f"DOB mismatch: form has '{iso_sub}' while document has '{iso_ext}'.",
            }

    # Case 5: Full Name and other text fields
    norm_sub = normalize_text(sub_raw)
    norm_ext = normalize_text(ext_raw)

    if norm_sub == norm_ext or norm_sub.replace(" ", "") == norm_ext.replace(" ", ""):
        return {
            "field": field_name,
            "submitted_value": sub_raw,
            "extracted_value": ext_raw,
            "result": "MATCH",
            "confidence": extracted_confidence,
            "reason": "Exact text match (whitespace normalized)." if norm_sub != norm_ext else "Exact text match.",
        }

    # Name similarity check (allow minor OCR noise if similarity >= 0.85)
    sim = calculate_string_similarity(norm_sub, norm_ext)
    if field_name == "full_name" and sim >= 0.85:
        return {
            "field": field_name,
            "submitted_value": sub_raw,
            "extracted_value": ext_raw,
            "result": "MATCH",
            "confidence": extracted_confidence,
            "reason": f"High name similarity ({sim:.2f}). Minor formatting/spacing differences accepted.",
        }

    return {
        "field": field_name,
        "submitted_value": sub_raw,
        "extracted_value": ext_raw,
        "result": "MISMATCH",
        "confidence": extracted_confidence,
        "similarity": round(sim, 2),
        "reason": f"Value mismatch (similarity {sim:.2f}): form has '{norm_sub}' vs document '{norm_ext}'.",
    }


def compare_all_fields(
    submitted_form: dict[str, Any],
    extracted_fields: dict[str, Any],
    document_type: str,
    overall_confidence: Optional[float] = 1.0,
) -> dict[str, Any]:
    """Compare all expected fields for a given document type.
    Returns typed check list and determines if manual review is required.
    """
    checks = []

    # Fields to check based on document type
    if document_type == "ktp":
        target_fields = ["full_name", "identity_number", "date_of_birth"]
    elif document_type == "account_opening_form":
        target_fields = ["full_name", "identity_number", "account_purpose"]
    else:
        # Default fallback
        target_fields = ["full_name", "identity_number"]

    manual_review = False
    has_mismatch = False

    for field in target_fields:
        sub_val = submitted_form.get(field)
        ext_val = extracted_fields.get(field)

        # Map date_of_birth aliases
        if field == "date_of_birth" and not ext_val:
            ext_val = extracted_fields.get("birth_date_raw") or extracted_fields.get("birth_place_date")

        check = compare_field(field, sub_val, ext_val, extracted_confidence=overall_confidence)
        checks.append(check)

        if check["result"] in ("MISMATCH", "NOT_DETECTED", "UNREADABLE"):
            manual_review = True
            if check["result"] == "MISMATCH":
                has_mismatch = True

    # If document was classified as unknown, flag manual review
    if document_type == "unknown":
        manual_review = True

    # If confidence is low, flag manual review
    if overall_confidence is not None and overall_confidence < 0.65:
        manual_review = True

    return {
        "document_type": document_type,
        "checks": checks,
        "has_mismatch": has_mismatch,
        "manual_review_required": manual_review,
        "overall_status": "REJECT_OR_REVISE" if has_mismatch else ("MANUAL_REVIEW_REQUIRED" if manual_review else "VERIFIED_MATCH"),
    }

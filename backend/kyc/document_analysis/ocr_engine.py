"""Local OCR Engine Adapter for VELTRIX BankKYC.
Powered by PaddleOCR with lazy-singleton loading, safe error handling,
and structured Indonesian KTP / document field extraction.
"""

import io
import os
import re
from typing import Any, Optional
import numpy as np
from PIL import Image

# Ensure Paddle does not block on remote source checks
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# Global singleton
_OCR_MODEL = None


def _apply_windows_paddle_compatibility():
    """Apply safe configuration patch to prevent PIR oneDNN attribute errors on Windows CPU."""
    try:
        import paddle.inference as p_inf

        if not getattr(p_inf, "_veltrix_patched", False):
            orig_create_predictor = p_inf.create_predictor

            def patched_create_predictor(config):
                config.disable_onednn()
                config.disable_mkldnn()
                config.enable_new_ir(False)
                return orig_create_predictor(config)

            p_inf.create_predictor = patched_create_predictor
            p_inf._veltrix_patched = True
    except Exception:
        pass


def get_ocr_engine():
    """Lazy-singleton loader for PaddleOCR engine."""
    global _OCR_MODEL
    if _OCR_MODEL is None:
        _apply_windows_paddle_compatibility()
        from paddleocr import PaddleOCR
        # Initialize with orientation detection
        _OCR_MODEL = PaddleOCR(use_textline_orientation=True, lang="en")
    return _OCR_MODEL


def parse_ktp_lines(rec_texts: list[str], rec_scores: list[float]) -> dict[str, Any]:
    """Parse raw OCR text lines and bounding confidence scores into structured KTP fields."""
    fields: dict[str, Any] = {}
    cleaned_lines = [t.strip() for t in rec_texts if t.strip()]

    # 1. Check if document looks like an Indonesian KTP
    full_text = " ".join(cleaned_lines).upper()
    ktp_keywords = ["PROVINSI", "KOTA", "KABUPATEN", "NIK", "REPUBLIK", "KARTU TANDA PENDUDUK"]
    matches_count = sum(1 for kw in ktp_keywords if kw in full_text)
    is_ktp = matches_count >= 2

    if not is_ktp:
        return {
            "document_type": "unknown",
            "is_ktp": False,
            "fields": {},
            "confidence": float(np.mean(rec_scores)) if rec_scores else 0.0,
        }

    # 2. Extract NIK (16 consecutive digits or prefixed by NIK)
    nik_found = None
    for i, line in enumerate(cleaned_lines):
        line_clean = line.replace(":", "").replace(" ", "").strip()
        nik_match = re.search(r"\b(\d{16})\b", line_clean)
        if nik_match:
            nik_found = nik_match.group(1)
            break
        # Sometimes NIK is on next line after label "NIK"
        if re.search(r"^NIK\b", line, re.IGNORECASE) and i + 1 < len(cleaned_lines):
            next_line = cleaned_lines[i + 1].replace(":", "").replace(" ", "").strip()
            nik_match2 = re.search(r"\b(\d{16})\b", next_line)
            if nik_match2:
                nik_found = nik_match2.group(1)
                break
    if nik_found:
        fields["identity_number"] = nik_found

    # 3. Extract Nama
    for i, line in enumerate(cleaned_lines):
        if re.search(r"^Nama\b", line, re.IGNORECASE):
            # Check if name is on same line after colon: e.g. "Nama : PUPUT NUGROHO"
            val = re.sub(r"^Nama\s*[:\s]*", "", line, flags=re.IGNORECASE).strip()
            if val and len(val) >= 3:
                fields["full_name"] = val.upper()
                break
            # Or on the next line
            elif i + 1 < len(cleaned_lines):
                next_val = cleaned_lines[i + 1].replace(":", "").strip()
                if next_val and not re.search(r"Tempat|Lahir|NIK", next_val, re.IGNORECASE):
                    fields["full_name"] = next_val.upper()
                    break

    # 4. Extract Tempat / Tanggal Lahir
    for i, line in enumerate(cleaned_lines):
        if re.search(r"Tempat.*Lahir|Tgl\s*Lahir", line, re.IGNORECASE):
            val = re.sub(r"^.*Lahir\s*[:\s]*", "", line, flags=re.IGNORECASE).strip()
            if val:
                fields["birth_place_date"] = val.upper()
                # Parse date
                date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", val)
                if date_match:
                    fields["birth_date_raw"] = date_match.group(1)
                break
            elif i + 1 < len(cleaned_lines):
                next_val = cleaned_lines[i + 1].replace(":", "").strip()
                fields["birth_place_date"] = next_val.upper()
                date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", next_val)
                if date_match:
                    fields["birth_date_raw"] = date_match.group(1)
                break

    # 5. Extract Jenis Kelamin
    if "PEREMPUAN" in full_text:
        fields["gender"] = "PEREMPUAN"
    elif "LAKI-LAKI" in full_text or "LAKI - LAKI" in full_text:
        fields["gender"] = "LAKI-LAKI"

    # 6. Extract Alamat, RT/RW, Kel/Desa, Kecamatan
    for i, line in enumerate(cleaned_lines):
        if re.search(r"^Alamat\b", line, re.IGNORECASE):
            val = re.sub(r"^Alamat\s*[:\s]*", "", line, flags=re.IGNORECASE).strip()
            if not val and i + 1 < len(cleaned_lines):
                val = cleaned_lines[i + 1].replace(":", "").strip()
            if val:
                fields["address_street"] = val.upper()

        if "RT/RW" in line.upper():
            rt_match = re.search(r"(\d{3}\s*/\s*\d{3})", line)
            if rt_match:
                fields["rt_rw"] = rt_match.group(1).replace(" ", "")

        if "KEL/DESA" in line.upper() or "DESA" in line.upper():
            val = re.sub(r"^.*(Kel/Desa|Desa)\s*[:\s]*", "", line, flags=re.IGNORECASE).strip()
            if val:
                fields["kel_desa"] = val.upper()

        if "KECAMATAN" in line.upper():
            val = re.sub(r"^.*Kecamatan\s*[:\s]*", "", line, flags=re.IGNORECASE).strip()
            if val:
                fields["kecamatan"] = val.upper()

    # 7. Extract Pekerjaan
    for i, line in enumerate(cleaned_lines):
        if re.search(r"^Pekerjaan\b", line, re.IGNORECASE):
            val = re.sub(r"^Pekerjaan\s*[:\s]*", "", line, flags=re.IGNORECASE).strip()
            if not val and i + 1 < len(cleaned_lines):
                val = cleaned_lines[i + 1].replace(":", "").strip()
            if val:
                fields["occupation"] = val.upper()
                break

    avg_conf = float(np.mean(rec_scores)) if rec_scores else 0.0

    return {
        "document_type": "ktp",
        "is_ktp": True,
        "fields": fields,
        "confidence": round(avg_conf, 3),
        "raw_lines": cleaned_lines,
    }


def analyze_image_bytes(image_bytes: bytes) -> dict[str, Any]:
    """Run OCR on image bytes and return structured analysis result."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return {
            "status": "FAILED",
            "document_type": "unknown",
            "fields": {},
            "confidence": 0.0,
            "error": f"Failed to decode image bytes: {str(e)}",
            "manual_review_required": True,
        }

    # Low resolution check
    w, h = img.size
    if w < 150 or h < 150:
        return {
            "status": "UNREADABLE",
            "document_type": "unknown",
            "fields": {},
            "confidence": 0.0,
            "error": "Image resolution too low for OCR.",
            "manual_review_required": True,
        }

    # Performance optimization: constrain oversized images to max dimension 1200
    # Speeds up CPU inference ~3x while maintaining crisp OCR text resolution
    max_dim = 1200
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    try:
        engine = get_ocr_engine()
        img_arr = np.array(img)
        res = engine.predict(img_arr)
    except Exception as e:
        return {
            "status": "FAILED",
            "document_type": "unknown",
            "fields": {},
            "confidence": 0.0,
            "error": f"OCR inference error: {str(e)}",
            "manual_review_required": True,
        }

    if not res:
        return {
            "status": "UNREADABLE",
            "document_type": "unknown",
            "fields": {},
            "confidence": 0.0,
            "manual_review_required": True,
        }

    item = res[0]
    rec_texts = item.get("rec_texts", []) if hasattr(item, "get") else getattr(item, "rec_texts", [])
    rec_scores = item.get("rec_scores", []) if hasattr(item, "get") else getattr(item, "rec_scores", [])

    parsed = parse_ktp_lines(rec_texts, rec_scores)

    # Check blur / low confidence
    avg_conf = parsed.get("confidence", 0.0)
    is_low_conf = avg_conf < 0.60

    status = "COMPLETED"
    if parsed["document_type"] == "unknown":
        status = "COMPLETED"  # Successfully analyzed, but not recognized as KTP
    elif is_low_conf:
        status = "MANUAL_REVIEW_REQUIRED"

    return {
        "status": status,
        "document_type": parsed["document_type"],
        "fields": parsed.get("fields", {}),
        "confidence": avg_conf,
        "raw_lines": parsed.get("raw_lines", []),
        "manual_review_required": is_low_conf or (parsed["document_type"] == "unknown"),
        "engine": "paddleocr-local",
        "model_version": "PP-OCRv6_medium",
    }

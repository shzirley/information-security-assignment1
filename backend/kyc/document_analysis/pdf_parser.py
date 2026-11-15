"""PDF Document Parser for digital and scanned PDFs.
Extracts raw text layer via pypdf and extracts structured bank KYC fields.
If the PDF contains no text layer (e.g. scanned image), flags it for OCR processing.
"""

import io
import re
from typing import Any
from pypdf import PdfReader


def is_scanned_pdf(reader: PdfReader, min_chars_per_page: int = 40) -> bool:
    """Detect if PDF is a scanned image without selectable digital text."""
    total_chars = 0
    total_pages = len(reader.pages)
    if total_pages == 0:
        return True
    for page in reader.pages[:3]:  # Check up to first 3 pages
        text = page.extract_text() or ""
        total_chars += len(text.strip())
    avg_chars = total_chars / min(total_pages, 3)
    return avg_chars < min_chars_per_page


def extract_pdf_text(pdf_bytes: bytes, max_pages: int = 5) -> dict[str, Any]:
    """Extract raw text from PDF bytes. Bounded by max_pages to prevent DOS."""
    stream = io.BytesIO(pdf_bytes)
    reader = PdfReader(stream)
    num_pages = len(reader.pages)
    scanned = is_scanned_pdf(reader)

    pages_text = []
    for i, page in enumerate(reader.pages[:max_pages]):
        text = page.extract_text() or ""
        pages_text.append(text)

    combined_text = "\n".join(pages_text)
    return {
        "num_pages": num_pages,
        "is_scanned": scanned,
        "raw_text": combined_text,
        "pages": pages_text,
    }


def parse_bank_account_form(raw_text: str) -> dict[str, Any]:
    """Parse structured fields from bank account opening form text.
    Handles both Indonesian and English labels.
    """
    fields: dict[str, Any] = {}
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    full_text = " ".join(lines)

    # 1. Full Name
    name_match = re.search(
        r"(?:Nama\s+Lengkap(?:\s*\([^)]*\))?|Full\s+Name)\s*[:\n]?\s*([A-Z\s.,']{3,60})",
        raw_text,
        re.IGNORECASE,
    )
    if name_match:
        val = name_match.group(1).strip()
        # Clean trailing keywords if greedy
        val = re.split(r"(?:Nomor|NIK|Tempat|Jenis|Alamat)", val, flags=re.IGNORECASE)[0].strip()
        if val:
            fields["full_name"] = val.upper()

    # 2. Identity Number / NIK (16 digits or DUMMY format)
    nik_match = re.search(r"\b(DUMMY-[0-9A-Z-]+|\d{16})\b", raw_text)
    if nik_match:
        fields["identity_number"] = nik_match.group(1).strip()

    # 3. Birth place & date
    dob_match = re.search(
        r"(?:Tempat\s*/?\s*Tanggal\s+Lahir|Place\s*/?\s*Date\s+of\s+Birth)\s*[:\n]?\s*([^\n,]+)[,\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        raw_text,
        re.IGNORECASE,
    )
    if dob_match:
        fields["birth_place"] = dob_match.group(1).strip().upper()
        fields["birth_date_raw"] = dob_match.group(2).strip()
    else:
        # Fallback date search
        date_match = re.search(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", raw_text)
        if date_match:
            fields["birth_date_raw"] = date_match.group(1).strip()

    # 4. Account Purpose
    purpose_match = re.search(
        r"(?:Tujuan\s+Pembukaan\s+Rekening|Account\s+Purpose)\s*[:\n]?\s*([^\n]+)",
        raw_text,
        re.IGNORECASE,
    )
    if purpose_match:
        purpose_val = purpose_match.group(1).strip()
        # Trim if next label captured
        purpose_val = re.split(r"(?:Sumber|Jenis|Tanggal|Pernyataan)", purpose_val, flags=re.IGNORECASE)[0].strip()
        if purpose_val:
            fields["account_purpose"] = purpose_val.upper()

    # 5. Account Type
    acc_type_match = re.search(
        r"(?:Jenis\s+Rekening(?:\s*yang\s+diminta)?|Account\s+Type)\s*[:\n]?\s*([^\n]+)",
        raw_text,
        re.IGNORECASE,
    )
    if acc_type_match:
        acc_type_val = acc_type_match.group(1).strip()
        acc_type_val = re.split(r"(?:Mata|Tujuan|Sumber)", acc_type_val, flags=re.IGNORECASE)[0].strip()
        if acc_type_val:
            fields["account_type"] = acc_type_val.upper()

    # Document type detection hint
    is_bank_form = bool(
        re.search(r"PEMBUKAAN\s+REKENING|ACCOUNT\s+OPENING|BANK", raw_text, re.IGNORECASE)
    )

    return {
        "document_type": "account_opening_form" if is_bank_form else "unknown",
        "fields": fields,
        "is_bank_form": is_bank_form,
    }


def render_pdf_to_images(pdf_bytes: bytes, max_pages: int = 1) -> list[bytes]:
    """Render PDF pages to PNG image bytes for OCR processing (e.g. scanned forms)."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_bytes)
        images = []
        for i in range(min(len(pdf), max_pages)):
            page = pdf[i]
            image = page.render(scale=2).to_pil()
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            images.append(buf.getvalue())
        return images
    except Exception as e:
        return []


def parse_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Main facade for PDF parsing.
    Returns extracted fields if digital text exists; otherwise signals need for OCR.
    """
    extracted = extract_pdf_text(pdf_bytes)
    if extracted["is_scanned"]:
        # Render first page for OCR
        rendered_images = render_pdf_to_images(pdf_bytes, max_pages=1)
        return {
            "status": "REQUIRES_OCR",
            "document_type": "scanned_document",
            "is_scanned": True,
            "fields": {},
            "raw_text": "",
            "rendered_images": rendered_images,
            "message": "PDF contains no digital text layer; OCR required.",
        }

    parsed = parse_bank_account_form(extracted["raw_text"])
    return {
        "status": "COMPLETED",
        "document_type": parsed["document_type"],
        "is_scanned": False,
        "fields": parsed["fields"],
        "raw_text": extracted["raw_text"],
        "confidence": 1.0,  # Digital text extraction is 100% confident
    }

"""DOCX Document Parser for Microsoft Word files (.docx).
Extracts structured text from paragraphs and form tables.
"""

import io
import re
from typing import Any
import docx


LABEL_MAP = {
    r"nama\s+lengkap": "full_name",
    r"nomor\s+identitas|nik": "identity_number",
    r"tempat\s*/?\s*tanggal\s+lahir": "birth_place_date",
    r"jenis\s+kelamin": "gender",
    r"alamat": "address",
    r"telepon|handphone|hp": "phone",
    r"email": "email",
    r"pekerjaan": "occupation",
    r"penghasilan": "income",
    r"tujuan\s+pembukaan\s+rekening": "account_purpose",
    r"jenis\s+rekening": "account_type",
    r"mata\s+uang": "currency",
    r"sumber\s+dana": "source_of_funds",
}


def parse_docx(docx_bytes: bytes) -> dict[str, Any]:
    """Parse DOCX bytes into structured key-value fields."""
    stream = io.BytesIO(docx_bytes)
    doc = docx.Document(stream)

    raw_lines = []
    fields: dict[str, Any] = {}

    # 1. Parse Tables (standard bank forms use key-value table rows)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if len(cells) >= 2:
                label_text = cells[0].lower()
                val_text = cells[1].strip()

                raw_lines.append(f"{cells[0]}: {val_text}")

                # Match against known label patterns
                for pattern, field_key in LABEL_MAP.items():
                    if re.search(pattern, label_text):
                        if field_key not in fields:  # preserve first match
                            fields[field_key] = val_text.upper() if field_key in ("full_name", "account_purpose", "account_type") else val_text
                        break

    # 2. Parse Paragraphs (for titles, notices, headers)
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            raw_lines.append(txt)

    combined_text = "\n".join(raw_lines)

    # 3. Document type hint
    is_bank_form = bool(
        re.search(r"PEMBUKAAN\s+REKENING|ACCOUNT\s+OPENING|BANK", combined_text, re.IGNORECASE)
    )

    # If identity_number was not captured from table, try regex on text
    if "identity_number" not in fields:
        nik_match = re.search(r"\b(DUMMY-[0-9A-Z-]+|\d{16})\b", combined_text)
        if nik_match:
            fields["identity_number"] = nik_match.group(1).strip()

    # If full_name was not captured from table, try fallback regex
    if "full_name" not in fields:
        name_match = re.search(
            r"(?:Nama\s+Lengkap|Full\s+Name)\s*[:\n]?\s*([A-Z\s.,']{3,60})",
            combined_text,
            re.IGNORECASE,
        )
        if name_match:
            fields["full_name"] = name_match.group(1).strip().upper()

    return {
        "status": "COMPLETED",
        "document_type": "account_opening_form" if is_bank_form else "unknown",
        "is_scanned": False,
        "fields": fields,
        "raw_text": combined_text,
        "confidence": 1.0,
        "parser": "docx_parser",
    }

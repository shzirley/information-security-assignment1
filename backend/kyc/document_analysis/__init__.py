"""Document Analysis Package for VELTRIX BankKYC.
Includes PDF parser, DOCX parser, text comparison rules, and OCR engine adapter.
"""

from .pdf_parser import parse_pdf
from .docx_parser import parse_docx
from .ocr_engine import analyze_image_bytes
from .comparator import compare_field, compare_all_fields, normalize_date, normalize_nik, normalize_text
from .service import analyze_document

__all__ = [
    "analyze_document",
    "analyze_image_bytes",
    "parse_pdf",
    "parse_docx",
    "compare_field",
    "compare_all_fields",
    "normalize_date",
    "normalize_nik",
    "normalize_text",
]

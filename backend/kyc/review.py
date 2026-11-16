"""Document contract and review rules shared by upload, review and analysis."""
from contextlib import closing
from threading import Lock

from sqlalchemy import case, func, select

from .db import evidence, evidence_types

DEFAULT_TYPES = {
    'identity': 'ktp',
    'document': 'account_opening_form',
    'video': 'verification_video',
}
ACCEPTED_TYPES = {category: {kind} for category, kind in DEFAULT_TYPES.items()}
ACCEPTED_TYPES['document'].add('kk_optional')
REQUIRED = set(DEFAULT_TYPES.values())
PROFILE_FIELDS = ('full_name', 'identity_number', 'date_of_birth', 'address')
ACTIVE_REVIEW = ('SUBMITTED', 'RESUBMITTED', 'UNDER_REVIEW')
PDF_RENDER_LOCK = Lock()
DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
PREVIEW_MIME = {'image/png', 'image/jpeg', 'application/pdf', 'video/mp4', DOCX}


def classified_evidence(case_id):
    # Preserve the meaning of documents uploaded before the subtype existed.
    kind = func.coalesce(evidence_types.c.document_type,
                         case({'identity': 'ktp', 'video': 'verification_video'},
                              value=evidence.c.category, else_='legacy_supporting_document'))
    return (select(evidence, kind.label('document_type'))
            .outerjoin(evidence_types, evidence_types.c.evidence_id == evidence.c.id)
            .where(evidence.c.application_id == case_id))


def review_slot(entry):
    kind = entry['document_type']
    return DEFAULT_TYPES['document'] if kind == 'legacy_supporting_document' else kind


def current_evidence(connection, case_id):
    entries = connection.execute(classified_evidence(case_id).order_by(evidence.c.version)).mappings()
    return {review_slot(entry): entry for entry in entries}


def passed(check):
    return (check['readable'] and check['correct_document_type']
            and check['matches_applicant_form'] and not check['needs_clarification'])


def valid_reason(check):
    return {
        'VERIFIED': passed(check),
        'UNREADABLE': not check['readable'],
        'WRONG_DOCUMENT_TYPE': not check['correct_document_type'],
        'MISMATCH': not check['matches_applicant_form'],
        'CLARIFICATION': check['needs_clarification'],
    }[check['reason_code']]


def docx_preview(data):
    from io import BytesIO
    from xml.etree import ElementTree
    from zipfile import ZipFile

    with ZipFile(BytesIO(data)) as archive:
        root = ElementTree.fromstring(archive.read('word/document.xml'))
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    lines = []
    remaining = 32_000
    for paragraph in root.iter(ns + 'p'):
        text = ''.join(node.text or '' for node in paragraph.iter(ns + 't')).strip()
        if text:
            lines.append(text[:remaining])
            remaining -= len(text) + 1
            if remaining <= 0:
                break
    return '\n'.join(lines)


def pdf_page_preview(data, page_number):
    """Render one bounded page without exposing an active PDF to the browser."""
    from io import BytesIO
    import pypdfium2 as pdfium

    with PDF_RENDER_LOCK, pdfium.PdfDocument(data) as document:
        count = len(document)
        if page_number > count:
            return None
        with closing(document[page_number - 1]) as page:
            width, height = page.get_size()
            scale = min(2.0, 1600 / max(width, height))
            with closing(page.render(scale=scale)) as bitmap:
                with BytesIO() as result:
                    bitmap.to_pil().save(result, format='PNG')
                    return result.getvalue(), count

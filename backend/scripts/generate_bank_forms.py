"""Generate synthetic bank account opening forms matching Kaggle synthetic KTP:
Applicant: PUPUT NUGROHO
Form formats:
1. DOCX (Word Document)
2. Digital PDF (Selectable text layer)
3. Scanned PDF (Raster image wrapped in PDF, simulating paper scan)
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUT_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic_kyc"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Synthetic Applicant Data from User's Kaggle KTP Fixture
DATA = {
    "bank_name": "BANK SIMULASI VELTRIX",
    "form_title": "FORMULIR PEMBUKAAN REKENING NASABAH PERORANGAN",
    "full_name": "PUPUT NUGROHO",
    "identity_number": "2912541012827585",
    "birth_place_date": "SURABAYA, 27-01-1950",
    "gender": "PEREMPUAN",
    "address": "GANG PHH. MUSTOFA NO. 2, RT/RW 010/020, KEL. PALANGKARAYA, KEC. BALIKPAPAN",
    "phone": "0812-9876-5432",
    "email": "puput.nugroho@example.com",
    "occupation": "TIDAK BEKERJA",
    "income": "DANA PRIBADI / KELUARGA",
    "account_type": "TABUNGAN VELTRIX REGULER",
    "currency": "IDR (RUPIAH)",
    "account_purpose": "TABUNGAN PRIBADI & TRANSAKSI KELUARGA",
    "source_of_funds": "SIMPANAN PRIBADI / KELUARGA",
    "application_date": "14 NOVEMBER 2026",
}


def create_docx(path: Path):
    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    # Header
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = title.add_run(DATA["bank_name"] + "\n")
    r1.bold = True
    r1.font.size = Pt(14)
    r1.font.color.rgb = RGBColor(16, 44, 87)

    r2 = title.add_run(DATA["form_title"] + "\n")
    r2.bold = True
    r2.font.size = Pt(11)
    r2.font.color.rgb = RGBColor(50, 50, 50)

    r3 = title.add_run("Dokumen Simulasi Akademik — Tidak Mewakili Akun Perbankan Nyata")
    r3.italic = True
    r3.font.size = Pt(8.5)
    r3.font.color.rgb = RGBColor(120, 120, 120)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # Section 1: Data Pribadi
    s1 = doc.add_paragraph()
    s1_run = s1.add_run("BAGIAN A: DATA PRIBADI PEMOHON")
    s1_run.bold = True
    s1_run.font.size = Pt(10)
    s1_run.font.color.rgb = RGBColor(16, 44, 87)

    t1_rows = [
        ("Nama Lengkap (sesuai KTP)", DATA["full_name"]),
        ("Nomor Identitas (NIK)", DATA["identity_number"]),
        ("Tempat / Tanggal Lahir", DATA["birth_place_date"]),
        ("Jenis Kelamin", DATA["gender"]),
        ("Alamat Tempat Tinggal", DATA["address"]),
        ("Nomor Telepon / Handphone", DATA["phone"]),
        ("Alamat Email", DATA["email"]),
        ("Pekerjaan", DATA["occupation"]),
        ("Penghasilan per Bulan", DATA["income"]),
    ]

    table1 = doc.add_table(rows=len(t1_rows), cols=2)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (label, val) in enumerate(t1_rows):
        row = table1.rows[i]
        c0 = row.cells[0]
        c1 = row.cells[1]
        c0.width = Inches(2.3)
        c1.width = Inches(4.5)
        c0.paragraphs[0].add_run(label).font.size = Pt(9)
        c1.paragraphs[0].add_run(val).font.size = Pt(9)
        c1.paragraphs[0].runs[0].bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Section 2: Informasi Rekening
    s2 = doc.add_paragraph()
    s2_run = s2.add_run("BAGIAN B: INFORMASI REKENING")
    s2_run.bold = True
    s2_run.font.size = Pt(10)
    s2_run.font.color.rgb = RGBColor(16, 44, 87)

    t2_rows = [
        ("Jenis Rekening yang Diminta", DATA["account_type"]),
        ("Mata Uang", DATA["currency"]),
        ("Tujuan Pembukaan Rekening", DATA["account_purpose"]),
        ("Sumber Dana Utama", DATA["source_of_funds"]),
    ]

    table2 = doc.add_table(rows=len(t2_rows), cols=2)
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (label, val) in enumerate(t2_rows):
        row = table2.rows[i]
        c0 = row.cells[0]
        c1 = row.cells[1]
        c0.width = Inches(2.3)
        c1.width = Inches(4.5)
        c0.paragraphs[0].add_run(label).font.size = Pt(9)
        c1.paragraphs[0].add_run(val).font.size = Pt(9)
        c1.paragraphs[0].runs[0].bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Section 3: Pernyataan & Tanda Tangan
    decl = doc.add_paragraph()
    decl.paragraph_format.space_before = Pt(4)
    d_run = decl.add_run(
        "Pernyataan Pemohon: Dengan menandatangani formulir ini, saya menyatakan bahwa data yang saya berikan "
        "adalah benar dan akurat untuk keperluan simulasi pembukaan rekening digital Bank Veltrix."
    )
    d_run.font.size = Pt(8)
    d_run.font.color.rgb = RGBColor(80, 80, 80)

    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_left = sig_table.rows[0].cells[0]
    c_right = sig_table.rows[0].cells[1]
    c_left.width = Inches(3.5)
    c_right.width = Inches(3.3)

    c_left.paragraphs[0].add_run(f"Tanggal Pengajuan: {DATA['application_date']}").font.size = Pt(8.5)
    p_sig = c_right.paragraphs[0]
    p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig.add_run(f"Tanda Tangan Pemohon:\n\n[ttd digital]\n{DATA['full_name']}").font.size = Pt(8.5)

    try:
        doc.save(str(path))
        print(f"[OK] DOCX generated: {path}")
    except PermissionError:
        alt_path = path.parent / "bank_account_form_puput.docx"
        doc.save(str(alt_path))
        print(f"[WARN] {path.name} is currently open in Word. Saved as: {alt_path.name}")


def create_digital_pdf(path: Path):
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=35,
        bottomMargin=35,
    )
    styles = getSampleStyleSheet()

    header_title = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#102C57"),
        alignment=1,
    )
    header_sub = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#333333"),
        alignment=1,
    )
    header_notice = ParagraphStyle(
        "HeaderNotice",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#777777"),
        alignment=1,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#102C57"),
    )
    cell_label = ParagraphStyle(
        "CellLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#444444"),
    )
    cell_val = ParagraphStyle(
        "CellVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#111111"),
    )
    decl_style = ParagraphStyle(
        "DeclStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#555555"),
    )

    story = [
        Paragraph(DATA["bank_name"], header_title),
        Paragraph(DATA["form_title"], header_sub),
        Spacer(1, 2),
        Paragraph("Dokumen Simulasi Akademik — Tidak Mewakili Akun Perbankan Nyata", header_notice),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#102C57")),
        Spacer(1, 8),
        Paragraph("BAGIAN A: DATA PRIBADI PEMOHON", section_title),
        Spacer(1, 4),
    ]

    t1_data = [
        [Paragraph("Nama Lengkap (sesuai KTP)", cell_label), Paragraph(DATA["full_name"], cell_val)],
        [Paragraph("Nomor Identitas (NIK)", cell_label), Paragraph(DATA["identity_number"], cell_val)],
        [Paragraph("Tempat / Tanggal Lahir", cell_label), Paragraph(DATA["birth_place_date"], cell_val)],
        [Paragraph("Jenis Kelamin", cell_label), Paragraph(DATA["gender"], cell_val)],
        [Paragraph("Alamat Tempat Tinggal", cell_label), Paragraph(DATA["address"], cell_val)],
        [Paragraph("Nomor Telepon / Handphone", cell_label), Paragraph(DATA["phone"], cell_val)],
        [Paragraph("Alamat Email", cell_label), Paragraph(DATA["email"], cell_val)],
        [Paragraph("Pekerjaan", cell_label), Paragraph(DATA["occupation"], cell_val)],
        [Paragraph("Penghasilan per Bulan", cell_label), Paragraph(DATA["income"], cell_val)],
    ]
    t1 = Table(t1_data, colWidths=[180, 335])
    t1.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#EAEAEA")),
        ])
    )
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(Paragraph("BAGIAN B: INFORMASI REKENING", section_title))
    story.append(Spacer(1, 4))

    t2_data = [
        [Paragraph("Jenis Rekening yang Diminta", cell_label), Paragraph(DATA["account_type"], cell_val)],
        [Paragraph("Mata Uang", cell_label), Paragraph(DATA["currency"], cell_val)],
        [Paragraph("Tujuan Pembukaan Rekening", cell_label), Paragraph(DATA["account_purpose"], cell_val)],
        [Paragraph("Sumber Dana Utama", cell_label), Paragraph(DATA["source_of_funds"], cell_val)],
    ]
    t2 = Table(t2_data, colWidths=[180, 335])
    t2.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#EAEAEA")),
        ])
    )
    story.append(t2)
    story.append(Spacer(1, 12))

    # Declaration & Signature
    story.append(
        Paragraph(
            "Pernyataan Pemohon: Dengan menandatangani formulir ini, saya menyatakan bahwa data yang saya berikan "
            "adalah benar dan akurat untuk keperluan simulasi pembukaan rekening digital Bank Veltrix.",
            decl_style,
        )
    )
    story.append(Spacer(1, 10))

    sig_data = [
        [
            Paragraph(f"Tanggal Pengajuan: <b>{DATA['application_date']}</b>", cell_label),
            Paragraph(f"Tanda Tangan Pemohon:<br/><br/><i>[ttd digital]</i><br/><b>{DATA['full_name']}</b>", cell_label),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[260, 255])
    t_sig.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ])
    )
    story.append(t_sig)

    doc.build(story)
    print(f"[OK] Digital PDF generated: {path}")


def create_scanned_pdf(path: Path):
    """Render an A4 paper image at 150 DPI with slight scanner grain/skew, then save as PDF."""
    dpi = 150
    w = int(8.27 * dpi)  # 1240 px
    h = int(11.69 * dpi)  # 1753 px

    img = Image.new("RGB", (w, h), (252, 252, 250))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_sub = ImageFont.truetype("arial.ttf", 20)
        font_sec = ImageFont.truetype("arial.ttf", 17)
        font_bold = ImageFont.truetype("arial.ttf", 15)
        font_reg = ImageFont.truetype("arial.ttf", 15)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except IOError:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_sec = font_title
        font_bold = font_title
        font_reg = font_title
        font_small = font_title

    # Header
    draw.text((w // 2, 60), DATA["bank_name"], fill=(16, 44, 87), font=font_title, anchor="mt")
    draw.text((w // 2, 95), DATA["form_title"], fill=(40, 40, 40), font=font_sub, anchor="mt")
    draw.text((w // 2, 125), "Dokumen Simulasi Akademik — Hasil Pindai (Scanned)", fill=(120, 120, 120), font=font_small, anchor="mt")
    draw.line([(80, 150), (w - 80, 150)], fill=(16, 44, 87), width=3)

    y = 180
    draw.text((80, y), "BAGIAN A: DATA PRIBADI PEMOHON", fill=(16, 44, 87), font=font_sec)
    y += 35

    t1_rows = [
        ("Nama Lengkap", DATA["full_name"]),
        ("Nomor Identitas (NIK)", DATA["identity_number"]),
        ("Tempat / Tanggal Lahir", DATA["birth_place_date"]),
        ("Jenis Kelamin", DATA["gender"]),
        ("Alamat Tempat Tinggal", DATA["address"]),
        ("Nomor Telepon", DATA["phone"]),
        ("Alamat Email", DATA["email"]),
        ("Pekerjaan", DATA["occupation"]),
        ("Penghasilan per Bulan", DATA["income"]),
    ]

    for label, val in t1_rows:
        draw.text((90, y), label, fill=(70, 70, 70), font=font_reg)
        draw.text((420, y), ":  " + val, fill=(10, 10, 10), font=font_bold)
        draw.line([(85, y + 26), (w - 85, y + 26)], fill=(230, 230, 230), width=1)
        y += 36

    y += 20
    draw.text((80, y), "BAGIAN B: INFORMASI REKENING", fill=(16, 44, 87), font=font_sec)
    y += 35

    t2_rows = [
        ("Jenis Rekening", DATA["account_type"]),
        ("Mata Uang", DATA["currency"]),
        ("Tujuan Rekening", DATA["account_purpose"]),
        ("Sumber Dana", DATA["source_of_funds"]),
    ]

    for label, val in t2_rows:
        draw.text((90, y), label, fill=(70, 70, 70), font=font_reg)
        draw.text((420, y), ":  " + val, fill=(10, 10, 10), font=font_bold)
        draw.line([(85, y + 26), (w - 85, y + 26)], fill=(230, 230, 230), width=1)
        y += 36

    y += 40
    decl = (
        "Pernyataan Pemohon: Saya menyatakan bahwa data di atas benar untuk simulasi pembukaan rekening Bank Veltrix."
    )
    draw.text((80, y), decl, fill=(90, 90, 90), font=font_small)

    y += 50
    draw.text((90, y), f"Tanggal Pengajuan: {DATA['application_date']}", fill=(60, 60, 60), font=font_reg)
    draw.text((w - 380, y), "Tanda Tangan Pemohon:", fill=(60, 60, 60), font=font_reg)
    draw.text((w - 380, y + 40), "[ttd basah / paraf]", fill=(20, 20, 140), font=font_small)
    draw.text((w - 380, y + 65), f"( {DATA['full_name']} )", fill=(20, 20, 20), font=font_bold)

    # Realistic slight scanner rotation
    scanned = img.rotate(0.4, resample=Image.BICUBIC, fillcolor=(245, 245, 243))

    scanned.save(str(path), "PDF", resolution=dpi)
    print(f"[OK] Scanned PDF generated: {path}")


if __name__ == "__main__":
    create_docx(OUT_DIR / "bank_account_form_template.docx")
    create_digital_pdf(OUT_DIR / "bank_account_form_digital.pdf")
    create_scanned_pdf(OUT_DIR / "bank_account_form_scanned.pdf")
    print(f"\nAll 3 bank forms successfully updated in:\n{OUT_DIR}")

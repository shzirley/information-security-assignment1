"""Generator for Assignment 2 Synthetic Demo Fixtures (Andi, Budi, Citra).
Creates authentic-looking synthetic KTP images and bank account opening forms.
Complies 100% with Indonesian UU PDP No. 27/2022 (Zero real PII).
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

TARGET_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic_kyc"
DEMO_KEYS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo_keys"


def get_font(size: int, bold: bool = False):
    """Load system font if available, fallback to default."""
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    font_path = Path("C:/Windows/Fonts") / font_name
    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass
    return ImageFont.load_default()


def create_synthetic_ktp(
    filename: str,
    provinsi: str,
    kota: str,
    nik: str,
    nama: str,
    ttl: str,
    jenis_kelamin: str,
    gol_darah: str,
    alamat: str,
    rtrw: str,
    keldesa: str,
    kecamatan: str,
    agama: str,
    status_kawin: str,
    pekerjaan: str,
    kewarganegaraan: str,
    photo_bg_color: tuple = (180, 20, 20),  # Red for odd birth year, Blue (20, 60, 180) for even
    is_female: bool = False,
):
    """Generate high-resolution Indonesian synthetic e-KTP image."""
    width, height = 1000, 630
    # Background: classic e-KTP cyan/sky-blue gradient with micro-pattern
    img = Image.new("RGB", (width, height), color=(115, 178, 206))
    draw = ImageDraw.Draw(img)

    # 1. Subtle wavy background pattern
    for y in range(0, height, 4):
        tint = int(170 + 20 * (y % 8 == 0))
        draw.line([(0, y), (width, y)], fill=(100, tint, 200, 40), width=1)

    # Inner border
    draw.rounded_rectangle([15, 15, width - 15, height - 15], radius=18, outline=(70, 130, 160), width=3)

    # 2. Header
    f_header = get_font(24, bold=True)
    f_sub = get_font(20, bold=True)
    draw.text((width // 2, 35), provinsi.upper(), fill=(10, 25, 40), font=f_header, anchor="mm")
    draw.text((width // 2, 65), kota.upper(), fill=(10, 25, 40), font=f_sub, anchor="mm")

    # 3. NIK Section
    f_nik_label = get_font(22, bold=True)
    f_nik_val = get_font(26, bold=True)
    draw.text((45, 105), "NIK", fill=(0, 0, 0), font=f_nik_label)
    draw.text((220, 105), f": {nik}", fill=(10, 20, 30), font=f_nik_val)

    # 4. Demographic Fields
    f_lbl = get_font(16, bold=True)
    f_val = get_font(16, bold=False)

    fields = [
        ("Nama", f": {nama}"),
        ("Tempat/Tgl Lahir", f": {ttl}"),
        ("Jenis Kelamin", f": {jenis_kelamin}"),
        ("Alamat", f": {alamat}"),
        ("    RT/RW", f": {rtrw}"),
        ("    Kel/Desa", f": {keldesa}"),
        ("    Kecamatan", f": {kecamatan}"),
        ("Agama", f": {agama}"),
        ("Status Perkawinan", f": {status_kawin}"),
        ("Pekerjaan", f": {pekerjaan}"),
        ("Kewarganegaraan", f": {kewarganegaraan}"),
        ("Berlaku Hingga", ": SEUMUR HIDUP"),
    ]

    start_y = 150
    line_h = 32
    for i, (label, val) in enumerate(fields):
        y = start_y + (i * line_h)
        draw.text((45, y), label, fill=(15, 25, 35), font=f_lbl)
        draw.text((220, y), val, fill=(15, 25, 35), font=f_val)
        if label == "Jenis Kelamin":
            draw.text((480, y), f"Gol. Darah : {gol_darah}", fill=(15, 25, 35), font=f_lbl)

    # 5. Photo Box (Right side)
    photo_x1, photo_y1 = 740, 160
    photo_x2, photo_y2 = 940, 420
    draw.rectangle([photo_x1, photo_y1, photo_x2, photo_y2], fill=photo_bg_color, outline=(40, 40, 40), width=2)

    # Synthetic Silhouette Avatar
    head_cx, head_cy = (photo_x1 + photo_x2) // 2, photo_y1 + 90
    draw.ellipse([head_cx - 40, head_cy - 48, head_cx + 40, head_cy + 48], fill=(225, 200, 175))
    if is_female:
        # Female hair silhouette
        draw.chord([head_cx - 50, head_cy - 60, head_cx + 50, head_cy + 55], 180, 360, fill=(40, 30, 25))
        draw.rectangle([head_cx - 48, head_cy - 10, head_cx - 36, head_cy + 70], fill=(40, 30, 25))
        draw.rectangle([head_cx + 36, head_cy - 10, head_cx + 48, head_cy + 70], fill=(40, 30, 25))
    else:
        # Male hair silhouette
        draw.chord([head_cx - 42, head_cy - 52, head_cx + 42, head_cy], 180, 360, fill=(35, 30, 30))

    # Body silhouette (shirt/suit)
    body_top = head_cy + 48
    draw.polygon(
        [
            (photo_x1 + 10, photo_y2),
            (photo_x2 - 10, photo_y2),
            (head_cx + 55, body_top + 30),
            (head_cx - 55, body_top + 30),
        ],
        fill=(25, 35, 55),
    )

    # 6. City, Issue Date, and Signature Box
    f_small = get_font(14, bold=True)
    draw.text((840, 445), "KOTA BANDUNG", fill=(10, 20, 30), font=f_small, anchor="mm")
    draw.text((840, 465), "16-08-2013", fill=(10, 20, 30), font=f_small, anchor="mm")

    # Synthetic signature squiggles
    draw.arc([770, 480, 850, 530], 0, 180, fill=(10, 20, 40), width=2)
    draw.line([(810, 520), (890, 490)], fill=(10, 20, 40), width=2)
    draw.line([(870, 500), (920, 530)], fill=(10, 20, 40), width=2)

    # Save output
    out_path = TARGET_DIR / filename
    img.save(out_path, "PNG")
    print(f"✓ Generated KTP: {out_path.name} ({width}x{height})")
    return out_path


def create_bank_form_pdf(filename: str):
    """Generate official VELTRIX Bank Account Opening Form for HIMA (Budi Pratama)."""
    pdf_path = TARGET_DIR / filename
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BankTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0B2545"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "BankSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#134074"),
        alignment=1,
    )
    section_style = ParagraphStyle(
        "BankSec",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0B2545"),
    )
    cell_lbl_style = ParagraphStyle(
        "CellLbl",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1D2D44"),
    )
    cell_val_style = ParagraphStyle(
        "CellVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0B2545"),
    )

    story = []
    story.append(Paragraph("VELTRIX BANK INDONESIA", title_style))
    story.append(Paragraph("FORMULIR PEMBUKAAN REKENING ORGANISASI MAHASISWA (GIRO & TABUNGAN)", subtitle_style))
    story.append(Paragraph("Kantor Cabang: KC Bandung Ganesha — Kode Formulir: ORG-KYC-2026-HIMA", subtitle_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B2545"), spaceAfter=10))

    # SECTION 1: DATA REKENING ORGANISASI
    story.append(Paragraph("BAGIAN 1: INFORMASI ORGANISASI & REKENING YANG DIMINTA", section_style))
    story.append(Spacer(1, 4))
    org_data = [
        [Paragraph("Nama Organisasi", cell_lbl_style), Paragraph("HIMPUNAN MAHASISWA TEKNIK INFORMATIKA (HIMA-IF)", cell_val_style)],
        [Paragraph("Jenis Rekening", cell_lbl_style), Paragraph("TABUNGAN VELTRIX REGULER ORGANISASI", cell_val_style)],
        [Paragraph("Mata Uang", cell_lbl_style), Paragraph("IDR (Rupiah)", cell_val_style)],
        [Paragraph("Tujuan Pembukaan Rekening", cell_lbl_style), Paragraph("REKENING OPERASIONAL ORGANISASI MAHASISWA", cell_val_style)],
        [Paragraph("Sumber Dana", cell_lbl_style), Paragraph("IURAN ANGGOTA & DANA KEMAHASISWAAN", cell_val_style)],
    ]
    t1 = Table(org_data, colWidths=[2.2 * inch, 4.8 * inch])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF4F8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8DA9C4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    # SECTION 2: DATA PENANDATANGAN 1 (KETUA - ANDI WIJAYA)
    story.append(Paragraph("BAGIAN 2: DATA PENGURUS 1 (KETUA / PEMOHON UTAMA)", section_style))
    story.append(Spacer(1, 4))
    andi_data = [
        [Paragraph("Nama Lengkap", cell_lbl_style), Paragraph("ANDI WIJAYA", cell_val_style)],
        [Paragraph("Jabatan Organisasi", cell_lbl_style), Paragraph("KETUA HIMA INFORMATIKA", cell_val_style)],
        [Paragraph("Nomor Identitas (NIK)", cell_lbl_style), Paragraph("3273011005950002", cell_val_style)],
        [Paragraph("Tempat & Tanggal Lahir", cell_lbl_style), Paragraph("BANDUNG, 10-05-1995", cell_val_style)],
        [Paragraph("Alamat Domisili", cell_lbl_style), Paragraph("JL. GANESHA NO. 10, BANDUNG", cell_val_style)],
    ]
    t2 = Table(andi_data, colWidths=[2.2 * inch, 4.8 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF4F8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8DA9C4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    # SECTION 3: DATA PENANDATANGAN 2 (BENDAHARA - BUDI PRATAMA)
    story.append(Paragraph("BAGIAN 3: DATA PENGURUS 2 (BENDAHARA / PEMILIK DATA CO-SIGNER)", section_style))
    story.append(Spacer(1, 4))
    budi_data = [
        [Paragraph("Nama Lengkap", cell_lbl_style), Paragraph("BUDI PRATAMA", cell_val_style)],
        [Paragraph("Jabatan Organisasi", cell_lbl_style), Paragraph("BENDAHARA HIMA INFORMATIKA", cell_val_style)],
        [Paragraph("Nomor Identitas (NIK)", cell_lbl_style), Paragraph("3273011508950001", cell_val_style)],
        [Paragraph("Tempat & Tanggal Lahir", cell_lbl_style), Paragraph("BANDUNG, 15-08-1995", cell_val_style)],
        [Paragraph("Alamat Domisili", cell_lbl_style), Paragraph("JL. DIPONEGORO NO. 45, BANDUNG", cell_val_style)],
        [Paragraph("Nomor Kontak & Email", cell_lbl_style), Paragraph("081234567890 / budi.pratama@hima-if.org", cell_val_style)],
    ]
    t3 = Table(budi_data, colWidths=[2.2 * inch, 4.8 * inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF4F8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8DA9C4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t3)
    story.append(Spacer(1, 12))

    # SECTION 4: TANDA TANGAN
    story.append(Paragraph("BAGIAN 4: PENGESAHAN & PERNYATAAN BERSAMA", section_style))
    sig_data = [
        [
            Paragraph("Pemohon 1 (Ketua HIMA):<br/><br/><br/><b>ANDI WIJAYA</b><br/>NIK: 3273011005950002", cell_val_style),
            Paragraph("Pemohon 2 (Bendahara HIMA):<br/><br/><br/><b>BUDI PRATAMA</b><br/>NIK: 3273011508950001", cell_val_style),
            Paragraph("Petugas Bank (Customer Service):<br/><br/><br/><b>VELTRIX CS OFFICER</b><br/>NIP: CS-2026-BDG", cell_val_style),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[2.3 * inch, 2.3 * inch, 2.4 * inch])
    t_sig.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#8DA9C4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_sig)

    doc.build(story)
    print(f"✓ Generated Bank Form PDF: {pdf_path.name}")
    return pdf_path


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_KEYS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Generating Synthetic KYC Fixtures for Assignment 2 (HIMA)")
    print("=" * 60)

    # 1. KTP Budi Pratama (Bendahara - Odd Year 1995 -> Red Background)
    create_synthetic_ktp(
        filename="ktp_budi_pratama.png",
        provinsi="PROVINSI JAWA BARAT",
        kota="KOTA BANDUNG",
        nik="3273011508950001",
        nama="BUDI PRATAMA",
        ttl="BANDUNG, 15-08-1995",
        jenis_kelamin="LAKI-LAKI",
        gol_darah="O",
        alamat="JL. DIPONEGORO NO. 45",
        rtrw="004/008",
        keldesa="CIHAPIT",
        kecamatan="BANDUNG WETAN",
        agama="ISLAM",
        status_kawin="BELUM KAWIN",
        pekerjaan="MAHASISWA",
        kewarganegaraan="WNI",
        photo_bg_color=(190, 25, 25),
        is_female=False,
    )

    # 2. KTP Andi Wijaya (Ketua - Odd Year 1995 -> Red Background)
    create_synthetic_ktp(
        filename="ktp_andi_wijaya.png",
        provinsi="PROVINSI JAWA BARAT",
        kota="KOTA BANDUNG",
        nik="3273011005950002",
        nama="ANDI WIJAYA",
        ttl="BANDUNG, 10-05-1995",
        jenis_kelamin="LAKI-LAKI",
        gol_darah="A",
        alamat="JL. GANESHA NO. 10",
        rtrw="002/005",
        keldesa="LEBAKSILIWANGI",
        kecamatan="COBLONG",
        agama="ISLAM",
        status_kawin="BELUM KAWIN",
        pekerjaan="MAHASISWA",
        kewarganegaraan="WNI",
        photo_bg_color=(190, 25, 25),
        is_female=False,
    )

    # 3. KTP Citra Lestari (Pihak Ketiga - Even Year 1996 -> Blue Background)
    create_synthetic_ktp(
        filename="ktp_citra_lestari.png",
        provinsi="PROVINSI JAWA BARAT",
        kota="KOTA BANDUNG",
        nik="3273015206960003",
        nama="CITRA LESTARI",
        ttl="BANDUNG, 12-06-1996",
        jenis_kelamin="PEREMPUAN",
        gol_darah="B",
        alamat="JL. DAGO NO. 88",
        rtrw="003/009",
        keldesa="DAGO",
        kecamatan="COBLONG",
        agama="ISLAM",
        status_kawin="BELUM KAWIN",
        pekerjaan="MAHASISWA",
        kewarganegaraan="WNI",
        photo_bg_color=(25, 70, 180),
        is_female=True,
    )

    # 4. Official Bank Form PDF for Budi & HIMA
    create_bank_form_pdf("bank_account_form_budi.pdf")

    print("\n✓ All Assignment 2 synthetic fixtures successfully generated!")


if __name__ == "__main__":
    main()

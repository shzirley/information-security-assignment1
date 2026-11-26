// ---------- Layout (two columns, A4) ----------
#set document(title: "VELTRIX: A Secure Digital Banking Onboarding and Encrypted KYC Evidence Vault")
#set page(
  paper: "a4",
  margin: (top: 1.7cm, bottom: 1.7cm, left: 1.6cm, right: 1.6cm),
  columns: 2,
)
#set columns(gutter: 0.65cm)
#set text(font: "New Computer Modern", size: 10pt, lang: "en")
#set par(justify: true, leading: 0.55em, spacing: 0.5em, first-line-indent: 0pt)

// Headings: numbered, compact spacing (setara titlesec[compact])
#set heading(numbering: "1.1")
#show heading: it => {
  set text(weight: "bold", size: if it.level == 1 { 14.4pt } else { 12pt }, hyphenate: false)
  set par(justify: false)
  block(
    above: if it.level == 1 { 8pt } else { 6pt },
    below: if it.level == 1 { 4pt } else { 3pt },
    it,
  )
}

// Lists: rapat (nosep)
#set list(tight: true, indent: 1.2em, body-indent: 0.5em, spacing: 0.4em)

// Links
#show link: set text(font: "DejaVu Sans Mono", size: 0.85em)

// Caption: "Table 1: ..." (caption tabel di atas)
#set figure.caption(separator: [: ])
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.caption: set text(size: 9pt)

// ---------- Title (spans both columns) ----------
#place(
  top + center,
  scope: "parent",
  float: true,
  {
    set align(center)
    set par(justify: false)
    set text(hyphenate: false)
    v(-0.4em)
    text(size: 17pt, weight: "bold")[
      VELTRIX: A Secure Digital Banking Onboarding and Encrypted KYC Evidence Vault
    ]
    v(0.3em)
    text(size: 9pt)[
      #raw("GitHub Repository: ") #link("https://github.com/shzirley/information-security-assignment1")
    ]
    v(0.8em)
    text(size: 9pt)[
      #grid(
        columns: (auto, auto),
        column-gutter: 2.5em,
        row-gutter: 0.9em,
        align: center,
        [Jahhaza Assiqoyah Nurul Hidayah \ (5025241019)],
        [Maleka Ghaniya \ (5025241189)],
        [Jorell Ramos Sinaga \ (5025241202)],
        [Angela Vania Sugiyono \ (5025241226)],
      )
    ]
    v(0.6em)
  },
)

// ==================================================
// Tulis isi dokumen di bawah ini.
// Contoh:
//
// = Judul Section
// == Judul Subsection
// Paragraf biasa dengan *teks tebal* dan _teks miring_.
// - Item daftar

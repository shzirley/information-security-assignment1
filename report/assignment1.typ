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
= Scenario and Motivation
== Setting and Users
Customers wans to open a bank account online, a process that may request identity documents, employment data, and forms, followed by remote verification. If identity images, employment information, or verification recordings are stored without controls, the impact of a data leak increases. The VELTRIX MVP is a vault for onboarding proof packages, not a system that can create real accounts.

== Why Protection Matters
Onboarding collects highly secret data like ID photos and videos. Storing them without encryption or strict access limits makes it very easy for hackers to steal identities. That's why locking this data securely is a must.

// ==================================================
= Data Classification and Regulation
The VELTRIX onboarding process mandates four distinct categories of data:
- *Personal data:* Name, address, employment information, contact details, and account purpose (Stored as encrypted JSON).
- *Scanned identity:* Official identity card scan (PNG / PDF).
- *Office documents:* Account opening form and declaration letter (DOCX / PDF).
- *Video:* Self-verification video with applicant consent (MP4).

#v(0.3em)
*Data Privacy Classification:*
- _General personal data:_ Full name, residential address, contact information, and employment details.
- _Specific (Sensitive) personal data:_ Identity card scans (containing the NIK and signature), biometric face verification videos, and financial consent forms protected by banking secrecy.

#v(0.3em)
*Applicable Indonesian Regulations:*
- *PDP Law (No. 27 of 2022):* Mandates explicit user consent for processing biometric data and requires strict encryption and access controls to prevent unauthorized data leaks.
- *OJK Regulations (POJK):* Governs mandatory electronic Customer Due Diligence (CDD) for anti-money laundering (AML) and strictly enforces the confidentiality of consumer data.
- *ITE Law and PP PSTE (Reg 71 of 2019):* Requires electronic system providers to implement reliable security measures, such as hashing and encrypted storage, to prevent data interception.

// ==================================================
= Design Decisions and Justification
== Architecture
VELTRIX uses a three-part system (Next.js for the website, FastAPI for the logic, and MySQL for the database). All encryption and decryption happen safely on the server. This provides three main benefits:
- *Hidden Keys:* Encryption keys are locked away on the server, keeping them safe from hackers trying to attack the user's browser.
- *Strict Access Rules:* The system double-checks exactly who owns the file before unlocking and revealing it.
- *No Unprotected Traces:* Uploaded files are processed in the server's active memory (RAM). They are never saved as unprotected temporary files on the hard drive.

== Cipher Modes
We strictly avoid the basic "ECB" encryption mode because it leaves visible patterns in files like ID images and videos. Instead, we use safer methods:
- *AES-256 & DES:* We use "CBC" mode with random starting values (IV) to ensure that even identical files look completely different when encrypted. For maximum safety, the outermost layer uses *AES-GCM*, which not only hides the data but also acts like a tamper-proof seal to prevent any modifications.
- *RC4:* We drop the first 3,072 bytes of this older algorithm (`drop=3072`) to fix its known predictable flaws.

== Key Management
Our key architecture decouples user data from decryption keys, preventing unauthorized access even if the database is compromised.
- *Unique Keys:* Every uploaded object is assigned three fresh random keys (for RC4, DES, and AES). These are bundled into a single unique payload.
- *Key Wrapping:* The key bundle is wrapped (encrypted) using a server-side Key Encryption Key (KEK) loaded strictly from environment variables, keeping it out of the database.
- *Fail-Closed Design:* Missing or invalid KEK settings force decryption to fail closed, keeping stored ciphertexts unreadable rather than risking plain text leakage.

== Authentication and Access Control
We enforce strict identity validation and session integrity checks.
- *Secure Authentication:* Passwords are hashed using Argon2id. Active sessions rely on SHA-256 digested tokens inside HttpOnly cookies with an eight-hour lifespan.
- *Owner-Only Access:* File requests execute strict ownership verification (`owner=True`). Unauthorized access attempts fail closed and return generic 404 responses.
- *Integrity Verification:* Every retrieved object undergoes payload length and constant-time SHA-256 hash validation. Any detected tampering immediately halts downloads.

== Storage Strategy
Database storage separates sensitive encrypted payloads from operational metadata.
- *Encrypted Vault:* Evidence objects and identity profiles reside in the `encrypted_objects` table with encrypted original filenames, payload content, and private headers.
- *Operational Metadata:* Non-sensitive attributes (such as `status`, owner IDs, file sizes, and MIME types) remain in plaintext to support UI listings and storage quota checks.

// ==================================================
= Cipher Comparison and Analysis
== Methodology
We evaluated performance to ensure multi-layered encryption remains responsive during interactive onboarding. Local bench tests (`lab.py`) measured four synthetic fixtures representing mandated payload types: JSON (profile data), PNG (ID scan), PDF (application form), and MP4 (verification video).

Each run comprised 100 timed trials following two discarded warm-up rounds. Measurements recorded median encryption latency using high-resolution timers, excluding network, HTTP, and database overheads (Trial CSV: #link("https://github.com/shzirley/information-security-assignment1/tree/main/backend/CSV_trial")).

== Results
Empirical measurements across 100 trials per fixture are presented in @tab:cipher-results. All algorithms successfully passed round-trip byte equality checks without data corruption.

#figure(
  placement: none,
  caption: [Median encryption time (ms) and inter-quartile range [IQR].],
  {
    set text(size: 8pt)
    table(
      columns: 5,
      align: (left, center, center, center, center),
      stroke: none,
      inset: (x: 2.5pt, y: 3pt),
      table.hline(stroke: 0.8pt),
      [Candidate], [JSON], [PNG], [PDF], [MP4],
      table.hline(stroke: 0.4pt),
      [AES-256-GCM], [0.13 [0.01]], [0.13 [0.02]], [0.11 [0.08]], [0.14 [0.07]],
      [DES-CBC], [0.05 [0.00]], [0.14 [0.01]], [0.06 [0.03]], [0.31 [0.08]],
      [RC4], [0.04 [0.00]], [0.04 [0.00]], [0.04 [0.02]], [0.06 [0.01]],
      [Layered pipeline], [0.22 [0.02]], [0.32 [0.02]], [0.25 [0.14]], [0.51 [0.13]],
      table.hline(stroke: 0.8pt),
    )
  },
) <tab:cipher-results>

== Interpretation
Evaluating benchmark results against VELTRIX scenario constraints reveals several insights:
- *AES-256-GCM Performance:* AES-256-GCM proved the most consistent cipher, maintaining deterministic latency (0.11--0.14#h(0.17em)ms) across all payload types due to hardware acceleration and built-in AEAD integrity protection.
- *Legacy Cipher Bottlenecks:* Stream cipher RC4 yielded minimal latency (0.04#h(0.17em)ms) but lacks modern security assurances. DES-CBC scaled poorly as payload size grew (increasing to 0.31#h(0.17em)ms on MP4 video).
- *Layered Pipeline Costs:* Encapsulating data across three ciphers added predictable overhead (0.22--0.51#h(0.17em)ms). While acceptable for prototype uploads, production systems should standardize exclusively on AES-256-GCM.

// ==================================================
#heading(numbering: none)[AI Usage Disclosure]
AI tools were used for initial brainstorming, drafting full-stack application code, assisting with debugging, etc. \
Conversation link: #link("https://chatgpt.com/share/6ae0c90d-b31c-83ec-8656-8472146a7e7e"). \
Agentic link: #link("https://chatgpt.com/s/cx_6ae0d06d3ef881919ac1f92ca5fb3175").

#figure(
  image("ai_conversation_screenshot.jpeg", width: 100%),
  caption: [AI assistance conversation transcript.],
) <fig:ai-screenshot>

// ---------- Layout (two columns, A4) ----------
#set document(title: "VELTRIX: Cross-Applicant Key Management and Secure Document Sharing for Joint Onboarding")
#set page(
  paper: "a4",
  margin: (top: 1.7cm, bottom: 1.7cm, left: 1.6cm, right: 1.6cm),
  columns: 2,
)
#set columns(gutter: 0.65cm)
#set text(font: "New Computer Modern", size: 10pt, lang: "en")

// Spacing: jarak antar paragraf SENGAJA lebih besar dari jarak antar baris
// (setara \parskip di LaTeX yang ditambahkan di atas baselineskip).
#set par(justify: true, leading: 0.6em, spacing: 0.85em, first-line-indent: 0pt)

// ---------- Headings ----------
#set heading(numbering: "1.1")

// true  = baris kedua heading sejajar dengan teks judul (hanging indent)
// false = baris kedua rata kiri di bawah nomor (gaya LaTeX)
#let hanging-headings = true

// Memecah baris heading secara SEIMBANG: mencari lebar tersempit yang tetap
// menghasilkan jumlah baris yang sama, sehingga tidak ada kata yatim di baris akhir.
#let balanced(body) = layout(size => {
  let h = measure(width: size.width, body).height
  let lo = 0pt
  let hi = size.width
  for _ in range(12) {
    let mid = (lo + hi) / 2
    if measure(width: mid, body).height <= h { hi = mid } else { lo = mid }
  }
  block(width: hi + 0.5pt, body)
})

#show heading: it => {
  set text(weight: "bold", size: if it.level == 1 { 14.4pt } else { 12pt }, hyphenate: false)
  set par(justify: false, leading: 0.5em)
  let num = if it.numbering != none {
    numbering(it.numbering, ..counter(heading).at(it.location()))
  }
  block(
    sticky: true,
    width: 100%,
    above: if it.level == 1 { 14pt } else { 10pt },
    below: if it.level == 1 { 6pt } else { 5pt },
    if num == none {
      balanced(it.body)
    } else if hanging-headings {
      grid(columns: (auto, 1fr), column-gutter: 0.4em, num, balanced(it.body))
    } else {
      balanced(num + h(0.4em) + it.body)
    },
  )
}

// ---------- Lists ----------
#set list(tight: true, indent: 0.8em, body-indent: 0.5em, spacing: 0.7em)
#set enum(tight: true, indent: 0.8em, body-indent: 0.5em, spacing: 0.6em)

// ---------- Monospace (kode inline, link) ----------
#let mono = "DejaVu Sans Mono"
// Inline code: pakai font mono yang setara \texttt, dan beri titik patah baris
// setelah "_" dan "." agar token panjang tidak merusak rata kiri-kanan.
#show raw.where(block: false): it => {
  let t = it.text
    .replace("_", "_\u{200B}")
    .replace(regex("\\.([A-Za-z])"), m => ".\u{200B}" + m.captures.at(0))
  text(font: mono, size: 0.85em, hyphenate: false, t)
}
// Code block: tanpa syntax highlighting berwarna, dengan latar abu-abu tipis.
#show raw.where(block: true): it => block(
  width: 100%,
  fill: luma(244),
  inset: (x: 5pt, y: 4pt),
  radius: 2pt,
  above: 7pt,
  below: 7pt,
  text(font: mono, size: 7.5pt, hyphenate: false, fill: black, it.text),
)
#show link: set text(font: mono, size: 0.85em)

// ---------- Math ----------
#show math.equation.where(block: true): set block(above: 8pt, below: 8pt)

// ---------- Figures & captions ----------
#set figure.caption(separator: [: ])
#show figure.where(kind: table): set figure.caption(position: top)
#show figure.caption: set text(size: 9pt)
#show figure.caption: set par(justify: false)
#show figure: set block(above: 10pt, below: 10pt)

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
      VELTRIX: Cross-Applicant Key Management and Secure Document Sharing for Joint Onboarding
    ]
    v(0.3em)
    text(size: 9pt)[
      GitHub Repository: #link("https://github.com/shzirley/information-security-assignment1")
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
= Scenario and Data Sharing Need
== Business Context and Problem Setting
In digital banking, opening organizational accounts (*e.g.*, student associations like _HIMA Informatika_) requires dual-signatory verification. Under POJK regulations on Electronic CDD and the Indonesian PDP Act (*UU PDP No. 27 of 2022*), financial onboarding mandates verifying primary officers. The chairman (*Andi*, Requester) must submit a consolidated KYC dossier incorporating identity credentials (KTP) and corporate opening forms from the treasurer (*Budi*, Data Owner / Co-signer).

Exchanging unencrypted identity cards over commercial channels (WhatsApp, email) risks interception and identity theft. Conversely, granting unconditional lateral server access violates data sovereignty: the owner must retain explicit consent, scoped approval, and revocation rights, while repelling eavesdroppers (*Citra*, an Unauthorized Student).

== End-to-End User Interaction Flow
The sharing interaction follows a five-phase lifecycle:
+ *Request Initiation:* Andi requests access to Budi's submitted application, specifying the operational purpose and selecting required items (Profile, KTP, Form). Status: `PENDING`.
+ *Owner Verification & Approval:* Budi reviews the request, verifies Andi's public key fingerprint out-of-band, and approves. Status: `APPROVED`.
+ *Out-of-Band Key Delivery:* The server generates an isolated symmetric key, re-encrypts requested evidence, wraps the key with Andi's public key into an armored token (`VELTRIX-SHARE-1.<base64url>`), and gives it to Budi to send via WhatsApp.
+ *Client-Side Unwrapping & Preview:* Andi pastes the token and imports his local private key `.pem` in the browser. Web Crypto unwraps the symmetric key locally, streaming decrypted evidence in memory without disk caching.
+ *Revocation & Crypto-Shredding:* Budi can revoke access at any time (`REVOKED`), or the 7-day TTL lapses (`EXPIRED`), instantly destroying all keys and shared ciphertext.

// ==================================================
= Design Decisions and Cryptographic Justifications
== Client-Side Asymmetric Cryptography (RSA-OAEP)
- *Decision:* Generate 2048-bit RSA-OAEP keypairs ($e = 65537$, SHA-256) inside the browser via Web Crypto API. Export the private key as a PKCS\#8 `.pem` file downloaded to the client machine.
- *Justification:* Enforces strict *Zero-Knowledge Architecture*. The server never receives or logs the private key, neutralizing database leak exposure. RSA-OAEP provides provable IND-CCA2 security, immune to Bleichenbacher padding oracle exploits that plague PKCS\#1 v1.5.
- *Key Fingerprints:* The public key SPKI digest is computed via SHA-256 and rendered as a 16-hex prefix in the UI, enabling visual out-of-band verification to defeat Man-in-the-Middle (MitM) attacks.

== Ephemeral Re-Encryption with Authenticated Context
- *Decision:* Generate an isolated 256-bit symmetric key ($K_"share"$) using CSPRNG (`os.urandom(32)`), and re-encrypt shared document copies using AES-256-GCM.
- *Justification:* Primary storage keys from Assignment 1 are never exposed. AES-256-GCM guarantees confidentiality and integrity. To prevent cross-item and replay attacks, we enforce strict Additional Authenticated Data (AAD):
  $ "AAD" = "share:" || "request_id" || ":" || "item_id" || ":" || "kind" $
  This couples each ciphertext block to its request scope, preventing an adversary from substituting an encrypted KTP into a form slot.

== At-Rest Key Wrapping and Out-of-Band Armoring
- *Decision:* At rest, the server wraps $K_"share"$ using the Master Key-Encryption Key ($"KEK"$) via AES Key Wrap (`RFC 3394`). For transit, the server wraps $K_"share"$ with Andi's public key into an armored token:
  $ "VELTRIX-SHARE-1." || "base64url"(\{ "alg": "RSA-OAEP-256", ... \}) $
- *Justification:* No raw symmetric keys exist at rest in `bankkyc.db`. Transit armoring ensures that even if WhatsApp is tapped, only Andi's private key can extract $K_"share"$.

== Ephemeral Client Memory and Crypto-Shredding
- *Decision:* Stream decrypted documents via `POST .../open` using `Cache-Control: no-store, no-cache, private`. Render documents in-memory via `URL.createObjectURL` and invoke `URL.revokeObjectURL` upon closing modal previews.
- *Justification:* Prevents OS disk swapping and browser cache leakage. Upon revocation, the server overwrites `wrapped_share_key` with `NULL` and executes `DELETE FROM share_items`. Without key and ciphertext, recovery is mathematically impossible.

// ==================================================
= Security Analysis and Threat Evaluation
Why this analysis fits joint onboarding: Banking regulations mandate that sharing must preserve non-repudiation, prevent lateral privilege escalation, and enforce strict lifetimes. As detailed in @tab:threat-analysis, we analyze five core failure modes across the sharing lifecycle:

#figure(
  placement: auto,
  caption: [Threat modeling, attack vectors, and design resilience analysis.],
  {
    set text(size: 8pt, hyphenate: false)
    set par(justify: false, leading: 0.48em)
    table(
      columns: (1fr, 1.2fr, 1.8fr, auto),
      align: (left, left, left, center),
      stroke: (x, y) => if y >= 2 { (top: 0.25pt + luma(200)) },
      inset: (x: 2.8pt, y: 2.8pt),
      table.hline(stroke: 0.8pt),
      table.header(
        [*Threat Vector*], [*Failure Mode*], [*Mitigation & Cryptographic Proof*], [*Result*],
        table.hline(stroke: 0.4pt),
      ),
      [OOB Interception (Citra)], [Adversary captures WhatsApp token], [RSA-OAEP rejects Citra's private key (bad padding); API checks requester identity (403).], [PASS],
      [Ciphertext Tampering], [Adversary flips bits in storage], [AES-GCM tag mismatch immediately halts decryption; zero plaintext leakage.], [PASS],
      [Cross-Item Swap], [Adversary exchanges KTP with Form], [Contextual AAD mismatch fails GCM integrity check; swapping detected.], [PASS],
      [Stale Access Replay], [Requester accesses revoked data], [Crypto-shredding: key nulled, `share_items` deleted; API returns 403.], [PASS],
      [Database Leak], [Attacker steals raw SQLite database], [Zero plaintext PII found on disk; symmetric keys remain wrapped under KEK.], [PASS],
    )
  },
) <tab:threat-analysis>

== Empirical Verification and Document Integrity
All 11 automated pytest test suites (implementing security assertions T01--T14) and 10 end-to-end scenarios (E01--E10) passed 100%:
- *Byte-Identical Integrity:* Decrypted documents matched original assets exactly: Profile JSON (305 B, SHA-256 `fd37d7bd...`), KTP Image (60,617 B, SHA-256 `92f7b399...`), and Form PDF (3,294 B, SHA-256 `e3220409...`).
- *Adversarial Rejection:* Citra's attempt to unwrap the package failed cryptographically with `DOMException: OperationError`. Direct API bypass returned `403 SHARE_OPEN_DENIED`.
- *Storage Forensics (E09):* Inspecting `bankkyc.db` while `APPROVED` showed raw ciphertext and a 32-byte wrapped key, with 0 string occurrences of NIK or Name. Post-`REVOKED`, `wrapped_share_key` was `NULL` and `share_items` count dropped to 0.

== System Limitations and Realistic Trust Boundaries
- *Trusted Server Re-Encryption:* The backend acts as a trusted broker and transiently accesses evidence in memory during re-encryption. Asymmetric keys protect the delivery channel, not against a compromised server kernel.
- *Private Key Recovery:* If Andi loses his local `.pem` file, data is irrecoverable. Andi must rotate keys and Budi must re-encrypt a new package.
- *Human Verification Dependency:* MitM defense relies on Budi manually verifying the 16-hex fingerprint before approval.
- *Analog Screen Capture:* Cryptography prevents digital cache leakage, but cannot prevent a rogue recipient from photographing a decrypted document on screen.

// ==================================================
#heading(numbering: none)[AI Usage Disclosure]
AI assistance was utilized for cryptographic threat modeling, drafting synthetic Indonesian fixtures, structuring test harnesses, and refining academic typography. Conversation link: #link("https://chatgpt.com/share/6ae0c90d-b31c-83ec-8656-8472146a7e7e").

/*#figure(
  image("ai_conversation_screenshot.jpeg", width: 95%),
  caption: [AI interaction transcript for Assignment 2 design and verification.],
) <fig:ai-screenshot>
*/
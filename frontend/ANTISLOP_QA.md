# VELTRIX frontend: antislop delivery gate

Date: 13 October 2026. Scope: local frontend prototype with browser mock API.
Filter source: `C:/Users/NITRO V15/.claude/skills/antislop/SKILL.md`, DURING mode selected by the user. Current design direction: the supplied `Veltrix Secure Brand Identity Board.png`, `../VELTRIX_GSM_v0.1.md`, and `DESIGN.md`. The explicitly requested `skill-creator` was read for scope and reusable-guidance principles; no global skill or entry-file installation was performed.

Delivery status: **PASS for this frontend prototype**. This report does not certify backend security, actual cryptography, or academic performance results.

## Execution evidence

- PASS: `npm.cmd run build` compiled and type-checked the final source, generated public/workspace pages, and included dynamic file/benchmark detail routes.
- PASS: standalone `npm.cmd run typecheck` completed successfully during implementation; the final build also reran TypeScript successfully.
- PASS: all seven scenarios were exercised after the GSM update on an isolated production server at port 3100. Six passed in the full run; the mobile scenario was then reverified successfully in 37.7 seconds after correcting an MSW service-worker unregister/update race. The development server at port 3000 was kept separate.
- PASS: the supporting-controls scenario checked Inter body font, Montserrat headings, loaded symbol/lockup assets, both themes, and the standalone brand catalog.
- PASS: axe WCAG 2 A/AA scans reported zero violations in the tested views: Dashboard in both themes; Vault and rendered Lab at mobile width; landing, login, register, personal-data view, and file detail in both themes; chart hover in the dark theme.
- PASS: 375px, 768px, and 1440px layouts were checked. Root scroll width did not exceed viewport width. The result table uses a labeled, keyboard-focusable horizontal scroll region.
- PASS: the mobile/theme scenario recorded zero browser `pageerror` events.
- PASS: current GSM text-token pairs were calculated explicitly, with ratios ranging from 4.72:1 to 14.68:1. Tooltip text is forced to the foreground token rather than its chart-series color.
- PASS: twelve generated brand SVGs parsed successfully; primary/stacked lockups embed Montserrat and Inter. The PNG board is preserved as the source, and reconstruction provenance is disclosed in GSM/catalog.

Automated scans cover the exercised states; they are not a claim of exhaustive WCAG certification. E2E assertions against the mock prove frontend behavior, not encryption correctness in a real backend.

## Recorded interaction evidence

| Control / flow | Observed behavior |
| --- | --- |
| Landing login, account CTA, workspace link, wordmark | Existing destinations opened; back-to-home and auth switch links worked |
| Registration submit | Empty/short fields, mismatched password, duplicate username, and successful account creation were exercised |
| Password visibility | Show/hide changed input type; password paste/managers are not blocked by source |
| Login | Invalid credentials displayed an error; valid new account and demo shortcut opened Dashboard |
| Logout / expired session | Returned to login; private reveal disappeared; unauthenticated workspace redirect occurred |
| New account owner scope | Empty vault appeared; requesting the demo account's file metadata returned 404 |
| Sidebar navigation / wordmark | Dashboard, personal-data, Vault, and Lab destinations opened |
| Mobile menu | Open, close button, outside scrim, navigation, and Escape worked |
| Theme toggle | Light/dark switched and survived subsequent navigation/reload through theme preference |
| Vault category controls | Document/identity/video/all categories filtered; empty result and reset behavior appeared |
| Search | Unknown filename displayed no-results state; resetting filters restored records |
| File chooser / drop alternative | Choose-file opened the native file picker; selected-file input updated the form |
| Upload validation | Unsupported extension, empty file, and a payload exceeding 25 MB were rejected visibly |
| Category selector | Identity/video categories updated permitted extensions and cleared previous selection |
| Clear selected file | Removed the current selection; a new file could then be chosen |
| Upload submit | Added one record; dialog closed; the list contained the uploaded filename |
| Detail links | Opened metadata and three cipher representations |
| AES / RC4 / DES retrieval | Each route downloaded the same uploaded bytes and original filename |
| File delete | Cancel preserved the item; confirm removed it and returned to Vault |
| Profile reveal / hide | Each cipher selection revealed dummy values; hiding removed them from the rendered view |
| Profile edit / cancel | Loaded fields; cancellation discarded the draft and returned to hidden view |
| Profile validation / dummy fill | Invalid email and missing full name produced field errors; dummy fill populated the form |
| Profile save / delete | Updated values could be revealed; cancel preserved the profile; confirm removed it; creation worked afterward |
| Lab source / repetition settings | File deep-link selection, personal-data selection, 10/20/30 choices, and recorded repetitions worked |
| Crypto run | Rendered explicitly simulated charts, numeric table, method notes, and a history record |
| Crypto CSV | Export contained a SIMULATED marker and 60 raw samples for 20 runs across three algorithms |
| History / return link | Opened benchmark detail and returned to Lab |
| Repeated downloads | Completed 30 requests for 10 runs across three algorithms; export contained 30 samples labeled CLIENT-MEASURED-MOCK |
| Stop downloads | Stopped the loop; completed samples were retained and the run button became usable |
| Dialog controls | Cancel, close button, and Escape closed dialogs; Tab stayed within the dialog; focus returned to Upload |
| Error retry / back | Missing-resource error remained controlled on retry; back returned to Vault |
| Toast close | Dismissed the displayed feedback message |
| Chart hover | Exercised tooltip interaction; the dark-mode contrast scan passed |

## Hard gate

R-02 PASS: source scan found no em dash in generated UI copy.
R-03 PASS: measured root overflow at 375/768/1440px; mobile screenshots show reflowed navigation, settings, and file rows.
R-17 PASS: file counts/source bytes come from actual mock records; storage estimates and generated crypto numbers are explicitly labeled simulated.
R-18 PASS: no testimonials or invented endorsements appear.
R-23 PASS: logo, wordmark, palette, and fonts follow the user's board; the web SVG is explicitly identified as a reconstruction. Navigation follows the blueprint, avatars are initials, and fixtures are dummy/demo.
R-24 PASS: all rendered nav links have existing routes; tested navigation and source route inventory agree.
R-25 PASS: token contrast calculations and axe scans passed in the listed views/themes; chart tooltip text uses the readable foreground token.
R-26 PASS: principal controls and supporting close/navigation controls were exercised with observable outcomes recorded above.
R-27 PASS: empty vault/profile/history, loading requests, validation errors, API errors, and session-expired states exist and were exercised.
R-28 PASS: no filler FAQ exists.
R-32 PASS: keyboard focus, Tab/Shift+Tab, Enter, Escape, mobile menu, and return focus were exercised.
R-33 PASS: features were authored directly in source with patches; no external source-rewriting UI script exists.
R-34 PASS: both shipped themes were exercised and scanned; theme choice is persisted separately from private data.
R-35 PASS: production builds and recorded Playwright click-throughs ran successfully; screenshots were inspected.
R-36 PASS: no unsupported security/compliance/performance claims; backend and simulated timing limits are visible.
R-37 PASS: blueprint direction was loaded before building and the Design Read/dials were declared; reasons are in DESIGN.md.
R-38 PASS: real product scope comes from the assignment/PRD; generated fixtures and numbers are honest demo content.

## Purpose gate

R-01 PASS: Royal Blue/Indigo/Cyan gradients serve the reference's folded logo identity; Midnight/Cloud/Royal implement the board palette without generic background glow.
R-04 PASS: file/upload/download/folder/user/chart icons correspond to content/actions, with rationale in DESIGN.md.
R-06 PASS: Montserrat logo/headings and Inter body/UI match the supplied typography direction; Fira Code is limited to byte values, indices, and hex.
R-07 PASS: no decorative background grid or dot pattern.
R-08 PASS: directional icons identify opening a detail/history destination; primary actions use their relevant action icon.
R-09 PASS: labels identify cipher versions, legacy algorithms, or actual demo mode; no promotional capsule/glow treatment.
R-10 PASS: no glassmorphism is used.
R-12 PASS: shadows identify temporary elevated dialogs/toasts; permanent records rely on borders and hierarchy.
R-13 PASS: no glow treatment is used.
R-14 PASS: summary ledger, records, profile area, and Lab tools have content-specific compositions.
R-19 PASS: animation is limited to interaction/loading feedback; reduced motion was exercised.
R-22 PASS: the landing diagram explains one source and three independent representations; no unrelated stock illustration.

## Liveliness

PASS: ENERGY 2 / RHYTHM 2 / MOTION 1 are declared in DESIGN.md.
PASS: layouts vary by task while retaining consistent navigation, typography, and action placement.
PASS: focal points are account submit, upload, reveal/save, download, or experiment run on their respective screens.
PASS: whitespace separates task header, source records, and secondary explanations.
PASS: blue is the deliberate action/selection accent; semantic warning/error colors serve status only.
PASS: indexed archive sections and three aligned cipher labels repeat across the workspace.
PASS: Design Read was declared before generation and recorded in DESIGN.md.

## Craftsmanship and quality locks

C-1 PASS: major color/type/layout/spacing/illustration decisions have written reasons in DESIGN.md.
C-2 PASS: controls have real navigation or state/API behaviors; no dead CTA or placeholder action remains.
C-3 PASS: sections correspond to assignment/PRD storage, retrieval, and analysis tasks; no filler marketing blocks.
C-4 PASS: exercised empty/loading/error/session states, both themes, three viewport widths, and keyboard dialog behavior.
C-5 PASS: no fabricated trust/customer claims; generated data and timings are labeled.
R-05 PASS: landing illustrates the actual storage model; dashboard and Lab compositions follow their tasks rather than a marketing template.
R-11 PASS: actions, panels, and labels use distinct 6/12/4px radii documented in DESIGN.md.
R-15 PASS: action labels name the task: Upload file, Tampilkan data, Simpan profil demo, Download file demo, Jalankan benchmark, Ekspor CSV.
R-16 PASS: generated copy does not use unsupported marketing buzzwords.
R-20 PASS: the reference-derived V/keyhole, Montserrat wordmark, brand tagline, archive indices, and source/crypto/download distinction give the workspace product-specific structure.
R-21 PASS: light is the blueprint default and a functioning dark toggle gives the user a choice.
R-29 PASS: Midnight/Cloud/Charcoal anchor surfaces, Royal marks actions, and Indigo/Cyan remain in logo identity; warning/error/success colors are semantic tokens.
R-30 PASS: design follows the VELTRIX brief without using another product as a visual template.
R-31 PASS: decision reasons are recorded in DESIGN.md, including chart series and tooltip contrast.

## Visual artifacts

- `artifacts/dashboard-desktop.png`
- `artifacts/dashboard-dark.png`
- `artifacts/vault-mobile.png`
- `artifacts/lab-desktop.png`
- `artifacts/lab-mobile-dark.png`
- `artifacts/landing-branded.png`
- `artifacts/brand-assets.png`

No backend tests are claimed. The next stage is FastAPI/MySQL implementation and integration against the established contract, followed by actual crypto round-trip, tampering, ownership, upload-content, and repeatable performance tests.

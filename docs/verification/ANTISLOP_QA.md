# VELTRIX BankKYC: frontend delivery gate

27 October 2026. Scope: the BankKYC frontend with browser mock API. This supersedes the 13 October vault UI audit (retained in Git history).

Filter: `C:/Users/NITRO V15/.claude/skills/antislop/SKILL.md`, DURING mode explicitly selected in this conversation. Direction: user-supplied VELTRIX brand board/GSM, BankKYC PRD, and [frontend/DESIGN.md](../../frontend/DESIGN.md). UI/UX Pro Max informed reduced motion and native scrolling; its default brand suggestions were not adopted.

This is a historical audit of the frontend work at the time described below. For subsequent live-backend checks and current test coverage, see the [implementation verification report](VERIFIKASI.md).

**Delivery gate: PASS for this frontend prototype.** This is not backend security verification, legal-compliance certification, or evidence of real encryption/benchmarking.

## Execution evidence

- PASS: `npm.cmd run build`, including strict TypeScript and generation of public/workspace routes.
- PASS: `npm.cmd run typecheck` independently.
- PASS: preceding full 12-scenario Playwright suite, Microsoft Edge, isolated production server at port 3100. After the isolated hero correction, `npm.cmd run test:e2e -- --grep 'animated headline without controls'` passed (1 scenario, 20.3 seconds), alongside a fresh production build and typecheck. Other role workflows were unchanged by that correction. Tests and browser runtime monitoring are in `tests/flows.spec.ts`.
- PASS: browser `pageerror` and unexpected console errors are asserted absent in each scenario. Deliberately induced HTTP 401/403/404/409/422 responses are expected negative tests, not suppressed application exceptions.
- PASS: axe WCAG 2 A/AA and 2.1 AA scans on landing light/dark and reduced-motion mobile; applicant/reviewer/admin/evaluator home views light/dark at desktop/mobile; applicant detail light/dark mobile; profile wizard dark; upload step; and verification result. Zero violations in these exercised views. This is not exhaustive WCAG certification.
- PASS: root scroll width checks at 375, 768, 1024, and 1440 px for landing and four role workspaces in both themes; detail was also checked across sizes. The lab table scrolls locally.
- PASS: reduced motion can be changed while the page is open; the rotating hero switches to fixed `bukti KYC-mu.` and the evidence sequence uses a subscribed media query for its static alternative. Landing accessibility and layout are checked with this preference active.
- PASS: synthetic MP4 checked with ffprobe: H.264, 640×360, 10.000 seconds, 8,664 bytes. Downloaded fixture bytes are compared with the source by E2E.
- PASS: downloaded uploaded PDF bytes are compared exactly with the source buffer. This proves mock transport behavior only, not encryption or server integrity.
- PASS: five consecutive full reloads preserve the fixture login and show the expected seeded cases without service-worker registration exceptions. Registration stays present while inactive clients bypass; application data still resets.

The build reports the intended 34 MiB proxy request cap. The backend's separate limits and new KYC contract are still pending. The test server is temporary and is stopped by Playwright after completion.

Copy and cleanup revision: development badges and the repeated debug footer were removed. Login now uses credentials only, without fixture-account shortcuts or a role selector. Terminal labels are “Diterima”/“Ditolak”, with API enums unchanged. The viewport checks reject visible FE/frontend/backend, API mock/live, service-worker/localhost instructions, and prototype labels on landing, login, and role views. Usage notices retain the synthetic-only, unencrypted, temporary-browser-storage scope; the lab and its CSV retain the unmeasured simulation boundary.

Latest user clarification keeps the headline animation active and removes only its visible pause control and footnote. `hero.tsx` rotates evidence nouns every 3.6 seconds at full opacity in a fixed-height line. Hover/focus, offscreen visibility, and hidden tabs suspend rotation; live reduced motion renders fixed text. The accessible heading remains stable. Landing tests observe an actual identity-to-document word change, assert the stable accessible name, and verify the control/footnote remain absent. The scroll-linked evidence sequence, removed academic decorations, and credential-only login remain as before.

Repository cleanup removed the superseded vault PRD/blueprint, legacy verification report, six vault-era screenshots, and the clean completed security worktree. Product/FE/BE BankKYC PRDs, GSM, assignment/brand references, legacy backend migration code, and current screenshots remain. Local documentation links were checked after deletion. The security branch and its commits remain available in Git.

## Recorded interactions

| Control / state | Observed behavior |
| --- | --- |
| Landing primary CTA | Opens registration |
| Landing alur/hak akses anchors and back to top | Navigate to real sections and restore top position |
| Four role rows | Open credential login without filling an account or assigning a role |
| Animated hero without extra controls | Evidence nouns change; accessible name remains stable; pause/resume buttons and hero footnote are absent |
| Reduced motion changed live | Rotating headline becomes fixed `bukti KYC-mu.`; landing stays readable and accessible |
| Theme controls | Switch tokens in landing/workspace; both themes scanned |
| Registration | Empty fields, password mismatch, duplicate username, and successful new applicant exercised |
| Password visibility | Show/hide changes the input type |
| Credential login | Invalid credentials show an error; each role opens its own home after login; no account shortcut panel |
| New applicant list | Empty state appears; demo owner's case returns 404 |
| Logout / expired session | Returns to login; attempted expired form mutation clears the workspace session |
| Search / status select | Matching rows filter; unmatched search displays contextual empty state |
| New application / create draft | Opens preparation, then creates a fresh DRAFT and enters wizard |
| Profile submit | Eight missing fields produce an error summary; real-domain email rejected; dummy profile saved |
| Profile example button | Fills synthetic values only in mock mode |
| Upload selector / upload button | Wrong extension and wrong signature rejected; valid identity/document/video saved separately |
| Wizard continue/back | Moves between saved steps; returns saved profile values when revisiting |
| Synthetic acknowledgement | Submit remains disabled until checked and all four categories exist |
| Submit confirmation | Sends once, moves to detail, and hides edit controls in SUBMITTED |
| Profile reveal / Escape | Opens owner profile only on request, removes plaintext on close, restores trigger focus |
| JSON download | Produces a downloadable dummy profile with DUMMY identifier |
| PDF preview / close | Opens titled document iframe and closes the dialog |
| Video preview / close | Opens an MP4 with native controls and no autoplay |
| Video / document download | Returns the exact source bytes through the mock retrieval route |
| Version disclosure / download | Expands version history and exposes an owner download per version |
| Revision upload / resubmit | Adds document v2, retains v1, and enters RESUBMITTED |
| Incomplete/stale/read-only requests | API mock rejects with CASE_INCOMPLETE, VERSION_CONFLICT, CASE_READ_ONLY |
| Withdraw / cancel / confirm | Cancel leaves status unchanged; confirm makes WITHDRAWN read-only |
| Reviewer queue / case link | Only assigned cases appear; unassigned detail returns 404 |
| Reviewer plaintext attempts | Profile/download routes return 404; case JSON omits filenames and profile values |
| Start review | Confirmation moves SUBMITTED to UNDER_REVIEW |
| Request revision | Note required; confirmation records a safe operational note and NEEDS_REVISION |
| Accept / reject demo | Correct terminal state appears; terminal controls disappear; reject requires an explanation |
| Admin assignment select / cancel / save | Opens dialog, cancels, or assigns the selected reviewer; list updates |
| Admin privacy / wrong-role route | No plaintext in metadata; unauthorized UI shows access-limited state; API rejects wrong role |
| Lab configuration | Fixture selector works; fewer than 30 repetitions disables run |
| Lab run / result / history | Shows pending/result, stores session history, and reopens the chosen run |
| Lab CSV export | Filename and content explicitly state SIMULATED |
| Verification navigation / run | Opens isolated verification view; backend gates remain explicitly not run |
| Mobile menu / navigation / Escape | Drawer opens, first link gets focus, navigation closes it, Escape restores menu-button focus |
| Keyboard dialog loop | Tab from last to first and Shift+Tab back remain inside dialog; Escape restores trigger |
| Unsaved profile link | Dismissing the native leave confirmation keeps the form; save/back retains the new value |
| Missing resource / retry | Generic not-found message appears and retry repeats the guarded request |
| Full reload | Seeded demo login recovers without worker update/unregister race |

Image/DOCX preview branches, native browser file-picker internals, real-server errors and live cryptography are not claimed as experimentally verified by these tests. Image rendering and unsupported-format download fallback were reviewed in source. Browser history does not have a complete navigation blocker; that prototype limitation is stated in the FE PRD.

## Per-rule delivery gate

- R-01 PASS: GSM colors retained; gradient limited to the existing brand symbol. Reason in DESIGN.md.
- R-02 PASS: no em dash in shipped React UI copy; wording uses KYC tasks and plain-language synthetic/session limits, with implementation jargon confined to developer documentation.
- R-03 PASS: four viewport sizes checked; cards move inward so initial animation does not crop their content.
- R-04 PASS: document, identity, video, review, assignment and lab icons name their adjacent purpose; fingerprint is an academic identity/privacy marker, not a biometric capability claim.
- R-05 PASS: case preview, evidence assembly, numbered process and permissions ledger provide distinct content-led sections.
- R-06 PASS: supplied Montserrat/Inter maintained; loaded font families asserted by E2E.
- R-07 PASS: no decorative background grid, blueprint, or dot texture.
- R-08 PASS: arrows indicate destination or next step; decisions, cancellation, toggles and upload use direct controls.
- R-09 PASS: labels represent actual case status, version, scope or simulation boundaries.
- R-10 PASS: no glassmorphism or stacked backdrop blur.
- R-11 PASS: actions, status labels, panels and document preview have distinct radii.
- R-12 PASS: soft elevation belongs to the illustrative case sheet and transient toast/dialog, not every panel.
- R-13 PASS: no ornamental glow system.
- R-14 PASS: equal evidence tiles express four equally mandatory categories; operational layout follows case priority.
- R-15 PASS: CTA names specify actions such as Mulai pengajuan, Simpan & lanjutkan, Minta revisi and Simpan penugasan.
- R-16 PASS: no unverified marketing superlatives, speed or compliance copy.
- R-17 PASS: counts derive from case fixtures; lab figures are explicitly static simulations, including CSV.
- R-18 PASS: no customer testimonials, stock team portraits, or fabricated endorsements.
- R-19 PASS: headline rotation and evidence assembly explain the KYC categories; headline has no visible controls as requested, retains full contrast, and suspends for hover/focus, offscreen/hidden tabs, or reduced motion.
- R-20 PASS: KYC evidence sheet, case references, revision notes and permission ledger carry product-specific identity.
- R-21 PASS: default light plus functional user-controlled dark mode; both inspected and scanned.
- R-22 PASS: case preview is a labeled synthetic application; MP4 is a labeled dummy fixture. No unrelated stock illustration.
- R-23 PASS: existing user-authorized logo/GSM reused; synthetic assets follow the supplied PRD and explicit demo labels. No invented real-person imagery.
- R-24 PASS: navigation targets exist; legacy routes redirect; no unbuilt user-management/delegation menu.
- R-25 PASS: semantic text tokens and exercised themes passed axe contrast scans; no claim of formal full accessibility certification.
- R-26 PASS: control matrix above records real navigation, mutation, download, disclosure and dialog behavior.
- R-27 PASS: list/detail/profile/assignment/history queries and experiments have loading, empty and error handling; empty/error paths exercised.
- R-28 PASS: no fabricated generic FAQ section.
- R-29 PASS: fixed GSM palette; green/amber/red have documented status functions.
- R-30 PASS: adapted motion references with original KYC composition, existing identity and contextual copy; no popular-product clone.
- R-31 PASS: major visual choices and exceptions have one-line reasons in DESIGN.md and the FE PRD.
- R-32 PASS: visible focus, dialog loops, async reveal return-focus, Escape, mobile drawer and form validation verified.
- R-33 PASS: UI/source edits made directly with patches; FFmpeg only generates a synthetic video asset, not UI/CSS replacements.
- R-34 PASS: both shipped themes checked for four role workspaces and responsive layout.
- R-35 PASS: production build run, actual browser click-through recorded above, runtime monitoring and screenshots inspected.
- R-36 PASS: no real security/compliance/performance claims inferred from mock data. Backend migration is explicitly outstanding.
- R-37 PASS: existing GSM and DESIGN.md read before edits; dials and motion purpose declared before generation.
- R-38 PASS: case/person/file data explicitly synthetic; lab values explicitly simulated; no ghost links or invented live service capabilities.

## Liveliness and craftsmanship

- Design Read PASS: supplied folded-V/keyhole identity, case-centric KYC task, Midnight/Royal Blue established before generation.
- Dials PASS: landing ENERGY 3 / RHYTHM 3 / MOTION 2; workspace 2 / 2 / 1, matching expressive landing and steady forms.
- Focal points PASS: hero heading/case sheet, dashboard next action, wizard current step, reviewer decision area.
- Whitespace PASS: section and task boundaries set the rhythm; numeric case rows stay compact.
- Accent PASS: Royal Blue prioritizes actions; status colors do not become decoration.
- Motif PASS: numbered evidence/process and case sheet/ledger repeat with content-specific roles.
- C-1 PASS: colors, type, spacing, cards, motion and illustration have documented purposes.
- C-2 PASS: existing controls execute meaningful actions; deferred live functionality is explained in the PRD rather than represented by dead buttons.
- C-3 PASS: every landing section answers scenario, evidence, process, access, or academic-evaluation questions.
- C-4 PASS: exercised empty/loading/error, keyboard, responsive and theme states remain usable within the stated mock scope.
- C-5 PASS: fixtures and simulated results remain distinguishable from real claims, including exports.

## Artifacts and limits

Current screenshots have prefix `artifacts/bankkyc-`: landing desktop/dark/mobile, dashboard, wizard dark, detail mobile dark, reviewer, admin, and lab. These were visually inspected; full-page screenshots can capture fixed elements relative to the scroll position, so they supplement actual viewport assertions.

The legacy `backend/` was not migrated or security-tested in this FE task. Work outstanding at that audit stage was tracked in the [frontend PRD](../prd/VELTRIX_BankKYC_FE_PRD.md): MySQL case schema/migrations, server roles/assignment, provisional layered AES-GCM pipeline, transactional encrypted storage, actual integrity/tamper tests, content validation, benchmark measurements and interpretation, persistence, retention, and lecturer decisions D-01/D-02. This paragraph records the audit's original scope; use the verification report above for subsequent implementation checks.

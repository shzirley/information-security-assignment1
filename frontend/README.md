# VELTRIX frontend

Next.js App Router + TypeScript + Tailwind CSS. The included backend is Python FastAPI + SQLAlchemy, supporting SQLite locally and MySQL through configuration. See the root README to start both servers in live mode.

## Run locally

From `D:\Kuliah\SMT5\KI\assignment1\frontend`:

```powershell
npm.cmd install
npm.cmd run dev
```

Open http://127.0.0.1:3000. On Windows, `npm.cmd` works when PowerShell blocks `npm.ps1`.

In mock mode only, use **Gunakan akun demo**, or login with `demo_user` / `veltrix123`. The demo account includes two generated sample PDFs, one small PNG, and a fictional profile. Create an account to try empty states. Mock registration and uploads are session-memory fixtures; a full page reload resets them. The default demo cookie identifies a prototype user and provides no real security.

## Frontend flows (real API in live mode, fixtures in mock mode)

- Landing, register, login, logout, and session-expired redirect.
- Dashboard derived from the current mock records.
- Personal profile creation, validation, reveal/hide, algorithm selection, edit, and confirmed delete.
- Vault search/category filters, single-file upload, validation, detail, three retrieval routes, and confirmed delete.
- Benchmark settings, simulated crypto results, charts, comparison table, history, and raw CSV export.
- Repeated download receipt timing through the mock API, cancellation, success statistics, and CSV export.
- Light/dark themes, mobile navigation, keyboard-operated dialogs, and reduced motion.

**Mock limitations:** uploaded bytes remain unencrypted in browser memory to test file retrieval. Cipher samples, storage estimates, and crypto timings are generated fixtures and visibly labeled simulated. Download duration measures the mock browser request path, not a FastAPI crypto engine. The mock validates extensions and size. The included backend implements real sessions, ownership, MACs, transactional writes and encryption; deep content validation and malware scanning remain outside the academic MVP scope. Do not put real personal data in the demo or use fixture results in the assignment report.

`public/mockServiceWorker.js` intentionally keeps its registration across full reloads. MSW's default immediate self-unregister on `CLIENT_CLOSED` can race the next page's background `update()` in Edge and produce a NotFound rejection. Inactive clients still bypass mocking; this does not retain user files or profiles. Regenerating the worker with the MSW CLI resets this small lifecycle adjustment.

## Connect the included FastAPI backend

Copy `.env.example` to `.env.local` and set:

```dotenv
NEXT_PUBLIC_API_MODE=live
API_ORIGIN=http://127.0.0.1:8000
```

Restart/rebuild Next.js after changing mode. Live mode skips MSW and forwards `/api/v1/*` to FastAPI. The included `../backend` implements the contract in `src/lib/contracts.ts` and `src/lib/api.ts`. Start it on port 8000 before using live mode. CSRF tokens are retrieved before mutations; all requests include credentials. Personal plaintext is kept in component state, not in query cache or browser storage.

The profile layout and file storage model follow the blueprint. The database choice has been updated to MySQL in the PRD and blueprint. UI primitives use Radix Dialog with component styles, following the accessible compositional approach used by shadcn/ui.

## Verify

```powershell
npm.cmd run build
npm.cmd run typecheck
npm.cmd run test:e2e
```

The original mock-only Playwright suite uses installed Microsoft Edge and starts an isolated production server on port 3100 for the test run, keeping the user's development server on port 3000 separate. Override the browser channel in `playwright.config.ts` if using another Chromium installation. These tests require a successful build with NEXT_PUBLIC_API_MODE=mock first; they intentionally expect simulation labels and demo accounts. Live integration is tested by ../backend/scripts/smoke_live.py. HTML results are in `playwright-report/`; screenshots are in `artifacts/`.

Design reasons and antislop dials are recorded in `DESIGN.md`. Final delivery-gate evidence is in `ANTISLOP_QA.md`.

## Brand identity

The UI follows the supplied VELTRIX brand board: Midnight Blue, Royal Blue, Indigo, Cyan, Cloud, Charcoal, Montserrat headings, and Inter body text. `../VELTRIX_GSM_v0.1.md` records implementation rules and asset provenance. The web logo is an SVG reconstruction of the PNG reference, not the original design master.

Use `/brand/preview.html` for standalone logo previews/downloads. A reusable `BrandLogo` appears on landing, auth, sidebar, loading, and not-found screens; `/icon.svg` is the browser icon. The six primary/stacked lockups embed Montserrat/Inter fonts. Run `node scripts/build-brand-assets.mjs` to regenerate derivative brand assets after an intentional symbol update.

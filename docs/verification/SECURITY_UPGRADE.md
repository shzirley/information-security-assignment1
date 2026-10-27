# Next.js security upgrade

27 October 2026. Requested command: `next upgrade --agent=security`.

The CLI selected **16.4.0 → 16.4.3** from its security advisory assessment. This is a same-major patch, so no codemod or major-version migration was run. React and unrelated dependency constraints were retained.

Changes: exact Next.js pin in package.json, npm lockfile with matching Next/env/SWC packages, and `experimental.agentUpgrade: 'security'` in next.config.ts. The 34 MiB proxy limit, API rewrites and other configuration are preserved.

Verification on the current BankKYC application in the isolated worktree:

- `npm install next@16.4.3 --save-exact`: successful.
- `npm exec -- next --version`: **Next.js v16.4.3**.
- `npm run build`: passed.
- `npm run typecheck`: passed.
- `npm run test:e2e`: **12 passed**, including all roles, owner/assignment restrictions in the mock, wizard/revisions, downloads, themes, accessibility, mobile and service-worker reloads.
- Re-running `next upgrade --agent=security`: **No security update is needed for Next.js 16.4.3.** This is the CLI's policy result, not a claim that every project dependency or the backend is vulnerability-free.

Duplicate checks: origin fetched, local/remote branches and commits checked, and GitHub open PR list queried; no equivalent upgrade found. Worktree: `.worktrees/next-security-16.4.3`, branch `upgrade/next-security-16.4.3`.

After integration, the completed temporary worktree was removed during project cleanup. Its checkpoint and security commit remain on `upgrade/next-security-16.4.3`; the main checkout contains the upgrade.

The worktree begins with a local checkpoint of existing uncommitted BankKYC work so the security commit contains only this upgrade and this record. The main checkout's pre-existing index/work is preserved; the verified patch is applied there without committing unrelated FE work. Test-generated screenshots are excluded from the security commit.

The upgrade follows the CLI-generated `shared.md` and `same-major.md` instructions. Release/advisory metadata comes from the npm registry. The original handoff run is reported once using the CLI's result-only telemetry command after local integration succeeds.

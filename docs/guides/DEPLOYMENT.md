# Deploy VELTRIX with Vercel, Render, and Aiven

Prepared 28 October 2026. This is a deployment procedure, not a record of a successful public deployment. Hosting configuration is prepared locally; accounts, cloud credentials, a container build, and public end-to-end checks are still required.

## 1. Hosting arrangement

| Component | Service | Configuration |
| --- | --- | --- |
| Next.js web application | Vercel Hobby | Git repository, root directory `frontend` |
| FastAPI and video inspection | Render Free web service | Docker image with Python and FFmpeg, configured by [render.yaml](../../render.yaml) |
| Persistent accounts and encrypted evidence | Aiven for MySQL Free | External MySQL with verified TLS; no local SQLite in the cloud |

```mermaid
flowchart LR
    Browser[Browser] --> Web[Next.js on Vercel]
    Web -->|External rewrite: /api/v1| API[FastAPI on Render]
    API -->|Verified TLS| DB[(Aiven MySQL)]
```

The browser uses its Vercel origin for both the interface and `/api/v1/*`. The existing Next.js external rewrite forwards API traffic to Render. Keep this arrangement so session cookies and CSRF requests remain same-origin. Do not replace it with a Next.js route handler that reads and forwards uploads.

Vercel supports FastAPI, but its Functions have a **4.5 MB request/response payload limit**, below VELTRIX's 30 MiB video requirement. The proposed API therefore runs on Render. External rewrites are a separate routing mechanism with a **120-second timeout**; this guide does not claim that every 30 MiB transfer is already verified through that path. See [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Functions limits](https://vercel.com/docs/functions/limitations), [external rewrites](https://vercel.com/docs/routing/rewrites), and [proxy limits](https://vercel.com/docs/limits).

Render Free sleeps after 15 minutes without traffic and can take about a minute to wake. Its filesystem is ephemeral, so a local SQLite database would lose data. Free services have no interactive shell/one-off jobs, which is why operator accounts are created from your computer. External-database traffic also counts toward Render's free-service restrictions. See [Render Free limitations](https://render.com/docs/free).

Aiven currently documents a free MySQL service with **1 GB disk**, 1 GB RAM, and no credit-card requirement or fixed expiry. Storage includes more than uploaded file bytes: every evidence version, database indexes, logs, and lab results consume space. Aiven may power off inactive free services. See [Aiven MySQL Free](https://aiven.io/docs/products/mysql/concepts/mysql-free-tier).

This arrangement is intended for the small synthetic-data coursework workload. Monitor each dashboard's usage; the ability to select a free plan does not establish that all loads fit it.

## 2. Create the accounts and publish deployment configuration

1. Use the existing Vercel account.
2. Create a [Render account](https://dashboard.render.com/) and connect the GitHub repository.
3. Create an [Aiven account](https://console.aiven.io/) and choose **MySQL Free**, not a paid service or time-limited paid trial.
4. Ensure the deployment files referenced by this guide are committed to the GitHub branch selected in each dashboard. Render cannot build files that exist only on your computer.

Keep passwords, database URLs containing credentials, and cryptographic keys in the hosting dashboards and a protected local configuration file. Do not paste their values into an issue, commit, screenshot, or AI conversation.

## 3. Create the MySQL database

1. In Aiven, create the free MySQL service and wait until it is running.
2. From its connection details, record the host, port, database name (commonly `defaultdb`), username, and password privately.
3. Download or copy the service's **CA certificate**, including the BEGIN/END CERTIFICATE lines.
4. Prepare a URL in this format, using the actual port and database:

   ```text
   mysql://USER:URL_ENCODED_PASSWORD@HOST:PORT/defaultdb
   ```

   URL-encode special characters in the username/password. The cloud bootstrap selects PyMySQL and adds verified TLS settings itself; never turn off certificate or hostname verification.

Use a new database for this deployment. Switching the connection URL does not migrate the existing local SQLite data or local accounts. For a different database user, grant the privileges needed to apply the project's Alembic migrations to this database.

## 4. Create the Vercel project

Import `shzirley/information-security-assignment1` and configure:

| Setting | Value |
| --- | --- |
| Framework preset | Next.js |
| Root directory | `frontend` |
| Node.js | 22.x |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | Framework default |
| Production branch | `main` |

For the first web deployment, set `NEXT_PUBLIC_API_MODE=live`. You can initially set `API_ORIGIN=https://example.invalid` to reserve the stable production web domain before Render exists. Public pages should build, but authentication/API calls will fail until section 6 is complete; this is only a bootstrap deployment.

Record the stable project URL, for example `https://YOUR-PROJECT.vercel.app`. Use the exact domain shown by Vercel, not a guessed slug or a per-commit preview URL. Do not put backend keys or database credentials in Vercel's frontend environment.

## 5. Create the Render API

In Render, choose **New → Blueprint**, connect the repository, select the intended branch, and use its root `render.yaml`. Review that the service plan is **Free** before creating it.

The Blueprint uses the Dockerfile at `backend/Dockerfile` with `backend/` as its build context. It installs FFmpeg, includes the synthetic fixtures and Alembic migrations, runs as a non-root user, and binds to Render's `PORT`. Startup requires the external MySQL configuration, applies migrations, checks the database/key fingerprints, and then starts one API worker.

Provide these requested environment variables:

| Variable | Value |
| --- | --- |
| `KYC_DATABASE_URL` | The private Aiven URL from section 3 |
| `KYC_MYSQL_CA_PEM` | Full Aiven CA certificate with actual newlines |
| `ALLOWED_ORIGINS` | Exact stable Vercel HTTPS origin, without a trailing path |

The Blueprint sets `APP_ENV=production` and `COOKIE_SECURE=true`. It generates two independent Base64-encoded 256-bit secrets for `VELTRIX_KEK_V1_BASE64` and `VELTRIX_AUTH_SECRET_BASE64`, matching the application's 32-byte requirements. Render documents this behavior in its [Blueprint specification](https://render.com/docs/blueprint-spec).

**Retain these two generated values across redeployments.** Save protected copies separately from database backups. Generating a different KEK cannot recover evidence encrypted with the original key; startup deliberately rejects a database/key mismatch. Recreating a service against an existing database requires restoring its original keys.

Wait for the build and startup to complete, then open:

```text
https://YOUR-API.onrender.com/api/v1/health
```

Expected response includes `api: bankkyc`, `status: ok`, and `storage: mysql`. A working landing page alone does not prove that the API or database is ready. The local machine does not currently have Docker available; the container build must still be verified in Render or another Docker environment.

For an existing Blueprint, variables marked `sync: false` are not prompted again on later syncs. Change their values in the service's Environment settings when necessary.

## 6. Connect Vercel to Render

Update the Vercel **Production** environment:

```dotenv
NEXT_PUBLIC_API_MODE=live
API_ORIGIN=https://YOUR-API.onrender.com
```

Use only the origin in `API_ORIGIN`, with no `/api/v1` suffix and no trailing slash. Redeploy Vercel after changing it because the Next.js rewrite is produced during the build.

Confirm that Render's `ALLOWED_ORIGINS` equals the stable Vercel production origin, then open:

```text
https://YOUR-PROJECT.vercel.app/api/v1/health
```

It should report the same MySQL-backed health response as the direct Render URL. Test the application through the production domain. Preview deployments are not automatically trusted; do not add a wildcard origin to make previews pass.

## 7. Create reviewer, administrator, and evaluator accounts

Applicants can register through the web interface. Operator roles must be provisioned through the CLI. Render Free has no shell, and the production deployment does not seed shared demo passwords.

From the repository root on your own computer:

```powershell
Copy-Item deploy/cloud.env.example .env.cloud
```

Privately edit `.env.cloud` with the same Aiven URL, CA certificate, Vercel origin, and both generated keys from Render. The file is ignored by Git. Keep it distinct from the local `backend/.env`; do not overwrite local keys to manage the cloud database.

With backend dependencies installed, run from the repository root:

```powershell
backend\.venv\Scripts\python.exe backend/scripts/cloud_manage.py --env-file .env.cloud create-user reviewer_team --role reviewer
backend\.venv\Scripts\python.exe backend/scripts/cloud_manage.py --env-file .env.cloud create-user admin_team --role admin
backend\.venv\Scripts\python.exe backend/scripts/cloud_manage.py --env-file .env.cloud create-user evaluator_team --role evaluator
```

Each command asks for a password through a hidden terminal prompt. The helper uses the cloud credentials explicitly, connects with verified TLS, and removes its temporary CA file afterward. It cannot run `demo-users`, evidence cleanup, or an arbitrary management command. If startup migration has not yet run, apply it using the same helper with `migrate` before creating users.

Linux/macOS uses `backend/.venv/bin/python` instead. This CLI requires network access from your computer to the Aiven database; check any database access restrictions if the connection fails.

## 8. Verify the public deployment

Use synthetic evidence only, and record actual results in the [verification report](../verification/VERIFIKASI.md) after running these checks:

- Direct Render health and Vercel-proxied health both report MySQL storage.
- Register, sign in, save a profile, and upload valid identity, office, and video evidence through the Vercel domain.
- Download each file and compare its bytes or SHA-256 with the original.
- Verify a valid 30 MiB MP4 through the public upload **and** download path. A small fixture alone does not validate the size requirement.
- Sign out and back in, refresh, and restart/redeploy the API; accounts, case versions, and evidence should remain accessible with the same keys.
- Attempt access as another applicant; check assigned reviewer metadata and administrator boundaries.
- Assign, review, request revision, resubmit, and record a decision through the four role workspaces.
- Run the evaluator lab and export actual results. Record the cloud environment separately; do not compare cloud and local timings as if their machines were identical.
- Check private responses retain `Cache-Control: no-store`, session cookies are Secure/HttpOnly, and login/logout/CSRF rotation works through the proxy.
- Exercise a cold start, and confirm benchmark and upload requests complete within proxy timeouts and host memory limits.

The existing smoke script can check registration, storage, recovery, submission, and logout through the public web origin:

```powershell
backend\.venv\Scripts\python.exe backend/scripts/smoke_kyc_live.py --origin https://YOUR-PROJECT.vercel.app
```

It creates a synthetic account/application and does not cover the entire checklist, maximum-size uploads, or cross-role browser flows. Wake the API through its health URL and wait until it is healthy before running the script.

## 9. Troubleshooting

| Symptom | Check |
| --- | --- |
| Vercel API calls still target localhost or the bootstrap placeholder | Correct Production `API_ORIGIN` and redeploy Vercel |
| `403` on login/save | Exact `ALLOWED_ORIGINS`, HTTPS production domain, current CSRF cookie/token, and proxy routing |
| Login returns to the login page | Cookie forwarding through the external rewrite; avoid direct cross-site browser API calls |
| Database connection/TLS failure | URL encoding, database port, complete CA certificate, hostname, and service availability |
| Database/key mismatch | Restore the original cloud KEK/auth secret; do not generate replacements against existing data |
| First request is slow or times out | Render cold start; check direct health before retrying |
| Large upload returns `413`, `502`, or times out | Inspect Vercel and Render logs, proxy route, memory, video validity, database packet limit, and request duration |
| Data disappears after redeploy | Health must say `storage: mysql`; do not use SQLite on Render Free |
| Database fills up | Review evidence versions, lab history, and actual database storage use; do not assume 1 GB is entirely available for file payloads |

For maximum-size files, inspect MySQL's `max_allowed_packet`: the stored encrypted envelope needs more space than the original input, and an insufficient server packet limit can reject otherwise valid uploads. The free provider's supported settings and actual behavior must be checked rather than assumed.

## 10. Alternative: one persistent server

A VPS can run Next.js, FastAPI, FFmpeg, and MySQL behind an HTTPS reverse proxy on the same machine. This removes the split-host proxy path but requires operating-system updates, backups, TLS, and service supervision. It is a useful alternative if a campus/lab server is available or a paid budget becomes acceptable; it is not required for the initial free-hosting plan.

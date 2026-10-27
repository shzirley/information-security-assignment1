# VELTRIX documentation

Specifications, brand references, setup guides, and verification records for VELTRIX BankKYC. See the [project README](../README.md) for an architecture overview and implementation status.

## Reading order

1. Read the [product PRD](prd/VELTRIX_BankKYC_PRD.md) for the KYC scenario, requirements, privacy boundaries, and outstanding lecturer decisions.
2. Follow the [running guide](guides/PANDUAN_MENJALANKAN.md) to start the application locally.
3. Use the [frontend PRD](prd/VELTRIX_BankKYC_FE_PRD.md) and [backend PRD](prd/VELTRIX_BankKYC_BE_PRD.md) together when changing screens, permissions, or API contracts.
4. Check the [verification report](verification/VERIFIKASI.md) for measured results, test environments, and remaining coverage. Requirements and historical audit records are not proof of current implementation.

## Documentation map

| Directory | Documents | Purpose |
| --- | --- | --- |
| `prd/` | [Product](prd/VELTRIX_BankKYC_PRD.md), [frontend](prd/VELTRIX_BankKYC_FE_PRD.md), [backend](prd/VELTRIX_BankKYC_BE_PRD.md) | Scenario, behavior, contracts, acceptance criteria, and technical decisions |
| `design/` | [Brand guidelines](design/VELTRIX_GSM_v0.1.md), [component references](design/REFERENCES.md) | Existing logo, colors, typography, and reference provenance |
| `guides/` | [Local setup and troubleshooting](guides/PANDUAN_MENJALANKAN.md) | Running, operating, and backing up the local application |
| `verification/` | [Implementation verification](verification/VERIFIKASI.md), [UI audit](verification/ANTISLOP_QA.md), [Next.js security upgrade](verification/SECURITY_UPGRADE.md) | Dated checks with their original scope and limitations |
| `references/` | [Assignment image 1](references/ki1.jpeg), [assignment image 2](references/ki2.jpeg), [brand identity board](<references/Veltrix Secure Brand Identity Board.png>) | Original materials supplied for this project |

## Guides beside the code

- [Frontend README](../frontend/README.md): local configuration, API transport, and mock-test scope.
- [Backend README](../backend/README.md): migrations, account provisioning, MySQL, backup, and API details.
- [Frontend design direction](../frontend/DESIGN.md): interface decisions kept close to the code for UI work.
- [Frontend agent instructions](../frontend/AGENTS.md): tooling guidance kept in its original discovery location.

Command examples and inline source paths refer to the repository root unless a document explicitly names another working directory. Moving a guide does not change where its commands should run. Relative links resolve from the document containing them.

Keep new requirements in `prd/`, brand decisions in `design/`, operational instructions in `guides/`, dated test/audit records in `verification/`, and original reference materials in `references/`. Keep executable scripts, application assets, and configuration with their owning code.

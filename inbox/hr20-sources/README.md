# Federal HR 2.0 / Core HCM — durable source copies

Recovered and snapshotted 2026-07-23. Companion to `../Federal_HR20_Core_HCM_Leadership_Summary.md` / `.docx`.

| File | What it is | Source |
| --- | --- | --- |
| `Federal_HR20_Core_HCM_memo_2025-12-10.pdf` | **Primary source.** OMB/OPM joint memorandum "Creating 'Federal HR 2.0' by Consolidating Core Human Capital Management Across the Federal Government" (Vought + Kupor, Dec 10, 2025; 6 pages) | [govdelivery mirror](https://content.govdelivery.com/attachments/USOPM/2025/12/10/file_attachments/3489280/HR%202.0%20memo%2012-10-2025.pdf) (opm.gov was resetting connections) |
| `Federal_HR20_Core_HCM_memo_2025-12-10.txt` | Plain-text extraction of the memo PDF, for grep | derived locally |
| `ms-oracle-hcm-provisioning-tutorial.snapshot.md` | Oracle HCM → Entra ID integration guide (ATOM feeds, SCIM bulkUpload, cloud-only vs hybrid AD targets, full attribute worksheets) | [learn.microsoft.com](https://learn.microsoft.com/en-us/entra/identity/saas-apps/oracle-hcm-provisioning-tutorial) (updated 2026-06-15) |
| `ms-inbound-provisioning-api-concepts.snapshot.md` | API-driven inbound provisioning architecture, /bulkUpload endpoint, permissions, throttling | [learn.microsoft.com](https://learn.microsoft.com/en-us/entra/identity/app-provisioning/inbound-provisioning-api-concepts) (updated 2026-02-05) |
| `ms-entra-id-governance-licensing.snapshot.md` | Licensing: P1 vs Governance, **GCC/GCC-High/DoD availability of Governance for Government**, provisioning quotas, Lifecycle Workflows | [learn.microsoft.com](https://learn.microsoft.com/en-us/entra/id-governance/licensing-fundamentals) (updated 2026-06-26) |

Key finding captured after the leadership summary was written: the licensing page **confirms Entra ID Governance for Government is available in GCC** — the summary's watch item can be narrowed to "verify feature-level availability of API-driven provisioning + Lifecycle Workflows in our tenant."

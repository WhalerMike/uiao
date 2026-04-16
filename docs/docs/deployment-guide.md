UIAO-Core Deployment Guide

**Document ID:** UIAO_DEP_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

1\. Overview

  ------------------------------------------------------------------------------------------
  **Mode**                    **Best For**                                  **Complexity**
  --------------------------- --------------------------------------------- ----------------
  pip install (development)   Development, testing, evaluation              Low

  Docker                      Production, nightly automation, portability   Medium

  Bare metal / VM             Air-gapped environments, GCC Moderate         High
  ------------------------------------------------------------------------------------------

2\. pip Install (Development)

2.1 Prerequisites

- Python 3.11+ (3.12 recommended)

- Git 2.30+

- pip 23.0+

- PowerShell 7+ (for ScubaGear integration on Windows)

2.2 Install from Source

\# Clone repository git clone https://github.com/WhalerMike/uiao-core.git cd uiao-core \# Create virtual environment python -m venv .venv \# Activate (Windows) .venv\\Scripts\\activate \# Activate (Linux/macOS) source .venv/bin/activate \# Install with dev dependencies pip install -e \'.\[dev\]\' \# Verify installation uiao \--version pytest tests/ -v \--tb=short

2.3 Install from PyPI

pip install uiao-core

2.4 Dependencies

**Core Dependencies:**

  --------------------------------------------------------
  **Package**   **Version**   **Purpose**
  ------------- ------------- ----------------------------
  pydantic      ≥ 2.0         Data models and validation

  typer         ≥ 0.9         CLI framework

  pyyaml        ≥ 6.0         YAML configuration parsing

  rich          ≥ 13.0        Terminal output formatting

  httpx         ≥ 0.24        HTTP client for webhooks
  --------------------------------------------------------

**Dev Dependencies:**

  ----------------------------------------------------
  **Package**   **Version**   **Purpose**
  ------------- ------------- ------------------------
  pytest        ≥ 7.0         Test framework

  pytest-cov    ≥ 4.0         Coverage reporting

  ruff          ≥ 0.1         Linting and formatting

  mypy          ≥ 1.0         Static type checking
  ----------------------------------------------------

3\. Docker Deployment

3.1 Build

\# Build production image docker build -t uiao-core:latest . \# Build with specific version tag docker build -t uiao-core:2.0.0 .

3.2 Dockerfile

The multi-stage Dockerfile uses a Python 3.12-slim base, installs only production dependencies in the first stage, and copies the built package into a clean runtime image. The final image runs as a non-root user (uiao-svc) for security.

3.3 Run Commands

\# Run full pipeline docker run \--rm \\ -v \$(pwd)/config:/app/config \\ -v \$(pwd)/output:/app/output \\ -e UIAO_SIGNING_KEY=\"\${UIAO_SIGNING_KEY}\" \\ uiao-core:latest scuba run \--products all \# Run specific plane docker run \--rm \\ -v \$(pwd)/results:/app/results \\ uiao-core:latest scuba transform \--input /app/results/ScubaResults.json \# Interactive shell docker run \--rm -it \\ -v \$(pwd):/app \\ uiao-core:latest /bin/bash \# Run tests inside container docker run \--rm \\ uiao-core:latest pytest tests/ -v

3.4 Docker Compose

\# docker-compose.yml version: \"3.8\" services: pipeline: build: . image: uiao-core:latest volumes: - ./config:/app/config - ./output:/app/output - ./results:/app/results environment: - UIAO_SIGNING_KEY=\${UIAO_SIGNING_KEY} - UIAO_M365_TENANT_ID=\${UIAO_M365_TENANT_ID} - UIAO_LOG_LEVEL=INFO command: \[\"scuba\", \"run\", \"\--products\", \"all\"\] nightly: build: . image: uiao-core:latest volumes: - ./config:/app/config - ./output:/app/output environment: - UIAO_SIGNING_KEY=\${UIAO_SIGNING_KEY} - UIAO_M365_TENANT_ID=\${UIAO_M365_TENANT_ID} command: \> sh -c \"uiao scuba run \--products all && uiao ksi evaluate \--ir latest && uiao evidence build \--eval latest && uiao oscal generate \--evidence latest\" profiles: - nightly dashboard: build: . image: uiao-core:latest volumes: - ./output:/app/output command: \[\"dashboard\", \"export\", \"\--format\", \"html\"\] profiles: - reporting

4\. Bare Metal / VM Deployment

4.1 Windows Server

\# PowerShell deployment script \# 1. Create service account (run as Administrator) \$svcAccount = \"uiao-svc\" \# 2. Install Python and create venv python -m venv C:\\uiao\\.venv C:\\uiao\\.venv\\Scripts\\Activate.ps1 \# 3. Install package cd C:\\uiao git clone https://github.com/WhalerMike/uiao-core.git . pip install -e \'.\[dev\]\' \# 4. Set environment variables (Machine scope) \[System.Environment\]::SetEnvironmentVariable(\"UIAO_SIGNING_KEY\", \$signingKey, \"Machine\") \[System.Environment\]::SetEnvironmentVariable(\"UIAO_M365_TENANT_ID\", \$tenantId, \"Machine\") \[System.Environment\]::SetEnvironmentVariable(\"UIAO_CONFIG_PATH\", \"C:\\uiao\\config\", \"Machine\") \# 5. Create scheduled task for nightly assessment \$action = New-ScheduledTaskAction \` -Execute \"C:\\uiao\\.venv\\Scripts\\python.exe\" \` -Argument \"-m uiao_core.cli scuba run \--products all\" \` -WorkingDirectory \"C:\\uiao\" \$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM Register-ScheduledTask -TaskName \"UIAO-Nightly\" -Action \$action -Trigger \$trigger -User \$svcAccount

4.2 Linux

#!/bin/bash \# Linux deployment script \# 1. Create service account sudo useradd -r -s /bin/false uiao-svc sudo mkdir -p /opt/uiao sudo chown uiao-svc:uiao-svc /opt/uiao \# 2. Install Python and create venv cd /opt/uiao sudo -u uiao-svc python3 -m venv .venv sudo -u uiao-svc .venv/bin/pip install \--upgrade pip \# 3. Install package sudo -u uiao-svc git clone https://github.com/WhalerMike/uiao-core.git . sudo -u uiao-svc .venv/bin/pip install -e \'.\[dev\]\' \# 4. Set environment variables cat \> /opt/uiao/.env \<\<EOF UIAO_SIGNING_KEY=your-signing-key-here UIAO_M365_TENANT_ID=your-tenant-id UIAO_CONFIG_PATH=/opt/uiao/config UIAO_LOG_LEVEL=INFO EOF chmod 600 /opt/uiao/.env \# 5. Create cron job for nightly assessment echo \"0 2 \* \* \* uiao-svc cd /opt/uiao && .venv/bin/uiao scuba run \--products all\" \\ \| sudo tee /etc/cron.d/uiao-nightly

5\. GCC Moderate Considerations

5.1 Boundary Definition

  ---------------------------------------------------------------------------------
  **Component**           **Boundary**                    **Classification**
  ----------------------- ------------------------------- -------------------------
  UIAO pipeline host      Inside authorization boundary   GCC Moderate

  M365 tenant             FedRAMP authorized SaaS         GCC / GCC High

  GitHub repository       Source code management          Controlled

  Evidence storage        Inside authorization boundary   GCC Moderate

  Auditor bundle export   Crosses boundary to auditor     Controlled distribution
  ---------------------------------------------------------------------------------

5.2 Data Handling

- Public repository --- GCC Moderate applies to M365 SaaS services only

- Evidence bundles encrypted at rest using AES-256

- All data in transit uses TLS 1.2+

- Signing keys stored in environment variables, never in source code

5.3 Network Requirements

  ---------------------------------------------------------------------------------------------
  **Direction**   **Destination**   **Port**   **Protocol**   **Purpose**
  --------------- ----------------- ---------- -------------- ---------------------------------
  Outbound        M365 Graph API    443        HTTPS          ScubaGear assessment

  Outbound        GitHub            443        HTTPS          Source code updates (dev only)

  Outbound        PyPI              443        HTTPS          Package installation (dev only)

  Outbound        Teams webhook     443        HTTPS          Notifications

  Outbound        SMTP relay        587        SMTP/TLS       Email notifications
  ---------------------------------------------------------------------------------------------

6\. Air-Gapped Installation

6.1 Prepare Packages

\# On internet-connected machine mkdir -p uiao-airgap/packages pip download -d uiao-airgap/packages uiao-core\[dev\] cp -r uiao-core/ uiao-airgap/source/ \# Transfer uiao-airgap/ to air-gapped machine via approved media

6.2 Install on Air-Gapped Machine

\# On air-gapped machine python -m venv /opt/uiao/.venv source /opt/uiao/.venv/bin/activate pip install \--no-index \--find-links=/media/uiao-airgap/packages uiao-core\[dev\]

6.3 Air-Gapped Workflow

71. Transfer ScubaGear JSON output to pipeline machine via approved media

72. Run pipeline: uiao scuba transform \--input /path/to/ScubaResults.json

73. Complete remaining pipeline stages locally

74. Transfer auditor bundle out via approved media

7\. Upgrade Procedures

7.1 Minor Version Upgrade

75. Review release notes for breaking changes

76. Back up current configuration: cp -r config/ config.bak/

77. Update: pip install -e \'.\[dev\]\' \--upgrade

78. Run tests: pytest tests/ -v

79. Verify pipeline: uiao scuba status

7.2 Major Version Upgrade

80. Review migration guide in release notes

81. Back up entire installation directory

82. Create fresh virtual environment

83. Install new version: pip install -e \'.\[dev\]\'

84. Run migration script (if provided)

85. Run full test suite: pytest tests/ -v

86. Run parallel pipeline comparison against previous version output

8\. Health Verification

8.1 Post-Deployment Checks

\# 1. Version check uiao \--version \# 2. Smoke test pytest tests/ -v -k \"T0\" \# 3. Configuration validation uiao ksi validate \# 4. Pipeline smoke test pytest tests/test_e2e.py -v \# 5. Evidence signing test uiao evidence build \--eval tests/fixtures/eval-sample.json uiao evidence verify \--bundle evidence/latest.json \# 6. Full test suite pytest tests/ -v \--cov=src/uiao_core \--cov-fail-under=45

8.2 Ongoing Health Monitoring

  --------------------------------------------------------------------------
  **Check**              **Frequency**   **Command**
  ---------------------- --------------- -----------------------------------
  Pipeline status        Daily           uiao scuba status

  Evidence freshness     Daily           uiao evidence freshness

  Test suite             Every push      pytest tests/ -v

  Governance scorecard   Weekly          uiao governance scorecard

  Coverage trend         Monthly         uiao coverage trend \--period 30d

  Dependency audit       Monthly         pip audit
  --------------------------------------------------------------------------

9\. Security Hardening

9.1 File Permissions (Linux)

\# Set restrictive permissions chmod 700 /opt/uiao chmod 600 /opt/uiao/.env chmod 600 /opt/uiao/config/\*.yaml chmod 755 /opt/uiao/.venv/bin/uiao

9.2 Environment Variable Security

- Never store secrets in source code or config files

- Use .env files with chmod 600 permissions

- Rotate signing keys on a quarterly basis

- Use separate keys for development and production

9.3 CI/CD Secrets

  ------------------------------------------------
  **Secret**           **Scope**    **Rotation**
  -------------------- ------------ --------------
  UIAO_SIGNING_KEY     Repository   Quarterly

  M365_TENANT_ID       Repository   On change

  M365_CLIENT_ID       Repository   On change

  M365_CLIENT_SECRET   Repository   Quarterly

  NOTIFY_WEBHOOK_URL   Repository   On change
  ------------------------------------------------

10\. Troubleshooting Deployment Issues

  -------------------------------------------------------------------------------------------------------------------------------
  **Issue**                           **Cause**                             **Resolution**
  ----------------------------------- ------------------------------------- -----------------------------------------------------
  ModuleNotFoundError: uiao_core      Package not installed                 Run pip install -e \'.\[dev\]\'

  uiao: command not found             Virtual env not activated             Activate venv or use full path

  Permission denied on .env           File permissions too restrictive      Check ownership matches service account

  Docker build fails on pip install   Network restrictions                  Use \--build-arg PIP_INDEX_URL for internal mirror

  Nightly cron not running            Cron service not started              Check systemctl status cron

  Tests fail with fixture errors      Missing test fixtures                 Ensure tests/fixtures/ is populated

  Signing key mismatch                Different key in env vs. production   Verify UIAO_SIGNING_KEY matches across environments
  -------------------------------------------------------------------------------------------------------------------------------

Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md

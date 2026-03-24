import argparse
import logging
import os
import warnings

import requests

warnings.warn(
    "scripts/cyberark_sync_orchestrator.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)
# --- Configuration ---
# CyberArk PAS (Privileged Access Security) API
CYBERARK_BASE_URL = os.getenv("CYBERARK_VAULT_URL")  # e.g., https://vault.agency.gov
CYBERARK_USER = os.getenv("CYBERARK_SVC_USER")
CYBERARK_PASS = os.getenv("CYBERARK_SVC_PASS")

# ServiceNow GCC-Moderate
SN_INSTANCE = os.getenv("SN_INSTANCE_NAME")
SN_BASE_URL = f"https://{SN_INSTANCE}.servicenowservices.gov/api/now/table"
SN_USER = os.getenv("SN_SVC_USER")
SN_PASS = os.getenv("SN_SVC_PASS")
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class SyncSummary:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.created = 0
        self.updated = 0
        self.failed = 0
        self.total_processed = 0

    def report(self):
        mode = "DRY RUN" if self.dry_run else "LIVE SYNC"
        print(f"\n{'=' * 40}\nCYBERARK ATLAS SYNC - {mode}\n{'=' * 40}")
        print(
            f"Total: {self.total_processed} | Created: {self.created} | Updated: {self.updated} | Failed: {self.failed}\n"
        )
        self.send_teams_notification()

    def send_teams_notification(self):
        if not TEAMS_WEBHOOK_URL:
            return
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {"type": "TextBlock", "text": "Atlas: CyberArk to ServiceNow Sync", "weight": "Bolder"},
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Mode", "value": "Dry Run" if self.dry_run else "Live"},
                                    {"title": "Privileged Accounts", "value": str(self.total_processed)},
                                    {"title": "Updates/Creates", "value": f"{self.updated}/{self.created}"},
                                    {"title": "Failures", "value": str(self.failed)},
                                ],
                            },
                        ],
                    },
                }
            ],
        }
        requests.post(TEAMS_WEBHOOK_URL, json=payload)


class CyberArkClient:
    def __init__(self):
        self.base_url = f"{CYBERARK_BASE_URL}/PasswordVault/API"
        self.token = self._authenticate()

    def _authenticate(self):
        """Standard CyberArk REST API Authentication."""
        auth_url = f"{self.base_url}/auth/Cyberark/Logon"
        body = {"username": CYBERARK_USER, "password": CYBERARK_PASS}
        res = requests.post(auth_url, json=body, verify=True)
        res.raise_for_status()
        return res.text.strip('"')

    def get_privileged_accounts(self):
        """Fetches all accounts from the Vault."""
        logging.info("Extracting accounts from CyberArk Vault...")
        headers = {"Authorization": self.token, "Content-Type": "application/json"}
        res = requests.get(f"{self.base_url}/Accounts", headers=headers)
        res.raise_for_status()
        return res.json().get("value", [])


class ServiceNowClient:
    def __init__(self, dry_run=False):
        self.auth = (SN_USER, SN_PASS)
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self.dry_run = dry_run
        self.table = "cmdb_ci_privileged_id"

    def upsert_account(self, account, summary):
        account_id = account.get("id")
        name = account.get("name")
        try:
            query = f"correlation_id={account_id}"
            res = requests.get(
                f"{SN_BASE_URL}/{self.table}", auth=self.auth, headers=self.headers, params={"sysparm_query": query}
            )
            res.raise_for_status()
            existing = res.json().get("result", [])

            payload = {
                "name": name,
                "correlation_id": account_id,
                "u_safe_name": account.get("safeName"),
                "u_platform": account.get("platformId"),
                "u_source": "CyberArk Vault",
                "short_description": "Privileged Access Managed by CyberArk",
            }

            if existing:
                if not self.dry_run:
                    sys_id = existing[0]["sys_id"]
                    requests.patch(
                        f"{SN_BASE_URL}/{self.table}/{sys_id}", auth=self.auth, headers=self.headers, json=payload
                    ).raise_for_status()
                logging.info(f"UPDATED: {name}")
                summary.updated += 1
            else:
                if not self.dry_run:
                    requests.post(
                        f"{SN_BASE_URL}/{self.table}", auth=self.auth, headers=self.headers, json=payload
                    ).raise_for_status()
                logging.info(f"CREATED: {name}")
                summary.created += 1
        except Exception as e:
            logging.error(f"FAILED: {name} - {str(e)}")
            summary.failed += 1


class SyncOrchestrator:
    def __init__(self, dry_run=False):
        self.ca_client = CyberArkClient()
        self.sn_client = ServiceNowClient(dry_run=dry_run)
        self.summary = SyncSummary(dry_run=dry_run)

    def run(self):
        try:
            accounts = self.ca_client.get_privileged_accounts()
            self.summary.total_processed = len(accounts)
            for account in accounts:
                self.sn_client.upsert_account(account, self.summary)
        finally:
            self.summary.report()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if all([CYBERARK_BASE_URL, CYBERARK_USER, SN_INSTANCE]):
        SyncOrchestrator(dry_run=args.dry_run).run()
    else:
        logging.error("Missing Environment Variables for CyberArk/ServiceNow.")

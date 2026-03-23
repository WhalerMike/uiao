import argparse
import logging
import os
import warnings
from datetime import datetime

import requests

warnings.warn(
    "scripts/sync_orchestrator.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)
# --- Configuration ---
INFOBLOX_KEY = os.getenv('INFOBLOX_PORTAL_KEY')
INFOBLOX_URL = "https://csp.infoblox.com/api/ddi/v1"
SN_INSTANCE = os.getenv('SN_INSTANCE_NAME')
SN_BASE_URL = f"https://{SN_INSTANCE}.servicenowservices.gov/api/now/table"
SN_USER = os.getenv('SN_SVC_USER')
SN_PASS = os.getenv('SN_SVC_PASS')
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL')

# --- mTLS Hardening (GCC-Moderate) ---
# When ATLAS_MTLS_CERT and ATLAS_MTLS_KEY are set, all ServiceNow API calls
# use client-certificate authentication instead of Basic Auth.
ATLAS_MTLS_CERT = os.getenv('ATLAS_MTLS_CERT')  # Path to client .crt
ATLAS_MTLS_KEY = os.getenv('ATLAS_MTLS_KEY')    # Path to client .key
ATLAS_CA_BUNDLE = os.getenv('ATLAS_CA_BUNDLE', True)  # Agency CA bundle or True for default

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_mtls_config():
    """Returns (cert, verify) tuple for mTLS or (None, True) for Basic Auth fallback."""
    if ATLAS_MTLS_CERT and ATLAS_MTLS_KEY:
        logging.info("mTLS: Using client certificate authentication (GCC-Moderate hardened).")
        cert = (ATLAS_MTLS_CERT, ATLAS_MTLS_KEY)
        verify = ATLAS_CA_BUNDLE
        return cert, verify
    else:
        logging.info("mTLS: Not configured. Falling back to Basic Auth (sandbox mode).")
        return None, True


class TeamsNotifier:
    """Handles sending Adaptive Cards to MS Teams."""

    @staticmethod
    def send_summary(summary):
        if not TEAMS_WEBHOOK_URL:
            logging.warning("Teams Webhook URL not set. Skipping notification.")
            return

        mode = "DRY RUN" if summary.dry_run else "LIVE SYNC"
        payload = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": "Modernization Atlas: Sync Report", "weight": "Bolder", "size": "Medium"},
                        {"type": "FactSet", "facts": [
                            {"title": "Mode:", "value": mode},
                            {"title": "Auth:", "value": "mTLS" if ATLAS_MTLS_CERT else "Basic"},
                            {"title": "Status:", "value": "Completed with Errors" if summary.failed > 0 else "Success"},
                            {"title": "Processed:", "value": str(summary.total_processed)},
                            {"title": "Created:", "value": str(summary.created)},
                            {"title": "Updated:", "value": str(summary.updated)},
                            {"title": "Failed:", "value": str(summary.failed)}
                        ]}
                    ],
                    "msteams": {"width": "Full"}
                }
            }]
        }
        try:
            response = requests.post(TEAMS_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            logging.info("Teams notification sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send Teams notification: {e}")


class SyncSummary:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.created = 0
        self.updated = 0
        self.failed = 0
        self.total_processed = 0

    def report(self):
        mode_label = "DRY RUN" if self.dry_run else "LIVE MODE"
        auth_mode = "mTLS (GCC-Moderate)" if ATLAS_MTLS_CERT else "Basic Auth (Sandbox)"
        report_text = (
            f"\n{'=' * 40}\n"
            f"MODERNIZATION ATLAS SYNC - {mode_label}\n"
            f"Authentication: {auth_mode}\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
            f"{'-' * 40}\n"
            f"Total Processed: {self.total_processed}\n"
            f"Created: {self.created}\n"
            f"Updated: {self.updated}\n"
            f"Failed: {self.failed}\n"
            f"{'=' * 40}\n"
        )
        print(report_text)
        TeamsNotifier.send_summary(self)


class BloxOneClient:
    def __init__(self, api_key):
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }

    def fetch_subnets(self):
        logging.info("Extracting live data from InfoBlox...")
        response = requests.get(
            f"{INFOBLOX_URL}/ipam/subnet",
            headers=self.headers,
            params={"_inherit": "full"}
        )
        response.raise_for_status()
        return response.json().get('results', [])


class ServiceNowClient:
    def __init__(self, dry_run=False):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.dry_run = dry_run

        # mTLS or Basic Auth configuration
        self.cert, self.verify = get_mtls_config()
        if self.cert:
            # mTLS mode: no username/password needed
            self.auth = None
        else:
            # Basic Auth fallback (sandbox only)
            self.auth = (SN_USER, SN_PASS)

    def _request(self, method, url, **kwargs):
        """Centralized request method supporting both mTLS and Basic Auth."""
        kwargs['headers'] = self.headers
        kwargs['verify'] = self.verify
        if self.cert:
            kwargs['cert'] = self.cert
        elif self.auth:
            kwargs['auth'] = self.auth
        return requests.request(method, url, **kwargs)

    def upsert_subnet(self, subnet_data, summary):
        cidr = subnet_data.get('address')
        name = subnet_data.get('name', 'Unnamed Subnet')

        try:
            query = f"correlation_id={cidr}"
            res = self._request(
                'GET',
                f"{SN_BASE_URL}/cmdb_ci_ip_network",
                params={'sysparm_query': query}
            )
            res.raise_for_status()
            existing = res.json().get('result', [])

            payload = {
                "name": name,
                "correlation_id": cidr,
                "u_source_system": "InfoBlox BloxOne"
            }

            if existing:
                if self.dry_run:
                    logging.info(f"[DRY RUN] Would update existing record: {cidr}")
                else:
                    sys_id = existing[0]['sys_id']
                    self._request(
                        'PATCH',
                        f"{SN_BASE_URL}/cmdb_ci_ip_network/{sys_id}",
                        json=payload
                    ).raise_for_status()
                    logging.info(f"UPDATED: {cidr}")
                summary.updated += 1
            else:
                if self.dry_run:
                    logging.info(f"[DRY RUN] Would create new record: {cidr}")
                else:
                    self._request(
                        'POST',
                        f"{SN_BASE_URL}/cmdb_ci_ip_network",
                        json=payload
                    ).raise_for_status()
                    logging.info(f"CREATED: {cidr}")
                summary.created += 1
        except Exception as e:
            logging.error(f"FAILED: {cidr} - {str(e)}")
            summary.failed += 1


class SyncOrchestrator:
    def __init__(self, dry_run=False):
        self.ib_client = BloxOneClient(INFOBLOX_KEY)
        self.sn_client = ServiceNowClient(dry_run=dry_run)
        self.summary = SyncSummary(dry_run=dry_run)

    def run(self):
        try:
            raw_subnets = self.ib_client.fetch_subnets()
            self.summary.total_processed = len(raw_subnets)
            for subnet in raw_subnets:
                self.sn_client.upsert_subnet(subnet, self.summary)
        except Exception as e:
            logging.critical(f"Pipeline crashed: {e}")
            self.summary.failed = 999
        finally:
            self.summary.report()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modernization Atlas Management Plane Sync")
    parser.add_argument('--dry-run', action='store_true', help="Simulate the sync.")
    args = parser.parse_args()

    if all([INFOBLOX_KEY, SN_INSTANCE, SN_USER, SN_PASS]):
        SyncOrchestrator(dry_run=args.dry_run).run()
    elif all([INFOBLOX_KEY, SN_INSTANCE, ATLAS_MTLS_CERT, ATLAS_MTLS_KEY]):
        # mTLS mode: no username/password needed
        SyncOrchestrator(dry_run=args.dry_run).run()
    else:
        logging.error("Missing required environment variables. Set Basic Auth OR mTLS creds.")

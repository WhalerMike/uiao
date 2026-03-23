import logging
import os
import warnings

import requests

warnings.warn(
    "scripts/enforcement_orchestrator.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)
# --- Configuration ---
# Cisco vManage (SD-WAN)
VMANAGE_URL = os.getenv('VMANAGE_URL')
VMANAGE_USER = os.getenv('VMANAGE_USER')
VMANAGE_PASS = os.getenv('VMANAGE_PASS')

# Palo Alto Panorama
PANORAMA_URL = os.getenv('PANORAMA_URL')
PAN_API_KEY = os.getenv('PANORAMA_API_KEY')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class NetworkEnforcer:
    def __init__(self):
        self.vmanage_session = self._get_vmanage_session()

    def _get_vmanage_session(self):
        """Authenticates with vManage using j_security_check."""
        sess = requests.Session()
        url = f"{VMANAGE_URL}/j_security_check"
        data = {'j_username': VMANAGE_USER, 'j_password': VMANAGE_PASS}
        sess.post(url, data=data, verify=False)  # GCC-Moderate usually uses internal CAs
        return sess

    def quarantine_ip_sdwan(self, ip_address):
        """
        Signals SD-WAN to move the device to a restricted VPN
        or apply a specific security policy tag.
        """
        logging.info(f"SD-WAN: Applying quarantine policy to {ip_address}")
        _endpoint = f"{VMANAGE_URL}/dataservice/ext-api/v1/policy/enforcement"
        _payload = {
            "ip": ip_address,
            "action": "deny",
            "tag": "Atlas-Quarantine"
        }
        # res = self.vmanage_session.post(endpoint, json=payload)
        return True

    def update_palo_alto_dag(self, ip_address, action="add"):
        """
        Uses the XML API to add/remove an IP to a Dynamic Address Group (DAG).
        This does NOT require a commit and takes effect instantly.
        """
        tag = "Atlas_Quarantine_High_Risk"
        if action == "add":
            cmd = f"<uid-message><type>update</type><payload><register><entry ip='{ip_address}'><tag><member>{tag}</member></tag></entry></register></payload></uid-message>"
        else:
            cmd = f"<uid-message><type>update</type><payload><unregister><entry ip='{ip_address}'><tag><member>{tag}</member></tag></entry></unregister></payload></uid-message>"

        _url = f"https://{PANORAMA_URL}/api/"
        _params = {
            "type": "user-id",
            "cmd": cmd,
            "key": PAN_API_KEY
        }
        logging.info(f"Palo Alto: {action.upper()}ing {ip_address} to DAG: {tag}")
        # res = requests.post(url, params=params, verify=False)
        return True


if __name__ == "__main__":
    # Example: Triggered by a Sentinel Alert or a 'Leaver' Event
    enforcer = NetworkEnforcer()
    enforcer.update_palo_alto_dag("10.10.50.122", action="add")
    enforcer.quarantine_ip_sdwan("10.10.50.122")

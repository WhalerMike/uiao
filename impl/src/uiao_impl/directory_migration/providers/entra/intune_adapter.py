# UIAO-GOS | Entra Intune Adapter
# Classification: Controlled | Boundary: GCC-Moderate (M365 SaaS only)
# Provider: entra.intune | ARC 5 Aligned
"""
Entra Intune Adapter - device compliance, configuration profiles,
app protection policies, and conditional-access device posture.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.providers.base_adapter import BaseAdapter, ProviderCapability

logger = logging.getLogger(__name__)


class ComplianceState(Enum):
        COMPLIANT = "compliant"
        NON_COMPLIANT = "non_compliant"
        IN_GRACE_PERIOD = "in_grace_period"
        NOT_EVALUATED = "not_evaluated"
        UNKNOWN = "unknown"
        ERROR = "error"


class ProfileType(Enum):
        DEVICE_RESTRICTIONS = "device_restrictions"
        WIFI = "wifi"
        VPN = "vpn"
        EMAIL = "email"
        CERTIFICATE = "certificate"
        CUSTOM = "custom"
        ENDPOINT_PROTECTION = "endpoint_protection"
        ADMINISTRATIVE_TEMPLATE = "administrative_template"


class EnrollmentType(Enum):
        AUTOPILOT = "autopilot"
        BULK_ENROLLMENT = "bulk_enrollment"
        USER_ENROLLMENT = "user_enrollment"
        DEVICE_ENROLLMENT_MANAGER = "device_enrollment_manager"
        CO_MANAGEMENT = "co_management"


class Platform(Enum):
        WINDOWS = "windows"
        IOS = "ios"
        ANDROID = "android"
        MACOS = "macos"
        LINUX = "linux"


@dataclass
class CompliancePolicy:
        policy_id: str
        display_name: str
        platform: Platform
        is_assigned: bool = False
        settings: Dict[str, Any] = field(default_factory=dict)
        grace_period_hours: int = 0
        actions_for_noncompliance: List[str] = field(default_factory=list)
        governance_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ConfigurationProfile:
        profile_id: str
        display_name: str
        profile_type: ProfileType
        platform: Platform
        is_assigned: bool = False
        settings: Dict[str, Any] = field(default_factory=dict)
        governance_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AppProtectionPolicy:
        policy_id: str
        display_name: str
        platform: Platform
        targeted_apps: List[str] = field(default_factory=list)
        data_protection_settings: Dict[str, Any] = field(default_factory=dict)
        access_requirements: Dict[str, Any] = field(default_factory=dict)
        conditional_launch: Dict[str, Any] = field(default_factory=dict)
        governance_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ManagedDevice:
        device_id: str
        device_name: str
        platform: Platform
        compliance_state: ComplianceState
        enrollment_type: EnrollmentType
        last_sync: Optional[str] = None
        os_version: Optional[str] = None
        serial_number: Optional[str] = None
        user_principal_name: Optional[str] = None
        is_supervised: bool = False
        is_encrypted: bool = False
        governance_tags: Dict[str, str] = field(default_factory=dict)


@dataclass
    class AutopilotProfile:
        profile_id: str
        display_name: str
        deployment_mode: str = "user_driven"
        join_type: str = "azure_ad_joined"
        oobe_settings: Dict[str, Any] = field(default_factory=dict)
        assigned_devices: List[str] = field(default_factory=list)
        governance_tags: Dict[str, str] = field(default_factory=dict)


    @dataclass
    class RemediationScript:
        script_id: str
        display_name: str
        detection_script: Optional[str] = None
        remediation_script: Optional[str] = None
        run_as_account: str = "system"
        enforce_signature_check: bool = True
        run_as_32bit: bool = False
    schedule: Optional[str] = None
        governance_tags: Dict[str, str] = field(default_factory=dict)



class IntuneAdapter(BaseAdapter):
        """UIAO-GOS Entra Intune Adapter. ARC-5 aligned."""

            PROVIDER_ID = "entra.intune"
    PROVIDER_VERSION = "1.0.0"
    CLASSIFICATION = "Controlled"
    BOUNDARY = "GCC-Moderate"

    CAPABILITIES = [
                ProviderCapability.ENUMERATE,
                ProviderCapability.VALIDATE,
                ProviderCapability.ENFORCE,
                ProviderCapability.REMEDIATE,
                ProviderCapability.DRIFT_DETECT,
    ]

    def initialize(self, config: Dict[str, Any]) -> None:
                self._tenant_id = config.get("tenant_id", "")
                self._graph_endpoint = config.get("graph_endpoint", "https://graph.microsoft.com/v1.0")
                                                     self._compliance_policies: Dict[str, CompliancePolicy] = {}
                self._configuration_profiles: Dict[str, ConfigurationProfile] = {}
                           self._app_protection_policies: Dict[str, AppProtectionPolicy] = {}
        self._managed_devices: Dict[str, ManagedDevice] = {}
        self._autopilot_profiles: Dict[str, AutopilotProfile] = {}
        self._remediation_scripts: Dict[str, RemediationScript] = {}
                           logger.info("IntuneAdapter initialized | tenant=%s", self._tenant_id)

    def healthcheck(self) -> Dict[str, Any]:
                return {
                    "provider": self.PROVIDER_ID,
                               "version": self.PROVIDER_VERSION,
            "boundary": self.BOUNDARY,
            "tenant_id": self._tenant_id,
                               "compliance_policies": len(self._compliance_policies),
            "configuration_profiles": len(self._configuration_profiles),
            "managed_devices": len(self._managed_devices),
            "status": "healthy",
}

    def enumerate_compliance_policies(self) -> List[CompliancePolicy]:
        logger.info("Enumerating compliance policies")
        return list(self._compliance_policies.values())

    def enumerate_configuration_profiles(self) -> List[ConfigurationProfile]:
        logger.info("Enumerating configuration profiles")
        return list(self._configuration_profiles.values())

    def enumerate_app_protection_policies(self) -> List[AppProtectionPolicy]:
        logger.info("Enumerating app protection policies")
        return list(self._app_protection_policies.values())

    def enumerate_managed_devices(self, platform_filter: Optional[Platform] = None) -> List[ManagedDevice]:
        devices = list(self._managed_devices.values())
        if platform_filter:
            devices = [d for d in devices if d.platform == platform_filter]
        return devices

    def get_device_compliance_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {s.value: 0 for s in ComplianceState}
        for device in self._managed_devices.values():
            summary[device.compliance_state.value] += 1
        return summary

    def enumerate_autopilot_profiles(self) -> List[AutopilotProfile]:
        return list(self._autopilot_profiles.values())

    def enumerate_remediation_scripts(self) -> List[RemediationScript]:
        return list(self._remediation_scripts.values())

    def detect_drift(self, desired_state: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        results = {"compliance": [], "profiles": [], "app_protection": [], "total_drift": 0}
        for pid, expected in desired_state.get("compliance_policies", {}).items():
            policy = self._compliance_policies.get(pid)
            if policy:
                for key, val in expected.items():
                    if policy.settings.get(key) != val:
                        results["compliance"].append({"policy": pid, "field": key, "expected": val, "actual": policy.settings.get(key)})
                        results["total_drift"] += 1
        for pid, expected in desired_state.get("configuration_profiles", {}).items():
            profile = self._configuration_profiles.get(pid)
            if profile:
                for key, val in expected.items():
                    if profile.settings.get(key) != val:
                        results["profiles"].append({"profile": pid, "field": key, "expected": val, "actual": profile.settings.get(key)})
                        results["total_drift"] += 1
        logger.info("Intune drift detection complete | total_drift=%d", results["total_drift"])
        return results

    def enforce(self, entity_type: str, entity_id: str, desired_state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Enforcing desired state | type=%s id=%s", entity_type, entity_id)
        return {
            "provider": self.PROVIDER_ID,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": "enforce",
            "desired_state": desired_state,
            "status": "pending_implementation",
            "note": "Graph API enforcement requires write permissions",
}

    def get_provider_manifest(self) -> Dict[str, Any]:
        return {
            "provider_id": self.PROVIDER_ID,
            "version": self.PROVIDER_VERSION,
            "classification": self.CLASSIFICATION,
            "boundary": self.BOUNDARY,
            "capabilities": [c.value for c in self.CAPABILITIES],
            "managed_entity_types": [
                "compliance_policy", "configuration_profile",
                "app_protection_policy", "managed_device",
                "autopilot_profile", "remediation_script",
],
            "platforms_supported": [p.value for p in Platform],
            "graph_api_required": True,
            "canon_constraints": {
                "no_fouo": True,
                "gcc_moderate_only": True,
                "fedramp_ceiling": "Moderate",
},
}

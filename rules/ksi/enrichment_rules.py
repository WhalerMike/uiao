"""UIAO-Core KSI Tier 2 Enrichment Rules"""

ENRICHMENT_RULES = {
    "iam": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "100% of non-exempt accounts use phishing-resistant MFA and automated lifecycle management",
            "type": "percentage",
            "threshold": 100,
            "operator": "equals"
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "private_endpoint_enforcement": True,
            "zero_trust_telemetry": True,
            "sase_global_secure_access": True
        }
    },
    "boundary-protection": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "All PaaS services use Private Endpoints only; public exposure minimized per hub-spoke model",
            "type": "boolean",
            "threshold": 1
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "private_endpoint_enforcement": True,
            "dns_segmentation_required": True,
            "hub_spoke_model": True,
            "video_project_isolation": True
        }
    },
    "monitoring-logging": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "All security-relevant events logged and auditable within 5 minutes",
            "type": "boolean",
            "threshold": 1
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "zero_trust_telemetry": True
        }
    },
    "configuration-management": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "Configuration drift < 5% across all systems; approved baselines enforced",
            "type": "threshold",
            "threshold": 5,
            "operator": "less_than"
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "zero_trust_telemetry": True
        }
    },
    "default": {
        "validation_type": "semi-automated",
        "pass_criteria": {
            "description": "Control implementation verified through evidence sources",
            "type": "boolean",
            "threshold": 1
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True
        }
    }
}


def get_enrichment_for_category(category: str):
    return ENRICHMENT_RULES.get(category.lower(), ENRICHMENT_RULES["default"])

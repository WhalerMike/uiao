"""uiao.oscal — Evidence → OSCAL artifacts (Plane 4)."""

from uiao.oscal.generator import generate_oscal
from uiao.oscal.kyc_evidence import (
    emit_customer_identity_record,
    emit_reciprocity_attribute_record,
    emit_reciprocity_record,
)

__all__ = [
    "generate_oscal",
    "emit_customer_identity_record",
    "emit_reciprocity_attribute_record",
    "emit_reciprocity_record",
]

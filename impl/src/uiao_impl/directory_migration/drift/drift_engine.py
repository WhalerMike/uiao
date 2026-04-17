import hashlib
from pydantic import BaseModel
from typing import Any, Dict, Optional


class DriftClassification(str):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"


class DriftState(BaseModel):
    """
    Represents the drift status of a resource by comparing
    expected vs actual state.
    """
    expected_hash: str
    actual_hash: str
    drift_detected: bool
    classification: DriftClassification
    details: Optional[Dict[str, Any]] = None


def compute_hash(obj: Any) -> str:
    """
    Compute a deterministic SHA256 hash of a Python object.
    """
    serialized = str(obj).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def classify_drift(expected: Any, actual: Any) -> DriftState:
    """
    Compare expected vs actual state and classify drift.
    """
    expected_hash = compute_hash(expected)
    actual_hash = compute_hash(actual)

    drift_detected = expected_hash != actual_hash

    if not drift_detected:
        classification = DriftClassification.NONE
    else:
        # Simple commercial classification logic
        classification = (
            DriftClassification.MAJOR
            if isinstance(expected, dict) and isinstance(actual, dict)
            and set(expected.keys()) != set(actual.keys())
            else DriftClassification.MINOR
        )

    return DriftState(
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=drift_detected,
        classification=classification,
        details={"expected": expected, "actual": actual} if drift_detected else None
    )

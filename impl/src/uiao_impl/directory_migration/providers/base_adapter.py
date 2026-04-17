from abc import ABC, abstractmethod
from typing import Dict, Any

from core.drift.drift_engine import DriftState


class BaseAdapter(ABC):
    """
        Abstract base class for all UIAO-GOS provider adapters.
            All providers must implement health_check, fetch_state,
                expected_state, and remediate.
                    """

                        version: str = "0.0.0"
                            capabilities: list = []

                                @abstractmethod
                                    def health_check(self) -> Dict[str, Any]:
                                            """Return provider health status."""
                                                    ...

                                                        @abstractmethod
                                                            def fetch_state(self) -> Dict[str, Any]:
                                                                    """Fetch current state from the provider."""
                                                                            ...

                                                                                @abstractmethod
                                                                                    def expected_state(self) -> Dict[str, Any]:
                                                                                            """Return the expected (desired) state for drift comparison."""
                                                                                                    ...

                                                                                                        @abstractmethod
                                                                                                            def remediate(self, drift: DriftState) -> Dict[str, Any] | None:
                                                                                                                    """Attempt to remediate detected drift."""
                                                                                                                            ...
import os
import json
from datetime import datetime
from typing import Any, Dict

from core.evidence.evidence_model import Evidence


class EvidenceStore:
      """
          Minimal deterministic evidence store.
              Stores evidence as JSON files under core/evidence/store/.
                  """

    def __init__(self, root: str | None = None):
              if root is None:
                            root = os.path.join(
                                              os.path.dirname(__file__),
                                              "store"
                            )
                        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def save(self, evidence: Evidence) -> str:
              filename = f"{evidence.id}.json"
        path = os.path.join(self.root, filename)

        with open(path, "w", encoding="utf-8") as f:
                      json.dump(evidence.dict(), f, indent=2, default=str)

        return path

    def load(self, evidence_id: str) -> Evidence:
              path = os.path.join(self.root, f"{evidence_id}.json")

        if not os.path.exists(path):
                      raise FileNotFoundError(f"No evidence found for id: {evidence_id}")

        with open(path, "r", encoding="utf-8") as f:
                      data = json.load(f)

        return Evidence(**data)

    def list(self) -> Dict[str, Any]:
              items = {}
        for filename in os.listdir(self.root):
                      if filename.endswith(".json"):
                                        evidence_id = filename.replace(".json", "")
                                        items[evidence_id] = os.path.join(self.root, filename)
                                return items

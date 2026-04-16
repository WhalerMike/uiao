from typing import Callable, Dict

from core.governance.action_model import Action
from core.governance.action_engine import determine_action


class ActionRegistry:
      """
          Simple deterministic registry for governance actions.
              Maps drift types -> handler functions.
                  """

    def __init__(self):
              self._registry: Dict[str, Callable] = {}

        # Default mapping for early UIAO-GOS
              self.register("missing-resource", determine_action)
              self.register("misconfiguration", determine_action)
              self.register("tag-drift", determine_action)
              self.register("generic-drift", determine_action)
              self.register("none", determine_action)

    def register(self, key: str, handler: Callable):
              self._registry[key] = handler

    def get(self, key: str) -> Callable:
              if key not in self._registry:
                            return determine_action
                        return self._registry[key]

    def list(self) -> Dict[str, Callable]:
              return dict(self._registry)

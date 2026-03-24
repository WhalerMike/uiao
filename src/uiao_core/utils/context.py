import os
import yaml
from typing import Any, Dict, List


def get_settings() -> Dict[str, Any]:
    # Implementation for getting settings
    pass


def load_canon() -> Dict[str, Any]:
    # Implementation for loading canon configuration
    pass


def load_context(yaml_files: List[str], overlay: List[str]) -> Dict[str, Any]:
    settings = get_settings()
    context = {}  # Initialize empty context
    
    # Load data/*.yml files first
    for file in yaml_files:
        context = _deep_merge(context, _load_yaml_path(file))
    
    # Load canon YAML, which can overwrite data
    context = _deep_merge(context, load_canon())
    
    # Apply overlays in provided order
    for overlay_file in overlay:
        context = _deep_merge(context, _load_yaml_path(overlay_file))
    
    return context


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merges two dictionaries.
    - Dicts recurse.
    - Lists append with deduplication (preserving order).
    - Scalars overwrite.
    """
    for key, value in b.items():
        if key in a:
            if isinstance(a[key], dict) and isinstance(value, dict):
                a[key] = _deep_merge(a[key], value)
            elif isinstance(a[key], list) and isinstance(value, list):
                a[key] = _dedupe_list(a[key] + value)
            else:
                a[key] = value
        else:
            a[key] = value
    return a


def _dedupe_list(items: List[Any]) -> List[Any]:
    seen = set()
    deduped = []
    for item in items:
        identifier = item.get('id') if isinstance(item, dict) else item
        if identifier not in seen:
            seen.add(identifier)
            deduped.append(item)
    return deduped


def _load_yaml_path(path: str) -> Dict[str, Any]:
    """
    Load a YAML file safely.
    """
    with open(path, 'r') as file:
        return yaml.safe_load(file)

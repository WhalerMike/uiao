"""SBOM (Software Bill of Materials) generator in CycloneDX JSON format."""

from __future__ import annotations

import importlib.metadata
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _first_project_url(meta: importlib.metadata.PackageMetadata) -> str:
    """Extract the first URL from Project-URL metadata (format: 'Label, url')."""
    raw = meta.get_all("Project-URL") or []
    for entry in raw:
        # `PackageMetadata.get_all()` is typed as returning `list[Any]` in
        # typeshed; coerce each header value to str to keep the return path
        # typed as `str` rather than leaking Any out of this function.
        parts = str(entry).split(",", 1)
        if len(parts) == 2:
            return parts[1].strip()
    return ""


def _get_installed_packages() -> list[dict[str, str]]:
    """Return a list of installed packages with name, version, and metadata."""
    packages = []
    for dist in importlib.metadata.distributions():
        # dist.metadata is an email.message.Message subclass; runtime supports
        # dict() coercion via the Mapping protocol (.keys() + __getitem__),
        # but typeshed's `PackageMetadata.__iter__` yields header names (str)
        # rather than (name, value) tuples and `dict()` doesn't pick up the
        # Mapping overload. Suppress the stub-gap locally.
        meta: dict[str, str] = dict(dist.metadata)  # type: ignore[arg-type]
        name = meta.get("Name") or ""
        version = meta.get("Version") or ""
        if name and version:
            packages.append(
                {
                    "name": name,
                    "version": version,
                    "description": meta.get("Summary") or "",
                    "homepage": meta.get("Home-page") or _first_project_url(dist.metadata),
                    "license": meta.get("License") or "",
                }
            )
    return sorted(packages, key=lambda p: p["name"].lower())


def build_sbom(output_path: str | Path = "exports/sbom/sbom.cyclonedx.json") -> Path:
    """Generate a CycloneDX 1.4 JSON SBOM of installed Python packages.

    Args:
        output_path: Destination path for the SBOM JSON file.

    Returns:
        Path to the written SBOM file.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    packages = _get_installed_packages()
    components = []
    for pkg in packages:
        component: dict = {
            "type": "library",
            "name": pkg["name"],
            "version": pkg["version"],
            "purl": f"pkg:pypi/{pkg['name'].lower()}@{pkg['version']}",
        }
        if pkg["description"]:
            component["description"] = pkg["description"]
        if pkg["license"]:
            component["licenses"] = [{"license": {"name": pkg["license"]}}]
        components.append(component)

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [{"vendor": "uiao", "name": "uiao generate-sbom"}],
            "component": {
                "type": "application",
                "name": "uiao",
                "version": _get_uiao_version(),
            },
        },
        "components": components,
    }

    out.write_text(json.dumps(sbom, indent=2))
    return out


def _get_uiao_version() -> str:
    """Return the uiao package version."""
    try:
        return importlib.metadata.version("uiao")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"

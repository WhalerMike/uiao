# Canon (YAML SSOT)

This directory holds the **canonical YAML Single Source of Truth** bundled
inside the installed `uiao` package. At runtime, `uiao.cli.bundled_canon_path()`
resolves this directory via `importlib.resources`, so end users never need to
pass `--canon-path`.

## Migration Status

Content is being migrated from the legacy `uiao-core/canon/` tree. Expected
layout once migration completes:

```
canon/
├── config.yaml         # top-level canon config
├── schema.yaml         # canon schema metadata
├── controls/           # control definitions (FedRAMP Moderate, ZTA, TIC 3.0)
├── ksi/                # Key Security Indicator definitions
├── rules/              # policy-as-code rules
└── oscal/              # OSCAL profile + catalog inputs
```

Package-data in `pyproject.toml` already includes `canon/**/*`, so any file
added under this directory will ship with the wheel automatically.

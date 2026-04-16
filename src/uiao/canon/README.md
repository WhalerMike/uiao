# Canon (YAML SSOT)

This directory holds the **canonical YAML Single Source of Truth** bundled
inside the installed `uiao` package. At runtime,
`uiao.cli.bundled_canon_path()` resolves this directory via
`importlib.resources`, so end users never need to pass `--canon-path`.

Package-data in `pyproject.toml` already includes `canon/**/*`, so any file
added under this directory will ship with the wheel automatically.

## Expected Layout (from legacy `uiao-core/canon/`)

```
canon/
├── config.yaml              # top-level canon config (project, version, toggles)
├── schema.yaml              # canon schema metadata / version pin
├── controls/                # control definitions
│   ├── fedramp-moderate/    # FedRAMP Moderate baseline
│   ├── zta/                 # Zero Trust Architecture mappings
│   └── tic3/                # TIC 3.0 mappings
├── ksi/                     # Key Security Indicator definitions
│   ├── catalog.yaml
│   └── <ksi-id>.yaml
├── rules/                   # policy-as-code rules
│   └── <rule-id>.yaml
├── oscal/                   # OSCAL profile + catalog inputs
│   ├── profile.yaml
│   └── catalog.yaml
└── mappings/                # cross-framework / control-to-KSI mappings
    └── <mapping>.yaml
```

## Migration Instructions (for Claude, when the tree becomes available)

1. **Receive the tree.** User pastes `git ls-files` output from the legacy
   `uiao-core` repo so we know the exact file list to pull.
2. **Pull in batches.** For each subtree (start with `controls/`, then
   `ksi/`, `rules/`, `oscal/`, `mappings/`, then top-level YAMLs), request
   the file contents from the user and commit in small batches.
3. **Preserve paths.** Keep the relative path under `canon/` identical to
   the legacy repo — downstream code paths assume it.
4. **Validate after each batch.**
   ```bash
   pip install -e ".[dev]"
   uiao validate
   pytest
   ```
5. **Remove the stub.** Once a real `config.yaml` is migrated, delete or
   replace the placeholder committed alongside this README.

## Do Not

- Do **not** hand-edit migrated canon content; it should round-trip from
  the legacy repo unchanged until we have tests covering it.
- Do **not** add sample or synthetic canon data here — the bundled tree
  is treated as the real SSOT by the CLI.

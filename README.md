# uiao-impl

Python implementation for the UIAO governance ecosystem: library, CLI, generators, adapters, and the pytest suite.

This repository holds **application code only**. Canonical governance artifacts (YAMLs, schemas, rules, playbooks) live in [`WhalerMike/uiao-core`](https://github.com/WhalerMike/uiao-core). Documentation and article series live in [`WhalerMike/uiao-docs`](https://github.com/WhalerMike/uiao-docs).

## Install

```bash
pip install git+https://github.com/WhalerMike/uiao-impl.git@v0.1.0
```

## CLI

```bash
uiao --help
```

## Development

```bash
git clone https://github.com/WhalerMike/uiao-impl.git
cd uiao-impl
pip install -e .[dev]
pytest
```

## Canon dependency

All generators and validators need a canon path at runtime:

```bash
uiao validate --canon-path ../uiao-core/canon
uiao generate-ssp --canon-path ../uiao-core/canon --out out/ssp.docx
```

## License

Apache 2.0

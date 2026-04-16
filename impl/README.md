# uiao-impl

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![FedRAMP Moderate](https://img.shields.io/badge/FedRAMP-Moderate%20Rev%205-orange.svg)](https://whalermike.github.io/uiao-docs/docs/03_FedRAMP20x_Crosswalk.html)

**UIAO Ecosystem:** [uiao-core](https://github.com/WhalerMike/uiao-core) (governance engine) · **uiao-impl** (this repo) · [uiao-docs](https://github.com/WhalerMike/uiao-docs) ([live site](https://whalermike.github.io/uiao-docs/docs/index.html))

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

## Compliance with Presidential Executive Orders

The UIAO implementation codebase supports the federal-cybersecurity
provisions of the following Executive Orders:

- **EO 14144** (January 16, 2025) — *Strengthening and Promoting Innovation in the Nation's Cybersecurity*
- **EO 14306** (June 6, 2025) — *Sustaining Select Efforts to Strengthen the Nation's Cybersecurity; amending EO 13694 and EO 14144*
- **EO 14390** (March 6, 2026) — *Combating Cybercrime, Fraud, and Predatory Schemes Against American Citizens* (paired with *President Trump's Cyber Strategy for America*, March 2026)

These orders shape UIAO's operational focus: Zero Trust architecture,
federal cybersecurity modernization, FedRAMP / cloud transition,
post-quantum cryptography, and continuous compliance. The canonical
mapping between UIAO artifacts and EO provisions lives in [`uiao-core/canon/compliance/executive-orders.md`](https://github.com/WhalerMike/uiao-core/blob/main/canon/compliance/executive-orders.md)
(UIAO_004). This repository is a **consumer** of that canon.

## License

Apache 2.0

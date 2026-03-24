# [0.30.0](https://github.com/WhalerMike/uiao-core/compare/v0.29.0...v0.30.0) (2026-03-24)


### Bug Fixes

* add pip-audit CI step (continue-on-error) and tighten dep minimums ([10b052c](https://github.com/WhalerMike/uiao-core/commit/10b052c3aaf73ca81daf6bd9852dabbdee6c82ea))
* add project_root to Settings and fix generate-artifacts workflow permissions ([884c755](https://github.com/WhalerMike/uiao-core/commit/884c75584a77a6d8db220e968ef61d90bd543945))
* AI Security Audit handles both PRs and direct pushes to main ([6bc9f42](https://github.com/WhalerMike/uiao-core/commit/6bc9f42d648ba2c0fd97b42908ffff238fe66f14))
* **ci:** add skip-tag to changelog - tag v0.30.0 already exists ([fac84fd](https://github.com/WhalerMike/uiao-core/commit/fac84fdff597837d42c1806c26d01a731ef50982))
* **ci:** correct --tb=shortcom typo to --tb=short in ci.yml ([0aa5374](https://github.com/WhalerMike/uiao-core/commit/0aa537478517632da8c8e032b492b4b922ac69ec))
* **ci:** fix changelog workflow git push failure (exit code 128) ([cd7fb73](https://github.com/WhalerMike/uiao-core/commit/cd7fb7375315a531b072477dd8f46ec673576cdc))
* **ci:** replace broken gh-mcp-server with TruffleHog for secret scanning ([0ddb737](https://github.com/WhalerMike/uiao-core/commit/0ddb737b64362943d92e4a4439606b73d090b87f))
* **cli:** restore gemini print and remove stray line in app.py ([6a33071](https://github.com/WhalerMike/uiao-core/commit/6a3307104925fd55bd68b66055ff3b7d296fc501))
* **cli:** rewrite app.py with correct indentation and __main__ guard ([6819078](https://github.com/WhalerMike/uiao-core/commit/6819078cdc53036552874a36f5ef12a25b91d3c0))
* complete PR [#48](https://github.com/WhalerMike/uiao-core/issues/48) continuous monitoring review fixes [refs UIAO-MEMORY.md] ([00b788a](https://github.com/WhalerMike/uiao-core/commit/00b788a52e3beb74c8a1eacab282ad6574430edf))
* **evidence:** add missing linker.py + bundler.py, prop:id on OSCAL back-matter, 34 tests (refs UIAO-MEMORY.md) ([2f07a41](https://github.com/WhalerMike/uiao-core/commit/2f07a41f3857beb3ee3ea52179b390d228d3270b))
* **evidence:** address code review — improve error logging, clarify OSCAL validation comment, add round-trip test ([5d5b711](https://github.com/WhalerMike/uiao-core/commit/5d5b7110f36ce844f5f1d605913b54b12b27ca91))
* **generators:** add isort skip_file to rich_docx.py for try/except imports ([19744ca](https://github.com/WhalerMike/uiao-core/commit/19744caf9eb7cef84f35e6e0ea678d5bff8e7dd9))
* **generators:** fix indentation and remove duplicate radar chart in rich_docx.py ([ed2654c](https://github.com/WhalerMike/uiao-core/commit/ed2654cebe78b749fdb9ac42cb7f809c9dd75588))
* **generators:** fix indentation in rich_docx.py radar chart section ([e773e36](https://github.com/WhalerMike/uiao-core/commit/e773e36176f4c47f12098b0f9ee99ff71cfc8777))
* **generators:** sort imports in rich_docx.py for ruff I001 ([873356a](https://github.com/WhalerMike/uiao-core/commit/873356a252f1d1a871b8223d91cd076db84b8d86))
* **generators:** sort imports in rich_docx.py for ruff I001 ([2599395](https://github.com/WhalerMike/uiao-core/commit/259939592f820de8061f0b72d38b38f2523a4ce5))
* **generators:** sort pptx.py imports for ruff I001 ([ffa4da5](https://github.com/WhalerMike/uiao-core/commit/ffa4da5b293b8754323340e4af9b74c019c24e44))
* **generators:** suppress I001 in charts.py for matplotlib backend setup ([426e6e5](https://github.com/WhalerMike/uiao-core/commit/426e6e59d31636843b79b5ec49691debb637047a))
* **lint:** add blank line after __future__ import in charts.py (ruff I001, ADR-0004) ([11bfbfb](https://github.com/WhalerMike/uiao-core/commit/11bfbfb1ce485fdec12f0fa73323666e36e85605))
* **lint:** add blank line after __future__ import in rich_docx.py (ruff I001, ADR-0004) ([3e2dead](https://github.com/WhalerMike/uiao-core/commit/3e2deadb4bf7509a4a86a1bc8c2f5651ff7e9e86))
* **lint:** add blank line after __future__ import in ssp.py (ruff I001, ADR-0004) ([d2e511a](https://github.com/WhalerMike/uiao-core/commit/d2e511aa5799c072ec5b8a5edb7c67faf68e8678))
* **lint:** enable force-sort-within-sections for ruff isort ([8790bf3](https://github.com/WhalerMike/uiao-core/commit/8790bf3d889ae9da7e578d7afdacd3674fe3ad30))
* **lint:** fix I001 import order + move Inches default to module constant in rich_docx.py (ADR-0004) ([56647e4](https://github.com/WhalerMike/uiao-core/commit/56647e4276feace4e617856473a4d9b542659930))
* **lint:** fix I001 import order + remove unused typing.Any in trestle.py (ADR-0004) ([9914e61](https://github.com/WhalerMike/uiao-core/commit/9914e61b87507c9847cf25a2ac77271ac52452b6))
* **lint:** properly group and sort imports in trestle.py for ruff isort (ADR-0004) ([91504fa](https://github.com/WhalerMike/uiao-core/commit/91504fa0f4b4f59c8030806d431542a41c623297))
* **lint:** properly group imports in docs.py, oscal.py, rich_docx.py, ssp.py for ruff isort (ADR-0004) ([d2bf67f](https://github.com/WhalerMike/uiao-core/commit/d2bf67fb1ebc1f14ddb87d2eb9373a15a131a02f))
* **lint:** remove blank line after __future__ import in charts.py (ruff I001, ADR-0004) ([74792ad](https://github.com/WhalerMike/uiao-core/commit/74792ad60bfa38b12210e126e253f77017521ce4))
* **lint:** remove unused yaml import in oscal.py (ruff F401, ADR-0004) ([a510cda](https://github.com/WhalerMike/uiao-core/commit/a510cda6d03a0746bc0c05329efc4d3320fe175b))
* **lint:** revert force-sort-within-sections that broke other files ([9eb9b1b](https://github.com/WhalerMike/uiao-core/commit/9eb9b1be116bed9ed21e69645e45899d0d020c48))
* **lint:** sort imports alphabetically in generators/__init__.py (ruff I001, ADR-0004) ([486804c](https://github.com/WhalerMike/uiao-core/commit/486804cb67893dfc07b44d8771621d7f8e0a02a6))
* **lint:** sort imports and __all__ in utils/__init__.py (ruff I001, ADR-0004) ([5364b18](https://github.com/WhalerMike/uiao-core/commit/5364b18fb288d361bd280a4f175bf208ecb7018a))
* **models:** add CanonEntry class to fix test import (ADR-0002) ([2d121bb](https://github.com/WhalerMike/uiao-core/commit/2d121bb88c0ca5b3e8bb40ef35f75d1b5a18e9b0))
* **oscal:** load canon before data files so control_planes and matrix resolve correctly ([5306b03](https://github.com/WhalerMike/uiao-core/commit/5306b03e9a1560a1eb9961b069d462e5b1f8471b))
* **oscal:** remove by-components from CD, fix empty prop values for trestle ([dee45f8](https://github.com/WhalerMike/uiao-core/commit/dee45f86473f26d48413bcc8ee9c6dd38e424e20))
* **oscal:** update component-definition metadata for FedRAMP Rev 5 OSCAL 1.0.4 ([81eb807](https://github.com/WhalerMike/uiao-core/commit/81eb80745d188e39bfc75145bb6d676227395077))
* **poam:** update metadata for FedRAMP Rev 5 OSCAL 1.0.4 compliance ([ec11443](https://github.com/WhalerMike/uiao-core/commit/ec11443dd5a9b0cb38c81944ba58ff2ed47c2253))
* resolve all 156 ruff lint errors on copilot/add-gemini-image-generation ([3fd52f9](https://github.com/WhalerMike/uiao-core/commit/3fd52f9216536fcdcc10f80a177b9b738765f542))
* resolve PR [#45](https://github.com/WhalerMike/uiao-core/issues/45) POA&M rule engine CI failures and MEMORY compliance ([5a5e984](https://github.com/WhalerMike/uiao-core/commit/5a5e9841a76323e705973c83c3678c4999cb579b))
* sort imports for ruff I001 compliance in generators __init__ ([d437137](https://github.com/WhalerMike/uiao-core/commit/d437137ae6e2bbbc94b91cd9e32d93ae5f3268bd))
* **ssp:** add parties/roles and party-uuids for OSCAL trestle validation ([be501c8](https://github.com/WhalerMike/uiao-core/commit/be501c8624586717a2ff65c093658a7403d4156d))
* **ssp:** inject Settings, fix datetime.utcnow() -> datetime.now(timezone.utc) (ADR-0003) ([305a322](https://github.com/WhalerMike/uiao-core/commit/305a32203ac6c46d7aae9d510eec72814854fcc5))
* **ssp:** rename system-inventory to inventory-items for OSCAL 1.0.x compliance ([1131341](https://github.com/WhalerMike/uiao-core/commit/11313410e1eaefb64655cc68db94da8f6728c42e))


### Features

* add build_rich_docx to generators __init__ exports ([a5e3cef](https://github.com/WhalerMike/uiao-core/commit/a5e3cef760490c96a2eeca4c6477d6c8fc965ba9))
* Add compliance-trestle assemble script (closes [#20](https://github.com/WhalerMike/uiao-core/issues/20)) ([3cca209](https://github.com/WhalerMike/uiao-core/commit/3cca2091419345673c7745696cccd9f96e87ae2d))
* add generate-docx and generate-artifacts CLI commands ([6e2ecf1](https://github.com/WhalerMike/uiao-core/commit/6e2ecf1adc4708847257df38b90c2a4acb0fe582))
* Add rich DOCX generator with native Word styles and compliance tables ([18995c9](https://github.com/WhalerMike/uiao-core/commit/18995c98f3d953b58435e39d53740c2ed75b58bd))
* Add vendor-neutral overlay example template (closes [#22](https://github.com/WhalerMike/uiao-core/issues/22)) ([f974580](https://github.com/WhalerMike/uiao-core/commit/f974580aadecd611f28f640ce99f6026cff221e8))
* **build:** add pyproject.toml with PEP 621 metadata and src-layout (ADR-0001) ([9ff91e3](https://github.com/WhalerMike/uiao-core/commit/9ff91e34605bbe2bcf8808a786772fb11e886d70))
* **cli:** add generate-gemini command with --name and --force-visuals flags (ADR-0005) ([f20aee0](https://github.com/WhalerMike/uiao-core/commit/f20aee0739acdd8553ff4ba58c05495aad16247e))
* **cli:** add generate-pptx command for leadership briefing ([5fa7bba](https://github.com/WhalerMike/uiao-core/commit/5fa7bbafc3e030f291b03051339003c92bb29b98))
* **cli:** add generate-visuals command with --force-visuals flag (ADR-0005) ([ff10509](https://github.com/WhalerMike/uiao-core/commit/ff105092898ca4b2d9f3fad4fa2334a2ad74e6b5))
* **cli:** add validate-ssp command wiring to validate_oscal_artifacts (ADR-0004) ([2f267b4](https://github.com/WhalerMike/uiao-core/commit/2f267b40f1549d19daa56eb300b8d77a6eff7711))
* **cli:** update generate-ssp command with --canon, --data-dir, --output (ADR-0002) ([860ad45](https://github.com/WhalerMike/uiao-core/commit/860ad4520b8c213fd280eefd2b1ce2bda15b7a77))
* FedRAMP Rev 5 SSP template alignment (Sections 1-12 + Appendix A) ([c90d87a](https://github.com/WhalerMike/uiao-core/commit/c90d87af73ea7bfbd6c8da5188d383376191c75e))
* **generators:** add gemini_visuals.py for on-demand Gemini image generation (ADR-0005) ([d8a82e3](https://github.com/WhalerMike/uiao-core/commit/d8a82e351bafac464b0dc14a9abdd9ba61466883))
* **generators:** add mermaid.py for server-side Mermaid-to-PNG rendering (ADR-0005) ([c70c5ad](https://github.com/WhalerMike/uiao-core/commit/c70c5ad8eb93898af424163823a2b5a9b9641be6))
* **generators:** add pptx.py leadership briefing generator ([a90789c](https://github.com/WhalerMike/uiao-core/commit/a90789c212de0c433660a2283cbbb7bc4c77d650))
* **generators:** embed Mermaid PNGs and Gemini images in rich_docx.py ([7f7b1c2](https://github.com/WhalerMike/uiao-core/commit/7f7b1c267dc9cf018a62303a95a8d3c3649f5443))
* **generators:** export build_gemini_visuals from __init__.py (ADR-0005) ([ec1b392](https://github.com/WhalerMike/uiao-core/commit/ec1b39267fb0e49c90820c2ca80899ffb707e495))
* **generators:** export build_mermaid_visuals from __init__.py (ADR-0005) ([2770a42](https://github.com/WhalerMike/uiao-core/commit/2770a4298a65bc936f8d54ce54733efaa2880a8d))
* **generators:** export build_pptx from __init__.py ([b80811b](https://github.com/WhalerMike/uiao-core/commit/b80811b439ddd54ad19113071b162bdaf80e01b3))
* **generators:** migrate charts generator with matplotlib visuals (ADR-0003) ([a617239](https://github.com/WhalerMike/uiao-core/commit/a617239c0389121a1672f094b97c7ae18a84fff7))
* **generators:** migrate docs generator into uiao_core package (ADR-0003) ([d7084ce](https://github.com/WhalerMike/uiao-core/commit/d7084ce84e72836b533338bd1671e17d214211dc))
* **generators:** migrate OSCAL component-definition generator (ADR-0003) ([622a264](https://github.com/WhalerMike/uiao-core/commit/622a264050e270e8fe16bb4fa528ea9c50a2ee2a))
* **generators:** migrate POA&M generator into uiao_core package (ADR-0003) ([90f37b2](https://github.com/WhalerMike/uiao-core/commit/90f37b26816e77a084cecb042d013230a0636a15))
* **generators:** update __init__.py with all migrated generator exports (ADR-0003) ([3b65ba2](https://github.com/WhalerMike/uiao-core/commit/3b65ba26fda099adae0c7eed9d252affb39636b7))
* Link SSP inventory section to core-stack component data ([d0273fc](https://github.com/WhalerMike/uiao-core/commit/d0273fc5d8e0cc2b4081f3a11590a474a6bcaa20))
* Link SSP inventory section to core-stack component data ([1badd29](https://github.com/WhalerMike/uiao-core/commit/1badd29bca20b892310e5b6141a1c6a20ec69156))
* **oscal:** add by-components control linkage per plane ([b60bc42](https://github.com/WhalerMike/uiao-core/commit/b60bc42f5f99fc011468ed7c20caa11c8cd1cadf))
* **oscal:** add SSP set-parameters from parameters.yml ([cdd222f](https://github.com/WhalerMike/uiao-core/commit/cdd222ffb6f3c6d22ed77e22a9521ca78b80e5a2))
* **overlay:** add Okta Identity Cloud overlay for vendor-neutral test ([6638bec](https://github.com/WhalerMike/uiao-core/commit/6638bec0fbcfc5dcd28ac2e19bbc09dec3eaf763))
* **pkg:** add __version__.py v0.1.0 (ADR-0001) ([7dbcca3](https://github.com/WhalerMike/uiao-core/commit/7dbcca3200ef4d62504641bac37e8dd421e8627a))
* **pkg:** add cli/__init__.py (ADR-0001) ([3ba631c](https://github.com/WhalerMike/uiao-core/commit/3ba631c27788f93df7e4a99fcbf456189452bd5e))
* **pkg:** add config.py with Pydantic Settings (ADR-0001) ([41fce83](https://github.com/WhalerMike/uiao-core/commit/41fce8390175cb7cc9b0c4da25c7bc5765192cf1))
* **pkg:** add generators/__init__.py (ADR-0001) ([96a0caa](https://github.com/WhalerMike/uiao-core/commit/96a0caa757c69b7f8f243413dc0788043d963ef4))
* **pkg:** add generators/ssp.py stub with build_ssp() (ADR-0001) ([03b1f77](https://github.com/WhalerMike/uiao-core/commit/03b1f77dc5435cb9940ee0da21400c9ef4d1c02f))
* **pkg:** add models/__init__.py (ADR-0001) ([72d15ca](https://github.com/WhalerMike/uiao-core/commit/72d15ca74f52edd713171b978ee259fb0a301aa5))
* **pkg:** add py.typed PEP 561 marker (ADR-0001) ([32a069c](https://github.com/WhalerMike/uiao-core/commit/32a069c75fcc039032b1fe2cf9a826789ed58479))
* **pkg:** add Pydantic canon model with load_canon() (ADR-0001) ([0340538](https://github.com/WhalerMike/uiao-core/commit/034053893ad6c98d2a8fd5faa98b55b8287336aa))
* **pkg:** add src/uiao_core/__init__.py package init (ADR-0001) ([4773e6f](https://github.com/WhalerMike/uiao-core/commit/4773e6f1aa2e71cbdc3893d141d05bfa621966cb))
* **pkg:** add Typer CLI entry point with generate-ssp, validate, canon-check (ADR-0001) ([d95016d](https://github.com/WhalerMike/uiao-core/commit/d95016d28bdc83a3d6786575c260114eeaa57c6e))
* redesign docs/index.html for clean executive-friendly layout ([5a926f3](https://github.com/WhalerMike/uiao-core/commit/5a926f3f84190865850f5b77e4117ce799cb1db4))
* **ssp:** migrate generate_ssp.py logic into uiao_core.generators.ssp (ADR-0002) ([d891b02](https://github.com/WhalerMike/uiao-core/commit/d891b02b2897aa2fdc47d0171b95f5c123c54321))
* **trestle:** add validate_oscal_artifacts() + PlanOfActionAndMilestones support (ADR-0004) ([c47f6ce](https://github.com/WhalerMike/uiao-core/commit/c47f6ce74af8829ffbca66b6b04c5a16d6a0b6d8))
* **utils:** add utils package with __init__.py (ADR-0004) ([1442961](https://github.com/WhalerMike/uiao-core/commit/1442961fe39a261e32414e48b1a0c4bd9d33ba89))


### Reverts

* **overlay:** restore microsoft as active overlay after successful Okta test ([8b79d88](https://github.com/WhalerMike/uiao-core/commit/8b79d88512809f02585468c2a947c4b0cb39b673))



# [0.29.0](https://github.com/WhalerMike/uiao-core/compare/v0.28.1...v0.29.0) (2026-03-22)


### Features

* Add continuous monitoring hooks for Sentinel telemetry to POA&M status updates ([ba65f5a](https://github.com/WhalerMike/uiao-core/commit/ba65f5a30ef26d8f9ac4a1c0c9482f9a72181752))



## [0.28.1](https://github.com/WhalerMike/uiao-core/compare/v0.28.0...v0.28.1) (2026-03-22)


### Bug Fixes

* consolidate gh-mcp-server install and run into a single step ([b4107bb](https://github.com/WhalerMike/uiao-core/commit/b4107bb04441a4725685223055e8a820d9d5aab4))
* replace invalid github/mcp-server action with gh extension install ([d974108](https://github.com/WhalerMike/uiao-core/commit/d97410846e68a92a5be382360197833dd824fc4a))
* update secret scanning command to gh mcp run-secret-scanning ([a793ae0](https://github.com/WhalerMike/uiao-core/commit/a793ae0c7151e791db1e62f6dae336272098ad11))
* use secrets.GITHUB_TOKEN for gh mcp-server step ([a775fb8](https://github.com/WhalerMike/uiao-core/commit/a775fb82f1448d54c556fd882c8869ae2a62b92f))



# [0.28.0](https://github.com/WhalerMike/uiao-core/compare/v0.27.0...v0.28.0) (2026-03-22)


### Features

* Add vendor-neutral abstraction layer with optional technology overlays ([6ec29d3](https://github.com/WhalerMike/uiao-core/commit/6ec29d3f95075d2fa31393c6bfe417aa52a577e2))



# [0.27.0](https://github.com/WhalerMike/uiao-core/compare/v0.26.0...v0.27.0) (2026-03-22)


### Features

* Add compliance-trestle OSCAL validation and fix schema compliance ([ded4b21](https://github.com/WhalerMike/uiao-core/commit/ded4b2191059eb28426869f2124db5c8f2b95dd9))




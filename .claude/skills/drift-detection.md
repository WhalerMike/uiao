# Skill: Drift Detection (Documentation Layer)
## Purpose
Detect cross-repository drift between uiao-docs and uiao-core, plus internal metadata and formatting drift.
## When to Use
- During PR review for changes touching any documentation
- Scheduled weekly cross-repo alignment scans
- On-demand via `/drift` command
- As part of the `/publish` pipeline for articles
## Detection Modes
### 1. Cross-Repository Scan
Compare every document's provenance reference against the current state of `uiao-core` canon. Detect version divergence, missing sources, and stale provenance.
### 2. Internal Scan
Validate metadata schema compliance, naming conventions, and formatting standards within `uiao-docs`.
### 3. Format Scan
Verify articles match the Article 1 canonical formatting template (muted-blue headers, black body text, correct structure).
### 4. Diff Scan
Compare two Git refs to identify drift introduced between them.
## Cross-Repository Detection Algorithm
```
FOR each document in scan scope:
1. Parse YAML frontmatter
2. Extract provenance.source and provenance.version
3. Resolve provenance.source to uiao-core path
4. IF source not found in uiao-core → PROVENANCE_DRIFT (BLOCKING)
5. Fetch current version from uiao-core source
6. IF provenance.version != current version → CROSS_REPO_DRIFT (BLOCKING)
7. Compare content hashes if versions match but dates diverge
8. Log alignment status for dashboard metrics
```
## Article Format Detection Algorithm
```
FOR each article in articles/ directory:
1. Verify section structure: story → comic → technical → disclaimer → bio
2. Check header styling (muted-blue required)
3. Check body text color (black required)
4. Verify pseudonym: Michal Doroszewski
5. Verify tone markers (narrative, dry-humor)
6. IF any check fails → FORMAT_DRIFT (WARNING)
```
## Execution
```bash
# Full cross-repo + internal scan
python tools/drift_detector.py --path . --mode full --cross-repo ../uiao-core
# Article format scan
python tools/drift_detector.py --path articles/ --mode format --template article-1
# Internal only
python tools/drift_detector.py --path . --mode full
# Diff scan
python tools/drift_detector.py --base main --head feature/update --mode diff
```
> **SSOT Reference:** See /ssot/UIAO-SSOT.md

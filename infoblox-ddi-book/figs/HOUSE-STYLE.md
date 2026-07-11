# Figure house style (AAN-style diagrams)

All figures in this volume are **Mermaid** sources (`*.mmd`) rendered to PNG by
[`render-figs.sh`](./render-figs.sh) with the shared theme
[`mermaid-theme.json`](./mermaid-theme.json) and embedded in the docs as
`![Descriptive caption](figs/<name>.png)` (AAN convention: every figure has a
descriptive caption, not just "Figure 1").

## Rules

1. **Location:** each package/chapter keeps its sources in a sibling `figs/` folder,
   e.g. `aws-lz-automation/figs/aws-01-reference-architecture.mmd`. Volume-chapter
   figures live in `infoblox-ddi-book/figs/`.
2. **Naming:** `<area>-<nn>-<slug>.mmd` → renders to `<area>-<nn>-<slug>.png`.
3. **Embed** the PNG (not the .mmd) with a descriptive caption. Keep the .mmd in the repo.
4. **Rendering is central:** author only the `.mmd`; do NOT hand-create PNGs — they are
   produced by `render-figs.sh` (run once at the end).

## Palette — copy these `classDef` lines into every diagram, apply with `:::class`

```
classDef ibx    fill:#C00000,stroke:#7d0000,color:#fff;   %% Infoblox components (vNIOS, Grid Master, IPAM, RPZ)
classDef native fill:#548235,stroke:#38571f,color:#fff;   %% cloud-native services (Route53/Cloud DNS/OCI DNS/NSX DNS, Private Resolver)
classDef spoke  fill:#2E75B6,stroke:#1c4e7a,color:#fff;   %% workloads / spokes / VMs
classDef ctrl   fill:#7030A0,stroke:#4c2070,color:#fff;   %% control-plane: identity, pipeline, Key Vault/secrets, Portal(CSP)
classDef ext    fill:#595959,stroke:#333333,color:#fff;   %% on-prem / external / WAN
```

- Use `subgraph` for cloud boundaries (hub VNet/VPC/VCN, spoke, on-prem, SaaS boundary).
- Keep labels short; use `<br/>` for a second line. Prefer `graph TD` (top-down) for
  topology, `graph LR` for flows/sequences.
- One idea per figure. 2–4 figures per platform is plenty (e.g. reference architecture,
  discovery/IPAM sync flow, DNS resolution flow).

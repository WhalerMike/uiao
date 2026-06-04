# 🖼️ Image Inventory — TED Talk

Every image in the project, with full absolute path, description, recommended slide, and notes.
Verified by visual inspection on 2026-06-04 (organized same day). Root: `C:\Users\whale\git\uiao\docs\TedTalk\`

**Legend:** ✅ recommended for the talk · ⚠ usable with caveat · ❌ not recommended (branding/licensing/off-message)

---

## A. Hero renders (custom, on-message) — `assets\real-images\`

The strongest visuals, organized here 2026-06-04 (formerly loose in the project root with random names). They map 1:1 to the narrative.

| Rating | Full path | Description | Recommended slide |
|--------|-----------|-------------|-------------------|
| ✅ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\real-images\hero-01-mainframe-room.jpg` | Color 1970s mainframe room — rows of blue IBM cabinets, spinning tape reels, two operators at green CRT terminals. Dramatic, on-theme. | **2 & 3** (Opening Hook / Mainframe Era) |
| ✅ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\real-images\hero-02-clientserver-map.jpg` | Client-server US map — regional SQL Server / DC icons across 12 labeled regions, arrows to a central SSOT stack. Minor label typos. | **4** (Act 1 — Decentralization) |
| ✅ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\real-images\hero-03-security-broken-sessions.jpg` | Security stack — frustrated users on the left; Firewall 1/2/3 → F5 Load Balancers → IDS/IPS in series; red "Broken Sessions / High Latency" callouts. | **5** (Act 2 — Security) |
| ✅ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\real-images\hero-04-future-sdwan-ssot.jpg` | Future state — central SD-WAN edge with direct green arrows to Azure & AWS; central "Single Source of Truth" DB; regional + field offices below. | **8, 10, 11** (Way Forward / New Architecture / CTA) |

---

## B. `assets\mainframe\`

| Rating | Full path | Description | Recommended slide | Notes |
|--------|-----------|-------------|-------------------|-------|
| ⚠ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\mainframe\mainframe-era-ibm-room.jpg` | B&W 1970s IBM tape-drive room, two operators (one in a suit). | 3 (B-roll) | **Visible Alamy watermark** — do not use in final render; licensing risk. |
| ⚠ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\mainframe\mainframe-era-operator-console.jpg` | B&W woman operator at a console with line printer, 1970s. | 3 (B-roll) | Stock photo; confirm licensing before public use. |

## C. `assets\client-server\`

| Rating | Full path | Description | Recommended slide | Notes |
|--------|-----------|-------------|-------------------|-------|
| ⚠ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\client-server\client-server-1990s-pc-setup.jpg` | Amateur snapshot of a vintage beige PC + CRT + Mac keyboard on a shelf. | 4 (texture/B-roll) | Low production quality; `hero-02-clientserver-map.jpg` is the better Act 1 hero. |

## D. `assets\security\`

| Rating | Full path | Description | Recommended slide | Notes |
|--------|-----------|-------------|-------------------|-------|
| ❌ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\security\security-defense-in-depth-stack.png` | "Cybersecurity Value Chain" marketing graphic — grid of vendor logos (Okta, Palo Alto, CrowdStrike, etc.). | — | Off-message + third-party logos. Use `hero-03-security-broken-sessions.jpg` instead. |
| ❌ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\security\security-layered-firewalls.png` | Juniper "DC WAN Gateway / Security Director Cloud" reference architecture (vSRX/cSRX), "Juniper Threat Labs" branded. | — | Vendor-branded. Use `hero-03-security-broken-sessions.jpg` instead. |

## E. `assets\cloud-chaos\`

| Rating | Full path | Description | Recommended slide | Notes |
|--------|-----------|-------------|-------------------|-------|
| ✅ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\cloud-chaos\cloud-collision-chaos-3d.jpg` | "Regional Data Center Collapse" — cracked black data-center cloud surrounded by Azure/AWS/M365/Cloud icons with red warnings; "Lost single source of truth and provenance". | **6** (Act 3 — Cloud Collision) | Strong & on-message. Minor typo "Clous". |
| ✅ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\cloud-chaos\cloud-collision-chaos-map.jpg` | US map "Lost Provenance / Inconsistency" — X'd-out regional databases, red arrows from Azure/AWS/M365 clouds. | **7** (The Breaking Point) | Strong & on-message. |
| ✅ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\cloud-chaos\cloud-collision-chaos-map-alt.jpg` | Alternate US-map render — regional/field-office databases with warning icons, Azure/AWS/M365 clouds, blue/red arrows; "Lost Provenance / InConsistency". | **6 or 7** (alternate) | On-message. Minor typo "InConsistency". |

## F. `assets\future-state\`

| Rating | Full path | Description | Recommended slide | Notes |
|--------|-----------|-------------|-------------------|-------|
| ⚠ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\future-state\future-state-sdwan-architecture.png` | Clean teal/magenta generic "SD-WAN Architecture" — branches → data center → Internet cloud (Salesforce/O365/AWS/Azure logos). | 9 (Four Pillars, secondary) | Generic + third-party logos; fine as a supporting diagram. |
| ⚠ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\future-state\future-state-sdwan-mesh-1.jpg` | "SD-WAN Architecture Explained", orange-on-black, branches → data center; MPLS/Cellular/Broadband. | (alt) | **EdgeDC watermark** — branding risk. |
| ⚠ | `C:\Users\whale\git\uiao\docs\TedTalk\assets\future-state\future-state-sdwan-mesh-2.jpg` | "SD-WAN Architecture Explained", red/white, branches → data center; cloud logos. | (alt) | **Fortinet logo** — branding risk. |

---

## Reference docs (not images)

- `C:\Users\whale\git\uiao\docs\TedTalk\assets\real-historical-images-reference.md` — notes on sourcing real historical photos.
- `C:\Users\whale\git\uiao\docs\TedTalk\diagrams\diagram-generation-prompts.md` — the 5 image-generation prompts used.

## Summary

- **15 image files** total: 4 hero renders (`real-images\`) + 3 cloud-chaos renders + 8 in the other `assets\` subfolders.
- **Build the deck on:** the 4 hero renders (§A) + the 3 cloud-chaos renders (§E). All clean and on-message.
- **Avoid in the final render:** the 4 vendor-branded/watermarked images (§D, §F-mesh) and the Alamy-watermarked mainframe photo (§B), unless licensing is cleared.

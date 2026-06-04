# 🎙️ Speaker Notes — TED Talk

**The Hidden Cost of Progress: How We Lost Truth in Our Systems — And How to Get It Back**

Tied to `script/ted-talk-full-script.md`. Tone: conversational, authoritative, hopeful.
**Delivery rule:** pause 4–6 seconds after each Act so the visual lands.
**Target:** 18–22 minutes.

Timeline bar (1940s → 2026) at the bottom; advance the highlight as you move through the eras.

---

### Slide 1 — Title · `0:00–0:15` (~15 s)
- **On screen:** Title + subtitle, your name + agency context. TED-style dark background (optional faded `assets/real-images/hero-04-future-sdwan-ssot.jpg`).
- **Say:** Let the title sit. Step on stage, breathe, make eye contact before the first line.
- **Cue:** No narration over the title beyond a beat of silence.

### Slide 2 — Opening Hook · `0:15–1:00` (~45 s)
- **On screen:** `assets/real-images/hero-01-mainframe-room.jpg` (color mainframe room).
- **Say:** *"Good morning. Imagine a world where we don't just hope the data is correct — we know it is."*
- **Note:** Slow down on "**know**." This is the thesis word; the whole talk pays it off.

### Slide 3 — Mainframe Era (1940s–1990s) · `1:00–2:00` (~60 s)
- **On screen:** `assets/real-images/hero-01-mainframe-room.jpg`; optional B&W operator B-roll (`assets/mainframe/mainframe-era-operator-console.jpg`) — *only if licensing cleared*.
- **Say:** One central computer, dumb green-screen terminals, **one** definitive answer. "How many people received benefits this month?" — no ambiguity. The system *knew* who was alive, who was eligible, what was true.
- **Cue:** Land hard on "**one** definitive answer." Pause. Advance timeline highlight to ~1990.

### Slide 4 — Act 1: The Great Decentralization · `2:00–6:00` (~4 min)
- **On screen:** `assets/real-images/hero-02-clientserver-map.jpg` (client-server US map, regional SQL servers → central SSOT).
- **Say:** Late 1980s — DEC VAX, Wang, PCs, the client-server revolution push intelligence to the edges. Regional offices get their own SQL Servers, their own AD child domains (SF, PH, BO, CH, BI…), their own apps. *Genuinely liberating* — decision-making spread beyond Washington.
- **Turn:** *"But we paid a hidden price."* Twelve regions → twelve versions of reality: different schemas, rules, interpretations. **We lost the single source of truth.**
- **Cue:** Beat before "hidden price." Pause 4–6 s on the map after the turn.

### Slide 5 — Act 2: When Security Ate the Architecture · `6:00–10:00` (~4 min)
- **On screen:** `assets/real-images/hero-03-security-broken-sessions.jpg` (Firewalls → F5 → IDS/IPS, frustrated users, "Broken Sessions / High Latency").
- **Say:** ~2010, two forces collide — compute consolidates into fewer regional data centers, and cybersecurity becomes the overriding priority. Defense-in-depth: F5 proxies, IPS, stacked firewalls, multiple NAT sessions — *designed to break and inspect sessions*.
- **Key:** Leadership assumed faster MPLS meant "local." But **latency is physics.** Sessions broke. Kerberos tickets failed. Group Policy slowed. Most importantly — **provenance disappeared.**
- **Cue:** "Latency is physics" is a quotable line — say it cleanly, then pause. Gesture to the angry users.

### Slide 6 — Act 3: The Cloud Collision · `10:00–13:00` (~3 min)
- **On screen:** `cloud-collision-chaos-3d.jpg` ("Regional Data Center Collapse").
- **Say:** M365, Azure, AWS arrive. Compute moves to the cloud — but our regional AD forest, OU structure, and session assumptions stay rooted in the early 2000s. Field offices reach across thousands of miles, across cloud boundaries, using tools built for machines in the same room. Regional variation that once meant agility becomes a **hiding place for discrepancies.**

### Slide 7 — The Breaking Point (2025–2026) · `13:00–14:00` (~60 s)
- **On screen:** `cloud-collision-chaos-map.jpg` ("Lost Provenance / Inconsistency").
- **Say:** The real-world consequences arrive — benefits paid to deceased individuals, duplicate payments, fraud hidden in fragmented data, eroded public trust.
- **Cue:** Drop to your most serious register. Land: *"We don't know what's true anymore."* Long pause.

### Slide 8 — Act 4: The Way Forward · `14:00–16:00` (~2 min)
- **On screen:** `assets/real-images/hero-04-future-sdwan-ssot.jpg` (SD-WAN edge → Azure/AWS, central SSOT).
- **Say:** *"We cannot patch our way out of this. We must rebuild the foundation."* Shift energy from diagnosis to hope.
- **Cue:** "We must rebuild" is a highlight phrase — emphasize and let the future-state image breathe.

### Slide 9 — The Four Pillars · `16:00–18:30` (~2.5 min)
- **On screen:** Four-pillar text build; secondary `future-state-sdwan-architecture.png`.
- **Say — reveal one at a time:**
  1. **Restore Single Source of Truth** — cryptographically verifiable, auditable, authoritative across the federal enterprise.
  2. **Application-Aware Networking & Cybersecurity** — Cisco Catalyst SD-WAN, Microsoft INR; understand *application intent*, not just packets.
  3. **Token-Based Identity with OrgPath** — Kerberos → Entra ID + OrgPath governance; authorization regardless of physical location.
  4. **Intelligent SD-WAN Mesh** — every field/area/regional office gets an edge device with direct, secure on-ramps to cloud + consolidated data centers.
- **Cue:** Emphasize "**OrgPath**" and "**Application-Aware**" (highlight phrases). One pillar per click.

### Slide 10 — The New Architecture · `18:30–19:30` (~60 s)
- **On screen:** `assets/real-images/hero-04-future-sdwan-ssot.jpg` full screen.
- **Say:** Tie it together — *"This is not just technical modernization. This is restoring the soul of our systems — the ability to know what is true."* OrgPath is the governance primitive that holds it.

### Slide 11 — Call to Action · `19:30–20:30` (~60 s)
- **On screen:** `assets/real-images/hero-04-future-sdwan-ssot.jpg` faded / clean future-state.
- **Say:** *"Every stage of this journey made sense in isolation. Together, they cost us truth."* In 2026, with fraud detection and public trust on the line, we have both the responsibility and the tools. *"Let's rebuild systems that don't just act — but know."*
- **Cue:** Callback to the opening "know." Slow, deliberate.

### Slide 12 — Thank You + Q&A · `20:30–end`
- **On screen:** Title background; contact / GitHub (uiao); final hopeful image.
- **Say:** *"Thank you."* Hold eye contact. Open the floor.

---

## Timing summary

| Segment | Slides | Window |
|---------|--------|--------|
| Opening + Mainframe | 1–3 | 0:00–2:00 |
| Act 1 Decentralization | 4 | 2:00–6:00 |
| Act 2 Security | 5 | 6:00–10:00 |
| Act 3 Cloud Collision | 6 | 10:00–13:00 |
| Breaking Point | 7 | 13:00–14:00 |
| Act 4 + Four Pillars | 8–9 | 14:00–18:30 |
| New Architecture + CTA | 10–11 | 18:30–20:30 |
| Thank You + Q&A | 12 | 20:30–end |

**Total spoken:** ~20:30, leaving headroom inside the 18–22 min target. If running long, tighten Act 1 (Slide 4) and the Four Pillars (Slide 9) first.

## Highlight phrases (emphasize / on-screen accent)
*Single Source of Truth* · *latency is physics* · *provenance disappeared* · *We must rebuild* · *Application-Aware* · *OrgPath* · *don't just act — but know*

# TED Talk Script: "The Hidden Cost of Progress: How We Lost Truth in Our Systems — And How to Get It Back"

**Target Duration:** 18–22 minutes
**Tone:** Conversational, authoritative, hopeful — like a seasoned federal IT leader sharing hard-won wisdom.
**Delivery Tip:** Pause after each major era for the visuals to land.

---

**Opening (0:00 – 2:00)**
Good morning. Imagine a world where we don’t just *hope* the data is correct — we *know* it is.

In the mainframe era of the 1940s through the 1990s, federal agencies operated with one massive central computer holding the single source of truth. Users had dumb terminals — green screens that sent keystrokes and received answers. When you asked “how many people received benefits this month?” there was **one** definitive answer. No ambiguity. No hidden discrepancies. The system *knew* who was alive, who was eligible, and what was true.

**Act 1: The Great Decentralization (2:00 – 6:00)**
By the late 1980s, the world rebelled against that rigidity. Minicomputers like DEC VAX and Wang, followed by PCs and the client-server revolution, spread intelligence to the edges.

Regional offices got their own SQL Servers, their own Active Directory child domains (SF, PH, BO, CH, BI, etc.), their own applications tailored to how their states worked. Email and instant messaging connected us across the country.

It was genuinely liberating. Programming and decision-making spread beyond Washington. Local teams could finally solve problems the way their states needed.

But we paid a hidden price: we lost the single source of truth. Twelve regions created twelve different versions of reality — different schemas, different business rules, different interpretations of the same policies.

**Act 2: When Security Ate the Architecture (6:00 – 10:00)**
Around 2010, two powerful forces collided: compute began consolidating into fewer regional data centers, and cybersecurity became the overriding priority.

Defense-in-depth brought layers of F5 load balancers acting as proxies, intrusion prevention systems, stacked firewalls, and multiple NAT sessions. These tools were designed to break and inspect sessions.

At the same time, leadership assumed that faster MPLS bandwidth meant the network was still “local.” But latency is physics. Sessions started breaking. Kerberos tickets failed. Group Policy processing slowed. Most importantly — **provenance disappeared**. We could no longer clearly trace who did what and why.

**Act 3: The Cloud Collision (10:00 – 14:00)**
Then M365, Azure, and AWS arrived. Compute moved to the cloud, but our regional Active Directory forest, OU structure, and session-based assumptions remained rooted in the early 2000s.

Field offices now reached across hundreds or thousands of miles — and across cloud boundaries — using tools designed for machines in the same room. Regional variations that once enabled agility became hiding places for discrepancies.

In 2025–2026, we began seeing the real-world consequences: benefits paid to deceased individuals, duplicate payments, fraud hidden in fragmented data, and eroded public trust.

**Act 4: The Way Forward (14:00 – 20:00)**
We cannot patch our way out of this. We must rebuild the foundation.

The solution rests on four pillars:

1. **Restore Single Source of Truth** — Cryptographically verifiable, auditable, and authoritative across the federal enterprise.
2. **Application-Aware Networking and Cybersecurity** — Tools like Cisco Catalyst SD-WAN and Microsoft INR that understand *application intent*, not just packets.
3. **Token-Based Identity with OrgPath** — Move from Kerberos to Entra ID + OrgPath governance that clearly defines authorization regardless of physical location.
4. **Intelligent Mesh Network** — Every field office, area office, and regional office gets an SD-WAN edge device with direct, secure on-ramps to the cloud and consolidated data centers.

This is not just technical modernization. This is restoring the soul of our systems — the ability to *know what is true*.

**Closing (20:00 – end)**
Every stage of this journey made sense in isolation. Together, they cost us truth.

In 2026, with fraud detection and public trust on the line, we have both the responsibility and the tools to fix it. Let’s rebuild systems that don’t just act — but *know*.

Thank you.

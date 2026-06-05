# TED Talk Script: "The Hidden Cost of Progress: How We Lost Truth in Our Systems — And How to Get It Back"

**Target Duration:** 18–22 minutes
**Tone:** Conversational, authoritative, hopeful — like a seasoned federal IT leader sharing hard-won wisdom.
**Delivery Tip:** Pause after each major era for the visuals to land.

---

**Opening (0:00 – 2:00)**
Good morning. Imagine a world where we don’t just *hope* the data is correct — we *know* it is.

In the mainframe era of the 1940s through the 1990s, federal agencies operated with one massive central computer holding the single source of truth. Users had dumb terminals — green screens that sent keystrokes and received answers. When you asked “how many people received benefits this month?” there was **one** definitive answer. No ambiguity. No hidden discrepancies. The system *knew* who was alive, who was eligible, and what was true.

Security was implicit. If you weren’t sitting at a terminal wired into that room, you had nothing. The network *was* the perimeter. It was slow and inflexible — but it was true.

**Act 1: The Great Decentralization (2:00 – 6:00)**
By the late 1980s, the world rebelled against that rigidity. Minicomputers like DEC VAX and Wang, followed by PCs and the client-server revolution, spread intelligence to the edges.

Regional offices got their own SQL Servers, their own Active Directory child domains (SF, PH, BO, CH, BI, etc.), their own applications tailored to how their states worked. Email and instant messaging connected us across the country.

It was genuinely liberating. Programming and decision-making spread beyond Washington. Local teams could finally solve problems the way their states needed.

But we paid a hidden price: we lost the single source of truth. Twelve regions created twelve different versions of reality — different schemas, different business rules, different interpretations of the same policies.

And nobody replaced the single source of truth the mainframe had given us. That was the original sin — the moment the architecture began to drift.

**Act 2: When Security Ate the Architecture (6:00 – 10:00)**
Around 2010, two powerful forces collided: compute began consolidating from twelve regional data centers toward four — California, two in Nebraska, and Virginia as the anchor — and cybersecurity became the overriding priority.

Defense-in-depth brought layers of F5 load balancers acting as proxies, intrusion prevention systems, stacked firewalls, and multiple NAT sessions. These tools were designed to break and inspect sessions.

At the same time, leadership assumed that faster MPLS bandwidth meant the network was still “local.” But latency is physics. Portland to Virginia is thousands of miles — thousands of milliseconds of round trip — and Active Directory expects under five. Sessions started breaking. Kerberos tickets failed. Group Policy processing slowed.

Most importantly — **provenance disappeared**. No one could say with certainty: *this came from this authorized source, processed by this authorized system.* We had secured the sessions in a way that broke them — adding complexity without adding truth.

**Act 3: The Cloud Collision (10:00 – 14:00)**
Then M365, Azure, and AWS arrived. Compute moved to the cloud, but our regional Active Directory forest, OU structure, and session-based assumptions remained rooted in the early 2000s.

A field office in Portland now authenticates to a domain controller in Virginia, queries a database in Azure, and runs an application in AWS — the session-based contract shattered across three different cloud vendors, using tools designed for machines in the same room. And the regional variations from Act 1 had calcified into institutional silos no one could see into.

In 2025–2026, we began seeing the real-world consequences: benefits paid to deceased individuals, duplicate payments, fraud hidden in fragmented data, and eroded public trust.

**Act 4: The Way Forward (14:00 – 20:00)**
We cannot patch our way out of this. We must rebuild the foundation.

The solution rests on four pillars:

1. **Restore Single Source of Truth** — Collapse the twelve regional SQL silos into one unified, auditable model. Not erasing regional autonomy — making it transparent and traceable back to policy. Cryptographically verifiable and authoritative across the federal enterprise.
2. **Application-Aware Networking and Cybersecurity** — Tools like Cisco Catalyst SD-WAN and Microsoft INR that understand *application intent*, not just packets. Every request leaves a cryptographically signed trail — a full chain of custody, so fraud has nowhere to hide.
3. **Token-Based Identity with OrgPath** — Kerberos assumed the client and server were in the same room; tokens assume they're strangers on the Internet. Move from Kerberos to Entra ID, with every token carrying an OrgPath claim that defines authorization regardless of physical location.
4. **Intelligent Mesh Network** — Stop routing everything through regional data centers that are now empty. Every field office, area office, and regional office gets an SD-WAN edge device with direct, secure on-ramps to the cloud and consolidated data centers.

This is not just technical modernization. This is restoring the soul of our systems — the ability to *know what is true*.

**Closing (20:00 – end)**
Every stage of this journey made sense in isolation. Together, they cost us truth.

In 2026, with fraud detection and public trust on the line, we have both the responsibility and the tools to fix it. Let’s rebuild systems that don’t just act — but *know*.

Thank you.

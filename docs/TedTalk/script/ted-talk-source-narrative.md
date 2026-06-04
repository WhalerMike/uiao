# TED Talk — Full Source Narrative (background / long-form)

> **Purpose.** This is the rich, long-form narrative the talk was distilled from. It runs
> well past the 18–22 minute stage target and is **not** the spoken script — it is the
> reference that gives the talk its depth, specifics, and argument.
>
> **Spoken script:** [`ted-talk-full-script.md`](ted-talk-full-script.md) (the ~20-minute condensation).
> **Per-slide cues:** [`speaker-notes.md`](speaker-notes.md).
>
> Source: working conversation, 2026-06-04. Chat scaffolding removed; prose preserved.

---

## The Mainframe Era (1940s–1990s)

Your agency's entire operation ran on mainframes. IBM systems, mostly. One massive computer in a locked room. Everything happened there. All the data. All the logic. All the state.

Users didn't have computers. They had terminals. Green screens. Keyboards. A terminal was a dumb device — it sent keystrokes to the mainframe and received screen refreshes back. Text-based. Synchronous. Simple.

The model was brutally elegant: one source of truth. The mainframe was the truth. When you asked "how many people received benefits this month," there was one answer, and it came from one place. No ambiguity. No regional variations. No hidden discrepancies.

Security was implicit. If you weren't sitting at a terminal physically connected to that mainframe room, you couldn't access anything. The network was the security perimeter. Control physical access, you controlled everything.

And crucially: the intelligence gatekeepers were in Washington. The mainframe programmers. The database administrators. If you wanted a new report, you waited. If you wanted to customize a process for your state, you couldn't. The mainframe was the mainframe.

This worked for forty years. It was slow. It was inflexible. But it was true.

---

## Act 1: The Great Decentralization (Late 1980s–2000)

By the late 1980s, the entire world was rejecting that model. Not because mainframes stopped working. Because the economics broke and the technology changed.

Minicomputers — DEC VAX, Wang — had already proven you didn't need one godlike machine. Departments could own their compute. Programmers could own their tools. Intelligence spread.

Then PCs arrived. Networks got faster. The vision became irresistible: put a SQL Server in every region. Put applications in every office. Spread programming expertise to the edges. Let local teams build solutions for their local problems — because they understood those problems better than Washington ever could.

For your agency, this was revolutionary. Twelve regional offices could each have their own database administrators, their own application developers, their own tools tailored to how their states and territories worked. The interaction with state governments in California was different from Massachusetts — so why force them into the same mold?

Email arrived. Then instant messaging. Suddenly you could communicate asynchronously across the organization. Regional teams could coordinate without waiting for Washington's approval.

It was a genuinely good idea. The decentralization of intelligence, expertise, and decision-making to the places where the work actually happened.

But here's where the architecture broke.

With the mainframe, there was one source of truth. One database. One version of the record. The moment you put SQL Servers in twelve regions, you lost that. Now California had its own database. Massachusetts had its own. New York had its own. And they didn't always talk to each other. Or they did, but inconsistently. Regional systems evolved their own schemas, their own business logic, their own definitions of what a "benefit" even meant.

The vision of distributed intelligence was real and good. But it came at a cost: distributed truth. And nobody replaced the single source of truth that the mainframe had given you.

That became the original sin — the moment the architecture started to drift toward fraud.

---

## Act 2: When Security Ate the Architecture (2010–2020)

Around 2010, your agency started consolidating compute. Not radically — but intentionally. The twelve regional data centers stayed, but the thinking shifted: consolidate to four. California. Two in Nebraska. Virginia as the anchor.

Simultaneously — and this is the critical inflection — cybersecurity became a board-level imperative. Not just "have a firewall." Defense-in-depth. Layered security. Multiple inspection points.

But here's the problem: the tools chosen to enforce security were fundamentally incompatible with the session-based client-server model your entire infrastructure depended on.

F5 load balancers became inline proxies. Intrusion detection and prevention systems were inserted into the traffic path. Multiple NAT sessions. Firewalls stacked on firewalls. Every packet from a field office to a regional data center had to traverse security devices designed to break sessions — to inspect, decrypt, re-encrypt, verify, block.

Active Directory Kerberos tickets have a lifespan. They're bound to a specific session. When a packet gets intercepted, decrypted, re-encrypted, and NATted three times, the session breaks. The Kerberos ticket becomes invalid. The application loses trust in where the request came from.

Meanwhile, bandwidth exploded. Gigabits across the country. Leadership made a fateful assumption: high bandwidth equals low latency. If we can push a gigabit per second, the network is basically local.

That's the lie.

Latency is physics. Portland to Virginia is thousands of miles. That's thousands of milliseconds of round-trip delay. Active Directory expects sub-five-millisecond latency. When you add session-breaking security appliances on top of that distance, sessions crater. Logon times creep up. GPO processing stalls.

But the agency didn't rearchitect. They just accepted the latency and kept the regional AD forest as-is. And they didn't rethink authentication — they added more proxies. Service accounts. Cached credentials. Trust relationships that bypassed the security stack because the security stack was incompatible with the authentication model.

And here's the deeper problem: with every security layer added, you lost visibility into what the application was actually doing. The security tools worked at the network layer, the session layer — they could see that a packet was encrypted, that it came from an IP address, that it matched a rule. But they couldn't see: Is this request legitimate? Does this user have permission to access this data? Is the data being accessed the same data that was supposed to be accessed?

Nobody said: "We're securing sessions in a way that breaks them. We're adding complexity without adding truth. We're layering proxies without adding Application-Aware intelligence."

Instead, cybersecurity became the priority. Performance became secondary. Compliance became the metric. "Are we passing the security scan?" Yes. "Are applications performing?" That's a separate conversation. "Can we still verify that the data is correct?" ...that question wasn't even on the table.

And you lost something else: you lost the ability to trace where data came from. You lost provenance. When a claim gets paid, when a benefit gets issued, when a record gets created — nobody can definitively say "This came from this authorized source, processed by this authorized system, verified by this authorized entity." The security layers broke sessions. They didn't restore truth.

---

## Act 3: The Breaking Point (2020–2026)

Then M365 happened. Microsoft forced the issue.

Your agency couldn't stay on-premise Exchange forever. Cloud was inevitable. So you migrated to Microsoft 365 — Exchange Online, Teams, SharePoint. Suddenly your email and collaboration were in Azure, managed by Microsoft, unreachable by your session-based authentication model.

But the agency didn't stop there. Application after application started moving to the cloud. SQL databases moved from regional data centers to Azure. Workloads moved to AWS. The compute scattered.

And here's the critical moment: the agency still had twelve regional Active Directory domains. Still had the OU tree structure designed for when compute lived regionally. Still had MPLS circuits connecting field offices to regional DCs that were increasingly just logical boundaries, not physical anchors.

Now a field office in Portland authenticates to a regional DC that's physically in Virginia. A SQL query goes to a database in Azure. An application runs in AWS. The session-based contract — the assumption that client and server are talking synchronously over a trusted link — was shattered across three continents and three different cloud vendors.

And the security stack? Still there. Still breaking sessions. Still working at the network layer, not the application layer. Still unable to verify provenance or trace where data actually came from.

Meanwhile, the regional variations that started in Act 1 had calcified into institutional silos. California's benefit calculation was different from Massachusetts's. Regional databases had evolved incompatible schemas. Local applications had local business rules. And because single source of truth had never been restored, nobody could see the discrepancies.

Then, in 2025 and into 2026, the fraud started surfacing. Dead people collecting benefits. Duplicate payments across states. Tax evasion hidden in regional variations. The very fragmentation that had made the system agile in 1995 had become the hiding place for systemic corruption.

And your agency — and the federal government — realized: we don't know what's true anymore.

The infrastructure you built to distribute intelligence and autonomy had become an infrastructure that obscured truth. The security you added to protect data had become security that hid provenance. The cloud migration you undertook to modernize had scattered compute across vendors and regions without a unifying governance model.

You had a system that could do things, but couldn't verify things. And in 2026, with electoral integrity and fraud detection as national imperatives — with dead people voting — that's unacceptable.

---

## Act 4: The Way Forward — Application-Aware Modernization

You can't fix this by patching the old model. You can't bolt Zero Trust onto a Kerberos-in-MPLS architecture. You can't add more proxies. You can't hope compliance scanning will restore integrity.

The only way forward is to rebuild the foundation around these principles:

### First: Restore Single Source of Truth

Every data type the federal government manages — who is alive, who is eligible, who owes taxes, who voted — must have one authoritative source. Not twelve regional databases with eventual consistency. Not caches that drift. One source. Cryptographically verifiable. Auditable. You must know where every piece of data came from, who accessed it, when, and why.

For your agency, that means collapsing the twelve regional SQL silos into a unified data model. Not erasing regional autonomy — but making it transparent. If California's benefit calculation is different from Massachusetts's, that difference is documented, auditable, and traceable back to policy, not hidden in schema variations.

OrgPath is how you enforce that. OrgPath is the governance primitive that makes single source of truth possible in a cloud-native world. Every user, every device, every service gets an OrgPath that describes what they're authorized to do and what data they're authorized to touch. Not "which region's DC are you closest to?" But "what is your actual authorization scope?" That becomes the basis for every access decision.

### Second: Application-Aware Networking and Application-Aware Cybersecurity

You can't enforce security at the network layer anymore. The network is the Internet now. Packets don't stay in a perimeter. Threats don't come from outside the firewall — they come from compromised devices, from supply-chain attacks, from insider threats, from nation-states.

The only way to know if a transaction is legitimate is to understand what the application is doing. Is this user authorized to access this data? Is the data being accessed the same data that policy says they should access? Is the request coming from a device in compliance? Is the request coming from a geographical location that makes sense?

That's Application-Aware Networking. That's Application-Aware Cybersecurity. Not proxies. Intelligence. Cisco Catalyst SD-WAN, Microsoft INR for cloud on-ramps, Azure Policy for application-level enforcement — these tools understand intent, not just packets.

And critically: they preserve provenance. Every request leaves a cryptographically signed trail. You can trace why a decision was made. You can prove who authorized what and when. You can detect fraud because you can see the full chain of custody for every transaction.

### Third: Move from Session-Based to Token-Based Identity

Active Directory Kerberos assumes clients and servers are in the same room. Tokens assume they're strangers on the Internet.

A token is a cryptographically signed assertion: "This user is who they claim to be. This device is compliant. This request is authorized. Timestamp: [now]. Signature: [cryptographic proof]." The server doesn't need to trust the network. Doesn't need to talk back to a domain controller. It just needs to verify the signature.

Entra ID, Conditional Access, device compliance policies — these are the token-based equivalents of what AD used to do. But they only work if you've fixed the underlying governance model. If you don't know what a user is actually authorized to do — if that's still encoded in twelve regional OU trees — tokens won't help you. You'll just be signing broken authorizations.

That's where OrgPath comes in. OrgPath is the canonical definition of who is authorized to do what. Every token includes an OrgPath claim. Every Application-Aware security decision checks that claim. Every data access is logged against that claim. You have an auditable trail.

### Fourth: SD-WAN as the Network Spine

You can't keep routing all traffic through regional data centers that are now empty. You can't keep MPLS circuits that assume compute lives regionally when compute now lives in the cloud.

> **Note:** the source conversation was truncated here (mid-sentence at "You can't keep MPLS circuits that assume compute…"). The spoken script's Pillar 4 — every field, area, and regional office getting an SD-WAN edge with direct, secure on-ramps to the cloud and consolidated data centers — is the completed form of this principle. See [`ted-talk-full-script.md`](ted-talk-full-script.md).

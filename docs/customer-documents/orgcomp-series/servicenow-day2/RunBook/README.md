# Live Validation RunBook — what is in this directory

The three validation tracks that close the gaps code reading and the mock ATF
harness cannot: real platform behaviour, a real domain controller, a real
tenant. Everything else in this kit is proven against fixture data.

| File | What it is |
|---|---|
| `00-cover.md` | Cover sheet and executive summary — why these tracks exist, what each one closes, and what it still does not prove. Read first. |
| `day2kit-live-validation-runbook.md` | The RunBook itself: all three tracks, step by step. |
| `Day2Kit-Live-Validation-RunBook.docx` | The same RunBook as Word, for reviewers who do not read Markdown. |

The AD lab provisioning script lives at **`../lab/New-Day2AdLab.ps1`**, not
here. Earlier builds shipped a byte-identical duplicate in this directory; it
was removed so there is one canonical copy to patch and review.

## How this relates to the kit's other validation docs

The two `CURRENT-STATE-*-VALIDATION.md` documents at the kit root are the
same two tracks in the kit's own reading order — they are what
`CURRENT-STATE-START-HERE.md` §6 points at, and what
`CURRENT-STATE-PILOT-ROLLOUT.md` §0 requires before a pilot may start:

- `../CURRENT-STATE-PDI-VALIDATION.md` — Track 1, ServiceNow PDI.
- `../CURRENT-STATE-AD-LAB-VALIDATION.md` — Track 2, Active Directory lab.

This RunBook additionally carries **Track 3 (Microsoft 365 tenant)**, which
exercises the SER-4 Graph scope read in the sibling `x_fed_compliance` scoped
app. That app is not shipped in this kit, so Track 3 does not apply if you are
running only Tracks 1 and 2.

Track order matters: PDI first (cheapest, no infrastructure), then the AD lab,
then the tenant.

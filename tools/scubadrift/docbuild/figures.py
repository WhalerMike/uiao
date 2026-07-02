"""Author the five ScubaDrift blueprint SVG diagrams (ADR-093 house style).

Blueprint register: 1280x720 canvas, white background first child, house
palette, literal correctly-spelled <text>, plain SVG primitives only (so
cairosvg rasterizes deterministically — no <foreignObject>). Naming uses the
`-diagram-NN-` infix reserved for blueprints.
"""

from __future__ import annotations

# House palette (src/uiao/canon/svg-style/palette.json)
NAVY = "#0D1B2E"
NAVY_MID = "#1E3A66"
TEAL = "#1E8C8C"
TEAL_TINT = "#D7F2EE"
AMBER = "#D4A017"
AMBER_TINT = "#FBEED2"
RED = "#C0392B"
RED_TINT = "#F7E2DE"
MID_BLUE = "#2E75B6"
ICE = "#EAF1FB"
GREY = "#5A5A5A"
MUTED = "#6B7A8D"
BODY = "#33414F"
HAIRLINE = "#E3E8EF"
WHITE = "#FFFFFF"

HDR = "Georgia, 'Times New Roman', serif"
SANS = "Arial, 'Helvetica Neue', Helvetica, sans-serif"
MONO = "Consolas, 'DejaVu Sans Mono', monospace"

W, H = 1280, 720


def _open(title: str, subtitle: str = "") -> list[str]:
    s = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="{SANS}">',
        f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
        f'<text x="{W // 2}" y="58" text-anchor="middle" font-family="{HDR}" '
        f'font-size="32" font-weight="bold" fill="{NAVY}">{title}</text>',
        f'<line x1="120" y1="78" x2="{W - 120}" y2="78" stroke="{TEAL}" stroke-width="2"/>',
    ]
    if subtitle:
        s.append(f'<text x="{W // 2}" y="102" text-anchor="middle" font-size="18" fill="{MUTED}">{subtitle}</text>')
    return s


def _caption(text: str) -> str:
    return f'<text x="{W // 2}" y="694" text-anchor="middle" font-size="17" fill="{MUTED}">{text}</text>'


def box(x, y, w, h, fill, stroke, lines, *, tcolor=WHITE, title_size=19, body_size=15, rx=10, mono=False):
    """A rounded rectangle with a bold first line and centered body lines."""
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    ]
    cx = x + w // 2
    n = len(lines)
    # vertical centering
    line_h = body_size + 9
    total = title_size + (n - 1) * line_h if n else 0
    ty = y + (h - total) // 2 + title_size - 4
    fam = MONO if mono else SANS
    for i, ln in enumerate(lines):
        if i == 0:
            out.append(
                f'<text x="{cx}" y="{ty}" text-anchor="middle" font-family="{fam}" '
                f'font-size="{title_size}" font-weight="bold" fill="{tcolor}">{ln}</text>'
            )
            ty += line_h + 2
        else:
            out.append(
                f'<text x="{cx}" y="{ty}" text-anchor="middle" font-family="{fam}" '
                f'font-size="{body_size}" fill="{tcolor}">{ln}</text>'
            )
            ty += line_h
    return out


def arrow_r(x1, y, x2, color=NAVY, width=2.5, label="", label_color=GREY, dash=False):
    d = ' stroke-dasharray="6 5"' if dash else ""
    out = [
        f'<line x1="{x1}" y1="{y}" x2="{x2 - 11}" y2="{y}" stroke="{color}" stroke-width="{width}"{d}/>',
        f'<polygon points="{x2 - 12},{y - 7} {x2},{y} {x2 - 12},{y + 7}" fill="{color}"/>',
    ]
    if label:
        out.append(
            f'<text x="{(x1 + x2) // 2}" y="{y - 10}" text-anchor="middle" font-size="13" '
            f'font-family="{MONO}" fill="{label_color}">{label}</text>'
        )
    return out


def arrow_d(x, y1, y2, color=NAVY, width=2.5, label="", label_color=GREY):
    out = [
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 11}" stroke="{color}" stroke-width="{width}"/>',
        f'<polygon points="{x - 7},{y2 - 12} {x},{y2} {x + 7},{y2 - 12}" fill="{color}"/>',
    ]
    if label:
        out.append(
            f'<text x="{x + 10}" y="{(y1 + y2) // 2}" font-size="13" font-family="{MONO}" '
            f'fill="{label_color}">{label}</text>'
        )
    return out


def _write(path, parts):
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def diagram_01_architecture(path):
    s = _open(
        "ScubaDrift architecture", "Stand on ScubaGear — one parser, a triage core, an independent diff, a thin gate"
    )
    # inputs
    s += box(40, 150, 250, 96, ICE, NAVY, ["ScubaGear results", "ScubaResults.json"], tcolor=NAVY)
    s += box(40, 330, 250, 96, ICE, NAVY, ["Risk-acceptance", "register (JSON / YAML)"], tcolor=NAVY)
    # parser
    s += box(
        360,
        190,
        230,
        210,
        NAVY,
        NAVY,
        ["parser", "load_run()", "load_exceptions()", "", "the only module", "that touches disk"],
        title_size=20,
        body_size=14,
    )
    s += arrow_r(290, 198, 360, label="")
    s += arrow_r(290, 378, 360, label="")
    # model -> triage / drift
    s += box(
        680, 150, 250, 120, NAVY, NAVY, ["triage.triage", "-> TriageReport", "new / lapsed / governed"], body_size=14
    )
    s += box(680, 330, 250, 120, NAVY, NAVY, ["drift.diff_runs", "-> DriftReport", "compare two runs"], body_size=14)
    s += arrow_r(590, 250, 680, color=TEAL, label="ScubaRun")
    s += arrow_r(590, 350, 680, color=TEAL, label="Acceptance[]")
    # gate
    s += box(
        990, 150, 250, 120, NAVY, NAVY, ["gate.evaluate_gate", "-> GateResult", "thin wrapper on triage"], body_size=14
    )
    s += arrow_r(930, 210, 990, color=TEAL)
    # outputs
    s += box(990, 330, 118, 90, TEAL_TINT, TEAL, ["exit 0", "PASS"], tcolor=NAVY, title_size=18, body_size=14)
    s += box(1122, 330, 118, 90, RED_TINT, RED, ["exit 1", "ACT"], tcolor=NAVY, title_size=18, body_size=14)
    s += arrow_d(1049, 270, 330, color=TEAL)
    s += arrow_d(1181, 270, 330, color=RED)
    # assessment boundary note
    s.append(
        f'<text x="165" y="470" text-anchor="middle" font-size="14" fill="{MUTED}">'
        f"assessment (needs tenant creds)</text>"
    )
    s.append(f'<text x="165" y="490" text-anchor="middle" font-size="14" fill="{MUTED}">stays in ScubaGear</text>')
    s.append(_caption("Figure 1 — Files in, a governed decision out. ScubaDrift never touches the tenant."))
    _write(path, s)


def diagram_02_disposition(path):
    s = _open("The disposition gate", "Every failing policy resolves to exactly one of three dispositions")
    s += box(515, 128, 250, 78, NAVY, NAVY, ["Failing policy", "(Result = Fail)"], title_size=19, body_size=14)
    # decision 1
    s += box(505, 250, 270, 74, ICE, NAVY, ["Risk-acceptance on file?"], tcolor=NAVY, title_size=18)
    s += arrow_d(640, 206, 250)
    # No -> actionable new drift (left)
    s += arrow_r(505, 287, 300, color=RED, label="")
    s.append(f'<text x="400" y="278" text-anchor="middle" font-size="14" font-weight="bold" fill="{RED}">no</text>')
    s += box(
        40,
        250,
        260,
        90,
        RED_TINT,
        RED,
        ["ACTIONABLE_NEW_DRIFT", "no acceptance — act now"],
        tcolor=NAVY,
        title_size=17,
        body_size=14,
    )
    # Yes -> decision 2 (down)
    s += arrow_d(640, 324, 400, label="  yes", label_color=NAVY)
    s += box(505, 400, 270, 74, ICE, NAVY, ["expiry_date &lt; as_of ?"], tcolor=NAVY, title_size=18)
    # Yes expired -> lapsed (left, amber=escalation)
    s += arrow_r(505, 437, 300, color=AMBER)
    s.append(f'<text x="400" y="428" text-anchor="middle" font-size="14" font-weight="bold" fill="{NAVY}">yes</text>')
    s += box(
        40,
        400,
        260,
        90,
        AMBER_TINT,
        AMBER,
        ["LAPSED_ACCEPTANCE", "expired — re-review / act"],
        tcolor=NAVY,
        title_size=17,
        body_size=14,
    )
    # No -> governed (right, teal=good)
    s += arrow_r(775, 437, 980, color=TEAL)
    s.append(f'<text x="880" y="428" text-anchor="middle" font-size="14" font-weight="bold" fill="{NAVY}">no</text>')
    s += box(
        980,
        400,
        260,
        90,
        TEAL_TINT,
        TEAL,
        ["GOVERNED_EXCEPTION", "in date — already governed"],
        tcolor=NAVY,
        title_size=17,
        body_size=14,
    )
    s.append(
        f'<text x="{W // 2}" y="560" text-anchor="middle" font-size="15" fill="{BODY}">'
        f"Left column is actionable (gate fails). Right box is governed (gate stays green).</text>"
    )
    s.append(
        f'<text x="{W // 2}" y="586" text-anchor="middle" font-size="14" fill="{MUTED}">'
        f"Only Fail counts by default; --include-warnings widens the set to Warning.</text>"
    )
    s.append(_caption("Figure 2 — The core decision: is this failure already governed, or must I act?"))
    _write(path, s)


def diagram_03_drift(path):
    s = _open("Run-to-run drift taxonomy", "Comparing two ScubaGear runs by policy id — passing->passing is omitted")
    rows = [
        ("Pass / absent", "Fail", "NEW_FAILURE", "regression — highest signal", RED, RED_TINT),
        ("Fail", "Pass", "RESOLVED", "remediation to credit", TEAL, TEAL_TINT),
        ("Fail", "Fail", "PERSISTENT_FAILURE", "still open — accept or POA&amp;M", NAVY, ICE),
        ("absent", "Fail", "NEW_POLICY", "baseline grew (version bump)", MID_BLUE, ICE),
        ("present", "absent", "REMOVED_POLICY", "baseline shrank / scope change", GREY, "#F0F2F5"),
    ]
    # column headers
    s.append(
        f'<text x="210" y="150" text-anchor="middle" font-size="16" font-weight="bold" fill="{MUTED}">baseline</text>'
    )
    s.append(
        f'<text x="500" y="150" text-anchor="middle" font-size="16" font-weight="bold" fill="{MUTED}">current</text>'
    )
    s.append(
        f'<text x="900" y="150" text-anchor="middle" font-size="16" font-weight="bold" fill="{MUTED}">DriftKind</text>'
    )
    y = 172
    for base, curr, kind, note, color, tint in rows:
        s += box(110, y, 200, 66, ICE, NAVY, [base], tcolor=NAVY, title_size=16, rx=8)
        s += arrow_r(310, y + 33, 400, color=color)
        s += box(400, y, 200, 66, ICE, NAVY, [curr], tcolor=NAVY, title_size=16, rx=8)
        s += box(690, y, 250, 66, tint, color, [kind], tcolor=NAVY, title_size=17, rx=8)
        s.append(f'<text x="960" y="{y + 40}" font-size="15" fill="{BODY}">{note}</text>')
        y += 90
    s.append(_caption("Figure 3 — Drift is compared by policy id only, so it is fully deterministic given two files."))
    _write(path, s)


def diagram_04_lifecycle(path):
    s = _open("Risk-acceptance lifecycle", "Expiry is deterministic: in date through the expiry day, lapsed the next")
    axis_y = 300
    s.append(f'<line x1="120" y1="{axis_y}" x2="1160" y2="{axis_y}" stroke="{NAVY}" stroke-width="3"/>')
    s.append(f'<polygon points="1160,{axis_y - 8} 1176,{axis_y} 1160,{axis_y + 8}" fill="{NAVY}"/>')
    s.append(f'<text x="1176" y="{axis_y + 40}" text-anchor="end" font-size="14" fill="{MUTED}">time (as_of)</text>')

    # governed band
    s.append(
        f'<rect x="330" y="{axis_y - 44}" width="470" height="44" fill="{TEAL_TINT}" stroke="{TEAL}" stroke-width="2"/>'
    )
    s.append(
        f'<text x="565" y="{axis_y - 16}" text-anchor="middle" font-size="16" font-weight="bold" fill="{NAVY}">'
        f"GOVERNED_EXCEPTION</text>"
    )
    # lapsed band
    s.append(
        f'<rect x="800" y="{axis_y - 44}" width="330" height="44" fill="{AMBER_TINT}" stroke="{AMBER}" stroke-width="2"/>'
    )
    s.append(
        f'<text x="965" y="{axis_y - 16}" text-anchor="middle" font-size="16" font-weight="bold" fill="{NAVY}">'
        f"LAPSED_ACCEPTANCE</text>"
    )

    # markers
    for mx, label, sub in [(330, "approved_date", "acceptance filed"), (800, "expiry_date", "in date through here")]:
        s.append(f'<circle cx="{mx}" cy="{axis_y}" r="9" fill="{NAVY}"/>')
        s.append(f'<line x1="{mx}" y1="{axis_y}" x2="{mx}" y2="{axis_y + 34}" stroke="{GREY}" stroke-width="1.5"/>')
        s.append(
            f'<text x="{mx}" y="{axis_y + 56}" text-anchor="middle" font-size="16" font-weight="bold" fill="{NAVY}">{label}</text>'
        )
        s.append(f'<text x="{mx}" y="{axis_y + 78}" text-anchor="middle" font-size="14" fill="{MUTED}">{sub}</text>')

    # retirable branch
    s += box(
        330,
        470,
        470,
        96,
        ICE,
        MID_BLUE,
        ["policy now passes  ->  RETIRABLE", "the acceptance is dead weight;", "prune it from the register"],
        tcolor=NAVY,
        title_size=17,
        body_size=14,
    )
    s += arrow_d(565, 256, 470, color=MID_BLUE)
    s.append(
        f'<text x="{W // 2}" y="150" text-anchor="middle" font-size="15" fill="{BODY}">'
        f"is_expired(as_of) = as_of &gt; expiry_date</text>"
    )
    s.append(_caption("Figure 4 — An acceptance is a time-boxed decision; ScubaDrift flags it the day it lapses."))
    _write(path, s)


def diagram_05_conmon(path):
    s = _open(
        "Gating a conmon pipeline", "The gate fails on new drift or a lapsed acceptance — governed keeps it green"
    )
    s += box(
        40, 250, 220, 120, ICE, NAVY, ["ScubaGear run", "(scheduled)", "needs tenant creds"], tcolor=NAVY, body_size=14
    )
    s += box(320, 250, 210, 120, ICE, NAVY, ["ScubaResults", ".json artifact"], tcolor=NAVY)
    s += arrow_r(260, 310, 320, color=TEAL)
    s += box(600, 250, 250, 120, NAVY, NAVY, ["scubadrift gate", "triage + exit code"], body_size=14)
    s += arrow_r(530, 310, 600, color=TEAL, label="--results")
    # register feeding gate
    s += box(600, 430, 250, 74, ICE, NAVY, ["risk-acceptance register"], tcolor=NAVY, title_size=16)
    s += arrow_d(725, 430, 372, color=TEAL)
    s.append(f'<text x="760" y="415" font-size="13" font-family="{MONO}" fill="{GREY}">--exceptions</text>')
    # outcomes
    s += box(940, 175, 300, 96, TEAL_TINT, TEAL, ["PASS — exit 0", "build stays green"], tcolor=NAVY, body_size=15)
    s += box(
        940, 350, 300, 96, RED_TINT, RED, ["FAIL — exit 1", "new drift or lapsed acceptance"], tcolor=NAVY, body_size=15
    )
    s += arrow_r(850, 250, 940, color=TEAL, label="clean")
    s += arrow_r(850, 360, 940, color=RED, label="actionable")
    s.append(
        f'<text x="{W // 2}" y="580" text-anchor="middle" font-size="15" fill="{BODY}">'
        f"Governed, in-date exceptions never break the build; input errors exit 2.</text>"
    )
    s.append(
        _caption("Figure 5 — Assessment and gating are separate jobs; the gate is credential-free and runs anywhere.")
    )
    _write(path, s)


def diagram_06_conmon_loop(path):
    s = _open("The continuous-monitoring loop", "Assess -> record -> report -> act, on a defined cadence")
    boxes = [
        (40, 200, 250, 120, ICE, NAVY, ["1. Assess", "ScubaGear", "point-in-time"], NAVY),
        (350, 200, 270, 120, NAVY, NAVY, ["2. Record", "conmon-record", "append to ledger"], WHITE),
        (680, 200, 270, 120, NAVY, NAVY, ["3. Report", "conmon-report", "trend + SLA aging"], WHITE),
        (1010, 200, 230, 120, ICE, NAVY, ["4. Act", "remediate /", "renew acceptance"], NAVY),
    ]
    for x, y, w, h, fill, stroke, lines, tc in boxes:
        s += box(x, y, w, h, fill, stroke, lines, tcolor=tc, body_size=14)
    s += arrow_r(290, 260, 350, color=TEAL)
    s += arrow_r(620, 260, 680, color=TEAL)
    s += arrow_r(950, 260, 1010, color=TEAL)
    # ledger store, written by Record, read by Report
    s += box(485, 385, 330, 70, ICE, MID_BLUE, ["conmon-ledger.jsonl  (history)"], tcolor=NAVY, title_size=16, rx=8)
    s += arrow_d(485, 320, 385, color=MID_BLUE)  # record -> ledger (down from record area)
    s.append(f'<line x1="815" y1="420" x2="815" y2="360" stroke="{MID_BLUE}" stroke-width="2.5"/>')
    s.append(f'<polygon points="808,372 815,360 822,372" fill="{MID_BLUE}"/>')  # ledger -> report (up)
    s.append(f'<text x="470" y="360" text-anchor="end" font-size="13" font-family="{MONO}" fill="{GREY}">write</text>')
    s.append(f'<text x="835" y="400" font-size="13" font-family="{MONO}" fill="{GREY}">read</text>')
    # loop-back: Act -> Assess on cadence
    s.append(f'<line x1="1125" y1="320" x2="1125" y2="520" stroke="{NAVY}" stroke-width="2.5"/>')
    s.append(f'<line x1="1125" y1="520" x2="165" y2="520" stroke="{NAVY}" stroke-width="2.5"/>')
    s.append(f'<line x1="165" y1="520" x2="165" y2="320" stroke="{NAVY}" stroke-width="2.5"/>')
    s.append(f'<polygon points="158,332 165,320 172,332" fill="{NAVY}"/>')
    s.append(
        f'<text x="645" y="512" text-anchor="middle" font-size="15" fill="{BODY}">'
        f"repeat on the monitoring cadence (e.g. monthly); --fail-on-breach gates on overdue findings</text>"
    )
    # federal mapping strip
    s.append(
        f'<rect x="120" y="590" width="1040" height="52" rx="6" fill="{TEAL_TINT}" stroke="{TEAL}" stroke-width="1.5"/>'
    )
    s.append(
        f'<text x="640" y="622" text-anchor="middle" font-size="16" fill="{NAVY}">'
        f"supports  CISA BOD 25-01  -  NIST SP 800-137 (ISCM)  -  NIST 800-53 CA-7  -  FedRAMP ConMon (30 / 90 / 180)</text>"
    )
    s.append(_caption("Figure 6 — ScubaDrift closes the loop ScubaGear opens: assessment becomes ongoing monitoring."))
    _write(path, s)


DIAGRAMS = [
    ("scubadrift-diagram-01-architecture.svg", diagram_01_architecture),
    ("scubadrift-diagram-02-disposition-gate.svg", diagram_02_disposition),
    ("scubadrift-diagram-03-drift-taxonomy.svg", diagram_03_drift),
    ("scubadrift-diagram-04-exception-lifecycle.svg", diagram_04_lifecycle),
    ("scubadrift-diagram-05-conmon-gate.svg", diagram_05_conmon),
    ("scubadrift-diagram-06-conmon-loop.svg", diagram_06_conmon_loop),
]


def build_all(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, fn in DIAGRAMS:
        p = out_dir / name
        fn(p)
        written.append(p)
    return written

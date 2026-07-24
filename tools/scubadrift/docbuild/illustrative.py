"""Illustrative ScubaDrift figures (ADR-095 illustrative register).

Concept art whose job is to make an idea land: metaphor, scene, gradients, and
stylized (non-photographic) silhouettes. Uses the illustrative palette tokens.
Still absolute: no photographs, no logos, literal correctly-spelled <text>,
amber = severity only, red = loss, portable vector for cairosvg. Naming uses the
`-image-NN-` infix reserved for illustrative figures.
"""

from __future__ import annotations

from figures import (
    AMBER,
    BODY,
    HDR,
    ICE,
    MID_BLUE,
    MUTED,
    NAVY,
    RED,
    SANS,
    TEAL,
    WHITE,
    H,
    W,
)

# Illustrative-register tokens (palette.json -> "illustrative")
FIGURE = "#2E4B6B"
FIGURE_MUTED = "#A9B8CA"
SKY_TOP = "#EAF1FB"
SKY_LOW = "#CFE0F2"
GLOW = "#D7F2EE"


def _open(defs=""):
    return [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="{SANS}">',
        f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
        defs,
    ]


def _title(s, title, sub=""):
    s.append(
        f'<text x="{W // 2}" y="60" text-anchor="middle" font-family="{HDR}" '
        f'font-size="34" font-weight="bold" fill="{NAVY}">{title}</text>'
    )
    if sub:
        s.append(f'<text x="{W // 2}" y="92" text-anchor="middle" font-size="19" fill="{MUTED}">{sub}</text>')


def _caption(s, text):
    s.append(f'<text x="{W // 2}" y="694" text-anchor="middle" font-size="17" fill="{MUTED}">{text}</text>')


def _figure(x, base_y, scale=1.0, color=FIGURE):
    """A stylized (non-photographic) standing silhouette: head + shoulders/body."""
    head_r = 26 * scale
    hy = base_y - 150 * scale
    body = (
        f"M {x - 42 * scale} {base_y} "
        f"C {x - 46 * scale} {base_y - 96 * scale}, {x - 30 * scale} {base_y - 118 * scale}, {x} {base_y - 118 * scale} "
        f"C {x + 30 * scale} {base_y - 118 * scale}, {x + 46 * scale} {base_y - 96 * scale}, {x + 42 * scale} {base_y} Z"
    )
    return [
        f'<path d="{body}" fill="{color}"/>',
        f'<circle cx="{x}" cy="{hy}" r="{head_r}" fill="{color}"/>',
    ]


def _write(path, parts):
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def image_00_cover(path):
    defs = (
        "<defs>"
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{SKY_TOP}"/><stop offset="1" stop-color="{SKY_LOW}"/></linearGradient>'
        f'<radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">'
        f'<stop offset="0" stop-color="{GLOW}" stop-opacity="0.9"/>'
        f'<stop offset="1" stop-color="{GLOW}" stop-opacity="0"/></radialGradient>'
        "</defs>"
    )
    s = _open(defs)
    s.append(f'<rect x="0" y="0" width="{W}" height="470" fill="url(#sky)"/>')
    # foundation slab = ScubaGear (the authority you stand on)
    s.append(f'<rect x="150" y="470" width="980" height="150" rx="6" fill="{NAVY}"/>')
    s.append(
        f'<text x="640" y="520" text-anchor="middle" font-size="22" font-weight="bold" fill="{WHITE}">ScubaGear</text>'
    )
    s.append(
        f'<text x="640" y="548" text-anchor="middle" font-size="16" fill="{ICE}">'
        f"CISA-sanctioned M365 baseline  -  mandated, free, NIST-mapped</text>"
    )
    s.append(
        f'<text x="640" y="576" text-anchor="middle" font-size="15" fill="{FIGURE_MUTED}">'
        f"the assessment you build on, not against</text>"
    )
    # ScubaDrift block on top
    s.append(f'<rect x="440" y="360" width="400" height="110" rx="8" fill="{ICE}" stroke="{TEAL}" stroke-width="3"/>')
    s.append(
        f'<text x="640" y="402" text-anchor="middle" font-size="20" font-weight="bold" fill="{NAVY}">ScubaDrift</text>'
    )
    s.append(
        f'<text x="640" y="430" text-anchor="middle" font-size="15" fill="{BODY}">'
        f"drift  -  exception lifecycle  -  conmon gate</text>"
    )
    # glow + figure standing atop
    s.append('<ellipse cx="640" cy="360" rx="150" ry="70" fill="url(#glow)"/>')
    s += _figure(640, 360, scale=1.15)
    _title(s, "Standing on the sanctioned baseline")
    _caption(s, "A thin operational layer on an authoritative assessment — the whole design in one picture.")
    _write(path, s)


def image_01_signal_in_noise(path):
    s = _open()
    _title(s, "Signal in the noise", "Most failures are already governed; triage surfaces the few you must act on")
    # field of quiet, governed marks
    import_note = FIGURE_MUTED
    x0, y0, dx, dy = 150, 170, 92, 78
    cols, rows = 9, 4
    actionable = {(2, 1), (6, 0), (4, 3)}  # highlighted
    idx = 0
    for r in range(rows):
        for c in range(cols):
            cx = x0 + c * dx
            cy = y0 + r * dy
            if (c, r) in actionable:
                continue
            s.append(f'<circle cx="{cx}" cy="{cy}" r="14" fill="{import_note}"/>')
            idx += 1
    # actionable marks: red (drift) + amber (lapsed), larger with ring
    highlights = [((2, 1), RED, "new drift"), ((6, 0), RED, "new drift"), ((4, 3), AMBER, "lapsed")]
    for (c, r), color, label in highlights:
        cx = x0 + c * dx
        cy = y0 + r * dy
        s.append(f'<circle cx="{cx}" cy="{cy}" r="26" fill="none" stroke="{color}" stroke-width="3"/>')
        s.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="{color}"/>')
        s.append(
            f'<text x="{cx}" y="{cy + 46}" text-anchor="middle" font-size="14" font-weight="bold" '
            f'fill="{NAVY}">{label}</text>'
        )
    # legend
    s.append(f'<circle cx="360" cy="560" r="12" fill="{FIGURE_MUTED}"/>')
    s.append(
        f'<text x="382" y="565" font-size="16" fill="{BODY}">governed / quiet  -  already accepted, in date</text>'
    )
    s.append(f'<circle cx="360" cy="595" r="12" fill="{RED}"/>')
    s.append(
        f'<text x="382" y="600" font-size="16" fill="{BODY}">actionable  -  new drift or a lapsed acceptance</text>'
    )
    _caption(s, "The gate stays green on the grey field and fails only on the ringed marks.")
    _write(path, s)


def image_02_expiry_horizon(path):
    defs = (
        "<defs>"
        f'<linearGradient id="dusk" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{GLOW}"/><stop offset="0.55" stop-color="{SKY_TOP}"/>'
        f'<stop offset="1" stop-color="{"#F3E3C6"}"/></linearGradient>'
        "</defs>"
    )
    s = _open(defs)
    _title(s, "The expiry horizon", "An acceptance is a time-boxed decision — in date, then lapsed")
    s.append('<rect x="120" y="150" width="1040" height="330" rx="8" fill="url(#dusk)"/>')
    # horizon line
    s.append(f'<line x1="120" y1="480" x2="1160" y2="480" stroke="{NAVY}" stroke-width="3"/>')
    # governed region (left, teal glow) vs lapsed region (right, amber)
    ex = 760  # expiry x
    s.append(
        f'<text x="440" y="230" text-anchor="middle" font-size="20" font-weight="bold" fill="{TEAL}">'
        f"GOVERNED_EXCEPTION</text>"
    )
    s.append(
        f'<text x="440" y="258" text-anchor="middle" font-size="15" fill="{BODY}">'
        f"in date  -  suppressed from the action list</text>"
    )
    s.append(
        f'<text x="960" y="230" text-anchor="middle" font-size="20" font-weight="bold" fill="{AMBER}">'
        f"LAPSED_ACCEPTANCE</text>"
    )
    s.append(
        f'<text x="960" y="258" text-anchor="middle" font-size="15" fill="{BODY}">'
        f"past expiry  -  back on the action list</text>"
    )
    # the setting sun at the expiry line
    s.append(f'<circle cx="{ex}" cy="480" r="52" fill="{AMBER}" fill-opacity="0.85"/>')
    s.append(f'<line x1="{ex}" y1="150" x2="{ex}" y2="520" stroke="{NAVY}" stroke-width="2.5" stroke-dasharray="8 6"/>')
    s.append(
        f'<text x="{ex}" y="545" text-anchor="middle" font-size="18" font-weight="bold" fill="{NAVY}">'
        f"expiry_date</text>"
    )
    s.append(
        f'<text x="{ex}" y="568" text-anchor="middle" font-size="14" fill="{MUTED}">'
        f"in date through this day; lapses the next</text>"
    )
    # retirable aside
    s.append(
        f'<text x="{W // 2}" y="612" text-anchor="middle" font-size="15" fill="{MID_BLUE}">'
        f"and when the policy passes again, the acceptance becomes retirable.</text>"
    )
    _caption(s, "Because expiry is deterministic, you can gate a future date and renew before the sun sets.")
    _write(path, s)


IMAGES = [
    ("scubadrift-image-00-cover.svg", image_00_cover),
    ("scubadrift-image-01-signal-in-noise.svg", image_01_signal_in_noise),
    ("scubadrift-image-02-expiry-horizon.svg", image_02_expiry_horizon),
]


def build_all(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, fn in IMAGES:
        p = out_dir / name
        fn(p)
        written.append(p)
    return written

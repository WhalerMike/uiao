#!/usr/bin/env python3
"""Refined: real ARCHITECTURE diagrams = boxes (┌┐└┘) + connectors/arrows,
NOT directory trees (├──/└── dominated, no ┌┐ boxes) and NOT code separators."""
from __future__ import annotations
import sys
from pathlib import Path
ROOTS=[Path("docs"),Path("src/uiao/canon")]
SKIP=("image-prompts","IMAGE-PROMPTS",".manifest","generate-series","_site","_freeze",".quarto","node_modules")
CORNERS=set("┌┐└┘╔╗╚╝")
ARROWS=set("▶◀►◄▲▼→←↓↑⟶")
TREE=set("├└")  # tree connectors
def scan(p):
    try: lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
    except Exception: return []
    out=[];inf=False;st=0;buf=[];lang=""
    for i,ln in enumerate(lines,1):
        s=ln.lstrip()
        if s.startswith("```"):
            if not inf: inf,st,buf,lang=True,i,[],s[3:].strip().lower()
            else:
                corners=sum(c in CORNERS for r in buf for c in r)
                arrows=sum(c in ARROWS for r in buf for c in r)
                tree=sum(c in TREE for r in buf for c in r)
                # heuristic: a real arch diagram has >=4 box corners and (arrows present OR
                # multiple boxes), and is NOT dominated by tree connectors, and not a code lang
                is_code = lang in ("powershell","ps1","bash","sh","python","py","yaml","json","sql")
                if corners>=4 and (arrows>=1 or corners>=8) and tree<corners and not is_code:
                    out.append((st,i,corners,arrows,tree,buf[:3]))
                inf=False
        elif inf: buf.append(ln)
    return out
hits=[]
for root in ROOTS:
    for ext in ("*.md","*.qmd"):
        for p in root.rglob(ext):
            if any(x in str(p) for x in SKIP): continue
            for h in scan(p): hits.append((p,*h))
hits.sort(key=lambda h:(-h[3]-h[4]//4, str(h[1])))
print(f"REAL architecture diagrams: {len(hits)}\n")
for (p,a,b,co,ar,tr,prev) in hits:
    print(f"{p}:{a}-{b}  (corners={co} arrows={ar})")
    for r in prev: print(f"    | {r[:72]}")
    print()

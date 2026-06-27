---
id: UIAO-FIG-023
slug: image-lifecycle
title: "Figure Registry Lifecycle — draft → current → deprecated"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#C0392B", "#5A5A5A", "#FFFFFF"]
---

## Description

House-style replacement for the ASCII image-lifecycle diagram: three states
— ice "draft" (prompt exists, no PNG), navy "current" (rendered + approved),
grey "deprecated" (superseded, retained) — joined by teal "PR review"
arrows. A red dashed branch shows "rejected → deleted from branch" from
draft; a small teal self-loop on current shows "version bump — same ID, new
version". A footnote ties the states to the image-registry status field.

## Prompt

A 16:9 blueprint schematic (ADR-093), white background, three state boxes:
ice "draft (prompt exists, no PNG)", navy "current (rendered + approved)",
grey-bordered "deprecated (superseded, retained)", joined by two teal "PR
review" arrows. A red dashed arrow from draft labelled "rejected → deleted
from branch"; a teal self-loop over current labelled "version bump — same
ID, new version". A footnote on the registry status field. Literal SVG text;
no logos, no photos.

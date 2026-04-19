---
document_id: UIAO_DG_003
title: "Diagram Form Factor Auto-Selection Logic"
version: "1.0"
status: DRAFT
classification: Controlled
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
artifact_type: OPERATIONAL
---

# Diagram Form Factor Auto-Selection Logic

## 1. Purpose

This document defines the rules by which consuming systems (documentation sites, dashboards, slide generators) automatically select the correct diagram form factor (Full/Banana or Compact/NanoBanana) based on rendering context.

## 2. Selection Matrix

| Context | Container Width | Form Factor | Rationale |
|---|---|---|---|
| Full-page documentation | ≥ 800px | **Full** | Sufficient space for complete detail |
| Appendix / reference section | ≥ 800px | **Full** | Deep-reference context expects detail |
| Dashboard tile | < 800px | **Nano** | Space-constrained; density matters |
| Slide embed | < 600px | **Nano** | Presentation context; minimal detail |
| Inline paragraph reference | < 400px | **Nano** | Thumbnail-scale; overview only |
| PDF export (A4/Letter) | ≥ 800px | **Full** | Print context; full detail appropriate |
| PDF export (half-page) | < 500px | **Nano** | Constrained print area |
| Mobile viewport | < 600px | **Nano** | Small screen; high density preferred |
| Email embed | any | **Nano** | Email clients have unreliable rendering |

## 3. Selection Algorithm

```
function selectFormFactor(context):
    // Step 1: Explicit override wins
    if context.explicit_form_factor is set:
        return context.explicit_form_factor

    // Step 2: Context-type rules
    if context.type in ["email", "notification", "alert"]:
        return NANO

    if context.type in ["appendix", "reference", "full_page"]:
        return FULL

    // Step 3: Container-width rules
    if context.container_width >= 800:
        return FULL
    elif context.container_width >= 400:
        return NANO
    else:
        return NANO

    // Step 4: Fallback
    return FULL
```

## 4. Implementation Patterns

### 4.1 Markdown Embedding (Documentation Sites)

Authors embed diagrams using a custom directive that triggers auto-selection:

```markdown
<!-- UIAO-DIAGRAM: DIAG_001 -->
```

The documentation build system:
1. Reads the directive.
2. Evaluates the rendering context (page layout, viewport hints).
3. Selects the appropriate form factor.
4. Inserts the correct rendered image with a link to the alternate form factor.

### 4.2 Dashboard Widget

Dashboard systems query the diagram registry and embed based on tile dimensions:

```yaml
widget:
  type: diagram
  diagram_id: DIAG_001
  auto_select: true        # Enables form-factor auto-selection
  fallback: nano            # If auto-selection fails
  link_alternate: true      # Clickable link to full version
```

### 4.3 Slide Generation

Slide templates reference diagrams by ID. The slide generator:
1. Measures the placeholder dimensions.
2. Applies the selection algorithm.
3. Embeds the selected form factor.
4. Adds a speaker-note link to the full version if nano was selected.

## 5. Override Mechanism

Authors and consumers can force a specific form factor:

```markdown
<!-- UIAO-DIAGRAM: DIAG_001 form_factor=full -->
<!-- UIAO-DIAGRAM: DIAG_001 form_factor=nano -->
```

Overrides are logged for governance audit but are always respected.

## 6. Alternate-Version Linking

When a nano diagram is displayed, the system **must** provide a discoverable link to the full version:
- In web contexts: a "View full diagram" link or click-to-expand behavior.
- In PDF contexts: a footnote referencing the appendix location of the full diagram.
- In email contexts: a link to the documentation page containing the full version.

When a full diagram is displayed, a note **may** indicate that a compact version exists for embedding.

## 7. Accessibility

- Both form factors must include `alt` text derived from the diagram's `title` and `description` metadata fields.
- Nano diagrams must include a tooltip or aria-label indicating that a more detailed version is available.
- Color is never the sole differentiator — all node distinctions must also use shape or border style.

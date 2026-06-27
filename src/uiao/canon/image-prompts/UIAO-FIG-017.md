---
id: UIAO-FIG-017
slug: uiao193-multicloud-binding
title: "UIAO_193 — OrgPath Multi-Cloud Binding Profiles"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#5A5A5A", "#FFFFFF"]
---

## Description

Engineering schematic of the UIAO_193 binding-profile model: the universal
15-facet codebook (UIAO_151) feeds a per-target binding-profile contract
(facet → native locator + read/write mechanics, normative per ADR-098),
which fans out to nine per-target storage profiles — microsoft-entra as the
teal-accented reference profile (onPremisesExtensionAttribute1..15) plus aws,
gcp, okta, ldap, vmware, and the three ADR-099 IdP targets (pingone,
keycloak, auth0), each shown as proposed-until-transport. A footer band
states the Zero Trust projection: OrgPath facets are the cross-vendor policy
subject, mapped to the CISA Zero Trust Maturity Model pillars.

## Prompt

A 16:9 technical schematic in the UIAO federal-whitepaper blueprint style
(ADR-093) on a white background. On the left, a navy box "15-facet Codebook
(UIAO_151) — universal". A teal arrow into a teal-bordered navy box
"Binding Profile — facet → native locator, read/write mechanics, normative
schema". A teal trunk arrow fans into a 3×3 grid of ice/navy-border target
boxes on the right, each naming a platform and its native locator:
microsoft-entra (reference, teal border) onPremisesExtensionAttribute1..15;
aws resource tags / IAM; gcp resource labels; okta profile attributes; ldap
directory attributes; vmware three-plane tags; pingone / keycloak / auth0
IdP attributes (ADR-099). A legend distinguishes the reference profile from
proposed profiles. A teal-tint footer band states the Zero Trust subject
projection. All text literal SVG; no photographs, no vendor logos.

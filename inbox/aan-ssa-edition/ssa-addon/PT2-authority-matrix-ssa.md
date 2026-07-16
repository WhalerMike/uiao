# SSA Add-On — PT-2 Legal Authority Matrix, Worked

**SSA edition only. Not published.** This file stays in `inbox/` and is not part of
the Federal AAN series that renders to the site. It is the agency-specific overlay
described in Vol 0 Book 01: the generic instrument plus one agency's filled answers.

## Why this is a separate document

Vol IV Book 04 teaches the *method* of a PT-2 authority matrix: which PII
categories demand a specific legal citation, why general mission authority is not
sufficient, and how retention and NIST 800-88 disposal attach per row. That method
is the same for every federal agency, so it is generic and it publishes.

The *citations* are not generic. A PT-2 matrix is only meaningful when each row
names the statute that actually authorizes that collection, and every agency cites
its own enabling act. Substituting a variable cannot produce them — there is no
value for `{{< meta agency.statute >}}` that turns `§205(c)(2)(C)(i)` into another
agency's provision. Genericizing the rows in place would not have made Book 04
agency-neutral; it would have deleted its worked example and left a hollow table.

So Book 04 ships the matrix with `[CITATION]` placeholders — the convention its own
`[ADDITIONAL PII CATEGORY]` row already used — and the filled instance lives here.
A reader with both sees the method and a completed example side by side, which is
more useful than either alone.

## The matrix, completed against the Social Security Act

Paste these rows into Book 04's **Legal Authority Matrix** in place of the
`[CITATION]` placeholders. Verify every citation against current law before use;
these were authored 2026-07 and statutes move.

| PII Category | Legal Basis | Statutory / Regulatory Citation | Retention Period | Disposal Method |
|-------------|-------------|--------------------------------|-----------------|-----------------|
| Social Security Number (SSN) | Statutory | Social Security Act §205(c)(2)(C)(i), 42 U.S.C. §405 | [N years per records schedule] | NIST 800-88 purge |
| Name and date of birth | Statutory | Social Security Act §202, 42 U.S.C. §402 | [N years per records schedule] | NIST 800-88 purge |
| Benefit payment records | Statutory | Social Security Act §1106, 42 U.S.C. §1306 | 7 years post-case closure | NIST 800-88 purge |
| Medical / disability records | Statutory | Social Security Act §223, 42 U.S.C. §423 | 5 years post-determination | Secure destruction + purge |
| Contact information (address, phone, email) | Statutory / Voluntary | Social Security Act §702, voluntary collection per E-Gov Act §208 | Duration of case + [N years] | NIST 800-88 purge |
| Financial account data (direct deposit) | Statutory | Social Security Act §205(j), 42 U.S.C. §405(j) | 7 years | NIST 800-88 purge |

## Related SSA-specific content in Book 04

- **SORN identifiers** render as `SSA/[NUMBER]` in this edition via
  `{{< meta agency.short >}}` — no action needed, they parameterize cleanly.
- **The model privacy notice** names the collecting agency through the same
  variable.
- **`figs/pii-fig-02-authority-sorn.png`** states "SSN to Social Security Act
  section 205(c)" in its pixels. It is a legacy figure with **no SVG source**
  (pre-ADR-093), so it cannot be edited or re-rendered. It must be re-authored as
  SVG with `[CITATION]` before Book 04 publishes, or the federal edition ships a
  figure naming one agency's statute. Tracked as a gap, not solved here.

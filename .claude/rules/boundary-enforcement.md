# Rule: Boundary Enforcement

## Scope
Always active. Enforces the GCC-Moderate boundary and operational limits.

## Cloud Boundary Rules

1. **GCC-Moderate Only:** All M365 service references must target GCC-Moderate. This applies to:
   - Tenant configurations
   - Compliance references
   - Service endpoints
   - Licensing documentation
   - Architecture diagrams

2. **Prohibited References:** The following are CI-blocking unless tagged `boundary-exception: true`:
   - GCC-High configurations or endpoints
   - DoD (IL4/IL5/IL6) references
   - Azure IaaS/PaaS services (GCC-Moderate covers M365 SaaS only)
   - Commercial Cloud services (except Amazon Connect Contact Center)

3. **Exception Handling:** Boundary exceptions require:
   ```yaml
   boundary-exception: true
   exception-justification: "<reason>"
   exception-approved-by: "<approver>"
   exception-date: "<ISO-8601>"
   ```

4. **FedRAMP Alignment:** UIAO operates under FedRAMP governance in Commercial Cloud. We are NOT FedRAMP High. All compliance references must align with the appropriate FedRAMP baseline.

## Operational Boundary Rules

5. **Placeholder Standards:** Every placeholder must include:
   - A unique ID (e.g., `PH-001`)
   - A fully detailed description specifying exactly what the final object must look like
   - Object references in prose use "Table X", "Diagram Y", or "Image Z" format

6. **Image Standards:** All images must include:
   - A title
   - Dimensions (width x height)
   - Alt text for accessibility

7. **Diagram Rendering:** PlantUML is the canonical diagram renderer. Do not use Mermaid.

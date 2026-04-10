# UIAO Zero-Trust Integration Layer

## Pillars

1. **Identity**
   - Evidence from:
     - Azure AD (MFA, Conditional Access)
   - Controls:
     - IA-2, AC-17

2. **Device**
   - Evidence from:
     - Endpoint management / Defender
   - Controls:
     - CM, SI families (future adapters)

3. **Network**
   - Evidence from:
     - Conditional Access locations
     - VPN / private access logs
   - Controls:
     - SC-7

4. **Data**
   - Evidence from:
     - DLP policies
     - Sharing settings
   - Controls:
     - SC-28, AC-21

## Integration Pattern
- Zero-trust systems → Evidence Collectors → IR → Controls → OSCAL
- Enforcement:
  - EPL policies call:
    - Conditional Access adapter
    - DLP policy adapter

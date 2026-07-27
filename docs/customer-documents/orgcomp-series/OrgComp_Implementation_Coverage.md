# OrgComp ServiceNow Implementation Coverage

> **Generated file — do not hand-edit.** Produced by `render_impl_coverage.py`
> from the six lane control maps and the kit artifacts on disk; CI-gated. This
> is the tracking board for the full-ServiceNow-implementation push: every
> governed catalog item, and how far its implementation has actually gotten.

**57 governed items** — 3 blueprinted (5%), 2 with an ATF spec (3%). 'Scripted' is recorded only via an explicit `impl.method` on the map item — never inferred.

| Lane | Catalog item | Control | Blueprint | ATF | Status | Client method |
|---|---|---|---|---|---|---|
| appreg | appreg.attest | AC-6 | — | — | specified | — |
| appreg | appreg.consent | AC-6 | — | — | specified | — |
| appreg | appreg.credential.issue | SC-17 | — | — | specified | — |
| appreg | appreg.credential.rotate | IA-5(2) | — | — | specified | — |
| appreg | appreg.request | AC-2 | — | — | specified | — |
| helpdesk | entra.access.ca_exception | AC-3 | — | — | specified | — |
| helpdesk | entra.access.group_assignment | AC-6 | — | — | specified | — |
| helpdesk | entra.access.guest_invite | AC-2 | — | — | specified | — |
| helpdesk | entra.access.license_assignment | AC-2 | — | — | specified | — |
| helpdesk | entra.credential.account_unlock | IA-5 | — | — | specified | — |
| helpdesk | entra.credential.mfa_reset | IA-5 | — | — | specified | — |
| helpdesk | entra.credential.password_reset | IA-5 | — | yes | tested | — |
| helpdesk | entra.jml.joiner | AC-2 | — | — | specified | — |
| helpdesk | entra.jml.leaver | AC-2 | — | — | specified | — |
| helpdesk | entra.jml.mover | AC-6 | — | — | specified | — |
| landingzone | lz.aws.instance.provision | CM-2 | — | — | specified | — |
| landingzone | lz.aws.patchschedule.change | CM-3 | — | — | specified | — |
| landingzone | lz.subnet.allocate | CM-8 | — | — | specified | — |
| landingzone | lz.subscription.provision | CM-2 | — | — | specified | — |
| landingzone | lz.vnet.provision | CM-3 | — | — | specified | — |
| saas | saas.account.audit | AC-2(4) | — | — | specified | — |
| saas | saas.approve | AC-5 | — | — | specified | — |
| saas | saas.assign | AC-3 | — | — | specified | — |
| saas | saas.attest | CA-7 | — | — | specified | — |
| saas | saas.audit.review | AU-6 | — | — | specified | — |
| saas | saas.change | CM-3 | — | — | specified | — |
| saas | saas.classify | AC-4 | — | — | specified | — |
| saas | saas.credential.issue | IA-5(2) | — | — | specified | — |
| saas | saas.credential.rotate | IA-5 | — | — | specified | — |
| saas | saas.identifier | IA-4 | — | — | specified | — |
| saas | saas.isa | CA-3 | — | — | specified | — |
| saas | saas.leaver | AC-2(3) | — | — | specified | — |
| saas | saas.logs | AU-2 | — | — | specified | — |
| saas | saas.mover | PS-5 | — | — | specified | — |
| saas | saas.offboard | AC-2 | — | — | specified | — |
| saas | saas.pki | SC-17 | — | — | specified | — |
| saas | saas.register.ci | CM-8 | — | — | specified | — |
| saas | saas.request | AC-20 | — | — | specified | — |
| saas | saas.retention | SI-12 | — | — | specified | — |
| saas | saas.roles | AC-6 | — | — | specified | — |
| saas | saas.scim.enable | AC-2(1) | — | — | specified | — |
| saas | saas.sso.configure | IA-2 | — | — | specified | — |
| saas | saas.verify.authorization | SA-9 | — | — | specified | — |
| saas | saas.verify.interfaces | SA-9(2) | — | — | specified | — |
| telephony | tel.audit.collect | AU-2 | — | — | specified | — |
| telephony | tel.callingpolicy.assign | CM-3 | — | — | specified | — |
| telephony | tel.e911.validate | CM-3 | — | — | specified | — |
| telephony | tel.number.assign | CM-3 | — | — | specified | — |
| telephony | tel.scuba.drift | CM-6 | — | — | specified | — |
| telephony | tel.voicerouting.change | CM-3 | — | — | specified | — |
| x_fed_compliance | attest.conmon.rollup | CA-7 | yes | — | blueprinted | — |
| x_fed_compliance | attest.control.test | CA-2 | — | — | specified | — |
| x_fed_compliance | attest.poam.item | CA-5 | yes | yes | tested | — |
| x_fed_compliance | azure.patch.remediation | SI-2 | — | — | specified | — |
| x_fed_compliance | azure.vuln.finding | RA-5 | — | — | specified | — |
| x_fed_compliance | m365.account.exception | AC-2 | yes | — | blueprinted | — |
| x_fed_compliance | m365.baseline.drift | CM-6 | — | — | specified | — |

: Implementation coverage by governed catalog item {.striped .hover}

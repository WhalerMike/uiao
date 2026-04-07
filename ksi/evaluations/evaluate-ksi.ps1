param(
    [Parameter(Mandatory = $true)]
        [string] $InputPath,
            [Parameter(Mandatory = $true)]
                [string] $OutputPath
                )

                $normalized = Get-Content $InputPath -Raw | ConvertFrom-Json
                $fields = $normalized.normalized.fields
                $results = @()

                function New-KsiResult {
                    param($Id, $Status, $Severity, $Details)
                        [pscustomobject]@{
                                ksi_id   = $Id
                                        status   = $Status
                                                severity = $Severity
                                                        details  = $Details
                                                            }
                                                            }

                                                            # KSI-001 MFA
                                                            $results += if ($fields.MFAEnabled) {
                                                                New-KsiResult "KSI-001" "PASS" "Low" "MFA enabled."
                                                                } else {
                                                                    New-KsiResult "KSI-001" "FAIL" "High" "MFA not enabled."
                                                                    }

                                                                    # KSI-002 Legacy Auth
                                                                    $results += if (-not $fields.LegacyAuthEnabled) {
                                                                        New-KsiResult "KSI-002" "PASS" "Low" "Legacy auth disabled."
                                                                        } else {
                                                                            New-KsiResult "KSI-002" "FAIL" "Critical" "Legacy auth enabled."
                                                                            }

                                                                            # KSI-003 Global Admin Count
                                                                            $results += if ($fields.AdminCount -le 5) {
                                                                                New-KsiResult "KSI-003" "PASS" "Low" "Admin count acceptable."
                                                                                } else {
                                                                                    New-KsiResult "KSI-003" "WARN" "Medium" "Admin count high."
                                                                                    }

                                                                                    # KSI-004 External Forwarding
                                                                                    $results += if (-not $fields.ExternalForwardingAllowed) {
                                                                                        New-KsiResult "KSI-004" "PASS" "Low" "External forwarding disabled."
                                                                                        } else {
                                                                                            New-KsiResult "KSI-004" "FAIL" "High" "External forwarding allowed."
                                                                                            }

                                                                                            # KSI-005 Mailbox Auditing
                                                                                            $results += if ($fields.MailboxAuditingEnabled) {
                                                                                                New-KsiResult "KSI-005" "PASS" "Low" "Mailbox auditing enabled."
                                                                                                } else {
                                                                                                    New-KsiResult "KSI-005" "FAIL" "High" "Mailbox auditing disabled."
                                                                                                    }
                                                                                                    
                                                                                                    # KSI-006 External Sharing
                                                                                                    $results += if (-not $fields.ExternalSharingEnabled) {
                                                                                                        New-KsiResult "KSI-006" "PASS" "Low" "External sharing disabled."
                                                                                                        } else {
                                                                                                            New-KsiResult "KSI-006" "WARN" "Medium" "External sharing enabled."
                                                                                                            }
                                                                                                            
                                                                                                            # KSI-007 Safe Links
                                                                                                            $results += if ($fields.SafeLinksEnabled) {
                                                                                                                New-KsiResult "KSI-007" "PASS" "Low" "Safe Links enabled."
                                                                                                                } else {
                                                                                                                    New-KsiResult "KSI-007" "FAIL" "High" "Safe Links disabled."
                                                                                                                    }
                                                                                                                    
                                                                                                                    # KSI-008 Safe Attachments
                                                                                                                    $results += if ($fields.SafeAttachmentsEnabled) {
                                                                                                                        New-KsiResult "KSI-008" "PASS" "Low" "Safe Attachments enabled."
                                                                                                                        } else {
                                                                                                                            New-KsiResult "KSI-008" "FAIL" "High" "Safe Attachments disabled."
                                                                                                                            }
                                                                                                                            
                                                                                                                            # KSI-009 Conditional Access
                                                                                                                            $results += if ($fields.ConditionalAccessPoliciesCount -ge 1) {
                                                                                                                                New-KsiResult "KSI-009" "PASS" "Low" "Conditional Access configured."
                                                                                                                                } else {
                                                                                                                                    New-KsiResult "KSI-009" "FAIL" "High" "No Conditional Access policies."
                                                                                                                                    }
                                                                                                                                    
                                                                                                                                    # KSI-010 DLP
                                                                                                                                    $results += if ($fields.DLPPoliciesCount -ge 1) {
                                                                                                                                        New-KsiResult "KSI-010" "PASS" "Low" "DLP configured."
                                                                                                                                        } else {
                                                                                                                                            New-KsiResult "KSI-010" "WARN" "Medium" "No DLP policies."
                                                                                                                                            }
                                                                                                                                            
                                                                                                                                            $normalized.ksi_results = $results
                                                                                                                                            $normalized | ConvertTo-Json -Depth 6 | Out-File $OutputPath -Encoding UTF8

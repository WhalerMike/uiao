param(
    [Parameter(Mandatory = $true)]
        [string] $InputPath,   # Raw SCuBA JSON file
            [Parameter(Mandatory = $true)]
                [string] $OutputPath   # Normalized JSON file
                )

                # Load raw SCuBA results
                $raw = Get-Content $InputPath -Raw | ConvertFrom-Json

                # NOTE: Adjust these mappings to match actual ScubaGear field names
                $normalized = [pscustomobject]@{
                    assessment_metadata = [pscustomobject]@{
                            assessment_date = $raw.AssessmentDate
                                    tool_version    = $raw.ToolVersion
                                            collector_host  = $raw.CollectorHost
                                                    collector_user  = $raw.CollectorUser
                                                            run_id          = ("scuba-run-{0:yyyyMMdd-HHmmss}" -f (Get-Date))
                                                                }
                                                                    tenant = [pscustomobject]@{
                                                                            tenant_id       = $raw.TenantId
                                                                                    subscription_id = $raw.SubscriptionId
                                                                                        }
                                                                                            scuba_raw = [pscustomobject]@{
                                                                                                    results_file          = (Split-Path $InputPath -Leaf)
                                                                                                            settings_export_file  = $raw.SettingsExportFile
                                                                                                                    action_plan_file      = $raw.ActionPlanFile
                                                                                                                        }
                                                                                                                            normalized = [pscustomobject]@{
                                                                                                                                    fields = [pscustomobject]@{
                                                                                                                                                MFAEnabled                     = [bool]$raw.Config.MFAEnabled
                                                                                                                                                            LegacyAuthEnabled              = [bool]$raw.Config.LegacyAuthEnabled
                                                                                                                                                                        AdminCount                     = [int] $raw.Config.AdminCount
                                                                                                                                                                                    ExternalForwardingAllowed      = [bool]$raw.Config.ExternalForwardingAllowed
                                                                                                                                                                                                MailboxAuditingEnabled         = [bool]$raw.Config.MailboxAuditingEnabled
                                                                                                                                                                                                            ExternalSharingEnabled         = [bool]$raw.Config.ExternalSharingEnabled
                                                                                                                                                                                                                        SafeLinksEnabled               = [bool]$raw.Config.SafeLinksEnabled
                                                                                                                                                                                                                                    SafeAttachmentsEnabled         = [bool]$raw.Config.SafeAttachmentsEnabled
                                                                                                                                                                                                                                                ConditionalAccessPoliciesCount = [int] $raw.Config.ConditionalAccessPoliciesCount
                                                                                                                                                                                                                                                            DLPPoliciesCount               = [int] $raw.Config.DLPPoliciesCount
                                                                                                                                                                                                                                                                    }
                                                                                                                                                                                                                                                                        }
                                                                                                                                                                                                                                                                            ksi_results = @()  # Filled by evaluate-ksi.ps1
                                                                                                                                                                                                                                                                            }
                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                            $normalized | ConvertTo-Json -Depth 8 | Out-File $OutputPath -Encoding UTF8

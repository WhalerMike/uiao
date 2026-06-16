@{
    # PSScriptAnalyzer ruleset for the UIAO PowerShell surface (~149 .ps1,
    # 9 .psm1, 7 .psd1). Consumed by .github/workflows/pwsh-lint.yml.
    #
    # Gate posture: the `analyze` job runs NON-BLOCKING (continue-on-error)
    # to establish a baseline without instantly reddening CI — the same
    # "land non-blocking, burn the baseline down, then flip to blocking"
    # pattern AGENTS.md records for ruff.yml and mypy.yml. Once the
    # warning baseline is cleared, drop `continue-on-error` from the job so
    # this becomes a hard gate.

    # Surface Errors and Warnings; Information-severity rules are too noisy
    # for a first baseline.
    Severity = @('Error', 'Warning')

    ExcludeRules = @(
        # Operator-facing one-shot scripts legitimately print status to the
        # host (these are interactive tools, not library functions whose
        # output is captured by a caller).
        'PSAvoidUsingWriteHost',

        # Many scripts here are deliberately imperative one-shots, not
        # advanced functions with -WhatIf/-Confirm plumbing. Requiring
        # ShouldProcess on every state-changing function is noise for this
        # tooling tier; the runtime adapters that DO mutate Entra/ARM/AD are
        # dry-run-by-default at a higher layer.
        'PSUseShouldProcessForStateChangingFunctions',

        # Positional parameters are idiomatic in short operator scripts.
        'PSAvoidUsingPositionalParameters'
    )
}

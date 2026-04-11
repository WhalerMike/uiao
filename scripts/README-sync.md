# sync-uiao.ps1  Canonical UIAO-Core Sync Script

**Classification:** Controlled
**Repository:** `uiao-core`
**Location:** `/scripts/sync-uiao.ps1`
**Author:** Michael Stratton

---

## Purpose

Deterministic, governance-aligned sync script for aligning a local `uiao-core` clone to `origin/main`. Designed for VM-based substrates where reproducibility, zero-drift, and zero-loss guarantees are non-negotiable.

Every run produces a timestamped transcript log. Every mode emits deterministic, parseable output. No hidden state, no surprises.

---

## Modes

| Mode | Switch | Behavior | Data Loss Risk |
|------|--------|----------|----------------|
| **Safe** | *(default)* | Aborts if any uncommitted changes exist | None  refuses to act |
| **Force** | `-Force` | Stashes all changes, syncs, auto-restores | None  stash preserved on conflict |
| **Nuclear** | `-Nuclear` | Deletes local repo, reclones from origin | **Total**  all local state destroyed |

> **Rule:** `-Force` and `-Nuclear` are mutually exclusive. The script will exit with an error if both are supplied.
>
> ---
>
> ## Usage
>
> ### Safe Mode (default)
>
> ```powershell
> .\sync-uiao.ps1
> ```
>
> Refuses to run if local drift (uncommitted changes) is detected.
>
> **Flow:** Validate repo > ensure `main` > check drift > fetch > hard-reset > clean > done.
>
> ### Force Mode (stash > sync > auto-restore)
>
> ```powershell
> .\sync-uiao.ps1 -Force
> ```
>
> **Guarantees:**
> - Zero drift after sync
> - - Zero loss  changes are either restored or safely preserved in the stash
>   - - Stash label format: `uiao-auto-stash-YYYY-MM-DD_HH-MM-SS`
>    
>     - ### Nuclear Mode (delete > reclone)
>    
>     - ```powershell
>       .\sync-uiao.ps1 -Nuclear
>       ```
>
> > **Warning:** Destroys all local state including stashes, branches, and untracked files. No recovery path.
> >
> > ---
> >
> > ## Parameters
> >
> > | Parameter | Type | Default | Description |
> > |-----------|------|---------|-------------|
> > | `-Force` | Switch | `$false` | Enable Force Mode |
> > | `-Nuclear` | Switch | `$false` | Enable Nuclear Mode |
> > | `-LogDir` | String | `~\uiao-logs` | Directory for transcript log files |
> >
> > ---
> >
> > ## Transcript Logging
> >
> > Every execution produces a transcript log at:
> >
> > ```
> > %USERPROFILE%\uiao-logs\sync-uiao_YYYY-MM-DD_HH-MM-SS.log
> > ```
> >
> > Override with `-LogDir`:
> >
> > ```powershell
> > .\sync-uiao.ps1 -Force -LogDir "D:\logs\uiao"
> > ```
> >
> > ---
> >
> > ## Guardrails
> >
> > | Guardrail | Behavior |
> > |-----------|----------|
> > | **Repo existence** | Validates both path and `.git` directory |
> > | **Branch enforcement** | Auto-switches to `main` if on a different branch |
> > | **Drift detection** | Safe Mode blocks; Force Mode stashes first |
> > | **Mutual exclusion** | `-Force` + `-Nuclear` = immediate error exit |
> > | **Stash conflict safety** | Stash preserved on merge conflict |
> > | **Git exit codes** | `Invoke-Git` throws on non-zero exit |
> > | **Error action** | `$ErrorActionPreference = 'Stop'` |
> >
> > ---
> >
> > ## Exit Codes
> >
> > | Code | Meaning |
> > |------|---------||
> > | `0` | Sync completed successfully |
> > | `1` | Drift detected (Safe Mode), validation failure, or mutual-exclusion violation |
> >
> > ---
> >
> > ## Decision Tree
> >
> > ```
> > Start
> >  |
> >  +- -Nuclear? --> Delete repo --> Reclone --> Exit 0
> >  |
> >  +- Repo exists? --> No --> Exit 1
> >  |
> >  +- On main? --> No --> git checkout main
> >  |
> >  +- Drift detected?
> >  |   +- No --> Fetch --> Reset --> Clean --> Exit 0
> >  |   +- Yes + Safe Mode --> Print drift --> Exit 1
> >  |   +- Yes + Force Mode --> Stash --> Fetch --> Reset --> Clean --> Pop stash
> >  |       +- Pop clean --> Exit 0
> >  |       +- Pop conflicts --> Warn --> Preserve stash --> Exit 0
> >  |
> >  +- Done
> > ```
> >
> > ---
> >
> > ## Integration
> >
> > ### Scheduled Task (Windows Task Scheduler)
> >
> > ```powershell
> > $Action  = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument "-File C:\Users\whale\uiao-core\scripts\sync-uiao.ps1"
> > $Trigger = New-ScheduledTaskTrigger -Daily -At 6am
> > Register-ScheduledTask -TaskName "UIAO-Core-DailySync" -Action $Action -Trigger $Trigger
> > ```
> >
> > ### GitHub Actions
> >
> > ```yaml
> > - name: Sync UIAO-Core
> >   run: pwsh -File ./scripts/sync-uiao.ps1
> >   shell: pwsh
> > ```
> >
> > ---
> >
> > ## Troubleshooting
> >
> > | Symptom | Cause | Fix |
> > |---------|-------|-----|
> > | `FAIL Not a valid Git repo` | Missing `.git` directory | Run `-Nuclear` to reclone |
> > | `FAIL Uncommitted changes detected` | Local drift in Safe Mode | Use `-Force` or commit/discard |
> > | `WARN Stash pop had conflicts` | Origin changes conflict with local work | Resolve manually, then `git stash drop` |
> > | `WARN Could not locate stash` | Stash label mismatch | Run `git stash list` and apply manually |
> > | Log file not created | Invalid path or permissions | Verify `-LogDir` path |
> >
> > ---
> >
> > ## Governance Notes
> >
> > - **Canonical artifact** in the UIAO-Core repository
> > - - Classification: **Controlled** (per UIAO Canon  not FOUO)
> >   - - Operates exclusively against `origin/main`
> >     - - No secrets, tokens, or credentials stored or transmitted
> >       - 

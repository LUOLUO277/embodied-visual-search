Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$syncScript = Join-Path $PSScriptRoot "sync_backend_code.ps1"

$watchTargets = @(
    (Join-Path $repoRoot "backend"),
    (Join-Path $repoRoot "requirements.txt"),
    (Join-Path $repoRoot "start_backend.sh"),
    (Join-Path $repoRoot "scripts/check_ai2thor.py"),
    (Join-Path $repoRoot "scripts/import_official_test_tasks.py"),
    (Join-Path $repoRoot "scripts/smoke_action_adapter.py"),
    (Join-Path $repoRoot "scripts/smoke_agent_loop.py")
)

$script:lastSync = [datetime]::MinValue
$script:isSyncing = $false

function Invoke-MirrorSync {
    if ($script:isSyncing) {
        return
    }

    $now = Get-Date
    if (($now - $script:lastSync).TotalMilliseconds -lt 300) {
        return
    }

    $script:isSyncing = $true
    try {
        & powershell -ExecutionPolicy Bypass -File $syncScript -Quiet
        $script:lastSync = Get-Date
        Write-Host ("[{0}] Synced Code mirror." -f $script:lastSync.ToString("yyyy-MM-dd HH:mm:ss"))
    } finally {
        $script:isSyncing = $false
    }
}

$watchers = New-Object System.Collections.Generic.List[System.IO.FileSystemWatcher]
$registrations = New-Object System.Collections.Generic.List[System.Management.Automation.PSEventJob]

foreach ($target in $watchTargets) {
    if (Test-Path -LiteralPath $target -PathType Container) {
        $watcher = New-Object System.IO.FileSystemWatcher
        $watcher.Path = $target
        $watcher.Filter = '*'
        $watcher.IncludeSubdirectories = $true
    } else {
        $watcher = New-Object System.IO.FileSystemWatcher
        $watcher.Path = Split-Path -Parent $target
        $watcher.Filter = Split-Path -Leaf $target
        $watcher.IncludeSubdirectories = $false
    }

    $watcher.NotifyFilter = [System.IO.NotifyFilters]::FileName -bor [System.IO.NotifyFilters]::DirectoryName -bor [System.IO.NotifyFilters]::LastWrite -bor [System.IO.NotifyFilters]::CreationTime
    $watcher.EnableRaisingEvents = $true
    $watchers.Add($watcher) | Out-Null

    foreach ($eventName in @('Changed', 'Created', 'Deleted', 'Renamed')) {
        $registration = Register-ObjectEvent -InputObject $watcher -EventName $eventName -Action {
            Invoke-MirrorSync
        }
        $registrations.Add($registration) | Out-Null
    }
}

Invoke-MirrorSync
Write-Host 'Watching backend-related files. Press Ctrl+C to stop.'

try {
    while ($true) {
        Wait-Event -Timeout 1 | Out-Null
    }
} finally {
    foreach ($registration in $registrations) {
        Unregister-Event -SubscriptionId $registration.Id -ErrorAction SilentlyContinue
        Remove-Job -Id $registration.Id -Force -ErrorAction SilentlyContinue
    }

    foreach ($watcher in $watchers) {
        $watcher.EnableRaisingEvents = $false
        $watcher.Dispose()
    }
}
param(
    [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$codeRoot = Join-Path $repoRoot "Code"

$fileSpecs = @(
    @{ Source = "backend/api/routes_agent.py"; Target = "01_routes_agent.py"; Note = "FastAPI agent route entry" },
    @{ Source = "backend/agents/llm_embodied_agent.py"; Target = "02_llm_embodied_agent.py"; Note = "Agent main loop" },
    @{ Source = "backend/llm/prompt_builder.py"; Target = "03_prompt_builder.py"; Note = "Prompt assembly" },
    @{ Source = "backend/llm/openai_compatible_client.py"; Target = "04_openai_compatible_client.py"; Note = "Model request client" },
    @{ Source = "backend/llm/output_parser.py"; Target = "05_output_parser.py"; Note = "Model output parser" },
    @{ Source = "backend/actions/action_adapter.py"; Target = "06_action_adapter.py"; Note = "High-level action executor" },
    @{ Source = "backend/actions/object_resolver.py"; Target = "07_object_resolver.py"; Note = "Object resolution" },
    @{ Source = "backend/actions/base_action.py"; Target = "08_base_action.py"; Note = "AI2-THOR primitive actions" },
    @{ Source = "backend/envs/thor_env.py"; Target = "09_thor_env.py"; Note = "Environment wrapper" },
    @{ Source = "backend/memory/trajectory.py"; Target = "10_trajectory.py"; Note = "Trajectory recording" },
    @{ Source = "backend/memory/search_state.py"; Target = "11_search_state.py"; Note = "Runtime search state" }
)

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Same-FileContent {
    param(
        [string]$SourcePath,
        [string]$TargetPath
    )

    if (-not (Test-Path -LiteralPath $TargetPath)) {
        return $false
    }

    $sourceHash = (Get-FileHash -LiteralPath $SourcePath -Algorithm SHA256).Hash
    $targetHash = (Get-FileHash -LiteralPath $TargetPath -Algorithm SHA256).Hash
    return $sourceHash -eq $targetHash
}

function Sync-File {
    param(
        [string]$SourcePath,
        [string]$TargetPath
    )

    if (-not (Same-FileContent -SourcePath $SourcePath -TargetPath $TargetPath)) {
        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
    }
}

Ensure-Directory -Path $codeRoot

$expectedNames = New-Object System.Collections.Generic.HashSet[string]
[void]$expectedNames.Add('README.md')

$readmeLines = @(
    '# Code',
    '',
    '这里只保留 Agent 一次完整执行主链路的关键后端代码，并直接平铺在 Code 根目录。',
    '',
    '阅读顺序：'
)

foreach ($spec in $fileSpecs) {
    $sourcePath = Join-Path $repoRoot $spec.Source
    $targetPath = Join-Path $codeRoot $spec.Target
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Source path does not exist: $sourcePath"
    }

    Sync-File -SourcePath $sourcePath -TargetPath $targetPath
    [void]$expectedNames.Add($spec.Target)
    $readmeLines += "- $($spec.Target) <- $($spec.Source) : $($spec.Note)"
}

$readmeLines += ''
$readmeLines += '同步方式：'
$readmeLines += '- 手动同步：powershell -ExecutionPolicy Bypass -File .\scripts\sync_backend_code.ps1'
$readmeLines += '- 持续监听：powershell -ExecutionPolicy Bypass -File .\scripts\watch_backend_code.ps1'

$readmeContent = $readmeLines -join [Environment]::NewLine
Set-Content -LiteralPath (Join-Path $codeRoot 'README.md') -Value $readmeContent -NoNewline

Get-ChildItem -LiteralPath $codeRoot -Force | ForEach-Object {
    if (-not $expectedNames.Contains($_.Name)) {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }
}

if (-not $Quiet) {
    Write-Host "Synced key backend files into $codeRoot"
}
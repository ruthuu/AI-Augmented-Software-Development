<#
.SYNOPSIS
  Independent verification harness for SpendWise. Runs every check, stores raw evidence in a new
  folder, and derives each status from the real exit code and output.

.DESCRIPTION
  Usage (from the repository root, Part-1A):
    .\harness\run-harness.ps1 -OutDir evidence\initial-generation
    .\harness\run-harness.ps1 -SelfTest -OutDir evidence\repairs\run-0-selftest

  Statuses (exactly these): PASS, FAIL, ERROR, NOT RUN.
    NOT RUN  the check's subject does not exist yet (precondition unmet), or a scan found nothing to
             scan (scan exit code 3); the command is not executed and the exit code is 'n/a'.
    ERROR    the command could not start, the harness threw, the command timed out, a server never
             answered, or the tool itself failed (pytest exit 2, 3, 4; ruff exit 2; scan exit code
             other than 0, 1, 3).
    PASS     exit code 0 AND the check was not vacuous (tests ran, a coverage percentage was
             reported, an API case was compared, files were scanned).
    FAIL     every other outcome, including exit 0 without a meaningful result and pytest exit 5.

  The harness never edits application code, never reads application output to derive an expected
  value, and refuses to write into a folder that already contains anything.

  Process exit code: 0 all required checks PASS; 1 at least one required check FAIL or ERROR;
  3 no required check failed but at least one required check is NOT RUN; 2 harness usage error.
  With -SelfTest: 0 when the four synthetic checks produced exactly PASS, FAIL, ERROR, NOT RUN;
  1 otherwise.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OutDir,
    [switch]$SelfTest
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
# Resolved before Set-Location so a relative -OutDir means relative to the caller's folder.
$OutPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutDir)
Set-Location -LiteralPath $RepoRoot

function Write-Text {
    param([string]$Path, [string]$Text)
    [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom)
}

function Get-NowUtc {
    (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}

# ---------------------------------------------------------------- output folder
if (Test-Path -LiteralPath $OutPath) {
    if (-not (Test-Path -LiteralPath $OutPath -PathType Container)) {
        [Console]::Error.WriteLine("Refusing to run: '$OutPath' exists and is not a folder.")
        exit 2
    }
    if (@(Get-ChildItem -LiteralPath $OutPath -Force).Count -gt 0) {
        [Console]::Error.WriteLine("Refusing to run: '$OutPath' is not empty. Evidence is never overwritten; use a new folder.")
        exit 2
    }
}
else {
    New-Item -ItemType Directory -Path $OutPath | Out-Null
}

$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Python = 'python'
if (Test-Path -LiteralPath $VenvPython) { $Python = $VenvPython }
$YarnCmd = Get-Command 'yarn.cmd' -ErrorAction SilentlyContinue | Select-Object -First 1
$Yarn = 'yarn'
if ($YarnCmd) { $Yarn = $YarnCmd.Source }

$WorkTemp = Join-Path ([System.IO.Path]::GetTempPath()) ('spendwise-harness-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $WorkTemp | Out-Null
$CoverageFile = Join-Path $WorkTemp 'coverage-data'

$script:Results = New-Object System.Collections.ArrayList
$RunStart = Get-NowUtc

# ---------------------------------------------------------------- process helpers
function Invoke-External {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutSeconds = 900,
        [hashtable]$ExtraEnv = @{}
    )
    $outcome = @{ Started = $false; TimedOut = $false; ExitCode = $null; Stdout = ''; Stderr = ''; Error = '' }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $psi.EnvironmentVariables['PYTHONUTF8'] = '1'
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $psi.EnvironmentVariables['CI'] = '1'
    $psi.EnvironmentVariables['NO_COLOR'] = '1'
    foreach ($key in $ExtraEnv.Keys) { $psi.EnvironmentVariables[[string]$key] = [string]$ExtraEnv[$key] }
    try {
        $process = [System.Diagnostics.Process]::Start($psi)
    }
    catch {
        $outcome.Error = $_.Exception.Message
        return $outcome
    }
    $outcome.Started = $true
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $outcome.TimedOut = $true
        & taskkill.exe /PID $process.Id /T /F 2>&1 | Out-Null
        $process.WaitForExit()
    }
    else {
        $process.WaitForExit()
        $outcome.ExitCode = $process.ExitCode
    }
    $outcome.Stdout = $stdoutTask.Result
    $outcome.Stderr = $stderrTask.Result
    return $outcome
}

function Get-FirstLine {
    param([string]$Text)
    foreach ($line in ($Text -split "`r?`n")) {
        if ($line.Trim().Length -gt 0) { return $line.Trim() }
    }
    return 'unavailable'
}

function Get-ToolVersion {
    param([string]$FilePath, [string]$Arguments)
    $r = Invoke-External -FilePath $FilePath -Arguments $Arguments -WorkingDirectory $RepoRoot -TimeoutSeconds 60
    if (-not $r.Started) { return 'not found' }
    $text = $r.Stdout
    if ((Get-FirstLine $text) -eq 'unavailable') { $text = $r.Stderr }
    return (Get-FirstLine $text)
}

# ---------------------------------------------------------------- status derivation
function Get-Verdict {
    param([string]$Tool, $ExitCode, [string]$Stdout)
    $code = [int]$ExitCode
    $passedCount = 0
    if ($Stdout -match '(\d+) passed') { $passedCount = [int]$Matches[1] }
    $hasCoverage = ($Stdout -match 'TOTAL\s+.*?\d+%') -or ($Stdout -match 'Total coverage:\s*[\d.]+%')
    switch ($Tool) {
        'pytest' {
            if (@(2, 3, 4) -contains $code) { return @{ Status = 'ERROR'; Reason = "pytest tool-level failure (exit code $code)" } }
            if ($code -eq 0) {
                if ($passedCount -gt 0) { return @{ Status = 'PASS'; Reason = "$passedCount tests passed" } }
                return @{ Status = 'FAIL'; Reason = 'exit code 0 but no test reported as passed (vacuous)' }
            }
            return @{ Status = 'FAIL'; Reason = "pytest exit code $code" }
        }
        'pytestcov' {
            if (@(2, 3, 4) -contains $code) { return @{ Status = 'ERROR'; Reason = "pytest tool-level failure (exit code $code)" } }
            if ($code -eq 0) {
                if ($passedCount -gt 0 -and $hasCoverage) { return @{ Status = 'PASS'; Reason = "$passedCount tests passed and a coverage percentage was reported" } }
                return @{ Status = 'FAIL'; Reason = 'exit code 0 but tests or the coverage percentage are missing (vacuous)' }
            }
            return @{ Status = 'FAIL'; Reason = "pytest exit code $code" }
        }
        'ruff' {
            if ($code -eq 2) { return @{ Status = 'ERROR'; Reason = 'ruff tool-level failure (exit code 2)' } }
            if ($code -eq 0) { return @{ Status = 'PASS'; Reason = 'exit code 0' } }
            return @{ Status = 'FAIL'; Reason = "exit code $code" }
        }
        'coverage' {
            if ($code -eq 0) {
                if ($hasCoverage) { return @{ Status = 'PASS'; Reason = 'coverage percentage reported and threshold met' } }
                return @{ Status = 'FAIL'; Reason = 'exit code 0 but no coverage percentage was reported (vacuous)' }
            }
            return @{ Status = 'FAIL'; Reason = "exit code $code" }
        }
        'scan' {
            if ($code -eq 3) { return @{ Status = 'NOT RUN'; Reason = 'nothing to scan (zero files examined)' } }
            if ($code -eq 0) {
                if ($Stdout -match 'FILES_EXAMINED=(\d+)' -and [int]$Matches[1] -gt 0) { return @{ Status = 'PASS'; Reason = "$($Matches[1]) files scanned, no findings" } }
                return @{ Status = 'FAIL'; Reason = 'exit code 0 but no file was examined (vacuous)' }
            }
            if ($code -eq 1) { return @{ Status = 'FAIL'; Reason = 'the scan reported findings (file, line, and rule only; see stdout)' } }
            return @{ Status = 'ERROR'; Reason = "scanner failed (exit code $code)" }
        }
        'tracked' {
            if ($code -eq 0) { return @{ Status = 'PASS'; Reason = 'no tracked .env or *.db file' } }
            if ($code -eq 1) { return @{ Status = 'FAIL'; Reason = 'a tracked .env or *.db file was found' } }
            return @{ Status = 'ERROR'; Reason = "scanner failed (exit code $code)" }
        }
        'yarntest' {
            if ($code -eq 0) {
                if ($passedCount -gt 0) { return @{ Status = 'PASS'; Reason = "$passedCount tests passed" } }
                return @{ Status = 'FAIL'; Reason = 'exit code 0 but no test reported as passed (vacuous)' }
            }
            return @{ Status = 'FAIL'; Reason = "exit code $code" }
        }
        'api' {
            $compared = 0
            if ($Stdout -match 'compared=(\d+)') { $compared = [int]$Matches[1] }
            if ($code -eq 0) {
                if ($compared -gt 0) { return @{ Status = 'PASS'; Reason = "$compared cases compared and all matched" } }
                return @{ Status = 'FAIL'; Reason = 'exit code 0 but no case was compared (vacuous)' }
            }
            if ($code -eq 1) { return @{ Status = 'FAIL'; Reason = 'at least one case did not match the expected value' } }
            return @{ Status = 'ERROR'; Reason = "the API check runner could not complete (exit code $code)" }
        }
        default {
            if ($code -eq 0) { return @{ Status = 'PASS'; Reason = 'exit code 0' } }
            return @{ Status = 'FAIL'; Reason = "exit code $code" }
        }
    }
}

# ---------------------------------------------------------------- recording
function Complete-Check {
    param(
        [string]$Id, [string]$Kind, [string]$Command, [string]$Cwd,
        [string]$StartUtc, [string]$EndUtc, [string]$ExitText,
        [string]$Status, [string]$Reason, [string]$Stdout, [string]$Stderr,
        [string[]]$ExtraFiles = @()
    )
    Write-Text (Join-Path $OutPath "$Id.stdout.txt") $Stdout
    Write-Text (Join-Path $OutPath "$Id.stderr.txt") $Stderr
    Write-Text (Join-Path $OutPath "$Id.exitcode.txt") ($ExitText + "`n")
    $meta = [ordered]@{
        id = $Id; kind = $Kind; command = $Command; working_directory = $Cwd
        start_utc = $StartUtc; end_utc = $EndUtc; exit_code = $ExitText
        status = $Status; reason = $Reason
    }
    Write-Text (Join-Path $OutPath "$Id.meta.json") ((ConvertTo-Json -InputObject $meta -Depth 4) + "`n")
    $files = @("$Id.stdout.txt", "$Id.stderr.txt", "$Id.exitcode.txt", "$Id.meta.json") + $ExtraFiles
    [void]$script:Results.Add([ordered]@{
            id = $Id; kind = $Kind; command = $Command; status = $Status; exit_code = $ExitText
            reason = $Reason; start_utc = $StartUtc; end_utc = $EndUtc; files = [string[]]$files
        })
    Write-Host ("{0,-8} {1,-26} {2}" -f $Status, $Id, $Reason)
}

function Invoke-Check {
    param([hashtable]$Check)
    $kind = $Check.Kind
    if (-not $kind) { $kind = 'required' }
    $cwd = $RepoRoot
    if ($Check.Cwd) { $cwd = $Check.Cwd }
    $pre = $null
    if ($Check.Pre) { $pre = & $Check.Pre }
    $now = Get-NowUtc
    if ($pre) {
        Complete-Check -Id $Check.Id -Kind $kind -Command $Check.Display -Cwd $cwd -StartUtc $now -EndUtc $now `
            -ExitText 'n/a' -Status 'NOT RUN' -Reason ("precondition not met: " + $pre) -Stdout '' -Stderr ''
        return
    }
    $timeout = 900
    if ($Check.Timeout) { $timeout = $Check.Timeout }
    $extraEnv = @{}
    if ($Check.Env) { $extraEnv = $Check.Env }
    $start = Get-NowUtc
    $r = Invoke-External -FilePath $Check.Exe -Arguments $Check.Args -WorkingDirectory $cwd -TimeoutSeconds $timeout -ExtraEnv $extraEnv
    $end = Get-NowUtc
    if (-not $r.Started) {
        Complete-Check -Id $Check.Id -Kind $kind -Command $Check.Display -Cwd $cwd -StartUtc $start -EndUtc $end `
            -ExitText 'n/a' -Status 'ERROR' -Reason ("the command could not be started: " + $r.Error) -Stdout '' -Stderr ''
        return
    }
    if ($r.TimedOut) {
        Complete-Check -Id $Check.Id -Kind $kind -Command $Check.Display -Cwd $cwd -StartUtc $start -EndUtc $end `
            -ExitText 'timeout' -Status 'ERROR' -Reason "the command did not finish within $timeout seconds and was stopped" `
            -Stdout $r.Stdout -Stderr $r.Stderr
        return
    }
    $verdict = Get-Verdict -Tool $Check.Tool -ExitCode $r.ExitCode -Stdout $r.Stdout
    Complete-Check -Id $Check.Id -Kind $kind -Command $Check.Display -Cwd $cwd -StartUtc $start -EndUtc $end `
        -ExitText ([string]$r.ExitCode) -Status $verdict.Status -Reason $verdict.Reason -Stdout $r.Stdout -Stderr $r.Stderr
}

# ---------------------------------------------------------------- preconditions
function Test-HasAppPython {
    $appDir = Join-Path $RepoRoot 'backend\app'
    if (-not (Test-Path -LiteralPath $appDir)) { return $false }
    foreach ($file in Get-ChildItem -LiteralPath $appDir -Recurse -Filter '*.py' -File) {
        if ($file.Name -ne '__init__.py') { return $true }
        if ((Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue) -match '\S') { return $true }
    }
    return $false
}

function Test-HasBackendTests {
    $dir = Join-Path $RepoRoot 'backend\tests'
    if (-not (Test-Path -LiteralPath $dir)) { return $false }
    return (@(Get-ChildItem -LiteralPath $dir -Recurse -Filter 'test_*.py' -File).Count -gt 0)
}

function Test-HasFrontendApp {
    return (Test-Path -LiteralPath (Join-Path $RepoRoot 'frontend\src\api\client.ts'))
}

function Get-ResultById {
    param([string]$Id)
    foreach ($r in $script:Results) { if ($r.id -eq $Id) { return $r } }
    return $null
}

# ---------------------------------------------------------------- environment, git state, manifest
function Write-EnvironmentRecord {
    $os = 'unknown'
    try {
        $info = Get-CimInstance -ClassName Win32_OperatingSystem
        $os = "$($info.Caption) $($info.Version)"
    }
    catch { $os = [System.Environment]::OSVersion.VersionString }
    $lines = @(
        'Tool versions only. No environment variable values are recorded.',
        "OS: $os",
        "PowerShell: $($PSVersionTable.PSVersion)",
        "Python: $(Get-ToolVersion $Python '--version')",
        "ruff: $(Get-ToolVersion $Python '-m ruff --version')",
        "pytest: $(Get-ToolVersion $Python '-m pytest --version')",
        "bandit: $(Get-ToolVersion $Python '-m bandit --version')",
        "coverage: $(Get-ToolVersion $Python '-m coverage --version')",
        "Node: $(Get-ToolVersion 'node' '--version')",
        "Yarn: $(Get-ToolVersion $Yarn '--version')",
        "git: $(Get-ToolVersion 'git' '--version')"
    )
    Write-Text (Join-Path $OutPath 'environment.txt') (($lines -join "`n") + "`n")
}

function Write-GitState {
    $head = Invoke-External -FilePath 'git' -Arguments 'rev-parse HEAD' -WorkingDirectory $RepoRoot -TimeoutSeconds 60
    $status = Invoke-External -FilePath 'git' -Arguments 'status --porcelain' -WorkingDirectory $RepoRoot -TimeoutSeconds 60
    $headText = 'unavailable'
    if ($head.Started -and $head.ExitCode -eq 0) { $headText = (Get-FirstLine $head.Stdout) }
    elseif ($head.Started) { $headText = 'no commit yet or not a repository' }
    $statusText = ''
    if ($status.Started) { $statusText = $status.Stdout }
    Write-Text (Join-Path $OutPath 'git-state.txt') ("git rev-parse HEAD`n$headText`n`ngit status --porcelain`n$statusText")
}

$ManifestPruneDirs = @('node_modules', 'dist', '.venv', '__pycache__', '.pytest_cache', '.ruff_cache', 'coverage', 'htmlcov', 'data', '.git')

function Test-ManifestExcludedFile {
    param([string]$Name)
    if ($Name -eq '.env') { return $true }
    if ($Name -like '.env.*' -and $Name -ne '.env.example') { return $true }
    if ($Name -like '*.log' -or $Name -like '*.db' -or $Name -like '.coverage*' -or $Name -like '*.pyc') { return $true }
    return $false
}

function Get-ManifestFiles {
    $found = New-Object System.Collections.ArrayList
    foreach ($top in @('backend', 'frontend', 'harness')) {
        $start = Join-Path $RepoRoot $top
        if (-not (Test-Path -LiteralPath $start)) { continue }
        $pending = New-Object System.Collections.Stack
        $pending.Push($start)
        while ($pending.Count -gt 0) {
            $dir = $pending.Pop()
            foreach ($sub in [System.IO.Directory]::GetDirectories($dir)) {
                $leaf = Split-Path -Leaf $sub
                if ($ManifestPruneDirs -notcontains $leaf) { $pending.Push($sub) }
            }
            foreach ($file in [System.IO.Directory]::GetFiles($dir)) {
                if (-not (Test-ManifestExcludedFile (Split-Path -Leaf $file))) { [void]$found.Add($file) }
            }
        }
    }
    $readme = Join-Path $RepoRoot 'README.md'
    if (Test-Path -LiteralPath $readme) { [void]$found.Add($readme) }
    return $found
}

function Write-Manifest {
    $lines = New-Object System.Collections.ArrayList
    foreach ($file in (Get-ManifestFiles)) {
        $relative = $file.Substring($RepoRoot.Length + 1).Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        [void]$lines.Add("$hash  $relative")
    }
    $sorted = @($lines | Sort-Object { $_.Substring(66) } -CaseSensitive)
    Write-Text (Join-Path $OutPath 'manifest.sha256.txt') (($sorted -join "`n") + "`n")
}

# ---------------------------------------------------------------- black-box API checks
function Get-FreePort {
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = $listener.LocalEndpoint.Port
    $listener.Stop()
    return $port
}

function Start-AppServer {
    param([int]$Port, [string]$DbPath, [int]$Number)
    $stdout = Join-Path $OutPath "api-server-$Number.stdout.txt"
    $stderr = Join-Path $OutPath "api-server-$Number.stderr.txt"
    $saved = @{}
    foreach ($name in @('SPENDWISE_DB_PATH', 'SPENDWISE_TODAY', 'SPENDWISE_CORS_ORIGINS')) {
        $saved[$name] = [System.Environment]::GetEnvironmentVariable($name, 'Process')
    }
    try {
        [System.Environment]::SetEnvironmentVariable('SPENDWISE_DB_PATH', $DbPath, 'Process')
        [System.Environment]::SetEnvironmentVariable('SPENDWISE_TODAY', '2026-11-12', 'Process')
        [System.Environment]::SetEnvironmentVariable('SPENDWISE_CORS_ORIGINS', $null, 'Process')
        $arguments = "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port"
        $process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $RepoRoot `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru
    }
    finally {
        foreach ($name in $saved.Keys) { [System.Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
    }
    return $process
}

function Wait-AppServer {
    param($Process, [int]$Port, [int]$Seconds = 40)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) { return $false }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/api/config" -TimeoutSec 3
            if ($response.StatusCode -eq 200) { return $true }
        }
        catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

function Stop-AppServer {
    param($Process)
    if ($Process -and -not $Process.HasExited) {
        & taskkill.exe /PID $Process.Id /T /F 2>&1 | Out-Null
        [void]$Process.WaitForExit(15000)
    }
}

function Add-ApiError {
    param([string]$Id, [string]$Kind, [string]$Display, [string]$Reason, [string[]]$ExtraFiles = @())
    $now = Get-NowUtc
    Complete-Check -Id $Id -Kind $Kind -Command $Display -Cwd $RepoRoot -StartUtc $now -EndUtc $now `
        -ExitText 'n/a' -Status 'ERROR' -Reason $Reason -Stdout '' -Stderr '' -ExtraFiles $ExtraFiles
}

function Invoke-ApiChecks {
    $apiFile = Join-Path $OutPath 'api-results.json'
    $runner = Join-Path $PSScriptRoot 'run_api_checks.py'
    $dbPath = Join-Path $WorkTemp 'spendwise-harness.db'
    $port = Get-FreePort
    $base = "http://127.0.0.1:$port"
    $server = $null
    $up = $false
    try {
        $server = Start-AppServer -Port $port -DbPath $dbPath -Number 1
        $up = Wait-AppServer -Process $server -Port $port
    }
    catch { $up = $false }
    $serverFiles1 = @('api-server-1.stdout.txt', 'api-server-1.stderr.txt')
    if (-not $up) {
        Stop-AppServer $server
        $reason = 'the server was started but never answered GET /api/config'
        Add-ApiError 'API-write' 'required' 'run_api_checks.py --phase write' $reason $serverFiles1
        Add-ApiError 'API-verify' 'required' 'run_api_checks.py --phase verify' $reason $serverFiles1
        Add-ApiError 'API-timing' 'supplementary' 'run_api_checks.py --phase timing' $reason $serverFiles1
        return
    }
    $writeArgs = "`"$runner`" --base-url $base --phase write --out `"$apiFile`""
    Invoke-Check @{ Id = 'API-write'; Kind = 'required'; Exe = $Python; Args = $writeArgs; Tool = 'api'
        Display = "python harness\run_api_checks.py --base-url $base --phase write --out api-results.json" }
    Stop-AppServer $server

    $server2 = $null
    $up2 = $false
    try {
        $server2 = Start-AppServer -Port $port -DbPath $dbPath -Number 2
        $up2 = Wait-AppServer -Process $server2 -Port $port
    }
    catch { $up2 = $false }
    if (-not $up2) {
        Stop-AppServer $server2
        $reason = 'the restarted server never answered GET /api/config'
        Add-ApiError 'API-verify' 'required' 'run_api_checks.py --phase verify' $reason @('api-server-2.stdout.txt', 'api-server-2.stderr.txt')
        Add-ApiError 'API-timing' 'supplementary' 'run_api_checks.py --phase timing' $reason @('api-server-2.stdout.txt', 'api-server-2.stderr.txt')
        return
    }
    $verifyArgs = "`"$runner`" --base-url $base --phase verify --out `"$apiFile`" --append"
    Invoke-Check @{ Id = 'API-verify'; Kind = 'required'; Exe = $Python; Args = $verifyArgs; Tool = 'api'
        Display = "python harness\run_api_checks.py --base-url $base --phase verify --out api-results.json --append" }
    $timingArgs = "`"$runner`" --base-url $base --phase timing --out `"$apiFile`" --append"
    Invoke-Check @{ Id = 'API-timing'; Kind = 'supplementary'; Exe = $Python; Args = $timingArgs; Tool = 'api'; Timeout = 1800
        Display = "python harness\run_api_checks.py --base-url $base --phase timing --out api-results.json --append" }
    Stop-AppServer $server2
}

# ---------------------------------------------------------------- results files
function Write-Results {
    param([bool]$IsSelfTest, $SelfTestInfo)
    $counts = @{}
    foreach ($kind in @('required', 'supplementary')) {
        $counts[$kind] = [ordered]@{ 'PASS' = 0; 'FAIL' = 0; 'ERROR' = 0; 'NOT RUN' = 0 }
    }
    foreach ($r in $script:Results) { $counts[$r.kind][$r.status] = $counts[$r.kind][$r.status] + 1 }
    $apiResults = $null
    if (Test-Path -LiteralPath (Join-Path $OutPath 'api-results.json')) { $apiResults = 'api-results.json' }
    $doc = [ordered]@{
        run_folder = $OutPath
        mode = $(if ($IsSelfTest) { 'self-test' } else { 'full' })
        started_utc = $RunStart
        finished_utc = (Get-NowUtc)
        counts = [ordered]@{ required = $counts['required']; supplementary = $counts['supplementary'] }
        api_results_file = $apiResults
        self_test = $SelfTestInfo
        checks = [object[]]@($script:Results)
    }
    Write-Text (Join-Path $OutPath 'results.json') ((ConvertTo-Json -InputObject $doc -Depth 6) + "`n")

    $md = New-Object System.Collections.ArrayList
    [void]$md.Add('# Harness results')
    [void]$md.Add('')
    [void]$md.Add("Mode: $($doc.mode). Started $RunStart UTC, finished $($doc.finished_utc) UTC.")
    [void]$md.Add('')
    [void]$md.Add('| Kind | PASS | FAIL | ERROR | NOT RUN |')
    [void]$md.Add('|------|------|------|-------|---------|')
    foreach ($kind in @('required', 'supplementary')) {
        $c = $counts[$kind]
        [void]$md.Add("| $kind | $($c['PASS']) | $($c['FAIL']) | $($c['ERROR']) | $($c['NOT RUN']) |")
    }
    [void]$md.Add('')
    [void]$md.Add('A supplementary result never offsets a required one.')
    [void]$md.Add('')
    [void]$md.Add('| Check | Kind | Status | Exit code | Reason | Evidence files |')
    [void]$md.Add('|-------|------|--------|-----------|--------|----------------|')
    foreach ($r in $script:Results) {
        $reasonText = ([string]$r.reason).Replace('|', '/')
        [void]$md.Add("| $($r.id) | $($r.kind) | $($r.status) | $($r.exit_code) | $reasonText | $($r.files -join ', ') |")
    }
    if ($IsSelfTest -and $SelfTestInfo) {
        [void]$md.Add('')
        [void]$md.Add("Self-test: $($SelfTestInfo.summary)")
    }
    Write-Text (Join-Path $OutPath 'results.md') (($md -join "`n") + "`n")
    return $counts
}

# ---------------------------------------------------------------- self-test
if ($SelfTest) {
    Write-Host "Self-test: four synthetic checks. Output folder: $OutPath"
    Invoke-Check @{ Id = 'selftest-pass'; Kind = 'required'; Exe = $Python; Tool = 'pytest'
        Args = '-c "print(''1 passed in 0.01s'')"'; Display = 'python -c "print(''1 passed in 0.01s'')"' }
    Invoke-Check @{ Id = 'selftest-fail'; Kind = 'required'; Exe = $Python; Tool = 'generic'
        Args = '-c "import sys; sys.exit(1)"'; Display = 'python -c "import sys; sys.exit(1)"' }
    Invoke-Check @{ Id = 'selftest-error'; Kind = 'required'; Exe = 'spendwise-nonexistent-command-xyz'; Tool = 'generic'
        Args = ''; Display = 'spendwise-nonexistent-command-xyz' }
    Invoke-Check @{ Id = 'selftest-not-run'; Kind = 'required'; Exe = $Python; Tool = 'generic'
        Args = '-c "print(1)"'; Display = 'python -c "print(1)"'
        Pre = { 'synthetic subject that does not exist' } }
    $expected = [ordered]@{ 'selftest-pass' = 'PASS'; 'selftest-fail' = 'FAIL'; 'selftest-error' = 'ERROR'; 'selftest-not-run' = 'NOT RUN' }
    $ok = $true
    foreach ($id in $expected.Keys) {
        $r = Get-ResultById $id
        if (-not $r -or $r.status -ne $expected[$id]) { $ok = $false }
    }
    $summaryText = 'the four synthetic checks produced exactly PASS, FAIL, ERROR, and NOT RUN'
    if (-not $ok) { $summaryText = 'MISMATCH: the synthetic checks did not produce exactly PASS, FAIL, ERROR, and NOT RUN' }
    $info = [ordered]@{ expected = $expected; matched = $ok; summary = $summaryText }
    Write-EnvironmentRecord
    Write-GitState
    [void](Write-Results -IsSelfTest $true -SelfTestInfo $info)
    Remove-Item -LiteralPath $WorkTemp -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host $summaryText
    if ($ok) { exit 0 }
    exit 1
}

# ---------------------------------------------------------------- real checks
$appPre = { if (Test-HasAppPython) { $null } else { 'no SpendWise Python source under backend/app (only empty __init__.py files)' } }
$testPre = { if (Test-HasBackendTests) { $null } else { 'no test_*.py under backend/tests' } }
$fePre = { if (Test-HasFrontendApp) { $null } else { 'frontend/src/api/client.ts does not exist (the stock Vite template alone does not count)' } }
$secretPre = {
    if ((Test-HasAppPython) -or (Test-HasFrontendApp)) { $null } else { 'no SpendWise application files exist yet to scan' }
}
$g6Pre = {
    $g5 = Get-ResultById 'G5-coverage'
    if (-not $g5 -or $g5.status -eq 'NOT RUN' -or $g5.status -eq 'ERROR') { return 'G5 did not run, so there is no coverage data' }
    if (-not (Test-Path -LiteralPath $CoverageFile)) { return 'G5 produced no coverage data file' }
    return $null
}
$covEnv = @{ COVERAGE_FILE = $CoverageFile }
$frontendDir = Join-Path $RepoRoot 'frontend'
$scan = Join-Path $PSScriptRoot 'scan_repo.py'

Write-Host "Harness run. Output folder: $OutPath"
Invoke-Check @{ Id = 'G1-ruff-check'; Exe = $Python; Args = '-m ruff check backend'; Tool = 'ruff'; Display = 'ruff check backend'; Pre = $appPre }
Invoke-Check @{ Id = 'G2-ruff-format'; Exe = $Python; Args = '-m ruff format --check backend'; Tool = 'ruff'; Display = 'ruff format --check backend'; Pre = $appPre }
Invoke-Check @{ Id = 'G3-bandit'; Exe = $Python; Args = '-m bandit -r backend/app -ll'; Tool = 'generic'; Display = 'bandit -r backend/app -ll'; Pre = $appPre }
Invoke-Check @{ Id = 'G4-pytest'; Exe = $Python; Args = '-m pytest backend'; Tool = 'pytest'; Display = 'pytest backend'; Pre = $testPre }
Invoke-Check @{ Id = 'G5-coverage'; Exe = $Python; Args = '-m pytest backend --cov=app --cov-fail-under=80'; Tool = 'pytestcov'
    Display = 'pytest backend --cov=app --cov-fail-under=80'; Pre = $testPre; Env = $covEnv }
Invoke-Check @{ Id = 'G6-core-services-coverage'; Exe = $Python; Tool = 'coverage'
    Args = '-m coverage report --include=*/app/services/*,*/app/core/* --fail-under=90'
    Display = 'coverage report --include=*/app/services/*,*/app/core/* --fail-under=90'; Pre = $g6Pre; Env = $covEnv }
Invoke-Check @{ Id = 'G7-float-scan'; Exe = $Python; Args = "`"$scan`" float"; Tool = 'scan'; Display = 'python harness\scan_repo.py float' }
Invoke-Check @{ Id = 'G9-tracked-files'; Exe = $Python; Args = "`"$scan`" tracked-files"; Tool = 'tracked'; Display = 'python harness\scan_repo.py tracked-files' }
Invoke-Check @{ Id = 'G9-secret-patterns'; Kind = 'supplementary'; Exe = $Python; Args = "`"$scan`" secret-patterns"; Tool = 'scan'
    Display = 'python harness\scan_repo.py secret-patterns'; Pre = $secretPre }
Invoke-Check @{ Id = 'G8-yarn-build'; Exe = $Yarn; Args = 'build'; Cwd = $frontendDir; Tool = 'generic'; Display = 'yarn build (in frontend)'; Pre = $fePre }
Invoke-Check @{ Id = 'FE-yarn-lint'; Exe = $Yarn; Args = 'lint'; Cwd = $frontendDir; Tool = 'generic'; Display = 'yarn lint (in frontend)'; Pre = $fePre }
Invoke-Check @{ Id = 'FE-yarn-test'; Exe = $Yarn; Args = 'test'; Cwd = $frontendDir; Tool = 'yarntest'; Display = 'yarn test (in frontend)'; Pre = $fePre }

if (Test-Path -LiteralPath (Join-Path $RepoRoot 'backend\app\main.py')) {
    Invoke-ApiChecks
}
else {
    $reason = 'precondition not met: backend/app/main.py does not exist'
    $now = Get-NowUtc
    foreach ($spec in @(@('API-write', 'required', 'run_api_checks.py --phase write'), @('API-verify', 'required', 'run_api_checks.py --phase verify'), @('API-timing', 'supplementary', 'run_api_checks.py --phase timing'))) {
        Complete-Check -Id $spec[0] -Kind $spec[1] -Command $spec[2] -Cwd $RepoRoot -StartUtc $now -EndUtc $now `
            -ExitText 'n/a' -Status 'NOT RUN' -Reason $reason -Stdout '' -Stderr ''
    }
}

# Files that describe this run are written first, then the run folder itself is scanned for secrets.
Write-EnvironmentRecord
Write-GitState
Write-Manifest
Invoke-Check @{ Id = 'evidence-secret-scan'; Exe = $Python; Args = "`"$scan`" secret-patterns --path `"$OutPath`""; Tool = 'scan'
    Display = 'python harness\scan_repo.py secret-patterns --path <run folder>' }

$counts = Write-Results -IsSelfTest $false -SelfTestInfo $null
Remove-Item -LiteralPath $WorkTemp -Recurse -Force -ErrorAction SilentlyContinue

$required = $counts['required']
Write-Host ("Required: PASS={0} FAIL={1} ERROR={2} NOT RUN={3}" -f $required['PASS'], $required['FAIL'], $required['ERROR'], $required['NOT RUN'])
$supplementary = $counts['supplementary']
Write-Host ("Supplementary: PASS={0} FAIL={1} ERROR={2} NOT RUN={3}" -f $supplementary['PASS'], $supplementary['FAIL'], $supplementary['ERROR'], $supplementary['NOT RUN'])
if (($required['FAIL'] + $required['ERROR']) -gt 0) { exit 1 }
if ($required['NOT RUN'] -gt 0) { exit 3 }
exit 0

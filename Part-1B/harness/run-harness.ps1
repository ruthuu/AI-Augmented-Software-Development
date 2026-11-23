<#
Runs quality gates G1-G5 for Part-1B and stores every command's output and exit code.

  G1  ruff check backend harness
  G2  pytest backend/tests (mocked LLM), and pytest harness/tests
  G3  yarn lint, yarn build
  G4  python harness/run_eval.py  (calls Gemini; skipped if G1-G3 fail or -SkipEvaluation is used)
  G5  python harness/scan_secrets.py

Evidence goes to <OutputRoot>\run-<UTC timestamp>\ (default: Part-1B\evidence).
Exit code 0 only if every gate passed and the evaluation verdict is PASS.
#>
param(
    [int]$DelaySeconds = 4,
    [string]$OutputRoot,
    [switch]$SkipEvaluation
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not $OutputRoot) { $OutputRoot = Join-Path $root 'evidence' }
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$runDir = Join-Path $OutputRoot "run-$stamp"
$pending = Join-Path ([System.IO.Path]::GetTempPath()) "reminder-gates-$stamp"
New-Item -ItemType Directory -Path $pending -Force | Out-Null

$results = New-Object System.Collections.ArrayList

function Invoke-Gate {
    param([string]$Name, [string]$WorkDir, [string]$File, [string]$Arguments, [string]$OutDir)
    $started = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $stdout = Join-Path $OutDir "$Name.stdout.txt"
    $stderr = Join-Path $OutDir "$Name.stderr.txt"
    $proc = Start-Process -FilePath $File -ArgumentList $Arguments -WorkingDirectory $WorkDir `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -Wait -PassThru -NoNewWindow
    $code = $proc.ExitCode
    $code | Set-Content -Path (Join-Path $OutDir "$Name.exitcode.txt") -Encoding ascii
    $record = [ordered]@{
        gate         = $Name
        command      = "$File $Arguments"
        exit_code    = $code
        started_utc  = $started
        finished_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    $record | ConvertTo-Json | Set-Content -Path (Join-Path $OutDir "$Name.meta.json") -Encoding utf8
    [void]$results.Add([pscustomobject]$record)
    Write-Host ("{0,-12} exit {1}" -f $Name, $code)
    return $code
}

Write-Host "Part-1B gates, run $stamp"
$g1 = Invoke-Gate 'G1-ruff-check' $root $python '-m ruff check backend harness' $pending
$g2 = Invoke-Gate 'G2-pytest-backend' $root $python '-m pytest backend/tests -q' $pending
$g2b = Invoke-Gate 'G2-pytest-harness' $root $python '-m pytest harness/tests -q' $pending
$fe = Join-Path $root 'frontend'
$g3a = Invoke-Gate 'G3-yarn-lint' $fe 'cmd.exe' '/c yarn lint' $pending
$g3b = Invoke-Gate 'G3-yarn-build' $fe 'cmd.exe' '/c yarn build' $pending

$preflight = ($g1 -eq 0) -and ($g2 -eq 0) -and ($g2b -eq 0) -and ($g3a -eq 0) -and ($g3b -eq 0)
$evalCode = $null
$evalDir = $pending
if ($SkipEvaluation) {
    Write-Host 'G4-evaluation skipped (-SkipEvaluation)'
}
elseif (-not $preflight) {
    Write-Host 'G4-evaluation skipped because G1-G3 failed'
}
else {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
    $evalCode = Invoke-Gate 'G4-evaluation' $root $python "harness/run_eval.py --run-dir `"$runDir`" --delay $DelaySeconds" $pending
}

# Gate output moves into the run folder (created by the evaluation, or here if it never ran).
New-Item -ItemType Directory -Path (Join-Path $runDir 'gates') -Force | Out-Null
Get-ChildItem -Path $pending -File | Move-Item -Destination (Join-Path $runDir 'gates') -Force
Remove-Item -Path $pending -Recurse -Force
$gatesDir = Join-Path $runDir 'gates'

$g5 = Invoke-Gate 'G5-secret-scan' $root $python "harness/scan_secrets.py --root `"$runDir`"" $gatesDir
$scanRepo = Invoke-Gate 'G5-secret-scan-repo' $root $python 'harness/scan_secrets.py' $gatesDir

$results | ConvertTo-Json | Set-Content -Path (Join-Path $gatesDir 'gates-summary.json') -Encoding utf8
& $python (Join-Path $root 'harness\run_eval.py') --write-manifest $runDir
& $python (Join-Path $root 'harness\run_eval.py') --verify-manifest $runDir
$manifestOk = ($LASTEXITCODE -eq 0)

$allGates = $preflight -and ($g5 -eq 0) -and ($scanRepo -eq 0) -and $manifestOk
Write-Host ''
Write-Host "Evidence folder : $runDir"
Write-Host "Gates G1-G3,G5  : $(if ($allGates) { 'PASS' } else { 'FAIL' })"
Write-Host "Manifest        : $(if ($manifestOk) { 'verified' } else { 'MISMATCH' })"
if ($null -eq $evalCode) { Write-Host 'Evaluation      : not run' }
elseif ($evalCode -eq 0) { Write-Host 'Evaluation      : PASS' }
elseif ($evalCode -eq 1) { Write-Host 'Evaluation      : FAIL (completed; see results.json)' }
else { Write-Host "Evaluation      : did not run (exit $evalCode)" }

if ($allGates -and ($evalCode -eq 0)) { exit 0 } else { exit 1 }

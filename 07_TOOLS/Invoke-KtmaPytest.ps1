[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$RunId,
    [string]$ProjectRoot = $(if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path })
)

$ErrorActionPreference = 'Stop'
if ($RunId -notmatch '^RUN_\d{3}$') { throw "INVALID_RUN_ID: $RunId. Must match RUN_nnn format." }

$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$expectedRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
if ($resolvedRoot -ne $expectedRoot) { throw "PROJECT_ROOT_BINDING_MISMATCH: $resolvedRoot" }

$runBase = Join-Path $resolvedRoot '90_RUNTIME/KTMA_TASK070_GUARDED_FINANCIAL_TESTS'
$runRoot = Join-Path $runBase $RunId
if (Test-Path -LiteralPath $runRoot) { throw "TASK070 fixture collision; refusing overwrite: $runRoot" }

$python = Join-Path $resolvedRoot '90_RUNTIME/venv_win/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Project-local Windows financial interpreter unavailable: $python" }
$pytestSite = (& py -3.11 -B -c "import site; print(next(p for p in site.getsitepackages() if p.endswith('site-packages')))" | Select-Object -First 1).Trim()
if (-not (Test-Path -LiteralPath $pytestSite -PathType Container)) { throw "Existing pytest package location unavailable: $pytestSite" }

$testFiles = @(
    '06_TESTS/test_task070_trusted_authorization.py',
    '06_TESTS/test_ph1_regression.py',
    '06_TESTS/test_ph15_database.py',
    '06_TESTS/test_windows_writer_guard.py'
)
$additionalIdentityPatterns = @(
    '06_TESTS/test_task070_trusted_authorization.py::test_lab_review_guard_is_ephemeral_and_non_productive',
    '06_TESTS/test_task070_trusted_authorization.py::test_lab_review_guard_rejects_non_fixture_destinations[destination0]',
    '06_TESTS/test_task070_trusted_authorization.py::test_lab_review_guard_rejects_non_fixture_destinations[destination1]'
)
$protectedExpected = [ordered]@{
    'RAW.INPUT/2026.08/MANIFEST.json' = '04a1154167649317226f3463e2c5b4ab5b828086d12ae6817b5e0ff263c6c96f'
    'RAW.INPUT/2026.08/Mayor Grupo Impulsa 2026 08 V 1.xlsb' = 'b074626b2380646b5c563492e66b4d0a19714d817e4e9c1f52ba310cadd1de43'
    'RAW.INPUT/2026.08/Mayor Inmob. Eplaza 2026 08 V 1.xlsb' = 'bca421c1a730fee0d44607d9bb0af49bea0407345d852e96c7135508585025c5'
    'OUTPUT/2026.08/CAM2026.08_CONSOL.ALIGN.xlsx' = '5acba7c7c09b743f53b7d5734a9042712d8116a1aaab9df0d54349218dbce5ec'
    'OUTPUT/2026.08/FM2026.08_VALIDATION.xlsx' = 'eda935a5f0e80a5f33ab04fd6b95ed3365d35fb1e0422cbe7b8a54a8f833ee6b'
    'OUTPUT/2026.08/KTMA_PH1_REPORT.json' = 'eed04df319538e62bb51d596ef5bcbfcbf1f16b50997255fae3a76c1869bf04a'
    'DATA/KTMA.sqlite' = 'b5f6b6eae6dcb2f1273f8e5d1706b6db30e52d9250ad148b68e88881ffac60d0'
}
$historicalPycPaths = @(
    'src/kt_movemacc/__pycache__/root_boundary.cpython-315.pyc',
    'src/kt_movemacc/__pycache__/engine.cpython-315.pyc',
    'src/kt_movemacc/__pycache__/cli.cpython-315.pyc',
    'src/kt_movemacc/__pycache__/ph15_database.cpython-315.pyc',
    '07_TOOLS/__pycache__/ktma_root_guard.cpython-315.pyc'
)

function Get-RelativePath([string]$Path) { return [System.IO.Path]::GetRelativePath($resolvedRoot, $Path).Replace('\', '/') }
function Get-FileRecord([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    return [ordered]@{
        path = Get-RelativePath $item.FullName
        size_bytes = [int64]$item.Length
        sha256 = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        modified_utc = $item.LastWriteTimeUtc.ToString('o')
    }
}
function Get-TreeRecords([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return @() }
    return @(Get-ChildItem -LiteralPath $Path -Force -Recurse -File | Sort-Object FullName | ForEach-Object { Get-FileRecord $_.FullName })
}
function Get-ProtectedState {
    return @(foreach ($entry in $protectedExpected.GetEnumerator()) {
        $record = Get-FileRecord (Join-Path $resolvedRoot $entry.Key)
        $record['expected_sha256'] = $entry.Value
        $record['match'] = ($record.sha256 -eq $entry.Value)
        $record
    })
}
function Get-PycState { return @(foreach ($relative in $historicalPycPaths) { Get-FileRecord (Join-Path $resolvedRoot $relative) }) }
function Get-SourceState {
    $paths = @((Join-Path $resolvedRoot '07_TOOLS/Invoke-KtmaPytest.ps1'), (Join-Path $resolvedRoot '06_TESTS/ktma_guarded_financial_fixtures.py'))
    $paths += @(Get-ChildItem -LiteralPath (Join-Path $resolvedRoot 'src/kt_movemacc') -File -Filter '*.py' | Sort-Object FullName | ForEach-Object { $_.FullName })
    $paths += @($testFiles | ForEach-Object { Join-Path $resolvedRoot $_ })
    return @($paths | Select-Object -Unique | ForEach-Object { Get-FileRecord $_ })
}
function Get-TextSha256([string]$Text) {
    $hash = [System.Security.Cryptography.SHA256]::HashData([System.Text.Encoding]::UTF8.GetBytes($Text))
    return [Convert]::ToHexString($hash).ToLowerInvariant()
}
function Get-GitInventory {
    $previousLocks = $env:GIT_OPTIONAL_LOCKS
    $env:GIT_OPTIONAL_LOCKS = '0'
    try {
        $tracked = @(git --no-optional-locks ls-files)
        $modified = @(git --no-optional-locks diff --name-only 2>$null)
        $staged = @(git --no-optional-locks diff --cached --name-only 2>$null)
        $untracked = @(git --no-optional-locks ls-files --others --exclude-standard 2>$null)
        $ignored = @(git --no-optional-locks ls-files --others --ignored --exclude-standard 2>$null)
        $ignoredTop = @($ignored | ForEach-Object { ($_ -split '/')[0] } | Group-Object | Sort-Object Name | ForEach-Object { [ordered]@{ name = $_.Name; count = $_.Count } })
        return [ordered]@{
            branch = (git --no-optional-locks branch --show-current)
            head = (git --no-optional-locks rev-parse HEAD)
            tracked_count = $tracked.Count
            tracked_paths_sha256 = Get-TextSha256 (($tracked -join "`n") + "`n")
            modified = $modified
            staged = $staged
            untracked = $untracked
            ignored_count = $ignored.Count
            ignored_paths_sha256 = Get-TextSha256 (($ignored -join "`n") + "`n")
            ignored_top_level_counts = $ignoredTop
        }
    } finally { $env:GIT_OPTIONAL_LOCKS = $previousLocks }
}
function Invoke-CapturedProcess([string]$FileName, [string[]]$Arguments) {
    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $FileName
    $info.WorkingDirectory = $resolvedRoot
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { [void]$info.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $info
    $started = [DateTimeOffset]::UtcNow
    if (-not $process.Start()) { throw "PROCESS_START_FAILED: $FileName" }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $ended = [DateTimeOffset]::UtcNow
    return [ordered]@{
        file = $FileName
        arguments = $Arguments
        command_display = ('"' + $FileName + '" ' + (($Arguments | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' }) -join ' '))
        started_utc = $started.ToString('o')
        ended_utc = $ended.ToString('o')
        exit_code = $process.ExitCode
        stdout = $stdoutTask.GetAwaiter().GetResult()
        stderr = $stderrTask.GetAwaiter().GetResult()
    }
}
function Write-JsonReceipt([string]$Path, $Value) {
    [System.IO.File]::WriteAllText($Path, (($Value | ConvertTo-Json -Depth 30) + "`n"), [System.Text.UTF8Encoding]::new($false))
}

$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:KTMA_RUN_ID = $RunId
$env:PYTHONPATH = (Join-Path $resolvedRoot 'src') + ';' + (Join-Path $resolvedRoot '06_TESTS') + ';' + $pytestSite
$env:TEMP = Join-Path $runRoot 'temp'
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP

$preflightStarted = [DateTimeOffset]::UtcNow
$protectedBefore = Get-ProtectedState
if (@($protectedBefore | Where-Object { -not $_.match }).Count -ne 0) { throw 'PROTECTED_FINANCIAL_DRIFT_BEFORE_EXECUTION' }
$run001Before = Get-TreeRecords (Join-Path $runBase 'RUN_001')
$run002Before = Get-TreeRecords (Join-Path $runBase 'RUN_002')
$pycBefore = Get-PycState
$sourceBefore = Get-SourceState
$gitBefore = Get-GitInventory

$runtimeProbe = Invoke-CapturedProcess $python @('-B', '-c', "import json,os,platform,sys,pytest; print(json.dumps({'executable':sys.executable,'version':sys.version,'platform':platform.platform(),'os_name':os.name,'pytest':pytest.__version__},sort_keys=True))")
if ($runtimeProbe.exit_code -ne 0) { throw 'NATIVE_RUNTIME_PROBE_FAILED' }

$collectionArgs = @('-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--collect-only', '-q') + $testFiles
$collection = Invoke-CapturedProcess $python $collectionArgs
$nodeIds = @($collection.stdout -split "`r?`n" | Where-Object { $_ -match '^06_TESTS/.+::' })
$additionalNodeIds = @($nodeIds | Where-Object { $_ -in $additionalIdentityPatterns })
$historicalNodeIds = @($nodeIds | Where-Object { $_ -notin $additionalIdentityPatterns })
if ($collection.exit_code -ne 0) {
    [void](New-Item -ItemType Directory -Path $runRoot -Force)
    Write-JsonReceipt (Join-Path $runRoot 'TASK076_COLLECTION.json') ([ordered]@{schema='ktma.task076.collection.v1';run_id=$RunId;root=$resolvedRoot;collection_process=$collection;node_ids=$nodeIds;historical_identities=$historicalNodeIds;additional_identities=$additionalNodeIds;execution_started=$false})
    Write-JsonReceipt (Join-Path $runRoot 'TASK076_TERMINAL_EXIT.json') ([ordered]@{schema='ktma.task076.terminal-exit.v1';run_id=$RunId;phase='collection';exit_code=$collection.exit_code;started_utc=$collection.started_utc;ended_utc=$collection.ended_utc;command=$collection.command_display})
    exit $collection.exit_code
}

$junitPath = Join-Path $runRoot 'TASK076_PYTEST_JUNIT.xml'
$testArgs = @('-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-vv', '--tb=short', "--junitxml=$junitPath") + $testFiles
$execution = Invoke-CapturedProcess $python $testArgs
if (-not (Test-Path -LiteralPath $runRoot -PathType Container)) { [void](New-Item -ItemType Directory -Path $runRoot -Force) }

$transcriptPath = Join-Path $runRoot 'TASK076_TERMINAL_TRANSCRIPT.txt'
$transcript = @('KTMA_TASK076 NATIVE WINDOWS PYTEST TRANSCRIPT',('RUN_ID=' + $RunId),('ROOT=' + $resolvedRoot),('COMMAND=' + $execution.command_display),('STARTED_UTC=' + $execution.started_utc),('ENDED_UTC=' + $execution.ended_utc),('EXIT_CODE=' + $execution.exit_code),'--- STDOUT ---',$execution.stdout,'--- STDERR ---',$execution.stderr) -join "`r`n"
[System.IO.File]::WriteAllText($transcriptPath, $transcript + "`r`n", [System.Text.UTF8Encoding]::new($false))

Write-JsonReceipt (Join-Path $runRoot 'TASK076_COLLECTION.json') ([ordered]@{
    schema='ktma.task076.collection.v1';run_id=$RunId;root=$resolvedRoot;collection_process=$collection;collected_count=$nodeIds.Count;node_ids=$nodeIds;historical_count=$historicalNodeIds.Count;historical_identities=$historicalNodeIds;additional_count=$additionalNodeIds.Count;additional_identities=$additionalNodeIds;excluded_relevant_security_suites=@('06_TESTS/test_task066_root_boundary.py','06_TESTS/test_task067_root_authority.py')
})
Write-JsonReceipt (Join-Path $runRoot 'TASK076_SOURCE_VERSION.json') ([ordered]@{
    schema='ktma.task076.source-version.v1';run_id=$RunId;captured_before_execution_utc=$preflightStarted.ToString('o');runtime=($runtimeProbe.stdout.Trim() | ConvertFrom-Json);pytest_site=$pytestSite;source_files=$sourceBefore
})
Write-JsonReceipt (Join-Path $runRoot 'TASK076_PREFLIGHT.json') ([ordered]@{
    schema='ktma.task076.preflight.v1';run_id=$RunId;root=$resolvedRoot;branch=$gitBefore.branch;head=$gitBefore.head;protected_financial=$protectedBefore;historical_pyc=$pycBefore;run_001_manifest=$run001Before;run_002_manifest=$run002Before;git_inventory=$gitBefore
})
Write-JsonReceipt (Join-Path $runRoot 'TASK076_TERMINAL_EXIT.json') ([ordered]@{
    schema='ktma.task076.terminal-exit.v1';run_id=$RunId;root=$resolvedRoot;native_windows=$true;python_executable=$python;runtime=($runtimeProbe.stdout.Trim() | ConvertFrom-Json);command=$execution.command_display;arguments=$execution.arguments;started_utc=$execution.started_utc;ended_utc=$execution.ended_utc;exit_code=$execution.exit_code;junit_path=(Get-RelativePath $junitPath);junit_exists=(Test-Path -LiteralPath $junitPath -PathType Leaf);transcript_path=(Get-RelativePath $transcriptPath)
})

$protectedAfter = Get-ProtectedState
$run001After = Get-TreeRecords (Join-Path $runBase 'RUN_001')
$run002After = Get-TreeRecords (Join-Path $runBase 'RUN_002')
$pycAfter = Get-PycState
$sourceAfter = Get-SourceState
$gitAfter = Get-GitInventory
Write-JsonReceipt (Join-Path $runRoot 'TASK076_INTEGRITY.json') ([ordered]@{
    schema='ktma.task076.integrity.v1';run_id=$RunId;protected_before=$protectedBefore;protected_after=$protectedAfter;protected_matches=@($protectedAfter | Where-Object {$_.match}).Count;run_001_before=$run001Before;run_001_after=$run001After;run_001_preserved=((ConvertTo-Json $run001Before -Depth 10 -Compress) -eq (ConvertTo-Json $run001After -Depth 10 -Compress));run_002_before=$run002Before;run_002_after=$run002After;run_002_preserved=((ConvertTo-Json $run002Before -Depth 10 -Compress) -eq (ConvertTo-Json $run002After -Depth 10 -Compress));historical_pyc_before=$pycBefore;historical_pyc_after=$pycAfter;historical_pyc_preserved=((ConvertTo-Json $pycBefore -Depth 10 -Compress) -eq (ConvertTo-Json $pycAfter -Depth 10 -Compress));source_before=$sourceBefore;source_after=$sourceAfter;source_preserved_during_execution=((ConvertTo-Json $sourceBefore -Depth 10 -Compress) -eq (ConvertTo-Json $sourceAfter -Depth 10 -Compress));git_before=$gitBefore;git_after=$gitAfter
})

$outputRecords = @(Get-ChildItem -LiteralPath $runRoot -Force -Recurse -File | Where-Object {$_.Name -notin @('TASK076_OUTPUT_SHA256.json','TASK076_RUN_MANIFEST.json')} | Sort-Object FullName | ForEach-Object {Get-FileRecord $_.FullName})
Write-JsonReceipt (Join-Path $runRoot 'TASK076_OUTPUT_SHA256.json') ([ordered]@{schema='ktma.task076.output-inventory.v1';run_id=$RunId;files=$outputRecords})
$manifestInputs = @(Get-ChildItem -LiteralPath $runRoot -Force -Recurse -File | Where-Object {$_.Name -ne 'TASK076_RUN_MANIFEST.json'} | Sort-Object FullName | ForEach-Object {Get-FileRecord $_.FullName})
Write-JsonReceipt (Join-Path $runRoot 'TASK076_RUN_MANIFEST.json') ([ordered]@{
    schema='ktma.task076.run-manifest.v1';task_id='KTMA_TASK076_RECEIPT_FIRST_RECOVERY';run_id=$RunId;root=$resolvedRoot;productive_trust='NOT_ENFORCED';receipts_are_atomic=$false;receipts_are_tamper_proof=$false;execution_exit_code=$execution.exit_code;collected_count=$nodeIds.Count;files_except_this_manifest=$manifestInputs
})

Write-Output $execution.stdout
if ($execution.stderr) { [Console]::Error.WriteLine($execution.stderr) }
exit $execution.exit_code

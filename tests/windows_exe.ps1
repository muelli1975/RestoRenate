param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$Version)
$ErrorActionPreference = 'Stop'
$exe = Join-Path (Resolve-Path $Root) 'RestoRenate.exe'
# 1.0 used an ASCII hyphen; later releases use an en dash in the window title.
$expectedTitle = if ($Version -eq '1.0') { "RestoRenate - $Version" } else { "RestoRenate – $Version" }
$process = Start-Process $exe -WorkingDirectory $env:RUNNER_TEMP -PassThru
try {
    $deadline = [DateTime]::UtcNow.AddSeconds(50)
    do {
        $process.Refresh()
        if ($process.HasExited) { throw "RestoRenate exited at startup: $($process.ExitCode)" }
        if ($process.MainWindowTitle -eq $expectedTitle -and $process.Responding) { break }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    if ($process.MainWindowTitle -ne $expectedTitle) { throw "Unexpected GUI title: $($process.MainWindowTitle)" }
    if (!$process.CloseMainWindow() -or !$process.WaitForExit(15000) -or $process.ExitCode -ne 0) {
        throw 'Packaged GUI did not close cleanly'
    }
} catch {
    Get-Content (Join-Path $Root 'logs/application.log') -Tail 60 -ErrorAction SilentlyContinue
    throw
} finally {
    if (!$process.HasExited) { $process.Kill() }
}

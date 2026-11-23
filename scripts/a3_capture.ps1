param([string[]]$Sections = @('A2','B','C','D1','D2','E','F1','F2','F3','F4'))
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$outDir='X:\semester 5\SCD\A2\rahbar-starter\docs\a3-screenshots'
foreach ($section in $Sections) {
    $ready=Join-Path $outDir "$section.ready"
    if (Test-Path -LiteralPath $ready) { Remove-Item -LiteralPath $ready }
    $child=Start-Process powershell.exe -WindowStyle Maximized -ArgumentList '-NoProfile','-NoExit','-File','"X:\semester 5\SCD\A2\rahbar-starter\scripts\a3_evidence_window.ps1"',$section -PassThru
    $deadline=(Get-Date).AddSeconds(45)
    while (-not (Test-Path -LiteralPath $ready)) {
        if ((Get-Date) -gt $deadline) { throw "Evidence window did not finish: $section" }
        Start-Sleep -Milliseconds 300
    }
    Start-Sleep -Milliseconds 1200
    $bounds=[Windows.Forms.SystemInformation]::VirtualScreen
    $shot=New-Object Drawing.Bitmap $bounds.Width,$bounds.Height
    $gfx=[Drawing.Graphics]::FromImage($shot)
    $gfx.CopyFromScreen($bounds.Location,[Drawing.Point]::Empty,$bounds.Size)
    $shot.Save((Join-Path $outDir "$section.png"))
    $gfx.Dispose(); $shot.Dispose()
    Stop-Process -Id $child.Id -ErrorAction SilentlyContinue
    Write-Output "Captured $section"
}

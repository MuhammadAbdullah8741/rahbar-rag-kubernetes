param([string]$Section = 'A1')
$Host.UI.RawUI.WindowTitle = "RAHBAR A3 evidence $Section"
Clear-Host
Write-Host "PS> wsl --cd 'X:\semester 5\SCD\A2\rahbar-starter' python scripts/a3_show.py $Section" -ForegroundColor Cyan
wsl --cd 'X:\semester 5\SCD\A2\rahbar-starter' -e /home/nemesis/.venvs/rahbar/bin/python scripts/a3_show.py $Section
Write-Host "`nEnd of evidence $Section" -ForegroundColor Cyan
Set-Content -LiteralPath "X:\semester 5\SCD\A2\rahbar-starter\docs\a3-screenshots\$Section.ready" -Value 'ready'

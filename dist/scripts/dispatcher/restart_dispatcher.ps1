Write-Host "=== SYS-Toolset Test Script ==="
Write-Host "Script avviato correttamente"
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "Hostname: $env:COMPUTERNAME"
Write-Host "Utente: $env:USERNAME"

Write-Host ""
Write-Host "Top 5 processi per uso CPU:"

Get-Process |
    Sort-Object CPU -Descending |
    Select-Object -First 5 Name, Id, CPU |
    Format-Table -AutoSize

Write-Host ""
Write-Host "Test completato con successo"

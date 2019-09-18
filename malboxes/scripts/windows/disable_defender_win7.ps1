# Disable Windows Defender on Windows 7
$path="HKLM:\SYSTEM\CurrentControlSet\services\WinDefend"
$name="Start"
Set-ItemProperty -Path $path -Name $name -Value 4
Write-Host "Set registry key: $path\$name to 4"


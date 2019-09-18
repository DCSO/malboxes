
## Remove chocolately
Remove-Item -Recurse -Force "$env:ChocolateyInstall"
if ($env:ChocolateyBinRoot -ne '' -and $env:ChocolateyBinRoot -ne $null) { Remove-Item -Recurse -Force "$env:ChocolateyBinRoot"}
if ($env:ChocolateyToolsRoot -ne '' -and $env:ChocolateyToolsRoot -ne $null) { Remove-Item -Recurse -Force "$env:ChocolateyToolsRoot"}
[System.Environment]::SetEnvironmentVariable("ChocolateyBinRoot", $null, 'User')
[System.Environment]::SetEnvironmentVariable("ChocolateyToolsLocation", $null, 'User')

## Remove itself from task scheduler
schtasks /delete /tn cleanup /f

## Remove packer schtasks
Remove-Item "$env:HOMEDRIVE\Windows\System32\Tasks\packer-*"

## Remove itself
#Remove-Item $MyInvocation.MyCommand.Definition

## Clear temp folders
$tempfolders = @("C:\Windows\Temp\*", "C:\Windows\Prefetch\*", "C:\Users\*\Appdata\Local\Temp\*")

Remove-Item $tempfolders -force -recurse


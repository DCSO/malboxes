Set-ExecutionPolicy Unrestricted
iex ((New-Object System.Net.WebClient).DownloadString('http://boxstarter.org/bootstrapper.ps1')); get-boxstarter -Force
Set-BoxstarterConfig -NugetSources "$env:FLARE_SOURCE;$env:CHOCO_SOURCE"
choco upgrade -y vcredist-all.flare
cinst -y powershell

$spasswd=ConvertTo-SecureString -String $env:PASSWORD -AsPlainText -Force
$cred=New-Object -TypeName "System.Management.Automation.PSCredential" -ArgumentList $env:USERNAME, $spasswd

$Boxstarter.RebootOk=$true # Allow reboots?
$Boxstarter.NoPassword=$false # Is this a machine with no login password?
$Boxstarter.AutoLogin=$true # Save my password securely and auto-login after a reboot

Install-BoxstarterPackage -PackageName flarevm.installer.flare -Credential $cred

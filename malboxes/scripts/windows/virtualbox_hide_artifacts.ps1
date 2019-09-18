
$dest="HKLM:\HARDWARE\ACPI\DSDT\VBOX__"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

$dest="HKLM:\HARDWARE\\ACPI\FADT\VBOX__"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

$dest="HKLM:\HARDWARE\ACPI\RSDT\VBOX__"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

$dest="HKLM:\SYSTEM\ControlSet001\Services\VBoxGuest"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

$dest="HKLM:\SYSTEM\ControlSet001\Services\VBoxMouse"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

$dest="HKLM:\SYSTEM\ControlSet001\Services\VBoxService"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

$dest="HKLM:\SYSTEM\ControlSet001\Services\VBoxSF"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

$dest="HKLM:\SYSTEM\ControlSet001\Services\VBoxVideo"
if(Test-Path -Path $dest)
{
    Remove-Item $dest -recurse
    Write-Host "Removed: $dest"
}

Function Test-RegistryValue($regkey, $name) {
    $exists = Get-ItemProperty -Path "$regkey" -Name "$name" -ErrorAction SilentlyContinue
    If (($exists -ne $null) -and ($exists.Length -ne 0)) {
        Return $true
    }
    Return $false
}


$reg_path="HKLM:\Hardware\Description\System"

# Set bios date
$name="SystemBiosDate"
if(Test-RegistryValue $reg_path $name)
{
    $biosDate = Get-Date -UFormat "2017/%m/%d"
    Set-ItemProperty -Type String -Path $reg_path -Name $name -value "$biosDate"
    Write-Host "Set: $name to $biosDate"

}

# Set bios version
$name="SystemBiosVersion"
if(Test-RegistryValue $reg_path $name)
{
    $biosVersion = Get-Random -Minimum 10.7 -Maximum 70.93
    Set-ItemProperty -Type String -Path $reg_path -Name $name -value "$biosVersion"
    Write-Host "Set: $name to $biosVersion"
}

# Remove video bios version
$name="VideoBiosVersion"
if(Test-RegistryValue $reg_path $name)
{
    Remove-ItemProperty -Path $reg_path -Name $name
    Write-Host "Removed: $reg_path\\$name "
}

#$virtualbox_wmi = Get-WmiObject -Query "Select DeviceID FROM Win32_PnPEnitity WHERE DeviceID LIKE 'PCI\\VEN_80EE&DEV_CAFE%'"

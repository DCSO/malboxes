
netsh int ip set address "local area connection 2" static "{{ guest_ip }}" "{{ netmask }}" "{{ gateway_ip }}"

if( "{{ dnsserver_ip }}" -ne "")
{
    netsh int ip set dns "local area connection 2" static "{{ dnsserver_ip }}" primary
}else
{
    Write-Host "dnsserver_ip is not set. Skipping..."
}


if( "{{ secondary_dnsserver_ip }}" -ne "")
{
    netsh interface ip add dns name="local area connection 2" addr={{ secondary_dnsserver_ip }} index=2
}else
{
    Write-Host "secondary_dnsserver_ip is not set. Skipping..."
}

Write-Host "Done."


schtasks /delete /tn set_static_ip /f

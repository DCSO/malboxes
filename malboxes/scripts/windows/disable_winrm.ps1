netsh advfirewall firewall set rule group="Windows Remote Management" new enable=no
netsh advfirewall firewall set rule name="Port 5985" new enable=no

# Disable winrm autostart
sc.exe config winrm start= disabled


## Remove itself from task scheduler
schtasks /delete /tn disable_winrm /f

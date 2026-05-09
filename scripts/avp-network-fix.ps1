# Boreas AVP — one-shot network + firewall fix
#
# Use when the Vision Pro Configurator app is "stuck on waiting for connection"
# and the Windows network profile is Public (more restrictive) AND the
# Boreas AVP firewall rules don't yet exist.
#
# HOW TO RUN:
#   Option A — right-click this file > "Run with PowerShell" + accept UAC
#   Option B — open PowerShell as Administrator, then:
#                cd C:\Users\Ranga\omniverse\kit-app-template
#                .\scripts\avp-network-fix.ps1
#   Option C — open this file in a text editor and copy/paste lines below
#              into an Administrator PowerShell window.
#
# The script is idempotent — safe to run multiple times.

# ---- 1. Reclassify the active Wi-Fi as Private (less restrictive than Public) ----
# Edit this name if your Wi-Fi SSID is not "ADS Lab".
$WIFI_NAME = "ADS Lab"
Set-NetConnectionProfile -Name $WIFI_NAME -NetworkCategory Private

# ---- 2. Drop any prior Boreas AVP rules so this script is idempotent ----
Get-NetFirewallRule -DisplayName "Boreas AVP*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule

# ---- 3. Add fresh Boreas AVP rules scoped to kit.exe ----
$KIT = "C:\Users\Ranga\omniverse\kit-app-template\_build\windows-x86_64\release\kit\kit.exe"

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (TCP connect 48010)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT -Protocol TCP -LocalPort 48010

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (UDP video 47998/48005/48008/48012)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT -Protocol UDP -LocalPort 47998,48005,48008,48012

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (UDP input 47999)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT -Protocol UDP -LocalPort 47999

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (UDP audio 48000)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT -Protocol UDP -LocalPort 48000

# ---- 4. Show what's now in place ----
Write-Output ""
Write-Output "=== network profile ==="
Get-NetConnectionProfile -Name $WIFI_NAME | Select-Object Name, NetworkCategory | Format-Table -AutoSize

Write-Output "=== Boreas AVP firewall rules ==="
Get-NetFirewallRule -DisplayName "Boreas AVP*" | Select-Object DisplayName, Enabled, Direction, Action | Format-Table -AutoSize

Write-Output "Done. Now: relaunch the AVP Kit app, then reconnect from the Vision Pro Configurator app."
Write-Output "Server IP for the headset to connect to: 192.168.0.185 (this Windows host)"
Read-Host "Press Enter to close this window"

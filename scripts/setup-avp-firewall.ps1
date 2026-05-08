# Boreas Operator — Apple Vision Pro CloudXR firewall setup (Windows)
#
# Opens the inbound TCP/UDP ports CloudXR needs for AVP streaming, scoped to
# the Boreas Kit binary so the rules don't permanently widen the firewall.
#
# Per NVIDIA's setup-network.html:
#   TCP 48010                          : connect channel
#   UDP 47998, 48005, 48008, 48012     : video channel
#   UDP 47999                          : input channel
#   UDP 48000                          : audio channel
#
# Run as Administrator:
#     powershell.exe -ExecutionPolicy Bypass -File scripts\setup-avp-firewall.ps1
#
# Removal (also as Administrator):
#     Get-NetFirewallRule -DisplayName "Boreas AVP CloudXR*" | Remove-NetFirewallRule

$KIT_EXE = "C:\Users\Ranga\omniverse\kit-app-template\_build\windows-x86_64\release\kit\kit.exe"

if (-not (Test-Path $KIT_EXE)) {
    Write-Error "kit.exe not found at $KIT_EXE — run .\repo.bat build first."
    exit 1
}

# Drop any prior Boreas AVP rules so this script is idempotent.
Get-NetFirewallRule -DisplayName "Boreas AVP CloudXR*" -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (TCP in, connect 48010)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT_EXE -Protocol TCP -LocalPort 48010

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (UDP in, video 47998/48005/48008/48012)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT_EXE -Protocol UDP -LocalPort 47998,48005,48008,48012

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (UDP in, input 47999)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT_EXE -Protocol UDP -LocalPort 47999

New-NetFirewallRule `
    -DisplayName "Boreas AVP CloudXR (UDP in, audio 48000)" `
    -Direction Inbound -Action Allow -Profile Any `
    -Program $KIT_EXE -Protocol UDP -LocalPort 48000

Write-Output ""
Write-Output "=== Boreas AVP firewall rules now in place ==="
Get-NetFirewallRule -DisplayName "Boreas AVP CloudXR*" |
    Select-Object DisplayName, Enabled, Direction, Action |
    Format-Table -AutoSize

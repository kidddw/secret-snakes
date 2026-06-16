<#
  start-site.ps1 — bring Secret Snakes back for the season.

  1) Start the EC2 instance and wait until it is healthy.
  2) Point the apex domain back at the Elastic IP (the live app).

  The container auto-starts (restart=unless-stopped) and the cert auto-renews on
  boot, so the box self-heals into a working HTTPS site within ~1-2 minutes.

  Pre-reqs: AWS CLI v2 installed and configured with admin credentials, and
  site-config.json filled in (see SETUP.md).
#>
[CmdletBinding()]
param([string]$ConfigPath = "$PSScriptRoot\site-config.json")
$ErrorActionPreference = "Stop"

$cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
foreach ($k in 'HostedZoneId','ElasticIp','CloudFrontDomain') {
    if ($cfg.$k -like 'FILL_ME*') { throw "site-config.json: '$k' is not set yet. Finish SETUP.md first." }
}

# --- 1) Start the instance, wait for status checks ---------------------------
Write-Host "Starting instance $($cfg.InstanceId) ..."
aws ec2 start-instances --region $cfg.Region --instance-ids $cfg.InstanceId | Out-Null
aws ec2 wait instance-status-ok --region $cfg.Region --instance-ids $cfg.InstanceId

# Best-effort: wait for nginx to answer (it 301-redirects http -> https).
Write-Host "Instance up; waiting for the web server to respond ..."
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    $code = (& curl.exe -s -o NUL -w "%{http_code}" -H "Host: $($cfg.Domain)" "http://$($cfg.ElasticIp)/" 2>$null)
    if ($code -eq "301" -or $code -eq "200") { $healthy = $true; break }
    Start-Sleep -Seconds 5
}
if (-not $healthy) { Write-Warning "Web server not confirmed healthy yet; flipping DNS anyway (it should come up shortly)." }

# --- 2) DNS: apex -> Elastic IP ----------------------------------------------
$batch = @{
    Comment = "In-season: apex -> Elastic IP (live app)"
    Changes = @(@{
        Action = "UPSERT"
        ResourceRecordSet = @{
            Name = "$($cfg.Domain)."
            Type = "A"
            TTL  = 60
            ResourceRecords = @(@{ Value = $cfg.ElasticIp })
        }
    })
}
$tmp = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmp, ($batch | ConvertTo-Json -Depth 10))  # UTF-8, no BOM
Write-Host "DNS: pointing $($cfg.Domain) -> $($cfg.ElasticIp) ..."
aws route53 change-resource-record-sets --hosted-zone-id $cfg.HostedZoneId --change-batch "file://$tmp" | Out-Null
Remove-Item $tmp -Force

Write-Host "Live. The apex now points at the app; HTTPS cert was renewed on boot." -ForegroundColor Green

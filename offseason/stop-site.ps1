<#
  stop-site.ps1 — put Secret Snakes into off-season hibernation.

  1) Point the apex domain at the CloudFront off-season page (HTTPS "hibernating" page).
  2) Stop the EC2 instance. Data persists on the EBS volume — nothing is lost.

  While stopped you pay only for storage (EBS) + the Elastic IP, not compute.

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

# --- 1) DNS: apex -> CloudFront (alias) --------------------------------------
$batch = @{
    Comment = "Off-season: apex -> CloudFront off-season page"
    Changes = @(@{
        Action = "UPSERT"
        ResourceRecordSet = @{
            Name = "$($cfg.Domain)."
            Type = "A"
            AliasTarget = @{
                HostedZoneId = "Z2FDTNDATAQYW2"   # constant: CloudFront's global zone id
                DNSName = "$($cfg.CloudFrontDomain)."
                EvaluateTargetHealth = $false
            }
        }
    })
}
$tmp = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmp, ($batch | ConvertTo-Json -Depth 10))  # UTF-8, no BOM
Write-Host "DNS: pointing $($cfg.Domain) -> CloudFront ($($cfg.CloudFrontDomain)) ..."
aws route53 change-resource-record-sets --hosted-zone-id $cfg.HostedZoneId --change-batch "file://$tmp" | Out-Null
Remove-Item $tmp -Force

# --- 2) Stop the instance ----------------------------------------------------
Write-Host "Stopping instance $($cfg.InstanceId) ..."
aws ec2 stop-instances --region $cfg.Region --instance-ids $cfg.InstanceId | Out-Null
aws ec2 wait instance-stopped --region $cfg.Region --instance-ids $cfg.InstanceId

Write-Host "Hibernating. Visitors now see the off-season page; compute billing has stopped." -ForegroundColor Green

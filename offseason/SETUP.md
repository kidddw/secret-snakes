# Off-season hibernation — setup & operation

Goal: in the off-season, show a friendly HTTPS "hibernating" page and stop the
EC2 instance (pay only for storage); in-season, run the live app as normal.
This is a **one-time setup**, after which the season is toggled with one script
(or a few console clicks).

Architecture:
- **In-season:** `secretsnakes.com` (apex A record) → **Elastic IP** → EC2/nginx/app. CloudFront is NOT in the live path, so there are no caching surprises for logged-in users.
- **Off-season:** apex record → **CloudFront** → **S3** static page (`offseason/index.html`), HTTPS via an **ACM** cert. Instance stopped.

---

## One-time setup

### 0. Prerequisites
- AWS CLI v2 installed locally and configured with **admin** credentials (`aws sts get-caller-identity` works). The EC2 instance role is S3-only and cannot do any of this.
- Region for the app stays **us-east-2**. **ACM/CloudFront certs must be in `us-east-1`** (CloudFront only reads certs from us-east-1).

### 1. Allocate a stable Elastic IP
A stopped instance loses an auto-assigned public IP, so the address must be an Elastic IP.
- **Console:** EC2 → Elastic IPs → Allocate → then Actions → Associate → instance `i-095bd5e15981b7b42`.
- Note the EIP → put it in `site-config.json` as `ElasticIp`. (If it differs from the current 3.14.66.202, that's expected.)

### 2. Move DNS to Route 53
> ⚠️ Before switching nameservers, **replicate every existing record** into the new hosted zone — especially the **SES domain-verification TXT, DKIM CNAMEs, SPF/TXT, and any MX**. Miss these and outbound email breaks.
- **Console:** Route 53 → Create hosted zone → `secretsnakes.com`.
- Recreate records: apex `A` → your EIP (TTL 60); `www` `CNAME` → `secretsnakes.com`; plus all mail/verification records from Google DNS.
- Copy the 4 Route 53 NS values → update the nameservers at your registrar (where Google/Squarespace manages the domain).
- Wait for propagation (`Resolve-DnsName secretsnakes.com -Type NS` should show `awsdns`).
- Put the **Hosted Zone ID** in `site-config.json` as `HostedZoneId`.

### 3. Request the ACM certificate (us-east-1)
- **Console (region = N. Virginia / us-east-1):** ACM → Request public cert → names `secretsnakes.com` and `www.secretsnakes.com` → DNS validation → "Create records in Route 53" (one click) → wait for **Issued**.

### 4. S3 bucket for the off-season page
- Create a bucket (e.g. `secretsnakes-offseason`), keep it **private** (CloudFront will use Origin Access Control).
- Upload `offseason/index.html` as the object key `index.html`:
  ```
  aws s3 cp offseason/index.html s3://secretsnakes-offseason/index.html
  ```

### 5. CloudFront distribution
- **Console:** CloudFront → Create distribution.
  - Origin: the S3 bucket, **Origin access: Origin access control (OAC)** → let it update the bucket policy.
  - Default root object: `index.html`.
  - Viewer protocol policy: **Redirect HTTP to HTTPS**.
  - Alternate domain names (CNAMEs): `secretsnakes.com`, `www.secretsnakes.com`.
  - Custom SSL certificate: the ACM cert from step 3.
  - **Custom error responses:** map `403` and `404` → response page `/index.html`, HTTP code `200` (so any path shows the page).
- Copy the distribution domain (e.g. `d1234abcd.cloudfront.net`) → `site-config.json` as `CloudFrontDomain`.

### 6. Verify, then lower TTL
- Temporarily run `.\stop-site.ps1` (or just the DNS swap) and confirm `https://secretsnakes.com` shows the hibernating page with a valid padlock. Then `.\start-site.ps1` to return to the app.
- Keep the apex record TTL at **60s** so swaps take effect quickly.

---

## Operating the season

### With the scripts (recommended)
```
# Go dark for the off-season:
.\offseason\stop-site.ps1

# Bring it back for the season:
.\offseason\start-site.ps1
```

### With console clicks (no scripts)
**Stop (off-season):**
1. Route 53 → hosted zone → edit the apex `A` record → switch to **Alias → CloudFront** → your distribution → Save.
2. EC2 → Instances → select → **Instance state → Stop**.

**Start (in-season):**
1. EC2 → Instances → select → **Instance state → Start**; wait ~1–2 min (status checks green).
2. Route 53 → edit the apex `A` record → **Alias off**, value = your Elastic IP, TTL 60 → Save.

---

## Notes
- **Data is safe across stop/start** — the SQLite DB lives on the EBS volume, which persists while stopped. No S3 restore is involved (that's only for a full instance rebuild/migration).
- **Cert self-heals:** the box renews Let's Encrypt on boot (`@reboot` cron) and via `certbot-renew.timer` in-season, so a long hibernation won't leave an expired cert.
- **Cost while stopped:** ~EBS + Elastic IP only (~$4/mo) vs ~$13–14/mo running.
- The container has `restart=unless-stopped` and Docker/nginx are enabled on boot, so starting the instance is all that's needed to bring the app back.

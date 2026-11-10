# Konfiguration

Zusammenführung in Reihenfolge: `config/defaults.json` → `config/project.json` → `config/environments/ENV.json`. Das vollständige Schema liegt in `config/schema.json`; unbekannte Schlüssel werden abgelehnt. Secrets gehören ausschließlich in die Prozessumgebung/GitHub-Secrets und werden nicht in Terraform-Variablen geschrieben. Die generierten `.runtime`-Dateien sind ignoriert und auf dem Controller geschützt.

| Kategorie | Parameter |
|---|---|
| Projekt | slug, github_repository, hcp_organization, ssh_public_key, acme_email |
| Environment | hostname, cloudflare_zone_id, ssh_cidrs; optional hcp_project/hcp_workspace |
| Compute | cloud_provider=hetzner, region=fsn1, server_type=cpx12, image=ubuntu-24.04 |
| Anwendung | odoo_image, postgres_image, database=odoo, workers=1 |
| DNS/Edge | dns_provider=cloudflare, cloudflare_proxied, manage_zone_settings, manage_cache_rules, cache_hostnames, external_cache_bypass_confirmed |
| Backup | s3_endpoint, s3_region, backup_keep_daily/weekly/monthly |
| Zugriff | ssh_user=deploy, ssh_cidrs, web_cidrs |

Proxied Origins akzeptieren HTTPS nur aus den eingecheckten Cloudflare-Netzen (`config/cloudflare-ips.json`). Das schützt den Origin vor direkter Umgehung. Bei DNS-only `cloudflare_proxied=false` und die gewünschten HTTPS-Quellnetze setzen, beispielsweise alle für eine öffentlich zugängliche Instanz. Port 80 wird nicht benötigt. Es gibt bewusst keinen AAAA-Record, weil die VM keinen öffentlichen IPv6-Ingress aktiviert. Ein zukünftiger IPv6-Adapter muss Firewall, NGINX und DNS gemeinsam erweitern.

Mindestens ein State je Zone muss Cache-Bypass verwalten oder ein bestehender externer Bypass muss ausdrücklich mit `external_cache_bypass_confirmed=true` bestätigt sein. Beispiel für den alleinigen Zonen-Eigentümer:

```json
{
  "manage_zone_settings": true,
  "manage_cache_rules": true,
  "cache_hostnames": ["odoo.dev.example.com", "odoo.stg.example.com", "odoo.example.com"]
}
```

Bei vorhandenen Rulesets nicht blind neue Entry-Points anlegen: Ownership/Import gemeinsam planen. Workflows erhalten den Projektinhalt als GitHub-Variable PROJECT_CONFIG und Environment-Override als ENVIRONMENT_CONFIG (jeweils JSON-Objekt).

Odoo/PostgreSQL-Defaults sind auf überprüfte Linux-amd64-Manifeste per Digest gepinnt. Neue Digests bewusst in dev prüfen, danach stg/prd aktualisieren. Betriebssystem und Docker werden über offizielle signierte Ubuntu-/Docker-Repositories installiert; Paketpatches sind nicht byteidentisch eingefroren. Sicherheitsupdates laufen automatisch über unattended-upgrades. Den gewünschten Paketstand für streng reproduzierbare OS-Builds separat spiegeln/versionieren.

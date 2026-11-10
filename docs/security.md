# Sicherheitsmodell und Credentials

| Secret | Mindestzweck / Geltungsbereich |
|---|---|
| HCLOUD_TOKEN | Hetzner-Projekt Read/Write für Compute/Firewall/Key; je Environment getrennt |
| CLOUDFLARE_API_TOKEN | DNS Edit für die konkrete Zone; Zone Settings Edit und Cache Rules Edit nur für den expliziten Zonen-Eigentümer |
| CF_DNS_API_TOKEN | Separater Certbot-Token: Zone Read, DNS Edit, ausschließlich betroffene Zone |
| TF_API_TOKEN / TF_TOKEN_app_terraform_io | HCP Bootstrap-Projekt/Workspace-Verwaltung; laufender Betrieb nur jeweiliger State/Workspace mit Write/Lock |
| AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY | Nur Terraform-Bootstrap: Bucketanlage und Versionierungsverwaltung |
| BACKUP_AWS_ACCESS_KEY_ID, BACKUP_AWS_SECRET_ACCESS_KEY | Separate Hostkeys: Get/List/Put/Delete für Backup-Daten und Restic-Locks; Rechte mit Bucket-Policy einschränken |
| RESTIC_PASSWORD | Eigenständiges starkes Backup-Verschlüsselungsgeheimnis; offline hinterlegen |
| DB_PASSWORD | Odoo-DB-Rolle, keine Superuser-/CREATEDB-/CREATEROLE-Rechte |
| PG_ADMIN_PASSWORD | PostgreSQL-Admin nur im internen Netzwerk und für Wartung |
| ODOO_MASTER_PASSWORD | DB-Manager-Mastersecret; Datenbankmanager zusätzlich am Proxy gesperrt |
| ODOO_ADMIN_PASSWORD | Nur erste Initialisierung des Odoo-Administrators, kein Reset bei wiederholtem Deploy |
| SSH_PRIVATE_KEY, SSH_KNOWN_HOSTS | GitHub-Runner-SSH und verifizierte Hostschlüssel |

DB-/Odoo-Passwörter müssen 32–128 Hexzeichen enthalten; dadurch werden INI-Injektion und mehrzeilige Werte vermieden. Je Secret separat zufällig generieren. Keine Secrets in project.json, tfvars, Artefakten oder Logs. Ansible-Secret-Tasks nutzen no_log und Modus 0600. Der Hostadministrator und Docker-root können auf Container-/Host-Secrets zugreifen; dieses Vertrauen lässt sich durch reine Dateiberechtigungen nicht aufheben.

Terraform verwendet AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY; Ansible schreibt ausschließlich die getrennten BACKUP_AWS_*-Werte auf den Host. Hetzner-S3-Keys gelten standardmäßig projektweit für alle Buckets. Getrennte Keys allein begrenzen daher keine Rechte: dediziertes Projekt pro Environment und eine mit dem Betreiber geprüfte Bucket-Policy verwenden; Verwaltungsaktionen für Hostkeys explizit verweigern und Restic-Daten-/Lockoperationen erlauben. Die konkrete Policy hängt von den Object-Storage-User-IDs und vorhandenen Projektzugängen ab und wird nicht geraten. Details: [Hetzner S3 credentials](https://docs.hetzner.com/storage/object-storage/faq/s3-credentials/). Vor prd mit Hostkeys testen, dass Bucket-/Policy-/Versionierungsverwaltung und fremde Buckets nicht zugänglich sind.

Provider unterstützen nicht überall generische OIDC-Federation (Hetzner-/Cloudflare-API-Tokens, S3-Schlüssel). Deshalb keine fingierten Kurzzeittokens. GitHub nutzt den kurzlebigen jobgebundenen GITHUB_TOKEN; Provider-Tokens regelmäßig rotieren und Ablauf/Minimalrechte überwachen. Ein späterer Vault-/OIDC-Broker kann Prozessvariablen ohne Änderung des CLI-Vertrags befüllen.

SSH nur Key, Root-Login nach verifiziertem Deploy-Zugang aus, keine Passwortauthentifizierung. Der Deployment-Administrator ist für Ansible Root-äquivalent, ausschließlich für geschützte Infrastrukturjobs. DB ohne Hostport; Odoo nur Loopback. Host-/Hetzner-Firewall ergänzen sich. NGINX vertraut Forwarding-Headern ausschließlich vom konfigurierten Edge. Nicht benötigte Ports/SMTP/Monitoring-Daemons bleiben geschlossen.

Produktionsgates: GitHub Required Reviewers, Default-Branch-Schutz, getrennte Environments, keine PR-Mutationsjobs, gespeicherter Plan, Blockade produktiver delete/replacement-Aktionen, zusätzliche Destroy-Bestätigung, Provider-Löschschutz sowie geschützter Backup-Bucket. Secrets an Reviewer/GitHub-Administratoren und privilegierte Runner mit gleichem Vertrauen behandeln. Ein Committer mit unkontrolliertem Default-Branch-Zugriff könnte Workflows ändern; Branch-Protection ist erforderlich.

Offline-Secret-Scan erkennt bekannte Private-Key-/AWS-/GitHub-Tokenmuster, keine vollständige Geheimniserkennung. Zusätzlich GitHub Secret Scanning/Push Protection oder einen organisationsweiten Scanner aktivieren. Image-Digests, Terraform-Lockdateien und gepinnte Action-SHAs werden eingecheckt; Abhängigkeiten bewusst aktualisieren und auf Sicherheitsmeldungen prüfen.

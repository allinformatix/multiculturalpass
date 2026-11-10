# Bestandsanalyse und Implementierungsplan

Stand: 2026-11-10. Quelle: APOII-Initializor, unverändert. Ziel ist ein separates, ausschließlich lokal erstelltes Template. Keine echten Environment-Dateien, Schlüssel, Zertifikate, Kundendaten oder Binärpakete werden kopiert.

## Umfang und Befunde

Die Verzeichnisinventur erfasst 2.229 versionierte Dateien; remote/compose enthält zusätzlich entpackte Herstellerpakete. Untersucht wurden die Orchestrierung, 23 Bash-Libraries, Compose-Stacks und Build-Dateien, 39 Remote-Skripte, Ansible-Playbook/Templates, Terraform-Module/Environments, fünf Workflows sowie Konfigurations-, Test- und Betriebsdokumentation. Hersteller-JARs/PDFs und generierter Hersteller-Webcode werden nicht als wiederverwendbare Implementierung behandelt. Private Environment-Dateien wurden nicht ausgelesen.

| Quelle | Befund | Entscheidung |
|---|---|---|
| ops.sh, lib/config.sh, lib/terraform.sh | Profilauflösung für QNAP/LXD, mehrere Topologien; Environment-Import ohne shell source; Fehler teilweise unterdrückt | Neue kleine CLI, strikte Fehler, JSON-Konfiguration ohne eval/source |
| lib/host.sh, lib/hosts/*, lib/compose.sh | Fernsteuerung und Compose-Abläufe, historischer QNAP-Treiber | Explizites SSH mit geprüften Hostschlüsseln; kein Legacy-Treiber |
| remote/compose/odoo | Projektimage latest, OIDC/Ping-Abhängigkeit, öffentliche Ports 8069/8072, Loki-Treiber | Offizielles Odoo 18, Loopback-Ports, kein Identity-Zwang |
| remote/compose/postgres | Geteilte DB für mehrere Anwendungen; Port 5432 veröffentlicht | Dedizierte PostgreSQL-16-Instanz ohne Hostport; getrennte Admin-/Anwendungsrolle |
| remote/compose/smtp | Postfix, DKIM, Sender-Policy-DB und SES-Fallback | Externer SMTP-Provider über native Odoo-Konfiguration; kein zusätzlicher Relay-Service erforderlich |
| remote/compose/rp; ansible/templates/nginx | Containeralternative vorhanden, aktiver Provisioning-Pfad nutzt natives NGINX/Certbot auf separater VM | Natives NGINX auf AIO-Host; Zertifikats-Erneuerung ohne Containerzugriff; GeoIP/IDM-Routen entfallen |
| ansible/playbooks/site.yml | Monolith, Registry-Login, Docker-Repository, Synchronisierung, Compose, Monitoring und Cron; Fehler-Recovery entfernt kollidierende Container | Rollen für Host, Docker, Anwendung; keine automatische Entfernung fremder Container; kein verpflichtendes Loki |
| terraform/modules/providers/hetzner | VM je Komponente, privates Netz, Firewall, SSH-Key, dynamische Preisabfrage | Eine VM mit Firewall, deterministischer Typ cpx12, keine Preisabfrage oder unnötiges Privatnetz |
| terraform/environments/* | HCP remote mit festem Organisationsnamen; Cloudflare v4; AWS-Provider als S3-Adapter | Dynamische Backend-Konfiguration; getrennte Compute/DNS/S3-Module; Cloudflare v5 |
| remote/scripts/backup-odoo-s3.sh | Dump und Filestore nacheinander ohne Schreibsperre, separate S3-Objekte unverschlüsselt | Odoo stoppen, Dump + Filestore in einem verschlüsselten Restic-Snapshot; Sperre gegen Parallelbetrieb |
| remote/scripts/restore-odoo-s3.sh | Interaktive Auswahl/eval; DROP und Dateilöschung; Stop-/Startfehler unterdrückt | Snapshot-ID und exakte Bestätigung; Sicherheitsbackup vor Überschreiben; bei Fehler Anwendung gestoppt lassen |
| .github/workflows/deploy-*.yml | Umfangreiche je Stage duplizierte Jobs, Apply mit auto-approve, teilweise Importfehler ignoriert | Wiederverwendbarer manueller Workflow, identische Concurrency-Gruppe, GitHub-Environment-Schutz, gespeicherter Plan |
| k8s, Ping AM/DS/IDM/Gateway, GeoIP, AD, SES-/Identity-Bootstrap | Für Einzel-Odoo nicht erforderlich | Nicht übernehmen |

## Risiken und Abhängigkeiten

CPX12 hat nur 1 vCPU/2 GB RAM: ein HTTP-Worker, ein Cron-Thread, begrenzter PostgreSQL-Cache; Lasttests und frühes Upsizing notwendig. Keine Hochverfügbarkeit. Docker-Portveröffentlichung kann UFW umgehen: ausschließlich Loopback binden. TLS-DNS-Validierung benötigt eigenes eingeschränktes Cloudflare-Token. Cloudflare-Zonenregeln betreffen andere Hosts: zonenweite TLS-Änderungen nur bewusst aktivieren. S3-Versionierung ersetzt weder getrennte Credentials noch externen Löschschutz. Backups benötigen Platz für Datenbankdump und Restore. HCP- und GitHub-Projekt-/Reviewer-Funktionen hängen von Rechten und Tarif ab. Externe Zugangsdaten und reale Cloud-Integration sind lokal nicht verifizierbar.

## Geplante Umsetzung

1. Architekturentscheidungen und Adaptervertrag dokumentieren.
2. Strikte JSON-Konfiguration mit Defaults, Projekt und Environment-Overrides.
3. HCP-API-Bootstrap ohne eigenen Terraform-State; Workspace-Ausführung lokal, State/Locking in HCP.
4. Terraform-Module für Hetzner-VM/Firewall, Cloudflare und Hetzner-S3, getrennte Environment-Roots.
5. Ansible-Rollen für SSH/Firewall, Docker, NGINX/Certbot, Odoo/PostgreSQL und Backup-Timer.
6. Bash-Einstieg und Libraries, sichere Plan-/Apply-, Application-only-, Backup-/Restore-/Destroy-Abläufe.
7. Manuelle GitHub-Workflows mit geprüftem Plan, Environment-Gates und Concurrency.
8. Lokale statische und Mock-Tests, Betriebs- und DR-Anleitung; verbleibende Integrationsrisiken explizit erfassen.

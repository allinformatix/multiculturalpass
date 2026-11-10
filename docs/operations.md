# Betrieb

| Befehl | Wirkung |
|---|---|
| doctor --env ENV | Werkzeuge, Konfiguration, lesende HCP/Hetzner/Cloudflare-Authentifizierung |
| init --env ENV | HCP-/GitHub-Bootstrap und Backend-Init |
| plan / apply / provision | Prüffähiger Plan, gespeicherten Plan anwenden, beide Schritte |
| configure | Host-, Docker- und Anwendungsrollen |
| deploy / deploy --app-only | Vollständige Kette / nur Anwendungsrolle |
| status / logs | Terraform-Output, SSH/Compose, HTTPS / letzte Containerlogs |
| backup-init / backup | Restic-Repository explizit initialisieren / konsistentes Backup |
| restore --snapshot ID --confirm SLUG-ENV:restore | Kontrollierte Wiederherstellung |
| update | Backup, Anwendungsrolle, Healthcheck; innerhalb Odoo 18 / PostgreSQL 16 |
| destroy --confirm SLUG-ENV:destroy | Backup, Compute/DNS löschen; Bucket erhalten |

--dry-run erzeugt/validiert ausschließlich lokale Runtime-Konfiguration und zeigt geplante Befehle; keine Provideroperation, kein SSH, kein Apply. Schutzprüfungen bleiben aktiv. Toolfehler und SSH-/Ansible-/Terraform-Exitcodes werden nicht verschluckt. Logs sind strukturiert; Fehlertraps enthalten keine Befehlszeilen mit Geheimnissen. Containerlogs können Geschäftsdaten enthalten: Zugriff wie auf Produktionsdaten behandeln.

Updates: neuen Odoo-/PostgreSQL-Digest konfigurieren, in dev testen, Sicherheitsbackup verifizieren, dann update. Ohne Konfigurations-/Digeständerung ist die Anwendungskonfiguration idempotent. Restart erfolgt nur bei geänderten Deployment-Dateien beziehungsweise wenn Odoo nicht läuft. Majorwechsel sind per Konfiguration gesperrt und benötigen eigenes DB-/Addon-Migrationsprojekt, etwa mit OpenUpgrade oder Odoo-Service. Ein bloßes Zurücksetzen des Images nach einer DB-Schemaänderung ist kein sicherer Rollback: zugehörigen Snapshot wiederherstellen.

Hostpatches: unattended-upgrades installiert Ubuntu-Sicherheitsupdates. Reboots kontrolliert nach Backup und Prüfung von /var/run/reboot-required durchführen. `configure` installiert fehlende Basis-/Dockerpakete, aktualisiert aber nicht pauschal alle bestehenden Dockerpakete. Docker-/Host-Versionsupgrades bewusst über einen Wartungsplan ausrollen und dokumentieren.

Auf dem Server: `/opt/odoo` ist rootgeschützt; config/odoo.conf gehört UID 101, PG-Secrets nur root, Odoo-Dateidaten UID 101. Der Anwendungscontainer hat keinen Host-sudo und keine Docker-Socket-Mounts. Custom Addons unter /opt/odoo/addons aus geprüften Releases installieren; sie sind im Container read-only, im Backup enthalten. Der Template-Controller synchronisiert bewusst keine beliebigen Original-Addons.

Monitoring ohne Zusatzdienst: systemctl --failed, systemctl status odoo-backup.timer, journalctl -u odoo-backup.service, /opt/odoo/state/last-backup-success und backup-failed prüfen. `sudo /usr/local/sbin/odoo-backup health` liefert einen Fehlercode bei fehlendem, fehlgeschlagenem oder über 36 Stunden altem Backup. Einen externen Monitor auf fehlendes/staleres Backup (>36 Stunden), HTTPS, Zertifikatsablauf, RAM/Swap, Disk und CPU anbinden. Journald/Timerfehler sind eine lokale Alarm-Schnittstelle, kein bereits eingerichteter externer Alarmkanal. journald und Containerlogs sind begrenzt; langfristige Audit-Logs bei Bedarf an ein separates Ziel senden.

Destroy belässt das verschlüsselte Repository und seinen Terraform-State. prd benötigt zusätzlich --allow-production-destroy; nur dann wird nach erfolgreichem Backup explizit Hetzner-Löschschutz deaktiviert. Die gezielte Terraform-Destroy-Planung umfasst module.compute und module.dns; die bewusst erwartete Target-Warnung bedeutet hier Backup-Erhalt. Nach Abbruch Schutz prüfen/erneut aktivieren. Bucketlöschung und HCP-/GitHub-Environment-Entfernung sind getrennte manuelle, ausdrücklich freizugebende Aufgaben. Destroy eines Zonen-Eigentümers wird vor jeder Mutation blockiert, bis gemeinsame Zonenressourcen sicher übertragen wurden. Ein letzter Environment-State darf nicht zonenweite TLS-/Cache-Regeln für noch aktive andere Environments entfernen; Ownership vorher übertragen.

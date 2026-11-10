# Lokale Validierung und verbleibende Abnahme

Stand: 2026-11-10. Ausschließlich das neue lokale Template wurde implementiert. Das ursprüngliche Repository hat keine Änderungen an versionierten Dateien. Keine vorhandenen Secrets, Zertifikate oder Kundendaten wurden übernommen. Das neue Repository ist lokal mit Branch main initialisiert, ohne Remote und ohne Veröffentlichung.

## Erfolgreich ausgeführte Prüfungen

| Prüfung | Ergebnis |
|---|---|
| Python unittest | 35 Tests bestanden: 27 CLI-/Konfigurations- und 8 Backup-/Restore-Tests |
| Terraform native tests | 2 Tests mit ausschließlich gemockten Providern bestanden: Adapteridentität und falsches Environment |
| Terraform fmt -check -recursive | Bestanden |
| Terraform init -backend=false und validate | dev, stg und prd bestanden; echte installierte Provider-Schemas, kein Cloud-Backend |
| Bash-Syntax und ShellCheck 0.10.0 | CLI, Libraries, Validierungsskript und gerenderte Wartungsskripte bestanden |
| YAML-Lint 1.38.0 | Workflows, Composite Action und Ansible-Dateien bestanden |
| Ansible-Lint 26.11.0 | Profil production: keine Fehler oder Warnungen |
| Ansible Syntaxcheck | Bestanden mit ansible-core 2.21.6 |
| Template-Rendering | Alle application-Templates mit Ansible und synthetischen Secrets gerendert |
| Docker Compose config | Gerenderte Compose-Konfiguration bestanden, Compose v5.6.1 |
| Python compileall | CLI-Hilfen und Tests syntaktisch gültig |
| Secret-Basisscan | Keine bekannten Private-Key-/AWS-/GitHub-Tokenmuster oder verbotenen Secretdateien im neuen Quellbaum |
| Quellrepository | git diff unverändert; einzig neues Template-Verzeichnis unversioniert im Elternrepository |

Reproduktion aus dem neuen Repository mit installierten Dependencies und Terraform: `./scripts/validate.sh`. Der erste Providerdownload benötigt Internet. Unter der lokalen macOS-Sandbox mussten Registry-Zugriff und lokale Terraform-Provider-Sockets für die Prüfung freigegeben werden. Python und Prüfwerkzeuge wurden isoliert unter /tmp installiert; keine globalen Pakete wurden verändert. Ansible-Prüfung unter UTF-8-Locale; auf macOS beispielsweise LC_ALL=en_US.UTF-8. GitHub verwendet Ubuntu 24.04/Python 3.12.

Provider: hcloud 1.70.1, Cloudflare 5.24.0, AWS 6.23.0. Terraform CLI 1.13.5. Provider-Lockdateien mit geprüften Downloadchecksummen liegen je Environment vor. Odoo 18.0 und PostgreSQL 16.13 sind auf öffentlich überprüfte amd64-Manifest-Digests gepinnt. Die Images wurden nicht gestartet.

Die Backup-Mocks führen das tatsächliche gerenderte Bash-Skript auf temporären lokalen Dateien aus. Docker, Restic, flock, chown, logger und Prüfsummen werden dabei kontrolliert ersetzt. Geprüft sind Schreibpause vor Dump, Wiederaufnahme vor Upload, Fehlerweitergabe, verweigerter Restore bei falscher Identität, Sicherheitsbackup vor DROP und Offline-Zustand nach Teil-Restore. Diese Tests beweisen weder die echte Restic-Verschlüsselung noch PostgreSQL-/S3-Kompatibilität oder Filestore-Konsistenz einer laufenden Odoo-Instanz; dafür gilt der folgende Abnahmeplan.

## Nicht ausgeführt und vor Produktion erforderlich

- Kein echtes Terraform Plan/Apply/Destroy mit Provider-Credentials, kein HCP-State-Zugriff und kein HCP-/GitHub-Bootstrap im Nutzeraccount.
- Keine kostenpflichtigen Ressourcen und keine Änderungen bestehender Cloud-Ressourcen.
- Kein laufender lokaler Docker-Daemon: kein Containerstart, kein echter Odoo-/PostgreSQL-Initialisierungstest, kein NGINX-Laufzeit-Syntax-/TLS-Test.
- Keine Ansible-Ausführung auf einer VM und kein Nachweis tatsächlicher Host-Idempotenz.
- Keine DNS-/Cloudflare-/ACME-Erstellung, keine GitHub-Actions-Ausführung und kein Test realer Reviewer-/Tarifrechte.
- Keine echte Hetzner-S3-Bucketanlage/Versionierung, keine Prüfung einer betreiberspezifischen Bucket-Policy, kein Upload/Download und kein echter Restore auf einer neuen VM.
- Keine Messung von Last, Backup-Wartungsfenster, RPO/RTO, Disk-Bedarf oder OOM-Verhalten auf CPX12.

Der vollständige Erstdeployment- und DR-Abnahmetest steht in getting-started.md und disaster-recovery.md. Er muss in einem genehmigten, isolierten Environment erfolgen. Das Template ist lokal implementiert und geprüft; eine produktiv verifizierte Installation wird ausdrücklich nicht behauptet.

## Bewusste Betriebsgrenzen

Eine VM ist kein HA-System. Odoo ist der einzige unterstützte DB-/Filestore-Schreiber. Restic-Retention entfernt Snapshots, aber nicht automatisch alle Packs/Objektversionen; physische Löschfristen und Kosten brauchen einen separaten Wartungsplan. S3-Versionierung ist kein WORM-Schutz. Host-Backup-Credentials müssen durch geprüfte Hetzner-Projekt-/Bucket-Policies begrenzt werden. Der Infrastrukturadministrator ist Root-äquivalent. Lokale und CI-Konfiguration dürfen nicht gleichzeitig über verschiedene Controller geändert werden; Terraform-State-Locking und Server-flock ersetzen keinen globalen Ansible-Deployment-Lock. Zonenweite Cloudflare-Regeln haben einen expliziten gemeinsamen Eigentümer. Produktive Major-Migrationen und destruktive VM-Ersetzungen erfordern ein eigenes geprüftes Verfahren.

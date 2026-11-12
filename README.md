# Odoo All-in-One IaC Template

Eigenständiges Template für Odoo 18 Community und PostgreSQL 16 auf einer Ubuntu-24.04-VM je Environment. Hetzner stellt Compute/Firewall und S3 bereit, Cloudflare DNS/Edge, HCP Terraform den getrennten State. Natives NGINX terminiert TLS; Ansible installiert und betreibt den Stack.

**Status:** Lokal implementiert und statisch beziehungsweise mit Mocks geprüft. Kein Cloud-Deployment und kein echter Container-/Restore-Lauf ausgeführt. Die genauen Ergebnisse stehen in [validation.md](docs/validation.md). Vor produktiver Verwendung ist der dokumentierte DR-Abnahmetest erforderlich.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
./ops.sh doctor
cp config/project.example.json config/project.json
# Projekt und config/environments/{dev,stg,prd}.json ausfüllen; Credentials exportieren.
./ops.sh env init --env dev
# .env.dev im Editor mit Credentials ergänzen.
./ops.sh env validate --env dev
./ops.sh init --env dev
./ops.sh plan --env dev
./ops.sh provision --env dev --confirm customer-odoo-dev:apply
# SSH-Hostschlüssel über die Hetzner-Konsole verifizieren und in known_hosts hinterlegen.
BOOTSTRAP_SSH_USER=root ./ops.sh configure --env dev
./ops.sh backup-init --env dev --confirm customer-odoo-dev:init-backup
./ops.sh backup --env dev
./ops.sh status --env dev
```

Nach dem erstmaligen Bootstrap ist `./ops.sh deploy --env dev` der vollständige Provisioning-/Konfigurationspfad. Lokal wird vor Apply eine exakte Bestätigung abgefragt; in CI muss sie explizit übergeben werden. `deploy --app-only` konfiguriert ausschließlich die Anwendung auf vorhandener Infrastruktur. Ein neuer Hostschlüssel muss vor Ansible verifiziert werden; die CLI vertraut niemals blind einem SSH-Scan.

Die manuellen GitHub-Workflows planen zuerst, veröffentlichen den Plan für einen Tag und wenden genau diesen Plan nach dem zweiten Environment-Gate an. Produktionsänderungen benötigen konfigurierte GitHub-Reviewer. PRs führen ausschließlich Validierungen ohne Deployment-Secrets aus.

| Verzeichnis | Inhalt |
|---|---|
| config/ | Schema, Defaults, Projektbeispiel, isolierte Environment-Overrides |
| terraform/ | Environment-Roots, Compute-, DNS- und Object-Storage-Adapter |
| ansible/ | Rollen für Host, Docker und Anwendung mit NGINX und Backup |
| lib/, scripts/, ops.sh | CLI, HCP-/GitHub-Bootstrap, Validierung |
| tests/ | Offline CLI- und Backup-/Restore-Mocks |
| docs/ | Architektur, Installation, Sicherheit und Betrieb |

Start: [Getting Started](docs/getting-started.md). Betrieb: [Operations](docs/operations.md). Wiederherstellung: [Disaster Recovery](docs/disaster-recovery.md). Herkunft und Entscheidungen: [Bestandsanalyse](docs/architecture/source-repository-analysis.md), [ADRs](docs/architecture/decisions.md).

Für eine neue GitHub-Vorlage ausschließlich dieses Verzeichnis als Repository-Root verwenden. Das APOII-Quellrepository gehört nicht in das neue Repository. Veröffentlichung und Aktivierung von „Template repository“ erfolgen erst nach separater Freigabe.

Lokale Plattformverwaltung: [Voraussetzungen](docs/prerequisites.md), [dotenv-Konfiguration](docs/environment-configuration.md), [GitHub-Synchronisierung](docs/github-integration.md) und [Grafana Cloud](docs/grafana-cloud.md). `doctor --json`, sichere `--fix`-Installation und `observability` sind Teil derselben ops.sh-CLI. Lokale .env-Dateien werden in CI nie gelesen.

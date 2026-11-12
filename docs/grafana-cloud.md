# Grafana Cloud aktivieren und prüfen

Für jeden echten Mandanten einen getrennten Grafana-Cloud-Stack oder nachweislich passende Zugriffskontrollen einrichten. Ein Loglabel tenant ermöglicht Filterung, aber verhindert keinen Zugriff anderer berechtigter Stackbenutzer. Region/Datenverarbeitung, Aufbewahrung, Zugriffsrollen, Audit und erforderliche organisatorische Vereinbarungen vor ERP-Logübertragung festlegen. Die Infrastruktur konfiguriert nicht automatisch den Grafana-Cloud-Vertrag oder dessen Retention.

In der gewählten .env.ENV beziehungsweise dem GitHub Environment setzen:

```dotenv
OBSERVABILITY_ENABLED=true
OBSERVABILITY_PROVIDER=grafana-cloud
TENANT_ID=customer-a
GRAFANA_CLOUD_LOKI_URL=https://logs-prod-001.grafana.net/loki/api/v1/push
GRAFANA_CLOUD_LOKI_USER=
GRAFANA_CLOUD_LOKI_TOKEN=
GRAFANA_CLOUD_STACK=
```

URL/User aus der Connection-Anleitung des eigenen Stacks nehmen; die obige URL ist nur ein Formatbeispiel. Token mit minimalem logs:write-Scope bereitstellen. Collector installiert ausschließlich diesen Write-Token. Optional lokal GRAFANA_CLOUD_LOKI_READ_TOKEN mit logs:read für die Zustellprüfung setzen; er wird nicht synchronisiert und nicht auf den Host geschrieben.

```bash
./ops.sh env validate --env dev
./ops.sh github sync --env dev --dry-run
./ops.sh configure --env dev
./ops.sh observability validate --env dev
./ops.sh observability status --env dev
./ops.sh observability logs --env dev
./ops.sh observability test --env dev
```

Beim Wechsel des Docker-Logtreibers muss Compose bestehende Container neu anlegen; vorher ein konsistentes Backup erstellen und ein Wartungsfenster nutzen. Erste Aktivierung über vollständiges configure/deploy, damit Host-Journald persistent eingerichtet wird. Alloy stammt aus dem signierten offiziellen Grafana-APT-Repository, genaue Version in config/tools.json (optional kompatibel über alloy_version überschreibbar). Eine Konfigurationsvalidierung vor Dateiaustausch verhindert Aktivierung ungültiger Pipelines. Credentials bleiben in /etc/alloy/loki-token mit root:alloy 0640, Konfiguration enthält nur den Pfad. Änderungen starten den Dienst über Handler neu. Deaktivierung stoppt/deaktiviert den bestehenden Dienst, installiert ihn nicht neu und entfernt keine Daten stillschweigend.

observability test schreibt nur bei explizitem Aufruf einen synthetischen Marker über logger auf dem Zielhost und sucht ihn mit Read-Token im passenden tenant/stage/project/component-Stream. Es pusht nicht direkt an Loki und umgeht somit nicht den Collector. Ein Status/Ready-Erfolg beweist keine Logankunft. Ohne Read-Token kann Zustellung nicht automatisch bewiesen werden; Grafana Explore benutzen:

```logql
{tenant="customer-a", stage="dev", project="customer-odoo"}
```

Vor Produktivfreigabe alle Komponenten einzeln auslösen, Labels/Redaction prüfen, Grafana-Verbindung unterbrechen, Collector neu starten und tatsächliche Verluste/Disk-/RAM-Spitzen messen. Die lokale Entwicklung hat keine Logdaten an einen echten Stack gesendet.

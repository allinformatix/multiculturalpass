# Environment-Konfiguration

Eine CLI, zwei klar getrennte Konfigurationsebenen: config/schema.json validiert nichtgeheime JSON-Projekt-/Environment-Daten. config/variables.json definiert Prozess-/dotenv-Variablen einschließlich Typ, Default, Secret, Scope, Environment, Pflichtkontext, GitHub-Zuordnung und expliziter Sync-Freigabe. Die Feldzuordnung config_key verbindet beide Ebenen.

Priorität: JSON-Defaults → Projekt-JSON → Environment-JSON → ausgewählte lokale .env.ENV → explizite Prozessumgebung. Keine Expansion, kein source, kein eval. CI=true ignoriert lokale dotenv-Dateien vollständig. Die CLI liest niemals eine andere dotenv-Datei als Ersatz für ein fehlendes Environment.

```bash
./ops.sh env init --env dev
chmod 600 .env.dev
# Werte im Editor setzen; Credentials selbst erzeugen/bereitstellen.
./ops.sh env validate --env dev
./ops.sh env show --env dev --redact
./ops.sh env diff --env dev --env2 stg
```

Init erstellt eine strukturell gültige Datei mit Defaults und vorhandenen nichtgeheimen Projektwerten. Notwendige Credentials bleiben leer; vollständige Validierung fordert sie anschließend an. Bestehende Dateien bleiben erhalten, solange nicht ausdrücklich --confirm dev:overwrite-env angegeben wird. Keine Symlinks und keine Datei mit Gruppen-/Fremdzugriff. --dry-run zeigt die beabsichtigte Dateianlage ohne Schreibzugriff; die Bestätigungsregeln bleiben aktiv.

Format: eine bekannte VARIABLE=Wert pro Zeile, optionale einfache/doppelte Anführungszeichen, vollständige Kommentarzeilen. Kein export, keine Inline-Kommentare, keine Backslash-Escapes, keine Mehrzeilenwerte, kein Dollarzeichen oder Backtick, keine Shelloperatoren in unquotierten Werten. Passwörter für Odoo/PostgreSQL bleiben zufällige 32–128 Hexzeichen. Mehrzeilige SSH-Schlüssel über SSH_PRIVATE_KEY_PATH, verifizierte Hostschlüssel über SSH_KNOWN_HOSTS_PATH oder CI-Prozessvariablen bereitstellen. SSH_PUBLIC_KEY_PATH kann das öffentliche JSON-Schlüsselfeld ersetzen.

show redigiert Secrets immer, auch ohne --redact. diff zeigt bei Secrets nur, dass sie sich unterscheiden. ENVIRONMENT muss --env entsprechen. LOG_STAGE/PROJECT/PROVIDER/REGION/TENANT/APPLICATION und S3_BUCKET werden aus der validierten Identität abgeleitet; widersprüchliche Angaben sind Fehler. TENANT_ID ist konfigurierbar, Standard ist der Slug. SERVER_TIMEZONE wird gegen IANA-Zeitzonen geprüft und durch Ansible gesetzt; der Backup-Timer bleibt ausdrücklich UTC.

Kompatibilitätsnamen TF_TOKEN/TF_API_TOKEN, POSTGRES_PASSWORD, POSTGRES_DB und S3_ACCESS_KEY/S3_SECRET_KEY sind dokumentierte Aliase; widersprüchliche Doppelbelegung wird abgelehnt. AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY bleiben Terraform-Managementcredentials, BACKUP_AWS_* separate Hostcredentials. Nicht jede illustrative Variable aus anderen Plattformen wird übernommen: SMTP wird weiterhin direkt in Odoo mit externem Provider konfiguriert, kein SMTP-Daemon oder funktionsloser SMTP-Schalter wird hinzugefügt.

Die vollständige generierte Referenz steht in [environment-reference.md](environment-reference.md). Nach Katalogänderungen `python3 scripts/generate_environment.py` ausführen. Der Validierungsworkflow prüft auf Abweichungen der Beispieldatei/Dokumentation. Echte .env.*-Dateien bleiben ignoriert; .env.example ist die einzige Ausnahme.

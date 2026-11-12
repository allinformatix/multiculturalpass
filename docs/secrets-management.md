# Secrets verwalten

Lokale .env.dev/.env.stg/.env.prd gehören dem Betreiber, Modus 0600, niemals committen oder als Artefakt hochladen. Der Parser akzeptiert nur bekannte Schlüssel des Variablenkatalogs, führt keinen Code aus und expandiert nichts. Alternativ Werte im Prozess aus einem Secretmanager bereitstellen; Prozesswerte haben Vorrang. Auf gemeinsame Controller und Shell-History achten.

Für CI werden Secrets und Variables direkt aus dem GitHub Environment geliefert. ci_prepare.py erstellt nur nichtgeheime JSON-Konfiguration und geschützte SSH-Dateien. Es erzeugt keine dotenv-Datei. Vor Plan/Apply/Ansible prüft dieselbe Schemaimplementierung die tatsächlich benötigten Werte. Eine erfolgreiche lokale Secretprüfung bestätigt Format/Existenz; reine GitHub-Metadaten können niemals einen Secretwert prüfen.

```bash
./ops.sh github secrets check --env dev
./ops.sh github vars check --env dev
./ops.sh github sync --env dev --dry-run
./ops.sh github sync --env dev
```

Sync überträgt ausschließlich als sync=true markierte Werte, keine unbekannten lokalen Variablen, keinen GH_TOKEN und keine lokalen Schlüsselpfade. Private SSH-Dateien werden nur bei expliziter Pfadkonfiguration eingelesen und als SSH_PRIVATE_KEY über stdin an gh übergeben. Token-/Secretwerte stehen nicht in Argumenten oder Ausgaben. gh übernimmt Public-Key-Verschlüsselung für GitHub Secrets.

Existierende Secrets und Variables werden standardmäßig behalten, auch wenn sie aus Repository/Organisation geerbt werden. --overwrite erlaubt bewusstes Überschreiben in das ausgewählte Environment; fremde Scopes werden nicht geändert. Bei unlesbarem möglichem Vererbungsscope wird ein neuer Wert blockiert, bis die Leseberechtigung geklärt wurde. prd benötigt zusätzlich --confirm SLUG-prd:sync-github, auch beim Dry-Run. Die Entwicklung hat keinerlei echte Secrets synchronisiert.

Ein Tenant-Label ersetzt keine Sicherheitsgrenze. Für Kunden eigene Provider-/S3-/Grafana-Credentials und geeignete getrennte Projekte/Stacks verwenden. Bereits im ursprünglichen Security-Dokument beschriebene Host-/Bucket-Rechte gelten weiter. Beispielwerte und Mocktokens sind synthetisch; der Basisscanner ist keine vollständige DLP-Lösung.

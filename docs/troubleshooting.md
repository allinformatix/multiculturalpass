# Fehlerbehebung

| Fehler | Prüfung und Maßnahme |
|---|---|
| Konfiguration abgelehnt | project.json anlegen, Pflichtwerte/Schema/SSH-CIDRs/Cache-Ownership prüfen; keine Secrets hineinschreiben |
| HCP 403/404 | Organisation, Projektrechte und Workspace-Zugriff prüfen; Administrator kann Ressourcen vorab anlegen |
| Init meldet fehlende prd-Reviewer | Required Reviewers im GitHub Environment einrichten; Tarif/Berechtigungen prüfen, dann wiederholen |
| SSH host verification failed | Fingerprint über Konsole prüfen und known_hosts gezielt pflegen; StrictHostKeyChecking nicht abschalten |
| SSH nach Bootstrap nicht erreichbar | Deploy-Key, Benutzer und feste Egress-CIDRs prüfen; Konsole für Reparatur nutzen |
| Cloudflare 525/526 | Originzertifikat, NGINX, Full (strict), DNS und erlaubte Cloudflare-Quellnetze prüfen |
| DNS-01 fehlgeschlagen | Separater CF_DNS_API_TOKEN mit Zone Read/DNS Edit, Delegation und Propagation prüfen |
| Ruleset conflict | Pro Zone/Phase nur einen Eigentümer nutzen; bestehende Regeln importieren/erweitern statt überschreiben |
| 502 / WebSocketfehler | compose ps/logs, /web/health, Worker=1 und Evented-Port 8072 prüfen |
| OOM oder langsame Berichte | docker stats, journalctl -k, CPU/Disk prüfen; CPX12 vergrößern, Parallelität begrenzen |
| Backup scheitert | journalctl -u odoo-backup.service, Repository-Credentials, freien Platz, staging/snapshot und Odoo-Status prüfen |
| Restore wurde unterbrochen | Anwendung offline halten, Fehler beheben und verifiziertes Sicherheitsbackup verwenden; kein blindes Starten |
| Plan-Prüfsumme oder State veraltet | Neu planen und erneut prüfen; keine Prüfsumme manuell überschreiben |
| Destroy blockiert Bucket | Erwartet: Backup wird erhalten; Zielauswahl compute/dns verwenden, keine prevent_destroy-Entfernung für normale Deinstallation |
| Lokale Sperre vorhanden | Prüfen, ob noch ein ops-Prozess läuft; nur verwaistes operation.lock-Verzeichnis entfernen |

Fehlerausgaben enthalten absichtlich keine Secretwerte. Bei eigener Debugausgabe niemals set -x für secretbehaftete Abläufe aktivieren. Echte `.runtime`-Outputs und Planartefakte nicht öffentlich in Issues posten.

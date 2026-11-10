# Architecture Decision Records

## ADR-001: Separate neue Quelle

Das Template entsteht in einem eigenen Verzeichnis/Repository. Keine Originaldateien, Secrets, Schlüssel, Zertifikate oder Herstellerpakete werden übernommen. Die generischen Ablaufmuster werden neu implementiert.

## ADR-002: Host-NGINX

Die vorhandene produktive Ansible-Strecke verwendet natives NGINX und Certbot. Diese Variante benötigt keinen Containerzugriff auf private Zertifikatsschlüssel und funktioniert mit dem systemweiten Renewal-Timer. Die Containeralternative ist portabel und könnte später verwendet werden, würde hier jedoch Zertifikats-Erneuerung und Host-Portschutz zusätzlich koppeln. Host-NGINX bleibt der einzige Ingress.

## ADR-003: SMTP direkt aus Odoo

Der bisherige SMTP-Stack implementiert Postfix, DKIM, Senderpolicies, eine zusätzliche Policy-Datenbank und SES-Fallback. Odoo kann direkt über einen externen SMTP-Provider senden. Deshalb kein SMTP-Container und kein offener SMTP-Port; Betreiber konfigurieren Server/STARTTLS beziehungsweise SMTPS im Odoo-UI. Ein Relay wird nur bei nachgewiesenem Bedarf als eigenständige Integration ergänzt. SPF/DKIM/DMARC bleiben Zuständigkeit des Mailanbieters.

## ADR-004: HCP API vor Backend

Ein API-Bootstrap erstellt Projekt und Workspace ohne eigenen Terraform-State. Workspaces verwenden local execution, HCP speichert State und Locks. Terraform läuft lokal/in Actions; Provider-Credentials müssen nicht zusätzlich in HCP verwaltet werden. Ein einzelner Hauptworkspace und CLI-Workspaces werden vermieden.

## ADR-005: Konsistenz vor unterbrechungsfreiem Backup

Odoo ist der einzige DB-/Filestore-Schreiber. Backup stoppt Odoo kontrolliert, erstellt einen geprüften Custom-Format-Dump und kopiert Filestore, Addons und Konfiguration in ein geschütztes Staging-Verzeichnis. Erst danach wird Odoo wieder gestartet. Upload und Retention laufen außerhalb der Schreibpause. Dieses Verfahren benötigt Zusatzplatz ungefähr in Größe der Odoo-Dateidaten plus Dump. Kein Snapshot eines laufenden Filestores wird als konsistent ausgegeben.

## ADR-006: Expliziter Restore und Datenerhalt

Restore erfordert vollständige Snapshot-ID und project-env:restore. Er prüft Tag, Prüfsummen, Versionen und Dump vor jeder DB-Mutation und erstellt ein Sicherheitsbackup. Teilfehler nach DROP lassen die Anwendung offline. Alte Datei-/Addonverzeichnisse werden erhalten. Destroy entfernt nur Compute und DNS; der Backup-Bucket bleibt durch prevent_destroy und force_destroy=false geschützt.

## ADR-007: Keine kostenpflichtigen Edge-Abhängigkeiten

Kein WAF-/Rate-Limit-Produkt wird vorausgesetzt. NGINX schützt Login und Datenbankmanager; Cloudflare-Managed-WAF kann separat tarifabhängig ergänzt werden. Odoo-Antworten sind nie Cache-Ziele. Zonenweite Regeln haben genau einen Eigentümer; andere States bestätigen explizit die externe Cache-Bypass-Konfiguration.

## ADR-008: Betriebsschlüssel und Vertrauen

Ansible benötigt Root-Rechte für OS-/Docker-/NGINX-Konfiguration. Der dedizierte Infrastrukturadministrator ist deshalb explizit Root-äquivalent, hat jedoch keine Passwortauthentifizierung und keine Docker-Gruppenmitgliedschaft. Ein scheinbar enges sudo-Recht auf frei ausführbares Ansible/Python wäre ebenfalls Root-äquivalent. Applikationsbenutzer erhalten keinerlei Host-sudo. Für strengere Trennung ist ein privilegierter, geschützter Infrastruktur-Runner erforderlich.

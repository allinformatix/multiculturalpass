# Environment-Isolation

| Environment | Standardressourcenname | Beispielhostname |
|---|---|---|
| dev | customer-odoo-dev | odoo.dev.example.com |
| stg | customer-odoo-stg | odoo.stg.example.com |
| prd | customer-odoo-prd | odoo.example.com |

Der Slug muss je abgeleitetem Repository eindeutig sein. Standardmäßig heißen HCP-Projekt und Workspace SLUG-ENV; Overrides sind je Environment möglich. Die Konfigurationsvalidierung lehnt gemeinsam verwendete Workspace-Namen innerhalb derselben Organisation, doppelte Hostnamen und doppelte Zonenregel-Eigentümer bereits vor der Backend-Initialisierung ab. Kein Terraform-CLI-Workspace-Switch und kein gemeinsamer State. Compute-Namen, Firewall und SSH-Key sind getrennt; Compose-Projektnamen und Bucketnamen enthalten SLUG-ENV. Pro Environment eigene Provider-Tokens und Passwörter sowie nach Möglichkeit getrennte Hetzner-Projekte verwenden.

Eine Cloudflare-Zone kann geteilt sein. Zonen-TLS und Cache-Entrypoints sind deshalb gemeinsame Infrastruktur mit genau einem State-Eigentümer. DNS-Records bleiben je Environment getrennt. GitHub nutzt environment-spezifische Secrets/Variablen und eine gemeinsame Concurrency-Gruppe für sämtliche Operationen auf demselben Environment. Lokale CLI-Aufrufe sperren `.runtime/ENV/operation.lock`; der Server sperrt Backup/Restore/Compose-Maintenance zusätzlich mit flock.

Sperren zwischen verschiedenen lokalen Checkouts sowie zwischen lokalen Ansible-Konfigurationsänderungen und GitHub-Jobs sind nicht global verteilt. HCP sperrt ausschließlich Terraform-State-Operationen. Für Betrieb nur einen autorisierten Deployment-Controller verwenden und keine Konfigurationsänderungen parallel ausführen. Ein nach Prozessabbruch verbliebenes lokales Lock-Verzeichnis erst nach Prüfung des Prozesses entfernen.

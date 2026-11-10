# Adaptervertrag

Ein Compute-Adapter empfängt name, environment, region, server_type, image, ssh_public_key, ssh_cidrs und web_cidrs. Output `host` enthält `id`, `ipv4`, `name`, `environment`. `scripts/inventory.py` prüft Name und Environment, bevor Ansible einen Host erhält. Der initiale Adapter enthält VM, Schlüssel und Firewall gemeinsam: für einen Einzelhost sind zusätzliche leere Netzwerkmodule unnötig.

Der DNS-/Edge-Adapter empfängt Zone, Hostname, Origin-IP, Proxy-Modus und bewusst aktivierte Einstellungen. Ein Object-Storage-Adapter liefert einen bestehenden oder angelegten Bucket; Backup-Endpoint und Region sind eigenständige Konfiguration. Der AWS-Terraform-Provider wird ausschließlich als S3-API-Client für Hetzner verwendet; es entsteht keine AWS-Infrastruktur.

Root-Module wählen konkrete Provider. Die CLI erwartet nur Environment-Root, Terraform-Plan und den Outputvertrag. Keine dynamischen Provider-Wechsel innerhalb eines bestehenden States; beim Cloud-Wechsel eigene Migration/State-Planung durchführen. HCP ist das Backend und bleibt von diesen Adaptern unabhängig.

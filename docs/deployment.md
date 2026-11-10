# Deployment und CI

`deploy` führt plan → bestätigtes apply → configure → status aus. `configure` betreibt Host/Docker/Anwendung; `deploy --app-only` führt nur die application-Rolle aus und prüft den Status. `provision` plant und wendet Infrastruktur an. `plan` initialisiert/validiert und speichert Plan, lesbare Darstellung und Prüfsumme. `apply` verwendet genau den gespeicherten Plan; Konfigurations-/Terraform-/Planänderungen werden über eine lokale Prüfsumme erkannt. HCP-State-Serial verhindert veraltete Pläne. Die Prüfsumme ist Integritätskontrolle, keine Signatur gegen einen kompromittierten Runner.

Lokale Applies erfordern `SLUG-ENV:apply`, per Terminal oder --confirm. Restore und Destroy benötigen eigene Tokens. Produktionspläne mit delete/replacement werden blockiert. Ein Serverwechsel ist eine separat geplante Migration mit Backup/DR, kein implizites Update.

GitHub Environment Variables:

- PROJECT_CONFIG: Inhalt der projektspezifischen JSON-Konfiguration.
- ENVIRONMENT_CONFIG: vollständiger Environment-Override als JSON.
- BOOTSTRAP_SSH_USER: root nur für den ersten, bereits verifizierten Host; danach deploy.

Environment Secrets stehen in [security.md](security.md). SSH_KNOWN_HOSTS enthält vorab geprüfte Hostschlüssel. SSH_PRIVATE_KEY wird nur im kurzlebigen Runner mit Modus 0600 geschrieben. Für einen neuen Host deshalb zunächst terraform-apply, Konsole/Hostschlüssel prüfen und dann deploy. Keine ungesicherte automatische Hostkey-Annahme.

Alle mutationsfähigen Workflows sind workflow_dispatch und nur vom Default-Branch ausführbar. Plan und Apply sind getrennte Jobs mit demselben GitHub-Environment; vor Freigabe des zweiten Jobs den Plan des ersten prüfen. Der Apply-Job lädt nur das Artefakt desselben Workflow-Runs, mit 1 Tag Retention. Bei Ablauf, Konfigurationswechsel oder State-Änderung neu planen. Keine PR-Artefakte übernehmen. PRs erhalten keine Environment-Secrets und führen ausschließlich validate.yml aus. Concurrency ist über alle Operationen je Environment identisch, cancel-in-progress=false.

Für prd erforderliche Reviewer sowie geschützten Default-Branch konfigurieren. Die CI-Vorbereitung prüft, dass Reviewer existieren; sie erfindet keine Reviewer-Identitäten. Ist dieses Feature im verwendeten Tarif nicht verfügbar, sind mutationsfähige prd-Workflows absichtlich blockiert. Dann geschützt lokal betreiben oder geeigneten Tarif/externen Freigabeprozess einführen. Dev/Stg-Reviewer werden ebenfalls empfohlen.

Runner müssen von den SSH-CIDRs zugelassen sein. Bevorzugt ein dedizierter geschützter Runner mit festem Egress; Standard-GitHub-Runner-IP-Bereiche nicht pauschal freigeben. Firewall-Änderungen nicht für jeden Job auf 0.0.0.0/0 erweitern.

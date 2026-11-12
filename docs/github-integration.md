# GitHub Environments und Preflight

```bash
./ops.sh github environments list
./ops.sh github doctor --env dev
./ops.sh github secrets check --env dev
./ops.sh github vars check --env dev
./ops.sh github sync --env dev --dry-run
```

gh muss angemeldet sein und das Zielrepository erreichen. Die nichtgeheime github_repository-Konfiguration bestimmt das Ziel; nicht der zufällige aktuelle gh-Kontext. Environments werden weiterhin durch ops.sh init/bootstrap.py angelegt; lesende GitHub-Managementbefehle erstellen keines stillschweigend.

Checks berücksichtigen Environment, Repository und Organisation mit dieser Priorität. Bei Organisationswerten werden private/selected-Repository-Sichtbarkeit und Repository-Zuordnung geprüft. Ein 403/401/404 kann ein verborgenes oder unzugängliches Objekt sein: die Ausgabe kennzeichnet unbekannte Berechtigungslage, statt einen fehlenden Secretwert zu behaupten. Secretstatus present-value-unverifiable bedeutet ausdrücklich nur, dass der Name sichtbar ist. Ein fehlender Name wird nur dann als missing bezeichnet, wenn alle relevanten Scopes lesbar waren.

PROJECT_CONFIG und ENVIRONMENT_CONFIG enthalten ausschließlich erlaubte JSON-Konfiguration. Sync erzeugt ENVIRONMENT_CONFIG aus den effektiven nichtgeheimen Werten einschließlich expliziter dotenv-Overrides. Provider-/Anwendungs-/Grafana-Secrets werden separat gemappt. GITHUB_REPOSITORY ist ein Laufzeitkontext, kein zu synchronisierender GitHub-Variablenname. Änderungen in prd brauchen das spezielle Sync-Bestätigungstoken. Der Variablenkatalog ist maßgeblich; ein Workflow-Audit erkennt neue secrets.NAME-/vars.NAME-Referenzen ohne Registereintrag.

Die Composite Action installiert gepinnte Python-/Terraform-Werkzeuge, bereitet JSON/SSH vor und führt Shared Preflight für die angeforderte Operation aus. CI ist unabhängig von lokalen .env-Dateien. Preflight prüft Schema, Auswahl, Versionen und lesende Hetzner-/Cloudflare-/HCP-/S3-Zugriffe vor Mutationen. Write-, State-Lock- und einzelne Produktberechtigungen sind nur teilweise über Read-APIs beweisbar; diese Grenze wird ausgegeben. Ein fehlender HCP-Workspace kann beim Doctor eine Init-Warnung sein, vor dem Plan ist er ein Fehler.

GitHub-Jobtokens dürfen häufig Secret-Metadaten nicht listen. CI prüft deshalb tatsächliche bereitgestellte Werte mit demselben Schema statt mit einem privilegierten Verwaltungs-PAT Secretlisten zu lesen. Lokale github check-Befehle bieten die zusätzliche Scope-Metadatenprüfung. Required Reviewers für prd, Default-Branch-Gates, Concurrency, gespeicherte Pläne und Restore-/Destroy-Barrieren bleiben erhalten. Kein Secretfile wird hochgeladen: Planartefakte bleiben auf die drei bisherigen nichtgeheimen Infrastrukturdateien beschränkt (Pläne trotzdem als vertraulich behandeln).

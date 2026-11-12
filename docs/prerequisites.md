# Lokale Voraussetzungen und Installation

Controller: macOS Intel/ARM64 sowie Debian/Ubuntu Intel/ARM64. Zielhost bleibt Ubuntu 24.04 amd64; zusätzliche Controllerarchitekturen ändern diesen Compute-Vertrag nicht. Zum Start mindestens Python 3.12 mit den Python-Abhängigkeiten aus requirements.lock.txt bereitstellen; für `doctor` ohne Environment genügt Python mit Standardbibliothek. Keine Paketmanager werden automatisch angelegt.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
./ops.sh doctor
./ops.sh prerequisites list --env dev
./ops.sh doctor --env dev --json
./ops.sh doctor --env dev --fix --interactive
```

config/tools.json definiert Versionen, Kategorien, Operationen und Installationsquellen. Terraform und Ansible werden nur für relevante Befehle geprüft, gh für GitHub/Bootstrap, SSH für Remote-Operationen. Docker/Compose ist nur für lokale Compose-Validierung nötig. Hetzner-, AWS-, Azure-, GCP- und DigitalOcean-CLIs sind registriert, aber für die implementierten Terraform-API-Abläufe optional. jq/yq sind nicht erforderlich: JSON/YAML werden durch Python/Ansible verarbeitet. Alternative Cloudadapter bleiben wie bisher unimplementiert.

Nichtinteraktiv ist eine ausdrückliche Installationsrichtlinie erforderlich:

```bash
./ops.sh prerequisites install --env dev --non-interactive --allow-install
```

Alternativ config/install-policy.json mit allow_tools pflegen. Ein apt-Systemeingriff benötigt zusätzlich --allow-system oder allow_system=true in dieser Datei. Ohne diese Freigabe wird sudo nicht aufgerufen. Mit Freigabe ausschließlich sudo -n (oder direkte Ausführung als root), niemals eine unkontrollierte Passwortabfrage. Homebrew wird nur verwendet, wenn vorhanden; andernfalls erklärt die CLI den manuellen Schritt. Fehlende oder zu alte Distributionspakete werden nach Installation erkannt, nicht als Erfolg ausgegeben. Funktionierende Werkzeuge werden nicht neu installiert; bereits vorhandene, inkompatible Versionen werden nicht automatisch aktualisiert.

Terraform wird auf die in tools.json gepinnte Version aus releases.hashicorp.com installiert, SHA256 gegen den separat geladenen Hersteller-Manifest geprüft und nur nach Erfolg unter .runtime/tools/bin abgelegt. Dies prüft Downloadintegrität über HTTPS, keine unabhängige GPG-Vertrauenskette. Ansible nutzt ausschließlich eine aktivierte Python-Virtualenv und die Lockdatei. Sonstige geeignete Pakete stammen aus bestehenden signierten Distributionsquellen oder Homebrew. CLI-Neuaufrufe ergänzen .runtime/tools/bin automatisch zum PATH.

Exitcodes: 0 erfolgreich, 2 fehlende/inkompatible Tools oder verweigerte Installation, 3 ungültige Konfiguration, 4 Authentifizierung/Berechtigung/Provider-Erreichbarkeit. Doctor aggregiert Befunde als Text oder JSON. --dry-run verhindert Installation und Provideraufrufe; es validiert weiterhin lokale Konfiguration. Initialisierte Beispieldateien sind keine funktionierenden Credentials.

Für die vollständige Offline-Prüfsuite zusätzlich den gepinnten Alloy-Validator installieren:

```bash
./ops.sh prerequisites install --operation alloy-validation --allow-install --non-interactive
export PATH="$PWD/.runtime/tools/bin:$PATH"
./scripts/validate.sh
```

Alloy-Binaries werden aus offiziellen Grafana-GitHub-Releases mit SHA256-Manifest geprüft. Die Prüfsuite verwendet einen lokalen Loopback-Port und synthetische Logfixtures; kein Grafana-Cloud-Account ist dafür nötig. Alternativ ALLOY_BIN auf einen kompatiblen bereits installierten Validator setzen. Die Ansible-Zielversion wird standardmäßig aus derselben Registry abgeleitet.

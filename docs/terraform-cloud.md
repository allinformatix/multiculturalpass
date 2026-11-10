# HCP Terraform

Organisation: bestehender Mandant mit Abrechnung, Benutzern und Teams. Projekt: Berechtigungs-/Ressourcengruppe innerhalb der Organisation. Workspace: eigene State-Versionen, Locks und Ausführungskonfiguration. Das Template erzeugt für dev/stg/prd standardmäßig jeweils Projekt UND Workspace; die Organisation wird nicht angelegt.

`scripts/bootstrap.py` verwendet die HCP-API und benötigt keinen Backend-State. Die Workspace-Erstellung wählt execution-mode=local und auto-apply=false. Terraform CLI/GitHub führen Provideroperationen aus; das Remote-Backend speichert State und unterstützt Locking. Keine Provider-Secrets in HCP nötig. GitHub-Workflows erzeugen gespeicherte Pläne und wenden sie nach dem Review an. State und Plan sind schützenswerte Daten; HCP-Zugriff minimieren und Backups/State-Versionierung der Organisation verwalten.

Für Projektanlage benötigt der Bootstrap-Benutzer Owners oder Manage projects; siehe [Projects API](https://developer.hashicorp.com/terraform/cloud-docs/api-docs/projects). Zusätzlich Workspaces erstellen und Projektzuordnung verwalten. Für laufenden Betrieb Token nur mit Zugriff auf den jeweiligen Workspace/State und erforderlichem Lock-/Write-Zugriff verwenden. Ein Organisations-Token für die ganze Deploymentkette ist unnötig breit. TF_TOKEN_app_terraform_io wird als Prozessvariable bzw. TF_API_TOKEN als GitHub-Secret geliefert.

Tarifabhängige Projekt-/Teamrechte und GitHub-Environment-Reviewer vorab prüfen. Ist Projektanlage nicht erlaubt, legt ein Administrator die Projekte und lokalen Workspaces vorher an; hcp_project/hcp_workspace passend konfigurieren. Es gibt keine stille Ausweichlösung in ein gemeinsames Projekt. Ein bestehender Workspace mit abweichender Projektzuordnung oder Remote-Ausführungsmodus wird abgelehnt. Nicht automatisch einen VCS-Run zusätzlich zur lokalen CLI aktivieren.

`terraform/environments/ENV/versions.tf` enthält ein partielles Remote-Backend. `ops.sh` generiert `.runtime/ENV/backend.hcl`. Den Backend-Container nicht in denselben State aufnehmen, den er speichern soll. Init ändert keine Cloudserver und führt keinen Apply aus.

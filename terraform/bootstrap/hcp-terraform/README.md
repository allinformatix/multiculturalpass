# HCP Bootstrap

`./ops.sh init --env dev` führt `scripts/bootstrap.py` aus. Die bestehende HCP-Organisation enthält ein Projekt und einen Workspace je Environment. Die API-Erstellung braucht keinen Terraform-State und vermeidet Backend-Zyklen. Es wird weder ein Cloudserver erstellt noch ein Apply ausgeführt. Workspace-Ausführung: local; Remote-Backend: HCP (State und Locking). Bestehende Workspaces mit abweichendem Projekt/Ausführungsmodus werden abgelehnt.

Für vordefinierte Projekte `hcp_project`/`hcp_workspace` im Environment setzen. Keine automatische Ausweichlösung auf ein unerwartetes Projekt bei fehlenden Rechten.

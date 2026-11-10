# Disaster Recovery und Abnahme

RPO: bei erfolgreichem täglichem Timer bis zu etwa 24 Stunden plus Jitter/Fehlerbehebungszeit. RTO hängt von VM-Bereitstellung, Datenmenge, Download und DB-Restore ab und wurde nicht gemessen. Keine Hochverfügbarkeit. Ein Restore-Drill vor Produktivnahme und anschließend regelmäßig ist verpflichtender Betreiberprozess.

Außerhalb der VM verwahren: Repository-Revision mit Image-Digests, Projekt-/Environment-Konfiguration, HCP-Zugang/State, SSH-Zugang, Backup-Bucket/Endpoint, S3-Zugang und RESTIC_PASSWORD. Ein allein im verschlüsselten Repository gespeichertes Restic-Passwort hilft im Notfall nicht.

## Wiederherstellung auf neue VM

1. Schadensbild feststellen und alte Instanz gegen Schreibzugriffe isolieren; Snapshot-ID und letzten erfolgreichen Sicherungsstand bestimmen. Keine zweite aktive Instanz mit derselben Identität starten.
2. Passende Repository-Revision und dieselben Images/Metadaten verwenden. Terraform-State aus HCP lesen. Bei verlorener VM den notwendigen Ersatzplan separat prüfen; der Produktions-Guard blockiert destruktiven automatischen Ersatz. Nicht den State blind löschen. Gezielten genehmigten Reparaturplan nach Backup-Erhalt durchführen; für produktive Replacement-Pläne ist eine dokumentierte manuelle Terraform-Migration erforderlich.
3. Neue VM mit demselben Environment-Namen, bestehenden Backup-Bucket und State bereitstellen. Der geschützte Bucket wird wiederverwendet, nicht neu initialisiert. DNS vor dem Umschalten kontrollieren. Für einen isolierten Drill eine abgeschirmte Test-VM mit derselben Backup-Identität, ohne öffentliche produktive DNS-Änderung und ohne ausgehende E-Mail verwenden; nicht zwei Terraform-States dieselben Ressourcen verwalten lassen.
4. Hostschlüssel neu über Konsole prüfen, known_hosts gezielt aktualisieren. Mit BOOTSTRAP_SSH_USER=root konfigurieren; dabei wird eine leere Odoo-DB mit den passenden Images angelegt. Das vorhandene Restic-Repository NICHT mit backup-init erneut initialisieren.
5. `./ops.sh restore --env prd --snapshot FULL_ID --confirm SLUG-prd:restore`. Sicherheitsbackup der leeren Instanz bleibt ebenfalls obligatorisch. Restore prüft Versions-/Environment-Gleichheit. Kein Restore eines fremden Environments per stillem Override.
6. HTTPS, Anmeldung, DB-Inhalt, Attachments/Filestore, Addons, WebSocket-Bus und SMTP prüfen. Ausgehenden Mailversand in einer Testkopie deaktivieren. Erst nach erfolgreicher fachlicher Abnahme produktiven Traffic freigeben.
7. Neues Backup erstellen, vollständig prüfen und gemessene RPO/RTO sowie Snapshot-/Release-ID protokollieren. Alte Datei-/Restore-Stände nach fachlicher Abnahme gezielt entfernen.

## Reproduzierbarer Abnahmetest

In dev einen Datensatz mit eindeutigem Namen und Dateianhang anlegen, Nachricht/WebSocket testen und Backup erstellen. Datensatz/Anhang verändern. Snapshot restaurieren und bestätigen, dass beide den alten Stand haben. Danach denselben Snapshot auf einer frischen abgeschirmten VM wiederherstellen. Fehlerfälle absichtlich simulieren: falsche Snapshot-ID, fremdes Tag, fehlendes S3-Recht, voller Staging-Datenträger, fehlgeschlagenes Sicherheitsbackup und abgebrochener DB-Restore. Vor DROP darf kein schädlicher Schritt erfolgen; danach muss ein Fehler Odoo offline lassen. Ergebnisse dokumentieren, nicht aus Mock-Erfolgen ableiten.

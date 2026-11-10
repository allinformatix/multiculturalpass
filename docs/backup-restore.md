# Konsistente verschlüsselte Backups

Hetzner S3: konfigurierbarer HTTPS-Endpoint, Bucket SLUG-ENV-backups und Restic-Prefix SLUG-ENV. Terraform erzeugt einen privaten Bucket mit Versionierung, prevent_destroy und force_destroy=false. Kein Public-Read und keine ACL-Freigaben. S3-Zugänge, Restic-Passwort und Zertifikats-DNS-Token liegen nur in rootgeschützten Dateien. Backups enthalten Konfiguration/Secrets verschlüsselt; RESTIC_PASSWORD und Wiederherstellungscredentials müssen zusätzlich außerhalb der VM aufbewahrt werden.

Einmalig nach Deployment `backup-init` mit SLUG-ENV:init-backup ausführen. Ein Auth-/Netzwerkfehler initialisiert niemals automatisch ein neues Repository. Der systemd-Timer läuft täglich 02:30 UTC plus bis zu 10 Minuten Jitter. Der Host verwendet UTC unabhängig von der Zeitzone des Bedieners.

Ablauf unter exklusiver Wartungssperre:

1. Repository-Zugriff prüfen, vorhandenes fehlgeschlagenes Staging ablehnen.
2. Odoo mit Timeout 120 Sekunden stoppen; PostgreSQL läuft weiter. Nur Odoo darf Datenbank/Filestore beschreiben.
3. pg_dump im Custom-Format erstellen und pg_restore --list prüfen; Filestore, Konfiguration, Versionen, Secrets und Addons kopieren.
4. Odoo wieder starten; Prüfsummen erzeugen und den kompletten Stand als EINEN Restic-Snapshot verschlüsselt hochladen.
5. Restic-Prüfung mit 5 Prozent Datenprobe, Snapshot-Retention täglich 7 / wöchentlich 4 / monatlich 6; Erfolg erst danach markieren.

Stop-/Dump-/Kopierfehler liefern Fehlercode; sofern der Backup-Prozess Odoo gestoppt hat, versucht der EXIT-Handler die Wiederaufnahme. Eine fehlgeschlagene Wiederaufnahme bleibt ein Fehler. Nach fehlgeschlagenem Backup Staging und Disk/Logs prüfen, erst danach den alten Stagingstand manuell entfernen. Nach SIGKILL/Hostausfall Odoo-Status manuell prüfen. Das Wartungsfenster skaliert mit DB-Dump plus Dateikopie, nicht mit Uploadzeit. Für kürzere Fenster später dateisystembasierte Snapshots mit sauberem Quiesce implementieren.

Snapshot-Liste: `sudo /usr/local/sbin/odoo-backup snapshots`. Vollprüfung: `sudo /usr/local/sbin/odoo-backup verify`. Snapshot-ID vollständig mit 64 Hexzeichen verwenden. Restore lädt/prüft zuerst Snapshot-Tag, Prüfsummen, Metadaten und Dump, erstellt danach zwingend ein Sicherheitsbackup des aktuellen Zustands, stoppt Odoo und ersetzt DB/Filestore/Addons. Aktuelle Runtime-Konfiguration und aktuelle Secrets bleiben aktiv; passende Images und Schema müssen identisch sein. Alte Daten-/Addonverzeichnisse und Restore-Staging bleiben zur Prüfung erhalten. Bei Fehler nach DB-Löschung bleibt Odoo offline; Fehler nicht durch blindes Starten übergehen.

Restic forget entfernt Snapshot-Referenzen, aber führt absichtlich kein automatisches prune aus. Ungenutzte Packs und S3-Noncurrent-Versionen können länger bestehen bleiben. Damit sind die oben genannten Fristen Wiederherstellungspunkte, keine zugesicherten physischen Löschfristen. In einem genehmigten Wartungsfenster mit separatem Bucket-Owner-Credential Restic prune und eine abgestimmte Noncurrent-Version-Lifecycle-Policy planen. Keine Objektablaufregel auf aktuelle Restic-Daten legen. Kosten und Datenschutzfristen gesondert prüfen.

Versionierung ist kein unveränderbares WORM-Backup. Bucket-spezifische Hostkeys und getrennte Verwaltungszugänge sowie eine zweite externe Kopie schützen vor kompromittiertem Root. Object-Lock-Retention kann Restic-Lock-/Metadatenlöschung beeinträchtigen und ist hier nicht ungeprüft aktiviert. Provider- und S3-Versionierungsverhalten müssen im Cloud-Abnahmetest verifiziert werden.

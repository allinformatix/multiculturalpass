#!/usr/bin/env bash
backup() { remote /usr/local/sbin/odoo-backup backup; }
restore() {
  [[ "$SNAPSHOT" =~ ^[a-f0-9]{64}$ ]] || die '--snapshot must be a full 64-character Restic snapshot ID'
  confirm_action restore
  remote /usr/local/sbin/odoo-backup restore "$SNAPSHOT" "$NAME:restore"
}

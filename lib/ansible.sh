#!/usr/bin/env bash
prepare_inventory() {
  tf_init
  if [[ "$DRY_RUN" == false ]]; then
    terraform "-chdir=$TF_DIR" output -json > "$RUNTIME/outputs.json"
    python3 "$ROOT/scripts/inventory.py" "$ENVIRONMENT"
  fi
}
configure() {
  prepare_inventory
  run ansible-playbook -i "$RUNTIME/inventory.json" "$ROOT/ansible/site.yml" -e "@$RUNTIME/config.json" --tags "$1"
}
remote() {
  prepare_inventory
  if [[ "$DRY_RUN" == true ]]; then log 'Would execute the requested operation on the verified environment host'; return; fi
  local ip
  ip="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["host"]["value"]["ipv4"])' "$RUNTIME/outputs.json")"
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes "$(get_config ssh_user)@$ip" sudo -n "$@"
}
status() {
  remote docker compose --project-directory /opt/odoo ps
  run curl --fail --silent --show-error --retry 5 --retry-delay 5 "https://$(get_config hostname)/web/health"
}

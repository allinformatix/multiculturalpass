#!/usr/bin/env bash
get_config() { python3 "$ROOT/scripts/config.py" "$ENVIRONMENT" get "$1"; }
load_config() {
  need python3
  RUNTIME="$(python3 "$ROOT/scripts/config.py" "$ENVIRONMENT")"
  NAME="$(get_config name)"
  TF_DIR="$ROOT/terraform/environments/$ENVIRONMENT"
  export RUNTIME NAME TF_DIR
  export ANSIBLE_CONFIG="$ROOT/ansible/ansible.cfg"
}

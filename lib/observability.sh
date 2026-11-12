#!/usr/bin/env bash
observability() {
  [[ "$(get_config observability_enabled)" == true ]] || die 'observability is disabled'
  case "$1" in
    status) remote systemctl status alloy --no-pager;;
    validate) remote /usr/bin/alloy validate /etc/alloy/config.alloy;;
    logs) remote journalctl -u alloy --no-pager -n 100;;
    test)
      # Marker travels through the host journal and the actual collector pipeline.
      local nonce
      nonce="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
      remote logger -t odoo-ops "observability delivery test $nonce"
      run python3 "$ROOT/scripts/loki_test.py" "$ENVIRONMENT" "$nonce";;
    *) die 'use observability status|validate|test|logs';;
  esac
}

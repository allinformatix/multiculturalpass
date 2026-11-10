#!/usr/bin/env bash
initialize() {
  run python3 "$ROOT/scripts/bootstrap.py" "$ENVIRONMENT"
  tf_init
}

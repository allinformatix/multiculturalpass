#!/usr/bin/env bash
preflight() {
  python3 "$ROOT/scripts/platform_ops.py" preflight --env "$ENVIRONMENT" --operation "$1"
}

#!/usr/bin/env bash
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
log() { printf '{"level":"info","message":"%s"}\n' "$1" >&2; }
need() { command -v "$1" >/dev/null 2>&1 || die "required executable missing: $1"; }
run() {
  if [[ "$DRY_RUN" == true ]]; then
    printf '[dry-run]' >&2; printf ' %q' "$@" >&2; printf '\n' >&2
  else
    "$@"
  fi
}
confirm_action() {
  if [[ -z "$CONFIRM" && -t 0 ]]; then
    read -r -p "Type $NAME:$1 to continue: " CONFIRM
  fi
  [[ "$CONFIRM" == "$NAME:$1" ]] || die "requires --confirm $NAME:$1"
}
doctor() {
  local tool
  for tool in bash python3 terraform ansible-playbook ssh curl gh docker shellcheck yamllint ansible-lint; do need "$tool"; done
  run terraform version
  run ansible-playbook --version
  run docker compose version
  if [[ "$DRY_RUN" == false ]]; then
    python3 "$ROOT/scripts/doctor.py" "$ENVIRONMENT"
    gh auth status
  fi
}

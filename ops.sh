#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ROOT
export PATH="$ROOT/.runtime/tools/bin:$PATH"
ORIGINAL_ARGS=("$@")
# shellcheck source=lib/common.sh
source "$ROOT/lib/common.sh"
# shellcheck source=lib/config.sh
source "$ROOT/lib/config.sh"
# shellcheck source=lib/terraform.sh
source "$ROOT/lib/terraform.sh"
# shellcheck source=lib/ansible.sh
source "$ROOT/lib/ansible.sh"
# shellcheck source=lib/github.sh
source "$ROOT/lib/github.sh"
# shellcheck source=lib/backup.sh
source "$ROOT/lib/backup.sh"
# shellcheck source=lib/prerequisites.sh
source "$ROOT/lib/prerequisites.sh"
# shellcheck source=lib/observability.sh
source "$ROOT/lib/observability.sh"
case "${1:-}" in
  doctor|prerequisites|env|github) exec python3 "$ROOT/scripts/platform_ops.py" "$@";;
esac
trap 'printf "{\"level\":\"error\",\"line\":%s,\"message\":\"operation failed\"}\n" "$LINENO" >&2' ERR
usage() {
  cat <<'HELP'
Usage: ./ops.sh COMMAND --env dev|stg|prd [OPTIONS]
Commands: doctor prerequisites env github observability init plan apply provision configure deploy status logs backup backup-init restore update destroy
Management: doctor [--env ENV] [--fix --interactive|--non-interactive] [--json]
  prerequisites list|install --env ENV [--allow-install] [--allow-system]
  env init|validate|show|diff --env ENV [--env2 ENV] [--redact]
  github doctor|sync|secrets check|vars check|environments list [--env ENV]
  observability status|validate|test|logs --env ENV
Options: --dry-run --app-only --confirm PROJECT-ENV:ACTION
         --snapshot FULL_RESTIC_ID --allow-production-destroy
Deploy: provision + configure; --app-only deploys application to an existing host.
Update: backup + application configuration (Odoo 18/PostgreSQL 16 only).
Restore/destroy require an exact confirmation, including in CI.
HELP
}
OBS_ACTION=""
COMMAND="${1:---help}"
[[ $# -eq 0 ]] || shift
if [[ "$COMMAND" == observability ]]; then OBS_ACTION="${1:-status}"; [[ $# -eq 0 ]] || shift; fi
ENVIRONMENT='' DRY_RUN=false APP_ONLY=false CONFIRM='' SNAPSHOT='' ALLOW_PRODUCTION_DESTROY=false
while (($#)); do
  case "$1" in
    --env|--confirm|--snapshot)
      [[ $# -ge 2 && "$2" != --* ]] || die "missing value for $1"
      case "$1" in --env) ENVIRONMENT="$2";; --confirm) CONFIRM="$2";; --snapshot) SNAPSHOT="$2";; esac
      shift 2;;
    --dry-run) DRY_RUN=true; shift;;
    --app-only) APP_ONLY=true; shift;;
    --allow-production-destroy) ALLOW_PRODUCTION_DESTROY=true; shift;;
    --help|-h) usage; exit 0;;
    *) die "unknown argument: $1";;
  esac
done
case "$COMMAND" in --help|-h|help) usage; exit 0;; doctor|init|plan|apply|provision|configure|deploy|status|logs|backup|backup-init|restore|update|destroy|observability) ;; *) die "unknown command: $COMMAND";; esac
[[ "$ENVIRONMENT" =~ ^(dev|stg|prd)$ ]] || die '--env dev|stg|prd is required'
[[ "$APP_ONLY" == false || "$COMMAND" == deploy ]] || die '--app-only is valid only for deploy'
[[ "$ALLOW_PRODUCTION_DESTROY" == false || "$COMMAND" == destroy ]] || die 'production override applies only to destroy'
if [[ "${OPS_ENV_READY:-}" != 1 ]]; then
  exec python3 "$ROOT/scripts/env_exec.py" "$ENVIRONMENT" "${ORIGINAL_ARGS[@]}"
fi
load_config
if [[ "$DRY_RUN" == false ]]; then preflight "$COMMAND"; fi
LOCK_DIR="$RUNTIME/operation.lock"
mkdir "$LOCK_DIR" 2>/dev/null || die 'another local operation is active; inspect .runtime/ENV/operation.lock'
trap 'rmdir "$LOCK_DIR"' EXIT
case "$COMMAND" in
 observability) observability "$OBS_ACTION";;
 init) initialize;;
 plan) plan;;
 apply) apply;;
 provision) provision;;
 configure) configure all;;
 deploy) if [[ "$APP_ONLY" == false ]]; then provision; configure all; else configure app; fi; status;;
 status) status;;
 logs) remote docker compose --project-directory /opt/odoo logs --tail 100;;
 backup) backup;;
 backup-init) confirm_action init-backup; remote /usr/local/sbin/odoo-backup init "$NAME:init-backup";;
 restore) restore;;
 update) backup; configure app; status;;
 destroy) destroy;;
esac

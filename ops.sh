#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ROOT
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
trap 'printf "{\"level\":\"error\",\"line\":%s,\"message\":\"operation failed\"}\n" "$LINENO" >&2' ERR
usage() {
  cat <<'HELP'
Usage: ./ops.sh COMMAND --env dev|stg|prd [OPTIONS]
Commands: doctor init plan apply provision configure deploy status logs backup backup-init restore update destroy
Options: --dry-run --app-only --confirm PROJECT-ENV:ACTION
         --snapshot FULL_RESTIC_ID --allow-production-destroy
Deploy: provision + configure; --app-only deploys application to an existing host.
Update: backup + application configuration (Odoo 18/PostgreSQL 16 only).
Restore/destroy require an exact confirmation, including in CI.
HELP
}
COMMAND="${1:---help}"
[[ $# -eq 0 ]] || shift
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
case "$COMMAND" in --help|-h|help) usage; exit 0;; doctor|init|plan|apply|provision|configure|deploy|status|logs|backup|backup-init|restore|update|destroy) ;; *) die "unknown command: $COMMAND";; esac
[[ "$ENVIRONMENT" =~ ^(dev|stg|prd)$ ]] || die '--env dev|stg|prd is required'
[[ "$APP_ONLY" == false || "$COMMAND" == deploy ]] || die '--app-only is valid only for deploy'
[[ "$ALLOW_PRODUCTION_DESTROY" == false || "$COMMAND" == destroy ]] || die 'production override applies only to destroy'
load_config
LOCK_DIR="$RUNTIME/operation.lock"
mkdir "$LOCK_DIR" 2>/dev/null || die 'another local operation is active; inspect .runtime/ENV/operation.lock'
trap 'rmdir "$LOCK_DIR"' EXIT
case "$COMMAND" in
 doctor) doctor;;
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

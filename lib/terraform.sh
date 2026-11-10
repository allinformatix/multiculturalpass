#!/usr/bin/env bash
tf() { run terraform "-chdir=$TF_DIR" "$@"; }
tf_init() { tf init -input=false "-backend-config=$RUNTIME/backend.hcl"; }
plan() {
  tf_init
  tf validate
  tf plan -input=false -lock-timeout=5m "-var-file=$RUNTIME/terraform.tfvars.json" "-out=$RUNTIME/apply.tfplan"
  if [[ "$DRY_RUN" == false ]]; then
    terraform "-chdir=$TF_DIR" show -no-color "$RUNTIME/apply.tfplan" > "$RUNTIME/plan.txt"
    python3 "$ROOT/scripts/plan_manifest.py" "$ENVIRONMENT" write
    log 'Review .runtime/ENV/plan.txt; plans can contain sensitive infrastructure values.'
  fi
}
provision() {
  plan
  apply
}
apply() {
  confirm_action apply
  tf_init
  run python3 "$ROOT/scripts/plan_manifest.py" "$ENVIRONMENT" check
  run python3 "$ROOT/scripts/check_plan.py" "$ENVIRONMENT" "$RUNTIME/apply.tfplan" "$TF_DIR"
  tf apply -input=false "$RUNTIME/apply.tfplan"
}
destroy() {
  confirm_action destroy
  [[ "$ENVIRONMENT" != prd || "$ALLOW_PRODUCTION_DESTROY" == true ]] || die 'prd requires --allow-production-destroy'
  [[ "$(get_config manage_zone_settings)" == false && "$(get_config manage_cache_rules)" == false ]] || die 'transfer shared Cloudflare zone ownership before destroying this environment'
  backup
  if [[ "$ENVIRONMENT" == prd ]]; then
    prepare_inventory
    run python3 "$ROOT/scripts/unprotect.py" "$ENVIRONMENT" "$CONFIRM"
  fi
  tf_init
  # Deliberately retain the backup bucket and its protected state.
  tf plan -destroy -target=module.compute -target=module.dns -input=false -lock-timeout=5m "-var-file=$RUNTIME/terraform.tfvars.json" "-out=$RUNTIME/destroy.tfplan"
  tf apply -input=false "$RUNTIME/destroy.tfplan"
}

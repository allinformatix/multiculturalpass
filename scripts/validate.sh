#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
find lib scripts tests -name '*.sh' -print0 | xargs -0 -n 1 bash -n
bash -n ops.sh
shellcheck -x ops.sh lib/*.sh scripts/*.sh
python3 -m unittest discover -s tests -v
python3 scripts/scan_secrets.py
yamllint .github ansible .yamllint .ansible-lint
ANSIBLE_LOCAL_TEMP="$PWD/.runtime/ansible-tmp" ansible-lint ansible/site.yml
ANSIBLE_LOCAL_TEMP="$PWD/.runtime/ansible-tmp" ansible-playbook -i localhost, ansible/site.yml --syntax-check
python3 scripts/render_test.py
shellcheck .runtime/rendered/*.sh
terraform fmt -check -recursive terraform
for environment in dev stg prd; do
  terraform "-chdir=terraform/environments/$environment" init -backend=false -input=false -lockfile=readonly
  terraform "-chdir=terraform/environments/$environment" validate
done

terraform -chdir=terraform/environments/dev test

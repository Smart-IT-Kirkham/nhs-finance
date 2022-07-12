#!/usr/bin/env bash

# scp this file to the project folder on dev-docker1
# Change the MODULES_TO_UPGRADE variable as appropriate

# Deployment script for dev-docker1
declare -a DATABASES

COMMAND=`docker-compose exec odoo_postgresql psql -U odoo -d postgres -c "\pset pager" -c "\l"`

# This regex is slightly wonky as the group indexes don't line up correctly
pattern='^[[:space:]]*([a-zA-Z0-9_]*)[[:space:]]*\|[[:space:]]*([a-zA-Z0-9_]*)[[:space:]]*\|[[:space:]]*([a-zA-Z0-9_]*)[[:space:]]*\|[[:space:]]*([a-zA-Z0-9_]*)[[:space:]]*.*$'
while read -r line; do
  if [[ ${line} =~ $pattern ]]; then
    db="${BASH_REMATCH[1]}"
    collate="${BASH_REMATCH[4]}"
    if [[ "${collate}" == "C" ]]; then
      DATABASES+=(${db})
    fi
  fi
done <<<"$COMMAND"

MODULES_TO_UPGRADE=""

docker-compose pull odoo

# Odoo 13 seems to need to require down/up before recompiling py files
docker-compose down
docker-compose up -d

docker-compose stop odoo

for database in ${DATABASES[@]}
  do
    docker-compose run --rm odoo -d ${database} -u ${MODULES_TO_UPGRADE} --stop-after-init
  done

docker-compose up -d

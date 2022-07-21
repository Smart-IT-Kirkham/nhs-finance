#!/bin/bash

PROGNAME=$(basename $0)
AUTHOR="Paul Bargewell <paul,bargewell@opusvl.com>"
COPYRIGHT="Copyright 2021, Opus Vision Limited T/A OpusVL"
LICENSE="SPDX-License-Identifier: AGPL-3.0-or-later"
RELEASE="Revision 1.0.0"

# This carries out the initial setup of the odoo containerset using the .env
# parameters. It creates the odoo user, sets session folder permissions and
# Setups up postgres replication via the dbproxy.

set -e

if [ ! -f ".env" ]; then
    
    echo "You need to create a .env file by following the README.md"
    exit 1
    
fi

source .env

docker-compose build && \
chmod ugo+rx init-db.sh && \
docker-compose up -d db

docker-compose run --rm -u root odoo chown odoo: /etc/odoo /var/lib/odoo /mnt/extra-addons -Rv

docker-compose run --rm -u root nginx chown 33 /etc/ssl/nginx/ -Rv

# Don't start cron as it will create an uninitialised db
docker-compose stop db && docker-compose up -d odoo nginx

echo ""
echo "Now Odoo has started for the first time you can visit http://localhost "
echo "and create a database."
echo ""
echo "You will need to use the default Master Password 'changeme' unless you have "
echo "already editted the odoo.conf file."
echo ""
echo "Once the database is created, you should then bring up all docker containers "
echo "using:"
echo ""
echo "  docker-compose up -d"
echo ""
#!/usr/bin/env bash

# Builds GPIT Odoo docker image and pushes to Harbor
# Replace PROJECT_NAME with the name of the project on Harbor

GIT_TAG=$(git describe --tags)

docker build -t registry.deploy.opusvl.net/PROJECT_NAME/odoo:${GIT_TAG} -t registry.deploy.opusvl.net/PROJECT_NAME/odoo:dev-docker1 odoo
docker push registry.deploy.opusvl.net/PROJECT_NAME/odoo:${GIT_TAG}
docker push registry.deploy.opusvl.net/PROJECT_NAME/odoo:dev-docker1

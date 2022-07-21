FROM quay.io/opusvl/custom-odoo-13:20191113

LABEL maintainer="Paul Bargewell <paul.bargewell@opusvl.com>" \
    copyright="Copyright 2021, Opus Vision Limited T/A OpusVL" \
    SPDX-License-Identifier="AGPL-3.0-or-later"

USER root

RUN apt update -qq -y && \
    DEBIAN_FRONTEND=noninteractive apt install -y python3-netifaces

COPY --chown=odoo:odoo addon-bundles/* /mnt/addon-bundles/

USER odoo
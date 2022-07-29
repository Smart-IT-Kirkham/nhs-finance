# Odoo NHS-Finance Repository

This is the repository for **Odoo Open Source - NHS Finance Edition**.

Designed in collaboration with NHS stakeholders, **Odoo Open Source - NHS Finance Edition** is a fully-featured accounting system meeting the specific needs of NHS organisations.

The software provides an extensive feature set including:

- Real-time reporting and modeling
- Full drill-down capability for forensic analysis
- Integration with your existing systems, banking, and HMRC

For full details, please see <https://nhs.odoo.uk>.

## Prerequisites

This project requires:

- docker
- docker-compose

## Usage

**NOTE:** Clone this entire repository from github ensuring that you do so recursively as it includes submodules:

```shell
git clone --recursive https://github.com/OpusVL/nhs-finance.git
```

Create a `.env` file containing the two required variables as detailed below - change the passwords as necessary. You can leave out the optional variables:

```shell
# REQUIRED VARIABLES

POSTGRES_PASSWORD=SecretKey
ODOO_POSTGRES_PASSWORD=SecretKey

# OPTIONAL VARIABLES

LOG_LEVEL=INFO
ODOO_DATA_VOLUME=./data
ODOO_POSTGRES_USER=odoo
POSTGRESQL_IMAGE=postgres
POSTGRESQL_IMAGE_VERSION=12-alpine
POSTGRES_USER=postgres
WORKERS=4
```

Edit the `odoo.conf` file and change the `admin_passwd` to something more suitable. This is the Odoo "Master Password" used for database management, and will be needed later when you create an empty database.

### Initialise the Docker Containers

The first time you run the container set you should run the init script to ensure permissions are granted:

```shell
./init.sh
```

Once this has been run all future start ups can be made using:

```shell
docker-compose up -d
```

The container set includes an instance of Nginx that acts as a reverse proxy to access Odoo.

Access Odoo by visiting the URL [http://localhost](http://localhost) - this will redirect you to a https version that uses a self signed certificate - you need to accept the risk. You should change this before production usage.

The first part of setting up Odoo is to use the master password and create a database, specify an email address and a password for the initial "admin" user.

## Minimum Steps to Working System

```shell
git clone --recursive https://github.com/OpusVL/nhs-finance.git
cd nhs-finance
cp example/dotenv .env
./init.sh
```

### Cutomisation

Modify the environment variables in the `.env` file to customise the project behaviour.

| Variable | Value | Description |
|:---|:---|:---|
| LOG_LEVEL | INFO | Odoo log level (DEBUG,INFO,WARN) |
| ODOO_DATA_VOLUME | ./data | Location of Odoo and PosgreSQL data |
| ODOO_POSTGRES_USER | odoo | Postgres user account for Odoo |
| POSTGRESQL_IMAGE | postgres | Docker Image used for PostgreSQL |
| POSTGRESQL_IMAGE_VERSION | 12-alpine | Docker Tag used for PostgreSQL |
| POSTGRES_USER | postgres | Default PostgreSQL super user |
| WORKERS | 4 | Number of Odoo Worker Threads |

### Nginx

Nginx is only included here as a basis to run this project locally for testing. You can copy the `nginx/default.conf` and modify it to suit your production needs.

You should remove the `nginx:` section from `docker-compose.yml` prior to using in production.

## Support

This Open Source software is provided free of charge for you to explore and use without warranty (see the licence). If you find a problem or have a suggestion, please do raise a Github issue. Although we will try our best to respond as soon as we can, we can't promise.

## Services

For production use, service-level backed contracts and professional services are available on demand. OpusVL provide assistance, development, deployemnt and support of this software, please get in touch using the details below:

- Telephone: +44 (0)1788 298 450
- Email: hello@opusvl.com
- Web: [https://opusvl.com](https://opusvl.com)

Professional services are available to UK Public Sector through G-Cloud and other procurement frameworks.

## Copyright and License

Copyright &copy; 2022 Opus Vision Limited T/A OpusVL. All rights reserved.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.

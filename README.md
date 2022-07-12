# Odoo Project Template Repository

Use this repository to create a new project from. Once you have created your new project
change to the branch for the Odoo version you want to use and remove the other branches.

## First steps
From the project root

### Edit environment variables
1. Copy the 'dotenv' file from the examples folder to the project root
    ```cp examples/dotenv .env```
2. Edit the .env file with paths, ports and users appropriate for the new project

### Edit docker compose override
1. Copy the 'docker-compose.override.yml' file from the examples folder to the project root
    ```cp examples/docker-compose.override.yml .```
2. Edit the new docker-compose.override.yml file according to your needs 

### Start the containers
When Odoo starts for the first time the permissions need to be set on the odoo data folder
```docker-compose up -d && docker-compose exec -u root odoo chown -R odoo:odoo /var/lib/odoo```

## Module development
From the project root

### Add third party modules
Add git submodules for third party repositories (OCA, etc)
1. Change to the addon-bundles folder
    ```cd odoo/addon-bundles```
2. Add the git submodule
    ```git submodule add git@git://PATH_TO_REPOSITORY```
3. Change back to project root
    ```cd ../..```
4. Commit the change

### Create custom module
Create a custom module for the new project
1. Create a folder to contain all the custom modules for this project
    ```mkdir odoo/addon-bundles/PROJECT-NAME-modules```
2. Create custom Odoo module
   1. Manual creation
      1. Create folder for the custom module
      ```mkdir odoo/addon-bundles/PROJECT-NAME-modules/MODULE-NAME```
   2. Bootstrap new module (experimental)
      1. Create a new module using Odoo's scaffolding command
      ```docker-compose exec odoo odoo.py scaffold MODULE-NAME /mnt/extra-addons-bundles/PROJECT-NAME-modules/```
      
## Deployment
### Build
Steps to build a new docker image and push to Harbor
1. Checkout the primary branch
2. Make sure there are no uncommitted changes on the primary branch
3. git pull to make sure all origin changes are present
4. Edit 'build.sh', changing PROJECT_NAME as appropriate
5. Create a git tag
6. Run build.sh ```./build.sh```

### Dev-docker deployment
Update the image on dev-docker and upgrade databases
1. Edit quick-deploy.sh and change 'MODULES_TO_UPGRADE' variable to the list of modules you will regularly need to upgrade
2. Copy 'quick-deploy.sh' to dev-docker ```scp quick-deploy.sh dev-docker1:/srv/docker/PROJECT_NAME```
> Command above to be confirmed
3. ssh to dev-docker1
4. Change to project folder ```cd /srv/docker/PROJECT_NAME```
5. Run the quick-deploy script ```./quick-deploy.sh``` 

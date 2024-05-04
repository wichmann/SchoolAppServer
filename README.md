# SchoolAppServer

Configures and prepares Docker Compose scripts to setup a schools app server.
It provides Docker stacks containing the following services:

* Traefik
* Portainer
* Watchtower
* Nextcloud
* Moodle
* Kanboard
* Etherpad
* Hedgedoc
* StirlingPDF
* Homer
* Heimdall

## Usage

After cloning the repository you should generate all configuration and
passwords files:

    ./school_app_server.py --initial-setup

If all stack are configured properly you can start and stop them by executing
the script without parameters:

    ./school_app_server.py

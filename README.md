# SchoolAppServer

Configures and prepares Docker Compose scripts to setup a schools app server.
It provides Docker stacks containing the following services:

* Traefik
* Portainer
* Watchtower
* Uptime Kuma
* Nextcloud
* Moodle
* Kanboard
* Jenkins CI
* Gitea
* Etherpad
* Hedgedoc Markdown Editor
* draw.io
* WeKan - Open-Source Kanban
* OnlyOffice
* StirlingPDF
* Homer
* Heimdall

![Screenshot of SchoolAppServer](docs/images/screenshot_status.png)

## Installation

Before using the tool you have to install all necessary packages:

    sudo apt install docker.io docker-compose-v2 git pipenv

Clone this repository:

    git clone https://github.com/wichmann/SchoolAppServer.git

To prepare the Python environment start pipenv in the cloned directory to
install all Python libraries:

    pipenv install

## Usage

After cloning the repository you should generate all configuration and
passwords files by starting the program and entering the command 'setup':

    pipenv run ./school_app_server.py

If you use a non-root user, please use sudo to get root permissions:

    pipenv run sudo ./school_app_server.py

If all stack are configured properly you can start and stop them by executing
the commands 'start' and 'stop'.

You should start the app 'infrastructure' first, before starting any of the
other apps:

     ➭ start infrastrukture

## Demo

[![asciicast](https://asciinema.org/a/JVsbfUozhtUg2YFezK8FdjOw3.svg)](https://asciinema.org/a/JVsbfUozhtUg2YFezK8FdjOw3)

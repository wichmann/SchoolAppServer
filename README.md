[![Pylint](https://github.com/wichmann/SchoolAppServer/actions/workflows/pylint.yml/badge.svg)](https://github.com/wichmann/SchoolAppServer/actions/workflows/pylint.yml)

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

After cloning the repository you should provide the basic configuration common
to all app by entering the command 'setup':

    pipenv run ./school_app_server.py

     ➭ setup

If you use a non-root user, please use sudo to get root permissions:

    pipenv run sudo ./school_app_server.py

     ➭ setup

After that you can start and stop apps by executing the commands 'start' and
'stop'. When starting an app for the first time, you have to generate all
environment variables and secrets files. This will be done automatically.

You should start the app 'infrastructure' first, before starting any of the
other apps:

     ➭ start infrastructure

## Demo

[![asciicast](https://asciinema.org/a/bVfOutzX5c1VB1wGT3rvQ9MmC.svg)](https://asciinema.org/a/bVfOutzX5c1VB1wGT3rvQ9MmC)

## Requirements:

* Python 3.11 or above
* python-on-whales
* prompt-toolkit
* pyyaml
* bcrypt

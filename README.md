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

![Screenshot of SchoolAppServer](docs/images/screenshot_status.png)

## Demo

[![asciicast](https://asciinema.org/a/JVsbfUozhtUg2YFezK8FdjOw3.svg)](https://asciinema.org/a/JVsbfUozhtUg2YFezK8FdjOw3)

## Installation

Before using the tool you have to install all necessary packages:

    sudo apt install docker.io git pipenv

Clone this repository:

    git clone https://github.com/wichmann/SchoolAppServer.git

To prepare the Python environment start pipenv in the cloned directory to
install all Python libraries:

    pipenv install

## Usage

After cloning the repository you should generate all configuration and
passwords files by starting the program and entering the command 'setup':

    pipenv run sudo ./school_app_server.py

If all stack are configured properly you can start and stop them by executing
the commands 'start' and 'stop'.

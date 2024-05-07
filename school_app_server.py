#! /usr/bin/env python3

"""
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
"""

import re
import os
import sys
import string
import secrets
import fileinput
import logging
import logging.handlers
from pathlib import Path
from argparse import ArgumentParser

# save Python's print function, so it can be overwritten by the one from prompt_toolkit
python_print = print

import yaml
import bcrypt
from prompt_toolkit import PromptSession, prompt, HTML
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.validation import Validator
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import checkboxlist_dialog, yes_no_dialog
from prompt_toolkit.key_binding import KeyBindings
from python_on_whales.exceptions import DockerException
from python_on_whales import DockerClient


# create logger instance
logger = logging.getLogger('school_app_server')

APP = 'SchoolAppServer'
VERSION = '1.0'
INITIAL_SETUP_MARKER_FILE = '.initial_setup_complete'

INFRASTRUCTURE_ENV = """UPTIMEKUMA_IMAGE=louislam/uptime-kuma:1
UPTIMEKUMA_DOMAIN=status.{domain}
TRAEFIK_IMAGE=traefik:v2.11
TRAEFIK_DASHBOARD_DOMAIN=dashboard.{domain}
TRAEFIK_METRICS_DOMAIN=metrics.{domain}
PORTAINER_IMAGE=portainer/portainer-ce:latest
PORTAINER_DOMAIN=portainer.{domain}
WATCHTOWER_IMAGE=containrrr/watchtower:latest
"""

NEXTCLOUD_ENV = """NEXTCLOUD_IMAGE=nextcloud:27.1-apache
NEXTCLOUD_DOMAIN=nextcloud.{domain}
NEXTCLOUD_DB_IMAGE=mariadb:10.6
NEXTCLOUD_REDIS_IMAGE=redis:latest
NEXTCLOUD_SMTP_ADDR={nextcloud_smtp_addr}
NEXTCLOUD_SMTP_USER={nextcloud_smtp_user}
NEXTCLOUD_SMTP_PORT=465
"""

KANBOARD_ENV = """KANBOARD_IMAGE=kanboard/kanboard:v1.2.36
KANBOARD_DOMAIN=kanboard.{domain}
KANBOARD_SMTP_ADDR={kanboard_smtp_addr}
KANBOARD_SMTP_PORT=465
KANBOARD_SMTP_USER={kanboard_smtp_user}
"""

TOOLS_ENV = """STIRLINGPDF_IMAGE=frooodle/s-pdf:latest
STIRLINGPDF_DOMAIN=pdf.{domain}
"""

MOODLE_ENV = """MOODLE_IMAGE=bitnami/moodle:latest
MOODLE_DOMAIN1=moodle.{domain}
MOODLE_DOMAIN2=moodle2.{domain}
MOODLE_DB_IMAGE=mariadb:latest
MOODLE_SMTP_ADDR={moodle_smtp_addr}
MOODLE_SMTP_PORT=465
MOODLE_SMTP_USER={moodle_smtp_user}
MOODLE_ADMIN_EMAIL={moodle_admin_mail_address}
MOODLE_SITE_NAME={moodle_site_name}
"""

STATIC_ENV = """
HEIMDALL_IMAGE=linuxserver/heimdall:latest
HEIMDALL_DOMAIN=www.{domain}
HOMER_IMAGE=b4bz/homer:latest
HOMER_DOMAIN=homer.{domain}
DEFAULTPAGE_IMAGE=nginx:latest
DEFAULTPAGE_DOMAIN=static.{domain}
"""

ETHERPAD_ENV = """ETHERPAD_IMAGE=etherpad/etherpad:1.9
ETHERPAD_DOMAIN=pad.{domain}
ETHERPAD_DB_IMAGE=postgres:16-alpine
"""

HEDGEDOC_ENV = """HEDGEDOC_IMAGE=quay.io/hedgedoc/hedgedoc:latest
HEDGEDOC_DOMAIN=md.{domain}
HEDGEDOC_DB_IMAGE=postgres:16-alpine
"""

DRAWIO_ENV = """DRAWIO_IMAGE=jgraph/drawio:latest
DRAWIO_DOMAIN=draw.{domain}
"""

ONLYOFFICE_ENV = """ONLYOFFICE_IMAGE=onlyoffice/documentserver:latest
ONLYOFFICE_DOMAIN=onlyoffice.{domain}
"""

JENKINS_ENV = """JENKINS_IMAGE=jenkins/jenkins:lts-jdk17
JENKINS_DOMAIN=jenkins.{domain}
"""

GITEA_ENV = """GITEA_DB_IMAGE=postgres:16
GITEA_IMAGE=gitea/gitea:latest
GITEA_DOMAIN=git.{domain}
GITEA_SMTP_ADDR={gitea_smtp_addr}
GITEA_SMTP_PORT=465
GITEA_SMTP_USER={gitea_smtp_user}
"""

WEKAN_ENV = """WEKAN_DB_IMAGE=mongo:6
WEKAN_IMAGE=wekanteam/wekan:latest
WEKAN_DOMAIN=wekan.{domain}
WEKAN_SMTP_USER={wekan_smtp_user}
WEKAN_SMTP_ADDR={wekan_smtp_addr}
WEKAN_SMTP_PASSWORD={wekan_smtp_password}
WEKAN_SMTP_PORT=465
"""

app_name_map = {'infrastructure': 'Infrastructure Services', 'nextcloud': 'Nextcloud',
                'kanboard': 'Kanboard', 'tools': 'Tool Apps', 'moodle': 'Moodle', 'static': 'Static apps',
                'etherpad': 'Etherpad', 'hedgedoc': 'Hedgedoc Markdown Editor', 'drawio': 'draw.io',
                'onlyoffice': 'OnlyOffice', 'jenkins': 'Jenkins CI', 'gitea': 'Gitea',
                'wekan': 'WeKan - Open-Source Kanban'}

app_var_map = {'infrastructure': INFRASTRUCTURE_ENV, 'nextcloud': NEXTCLOUD_ENV, 'kanboard': KANBOARD_ENV,
               'tools': TOOLS_ENV, 'moodle': MOODLE_ENV, 'static': STATIC_ENV, 'etherpad': ETHERPAD_ENV,
               'hedgedoc': HEDGEDOC_ENV, 'drawio': DRAWIO_ENV, 'onlyoffice': ONLYOFFICE_ENV,
               'jenkins': JENKINS_ENV, 'gitea': GITEA_ENV, 'wekan': WEKAN_ENV}


def create_logger():
    """Creates and configures a logger for logging to file and stdout."""
    logger.setLevel(logging.DEBUG)
    log_to_file = logging.handlers.RotatingFileHandler(
        'SchoolAppServer.log', maxBytes=262144, backupCount=5)
    log_to_file.setLevel(logging.DEBUG)
    logger.addHandler(log_to_file)
    log_to_screen = logging.StreamHandler(sys.stdout)
    log_to_screen.setLevel(logging.WARN)
    logger.addHandler(log_to_screen)


def parse_arguments():
    """Parses command line arguments and return the given arguments."""
    parser = ArgumentParser(description='Administrative tool for SchoolAppServer.')
    parser.add_argument('-i', '--initial-setup', action='store_true',
                        help='set up all initial configuration and secret files')
    parser.add_argument('-v', '--version', action='version',
                        version=f'{APP} {VERSION}')
    args = parser.parse_args()
    return args


def prepare_cli_interface():
    """Sets up style, key bindings and autocompletion for command line interface."""
    bindings = KeyBindings()

    @bindings.add('c-x')
    def _(event):
        event.app.exit()
    style = Style.from_dict({
        '':       '#00ff00',
        'pound':  '#00ff00',
        'path':   'ansicyan',
        'bottom-toolbar': '#333333 bg:#ffcc00'
    })
    app_list = {k: None for k, v in app_name_map.items()}
    app_list.update({'all': None})
    completer = NestedCompleter.from_nested_dict({
        'start': app_list,
        'stop': app_list,
        'pull': app_list,
        'help': None,
        'setup': None,
        'status': None,
        'exit': None,
    })
    toolbar_text = '<b><style bg="ansired">Commands:</style></b>  -  '
    toolbar_text += 'start [app] - stop [app] - pull [app] - status - setup - help - exit - ctrl+c to quit'
    toolbar_text = HTML(toolbar_text)
    session = PromptSession(auto_suggest=AutoSuggestFromHistory(), style=style, completer=completer,
                            key_bindings=bindings, bottom_toolbar=toolbar_text, complete_while_typing=True)
    return session


def create_password(length=25):
    """
    Creates a secure password of a given length. The password should contain at
    least one lower case character, one upper case character and one digit.

    Source: https://docs.python.org/3/library/secrets.html#recipes-and-best-practices
    """
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
                any(c.isdigit() for c in password)):
            break
    return password


def find_all_secrets():
    """Iterates over the Docker Compose files of each stack and finds all secrets defined there."""
    all_secrets = []
    for path in Path('.').glob('*/docker-compose.yml'):
        data = yaml.safe_load(path.open())
        if 'secrets' in data:
            all_secrets.extend(
                [(str(path.parent), data['secrets'][s]['file']) for s in data['secrets']])
    return all_secrets


def generate_htpasswd_bcrypt(username, password):
    """
    Generates a htpasswd entry by calculating the bcrypt hash of a given
    password and append it to the username.

    Sources:
     - https://www.toor.su/posts/2019/06/htpasswd-with-bcrypt/
     - https://gist.github.com/zobayer1/d86a59e45ae86198a9efc6f3d8682b49
    """
    # generating on command line: printf "admin:$(openssl passwd -apr1 {chosen_password})\n" > traefik_dashboard_auth
    bcrypted = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    return f'{username}:{bcrypted}'


def create_secret_files():
    """
    Creates all files with secrets referenced in the Docker Compose files and
    fill them with long passwords.
    """
    smtp_password = prompt('Please enter the SMTP password: ', is_password=True)
    for app, filename in find_all_secrets():
        filepath = Path(app) / filename
        if 'dashboard_auth' in filename:
            chosen_password = create_password()
            print(f'Generated password for Traefik Dashboard (user "admin"): {chosen_password}')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(generate_htpasswd_bcrypt('admin', chosen_password))
                logger.debug('Writing HTTP auth string to file: %s', filename)
        elif 'smtp_password' in filename:
            # handle SMTP password files
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(smtp_password)
                logger.debug('Writing SMTP password to file: %s', filename)
        elif 'telegram' in filename:
            # handle telegram URL files
            with open(filepath, 'w', encoding='utf-8') as f:
                bot_id = prompt('Please enter the Telegram bot id: ')
                bot_id = '[bot_id]' if not bot_id else bot_id
                chat_id = prompt('Please enter the Telegram chat id: ')
                chat_id = '[chat_id]' if not chat_id else chat_id
                url = f'telegram://{bot_id}@telegram/?channels={chat_id}'
                f.write(url)
                logger.debug('Writing Telegram IDs to file: %s', filename)
        else:
            # handle all other files by just filling them with a long password
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(create_password())
                logger.debug('Writing password to secrets file: %s', filename)


def replace_string_in_file(filename, old_string, new_string):
    """Replaces a string in a given file (https://stackoverflow.com/a/20593644)"""
    with fileinput.FileInput(Path(filename), inplace=True, backup='.bak') as file:
        for line in file:
            python_print(line.replace(old_string, new_string), end='')


def replace_mail_address_in_files(mail_address):
    """Replaces a given mail address in all configuration files."""
    placeholder = 'mail@example.com'
    for path in Path('.').glob('*/*.yml'):
        if path.is_file():
            with open(path, 'r', encoding='utf-8') as file:
                if placeholder in file.read():
                    logger.debug('Found mail address to be replaced: %s', path)
                    replace_string_in_file(path, placeholder, mail_address)


def do_initial_setup():
    """Initializes all configuration and secret files."""
    print(' *** Initializing all configuration and secret files *** ')
    # input all information from user
    mail_validator = Validator.from_callable(
        # do a very simple check for validity (https://stackoverflow.com/a/8022584)
        lambda text: re.match(r'[^@]+@[^@]+\.[^@]+', text),
        error_message="Not a valid e-mail address!",
        move_cursor_to_end=True,
    )
    domain_validator = Validator.from_callable(
        lambda text: re.match(r'\w+\.\w+', text),
        error_message="Not a valid domain name!",
        move_cursor_to_end=True,
    )
    mail_address = prompt('Please enter your mail address: ', validator=mail_validator)
    domain_prompt = 'Please enter your domain name (third-level domain will be added, e.g. nicedomain.com): '
    domain_name = prompt(domain_prompt, validator=domain_validator)
    create_secret_files()
    replace_mail_address_in_files(mail_address)
    # handle environment variable files
    for app, env_vars in app_var_map.items():
        parameters = {'domain': domain_name}
        # get all placeholders from string  (https://stackoverflow.com/a/14061832)
        parameter_names = [name for text, name, spec, conv in string.Formatter().parse(
            env_vars) if name is not None]
        # filter missing parameters and input them from user
        parameter_names = set(parameter_names)
        parameter_names.remove('domain')
        for p in parameter_names:
            parameters[p] = prompt(f'Please enter parameter "{p}": ')
        filename = Path(app, '.env')
        logger.debug('Writing env vars to file: %s', filename)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(env_vars.format(**parameters))
    # set correct file permissions for acme.json
    os.chmod(Path('infrastructure') / 'acme.json', 0o600)
    Path(INITIAL_SETUP_MARKER_FILE).touch()


def output_status(docker_clients):
    """Outputs status information about all stacks and their respective containers."""
    print(' *** Stacks and Container *** \n')
    for app, docker in docker_clients.items():
        container = docker.compose.ps(all=True)
        mark = '✔️' if container else '❌'
        print(f' {mark} {app_name_map[app]} {"⣿" * len(container)}')
        for c in container:
            print(f'    - {c.name}')


def start_app(docker_clients, app):
    """Starts all containers of a specific Docker stack."""
    print(f' *** Starting app {app} *** \n')
    try:
        docker_client = docker_clients[app]
        docker_client.compose.up(services=None, build=False, detach=True, pull='missing')
    except DockerException:
        print('Could not start app. Maybe you have not started the app "infrastructure" first?')


def stop_app(docker_clients, app):
    """Stops all containers of a specific Docker stack."""
    print(f' *** Stopping app {app} *** \n')
    docker_client = docker_clients[app]
    docker_client.compose.down()


def pull_app(docker_clients, app):
    """Pulls all containers of a specific Docker stack."""
    print(f' *** Pulling app {app} *** \n')
    docker_client = docker_clients[app]
    docker_client.compose.pull()


def check_if_initial_setup_completed():
    """Checks whether initial setup has been executed."""
    if Path(INITIAL_SETUP_MARKER_FILE).is_file():
        return True
    return False


def main():
    """Starts command line interface and waits for commands."""
    # check for commandline arguments
    args = parse_arguments()
    if args.initial_setup:
        logger.info('Initializing all configuration and secret files...')
        do_initial_setup()
    # begin commandline session
    session = prepare_cli_interface()
    prompt_message = [('class:pound', '\n ➭ ')]
    # prepare instances of Docker client
    # (Python-on-Whales: https://gabrieldemarmiesse.github.io/python-on-whales/sub-commands/compose/)
    docker_clients = {}
    for app, _ in app_var_map.items():
        docker = DockerClient(compose_files=[Path(app) / 'docker-compose.yml'], compose_env_file=Path(app) / '.env')
        docker_clients[app] = docker
    print(f'{APP} {VERSION}')
    while True:
        try:
            user_input = session.prompt(prompt_message)
            if not user_input:
                continue
            user_input = user_input.split()
            command, args = user_input[0], user_input[1:]
        except KeyboardInterrupt:
            return
        if command in ('exit', 'quit'):
            return
        if command != 'setup' and not check_if_initial_setup_completed():
            print('Please start initial setup first by entering the command "setup"!')
            continue
        if command == 'status':
            output_status(docker_clients)
        elif command == 'start':
            if args:
                if args[0] in app_name_map:
                    start_app(docker_clients, args[0])
                elif args[0] == 'all':
                    for app in app_name_map:
                        start_app(docker_clients, app)
                else:
                    print(HTML('<red>Given app not available!</red>'))
            else:
                results_array = checkboxlist_dialog(
                    title="Start apps", text="Which apps should be started?",
                    values=list(app_name_map.items())
                ).run()
                for app in results_array:
                    start_app(docker_clients, app)
        elif command == 'stop':
            if args:
                if args[0] in app_name_map:
                    stop_app(docker_clients, args[0])
                elif args[0] == 'all':
                    for app in app_name_map:
                        stop_app(docker_clients, app)
                else:
                    print(HTML('<red>Given app not available!</red>'))
            else:
                results_array = checkboxlist_dialog(
                    title="Stop apps", text="Which apps should be stopped?",
                    values=list(app_name_map.items())
                ).run()
                for app in results_array:
                    stop_app(docker_clients, app)
        elif command == 'pull':
            if args:
                if args[0] in app_name_map:
                    pull_app(docker_clients, args[0])
                elif args[0] == 'all':
                    for app in app_name_map:
                        pull_app(docker_clients, app)
                else:
                    print(HTML('<red>Given app not available!</red>'))
            else:
                results_array = checkboxlist_dialog(
                    title="Pull apps", text="Which apps should be pulled?",
                    values=list(app_name_map.items())
                ).run()
                for app in results_array:
                    pull_app(docker_clients, app)
        elif command == 'setup':
            if check_if_initial_setup_completed():
                text = 'The initial setup has already been executed. Do you want to run it again?'
                run_again = yes_no_dialog(
                    title='Run initial setup again?', text=text).run()
                if run_again:
                    do_initial_setup()
            else:
                do_initial_setup()
        elif command == 'help':
            print(HTML(f'<skyblue>{APP}</skyblue> <violet>{VERSION}</violet>'))
            print(HTML('<orange>start [app]</orange> - Start one or all Docker Compose stack.'))
            print(HTML('<orange>stop [app]</orange>  - Stop one or all Docker Compose stack.'))
            print(HTML('<orange>pull [app]</orange>  - Stop one or all Docker Compose stack.'))
            print(HTML('<orange>status</orange>      - Show status of all Docker Compose stacks.'))
            print(HTML('<orange>setup</orange>       - Execute initial set up of configuration files.'))
            print(HTML('<orange>help</orange>        - Show this list of commands.'))
            print(HTML('<orange>exit</orange>        - Exit the programm.'))
        else:
            print(HTML('<red>Invalid command!</red>'))


if __name__ == '__main__':
    create_logger()
    main()

#! /usr/bin/env python3

"""
Configures and prepares Docker Compose scripts to setup a schools app server.
For a list of provided services, see README file.
"""

import re
import os
import sys
import string
import secrets
try:
    import tomllib
except ModuleNotFoundError:
    # fall back if Python version does not include tomllib
    import tomli as tomllib
import fileinput
import logging
import logging.handlers
from pathlib import Path
from argparse import ArgumentParser

# save Python's print function, so it can be overwritten by the one from prompt_toolkit
python_print = print

import yaml
import bcrypt
from argon2 import PasswordHasher
from python_on_whales import DockerClient
from python_on_whales.exceptions import DockerException
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import checkboxlist_dialog, yes_no_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.validation import Validator
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit import PromptSession, prompt, HTML


# create logger instance
logger = logging.getLogger('school_app_server')

APP = 'SchoolAppServer'
VERSION = '2.0'
INITIAL_SETUP_MARKER_FILE = '.initialized'
ENV_FILE_TEMPLATE_FILENAME = '.env.template'
EXAMPLE_MAIL_PLACEHOLDER = 'mail@example.com'

SUBDOMAIN_MAP = {
    'UPTIMEKUMA_DOMAIN': 'status',
    'TRAEFIK_DASHBOARD_DOMAIN': 'dashboard',
    'TRAEFIK_METRICS_DOMAIN': 'metrics',
    'PORTAINER_DOMAIN': 'portainer',
    'NEXTCLOUD_DOMAIN': 'nextcloud',
    'KANBOARD_DOMAIN': 'kanboard',
    'STIRLINGPDF_DOMAIN': 'pdf',
    'MOODLE_DOMAIN': 'moodle',
    'HEIMDALL_DOMAIN': 'www',
    'HOMER_DOMAIN': 'homer',
    'DEFAULTPAGE_DOMAIN': 'static',
    'ETHERPAD_DOMAIN': 'pad',
    'HEDGEDOC_DOMAIN': 'md',
    'DRAWIO_DOMAIN': 'draw',
    'ONLYOFFICE_DOMAIN': 'onlyoffice',
    'JENKINS_DOMAIN': 'jenkins',
    'GITEA_DOMAIN': 'git',
    'WEKAN_DOMAIN': 'wekan',
    'OPENCART_DOMAIN': 'opencart',
    'PHPMYADMIN_DOMAIN': 'phpmyadmin',
    'JUPYTER_DOMAIN': 'jupyter',
    'COLLABORA_DOMAIN': 'collabora',
    'COLLABORA_NEXTCLOUD_DOMAIN': 'nextcloud',
    'MATTERMOST_DOMAIN': 'mm',
    'NODE_RED_DOMAIN': 'nodered',
    'VAULTWARDEN_DOMAIN': 'vaultwarden',
    'TEAMMAPPER_DOMAIN': 'teammapper',
    'GRAFANA_DOMAIN': 'grafana',
    'INFLUX_DOMAIN': 'influx',
    'CHRONOGRAF_DOMAIN': 'chronograf',
    'PROMETHEUS_DOMAIN': 'prometheus',
    'LOKI_DOMAIN': 'loki',
    'ALLOY_DOMAIN': 'alloy',
    'AUTHENTIK_DOMAIN': 'auth',
    'KIWIX_DOMAIN': 'kiwix',
    'HESK_DOMAIN': 'hesk'
}

app_name_map = {'infrastructure': 'Infrastructure Services (Traefik, Portainer, Uptime Kuma, Watchtower)',
                'identity-provider': 'Authentik - An open-source identity provider and user management',
                'grafana': 'Grafana - Create, explore, and share data through beautiful, flexible dashboards',
                'nextcloud': 'Nextcloud - Self hosted open source cloud file storage',
                'kanboard': 'Kanboard - Free and open source Kanban project management software',
                'moodle': 'Moodle - Open Source Learning Management System',
                'etherpad': 'Etherpad - Real-time collaborative editor for the web',
                'hedgedoc': 'HedgeDoc - An open-source, web-based, self-hosted, collaborative markdown editor',
                'drawio': 'draw.io - Web-based application for creating diagrams and flowcharts',
                'jenkins': 'Jenkins - An open source automation server for CI/CD',
                'gitea': 'Gitea - Open Source Self-Hosted Git Service', 'wekan': 'WeKan - Open-Source Kanban',
                'jupyter-lab': 'Jupyter Notebook Scientific Python Stack',
                'node-red': 'Node-RED - Low-code programming for event-driven applications',
                'collabora': 'Collabora Online Development Edition - A online office suite',
                'onlyoffice': 'OnlyOffice - A free and open source office and productivity suite',
                'teammapper': 'TeamMapper - Online tool to create and collaborate on mindmaps',
                'mattermost': 'Mattermost - Open-source, self-hostable online chat service with file sharing',
                'vaultwarden': 'Vaultwarden - Community driven web-based Bitwarden compatible password manager server',
                'kiwix': 'Kiwix - Provides offline access to free educational content',
                'hesk': 'Help Desk Software HESK',
                'tools': 'Tools (Stirling PDF)', 'static': 'Landing Pages (Heimdall, Homer)',
                'opencart': 'OpenCart - Open Source Shopping Cart Solution (not yet working!)',
                'phpmyadmin': 'phpMyAdmin - Web interface for MySQL and MariaDB (not yet working!)'}

basic_configuration = {}


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
        'bottom-toolbar': '#444444 bg:#ffcc00'
    })
    app_list = {k: None for k, v in app_name_map.items()}
    app_list.update({'all': None})
    completer = NestedCompleter.from_nested_dict({
        'start': app_list,
        'stop': app_list,
        'pull': app_list,
        'help': None,
        'setup': app_list,
        'status': None,
        'exit': None,
    })
    command_history = FileHistory(".schoolappserver_history")
    toolbar_text = '<b>Commands:</b>  -  '
    toolbar_text += 'start [app] - stop [app] - pull [app] - status - setup [app] - help - exit - ctrl+c to quit'
    toolbar_text = HTML(toolbar_text)
    session = PromptSession(auto_suggest=AutoSuggestFromHistory(), style=style, completer=completer,
                            history=command_history, key_bindings=bindings, bottom_toolbar=toolbar_text,
                            complete_while_typing=True)
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
            all_secrets.extend([(str(path.parent), data['secrets'][s]['file']) for s in data['secrets']])
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


def generate_argon_password_hash(password):
    """
    Generate a hashed password with argon2 in PHC string format used by Vaultwarden for example.

    Sources:
     - https://github.com/dani-garcia/vaultwarden/wiki/Enabling-admin-page#secure-the-admin_token 
     - https://github.com/P-H-C/phc-string-format/blob/master/phc-sf-spec.md

    The gennerated hash should look like this:
    $argon2id$v=19$m=65540,t=3,p=4$bXBGMENBZUVzT3VUSFErTzQzK25Jck1BN2Z0amFuWjdSdVlIQVZqYzAzYz0$T9m73OdD...
    """
    ph = PasswordHasher(time_cost=3, memory_cost=65540,
                        parallelism=4, hash_len=32, salt_len=32)
    return ph.hash(password)


def create_secret_files(given_app):
    """
    Creates all files with secrets referenced in the Docker Compose files and
    fill them with long passwords for a given app.
    """
    for app, filename in find_all_secrets():
        if app != given_app:
            continue
        filepath = Path(app) / filename
        if 'dashboard_auth' in filename:
            chosen_password = create_password()
            print(f'Generated htpasswd password for Traefik Dashboard (user "admin"): {chosen_password}')
            print('Please save this password for later use!')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(generate_htpasswd_bcrypt('admin', chosen_password))
                logger.debug('Writing HTTP auth string to file: %s', filename)
        elif 'chronograf_htpasswd_auth' in filename:
            chosen_password = create_password()
            print(f'Generated htpasswd password for Chronograf (user "admin"): {chosen_password}')
            print('Please save this password for later use!')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(generate_htpasswd_bcrypt('admin', chosen_password))
                logger.debug('Writing HTTP auth string to file: %s', filename)
        elif 'smtp_password' in filename:
            # handle SMTP password files
            with open(filepath, 'w', encoding='utf-8') as f:
                smtp_password = prompt('Please enter the SMTP password: ', is_password=True)
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
    for path in Path('.').glob('*/*.yml'):
        if path.is_file():
            with open(path, 'r', encoding='utf-8') as file:
                if EXAMPLE_MAIL_PLACEHOLDER in file.read():
                    logger.debug('Found mail address to be replaced: %s', path)
                    replace_string_in_file(path, EXAMPLE_MAIL_PLACEHOLDER, mail_address)


def do_initial_basic_setup():
    """Initializes basic configuration."""
    print(' *** Initializing basic configuration *** ')
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
    # get base domain name (for non-ASCII characters in domain names, punycode has to used!)
    # Source: https://doc.traefik.io/traefik/routing/routers/#host-and-hostregexp
    domain_prompt = 'Please enter your domain name (third-level domain will be added, e.g. nicedomain.com): '
    domain_name = prompt(domain_prompt, validator=domain_validator)
    # write basic configuration to file
    with open(Path(INITIAL_SETUP_MARKER_FILE), 'w', encoding='utf-8') as f:
        f.write(f'mail-address = "{mail_address}"\ndomain-name = "{domain_name}"\n')
        logger.debug('Writing basic configuration to file: %s',
                     INITIAL_SETUP_MARKER_FILE)
    replace_mail_address_in_files(mail_address)
    # set correct file permissions for acme.json in app 'infrastructure'
    os.chmod(Path('infrastructure') / 'acme.json', 0o600)


def generate_env_file_from_template(app):
    """
    Generate a file with all environment variables from a template
    (.env.template) and fill in all missing element, like specific domain
    names, passwords, SMTP parameters, etc.
    """
    parameters = {}
    # find all env variables that contain domain names and generate them
    with open(Path(app) / ENV_FILE_TEMPLATE_FILENAME, 'r', encoding='utf-8') as f:
        template = f.read()
    for line in template.strip().split('\n'):
        if not line.strip():
            # skip empty lines
            continue
        var_name, _ = line.split('=')
        if 'DOMAIN' in var_name:
            app_domain_name = f'{SUBDOMAIN_MAP[var_name]}.{
                basic_configuration["domain-name"]}'
            app_domain_key = var_name.lower()
            parameters[app_domain_key] = app_domain_name
    # get all placeholders that are not domain from string  (https://stackoverflow.com/a/14061832)
    parameter_names = [name for text, name, spec, conv in string.Formatter().parse(
        template) if name is not None]
    # filter missing parameters and input them from user
    parameter_names = set(parameter_names)
    for p in parameter_names:
        if 'domain' in p:
            # skip parameters that have been filled already (see above)
            continue
        cleaned_up_p = p.replace('_', ' ')
        if 'password' in p or 'token' in p:
            print('This seems to be a password or token, so a random secure value is suggested.')
            parameters[p] = prompt(f'Please enter parameter "{
                                   cleaned_up_p}": ', default=create_password())
        else:
            parameters[p] = prompt(f'Please enter parameter "{cleaned_up_p}": ')
        if 'vaultwarden_admin_token' == p:
            print(f'Generating argon2 password hash for password {parameters[p]}.')
            # write hashed password to .env file and put single quotation marks around it
            parameters[p] = f"'{generate_argon_password_hash(parameters[p])}'"
    filename = Path(app, '.env')
    print(f'Writing environment variables to file: {filename}')
    logger.debug('Writing env vars to file: %s', filename)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(template.format(**parameters))
    # mark single app directories as initialized
    (Path(app) / INITIAL_SETUP_MARKER_FILE).touch()


def do_initial_setup_for_app(given_app):
    """
    Initializes all environment variables from a template file (.env.template)
    and fill all missing element, like specific domain names, passwords, SMTP
    parameters, etc. Also all necessary secret files will be created and filled
    with a random and secure password.
    """
    print(f' *** Initializing app configuration for {given_app} *** ')
    create_secret_files(given_app)
    generate_env_file_from_template(given_app)


def output_status(docker_clients):
    """Outputs status information about all stacks and their respective containers."""
    print(' *** Stacks and Container *** \n')
    for app, docker in docker_clients.items():
        if check_if_initial_setup_completed(app):
            container = docker.compose.ps(all=True)
            mark = '✔️' if container else '❌'
            print(f' {mark} {app_name_map[app]} {"⣿" * len(container)}')
            for c in container:
                print(f'    - {c.name}')
        else:
            print(HTML(f' ❌ {app_name_map[app]} - <style color="#ffcc00">Not yet initialized!</style>'))


def start_app(docker_clients, app):
    """Starts all containers of a specific Docker stack."""
    print(f' *** Starting app {app} *** \n')
    if not check_if_initial_setup_completed(app):
        do_initial_setup_for_app(app)
    try:
        docker_client = docker_clients[app]
        docker_client.compose.up(services=None, build=False, detach=True, pull='missing')
    except DockerException:
        print('Could not start app. Maybe you have not started the app "infrastructure" first?')


def stop_app(docker_clients, app):
    """Stops all containers of a specific Docker stack."""
    if check_if_initial_setup_completed(app):
        print(f' *** Stopping app {app} *** \n')
        docker_client = docker_clients[app]
        docker_client.compose.down()


def pull_app(docker_clients, app):
    """Pulls all containers of a specific Docker stack."""
    print(f' *** Pulling app {app} *** \n')
    if check_if_initial_setup_completed(app):
        docker_client = docker_clients[app]
        docker_client.compose.pull()


def check_if_initial_setup_completed(app=None):
    """Checks whether initial setup has been executed."""
    if app:
        if (Path(app) / INITIAL_SETUP_MARKER_FILE).is_file():
            return True
    else:
        if Path(INITIAL_SETUP_MARKER_FILE).is_file():
            return True
    return False


def show_help_info():
    """Show help page with information about available commands."""
    print(HTML(f'<skyblue>{APP}</skyblue> <violet>{VERSION}</violet>'))
    print(HTML('<orange>start [app]</orange> - Start one or all Docker Compose stack.'))
    print(HTML('<orange>stop [app]</orange>  - Stop one or all Docker Compose stack.'))
    print(HTML('<orange>pull [app]</orange>  - Stop one or all Docker Compose stack.'))
    print(HTML('<orange>status</orange>      - Show status of all Docker Compose stacks.'))
    print(HTML('<orange>setup [app]</orange> - Execute initial set up of configuration files.'))
    print(HTML('<orange>help</orange>        - Show this list of commands.'))
    print(HTML('<orange>exit</orange>        - Exit the programm.'))


def load_basic_configuration():
    """Loads basic configuration from file."""
    try:
        with open(Path(INITIAL_SETUP_MARKER_FILE), 'rb') as f:
            global basic_configuration
            basic_configuration = tomllib.load(f)
    except FileNotFoundError:
        logger.debug('Could not find basic configuration file.')


def evaluate_command(docker_clients, command, args):
    """
    Evaluates the given command and executes it. Can be called from the
    commandline or as command from inside SchoolAppServer.
    """
    if command == 'status':
        output_status(docker_clients)
    elif command == 'start':
        if args:
            # TODO: Handle multiple given app names instead of just on app.
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
            if results_array:
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
            if results_array:
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
            if results_array:
                for app in results_array:
                    pull_app(docker_clients, app)
    elif command == 'setup':
        if args:
            if args[0] in app_name_map:
                do_initial_setup_for_app(args[0])
            elif args[0] == 'all':
                for app in app_name_map:
                    do_initial_setup_for_app(app)
            else:
                print(HTML('<red>Given app not available!</red>'))
        else:
            if check_if_initial_setup_completed():
                text = 'The initial basic setup has already been executed. Do you want to run it again?'
                title_text = 'Run initial setup again?'
            else:
                text = 'Do you really want to run the initial basic setup?'
                title_text = 'Run initial setup for all apps?'
            do_run = yes_no_dialog(title=title_text, text=text).run()
            if do_run:
                do_initial_basic_setup()
                load_basic_configuration()
    else:
        print(HTML('<red>Invalid command!</red>'))


def main():
    """Starts command line interface and waits for commands."""
    # prepare session
    session = prepare_cli_interface()
    prompt_message = [('class:pound', '\n ➭ ')]
    # check for commandline arguments
    args = parse_arguments()
    if args.initial_setup:
        logger.info('Initializing all configuration and secret files...')
        do_initial_basic_setup()
    # prepare instances of Docker client
    # (Python-on-Whales: https://gabrieldemarmiesse.github.io/python-on-whales/sub-commands/compose/)
    docker_clients = {}
    for app, _ in app_name_map.items():
        docker = DockerClient(compose_files=[Path(
            app) / 'docker-compose.yml'], compose_env_file=Path(app) / '.env')
        docker_clients[app] = docker
    load_basic_configuration()
    print(f'{APP} {VERSION}')
    while True:
        try:
            user_input = session.prompt(prompt_message)
            if not user_input:
                continue
            user_input = user_input.split()
            command, args = user_input[0], user_input[1:]
            if command in ('exit', 'quit'):
                return
            if command == 'help':
                show_help_info()
            elif command != 'setup' and not check_if_initial_setup_completed():
                print('Please start initial setup first by entering the command "setup"!')
            else:
                evaluate_command(docker_clients, command, args)
        except KeyboardInterrupt:
            return


if __name__ == '__main__':
    create_logger()
    main()

#! /usr/bin/env python3

import sys
import string
import secrets
import logging
import getpass
import fileinput
import logging.handlers
from pathlib import Path
from argparse import ArgumentParser

# create logger instance
logger = logging.getLogger('school_app_server')

infrastructure_env = """UPTIMEKUMA_IMAGE=louislam/uptime-kuma:1
UPTIMEKUMA_DOMAIN=status.{domain}
TRAEFIK_IMAGE=traefik:v2.11
TRAEFIK_DASHBOARD_DOMAIN=dashboard.{domain}
TRAEFIK_METRICS_DOMAIN=metrics.{domain}
PORTAINER_IMAGE=portainer/portainer-ce:latest
PORTAINER_DOMAIN=portainer.{domain}
WATCHTOWER_IMAGE=containrrr/watchtower:latest
"""

nextcloud_env = """NEXTCLOUD_IMAGE=nextcloud:27.1-apache
NEXTCLOUD_DOMAIN=nextcloud.{domain}
NEXTCLOUD_DB_IMAGE=mariadb:10.6
NEXTCLOUD_REDIS_IMAGE=redis:latest
"""

kanboard_env = """KANBOARD_IMAGE=kanboard/kanboard:v1.2.36
KANBOARD_DOMAIN=kanboard.{domain}
KANBOARD_SMTP_ADDR={kanboard_smtp_addr}
KANBOARD_SMTP_PORT=465
KANBOARD_SMTP_USER={kanboard_smtp_user}
"""

tools_env = """STIRLINGPDF_IMAGE=frooodle/s-pdf:latest
STIRLINGPDF_DOMAIN=pdf.{domain}
"""

moodle_env = """MOODLE_IMAGE=bitnami/moodle:latest
MOODLE_DOMAIN1=moodle.{domain}
MOODLE_DOMAIN2=moodle2.{domain}
MOODLE_DB_IMAGE=mariadb:latest
MOODLE_SMTP_ADDR={moodle_smtp_addr}
MOODLE_SMTP_PORT=465
MOODLE_SMTP_USER={moodle_smtp_user}
MOODLE_ADMIN_EMAIL={moodle_admin_mail_address}
MOODLE_SITE_NAME={moodle_site_name}
"""

static_env = """
HEIMDALL_IMAGE=linuxserver/heimdall:latest
HEIMDALL_DOMAIN=www.{domain}
HOMER_IMAGE=b4bz/homer:latest
HOMER_DOMAIN=homer.{domain}
DEFAULTPAGE_IMAGE=nginx:latest
DEFAULTPAGE_DOMAIN=static.{domain}
"""

etherpad_env = """ETHERPAD_IMAGE=etherpad/etherpad:1.9
ETHERPAD_DOMAIN=pad.{domain}
ETHERPAD_DB_IMAGE=postgres:16-alpine
"""

hedgedoc_env = """HEDGEDOC_IMAGE=quay.io/hedgedoc/hedgedoc:latest
HEDGEDOC_DOMAIN=md.{domain}
HEDGEDOC_DB_IMAGE=postgres:16-alpine
"""

app_name_map = {'infrastructure': 'Infrastructure Services', 'nextcloud': 'Nextcloud',
                'kanboard': 'Kanboard', 'tools': 'Tool Apps', 'moodle': 'Moodle',
                'static': 'Static apps', 'etherpad': 'Etherpad',
                'hedgedoc': 'Hedgedoc Markdown Editor'}

app_var_map = {'infrastructure': infrastructure_env, 'nextcloud': nextcloud_env,
               'kanboard': kanboard_env, 'tools': tools_env, 'moodle': moodle_env,
               'static': static_env, 'etherpad': etherpad_env, 'hedgedoc': hedgedoc_env}

telegram_url_files = [('infrastructure', 'watchtower_telegram_url.txt')]

secret_password_files = [('infrastructure', 'traefik_dashboard_auth.txt'),
                         ('moodle', 'moodle_db_password.txt '),
                         ('moodle', 'moodle_db_root_password.txt'),
                         ('etherpad', 'etherpad_admin_password.txt'),
                         ('etherpad', 'etherpad_db_password.txt'),
                         ('hedgedoc', 'hedgedoc_db_password.txt'),
                         ('hedgedoc', 'hedgedoc_session_secret.txt'),
                         ('nextcloud', 'nextcloud_db_password.txt'),
                         ('nextcloud', 'nextcloud_db_root_password.txt'),
                         ('nextcloud', 'nextcloud_redis_password.txt')]

smtp_password_files = [('moodle', 'moodle_smtp_password.txt'),
                       ('kanboard', 'kanboard_smtp_password.txt')]

mail_address_files = [('infrastructure', 'traefik.yml')]


def create_logger():
    global logger
    logger.setLevel(logging.DEBUG)
    log_to_file = logging.handlers.RotatingFileHandler(
        'SchoolAppServer.log', maxBytes=262144, backupCount=5)
    log_to_file.setLevel(logging.DEBUG)
    logger.addHandler(log_to_file)
    log_to_screen = logging.StreamHandler(sys.stdout)
    log_to_screen.setLevel(logging.INFO)
    logger.addHandler(log_to_screen)


def parse_arguments():
    parser = ArgumentParser(
        description='Administrative tool for SchoolAppServer.')
    parser.add_argument('-i', '--initial-setup', action='store_true',
                        help='set up all initial configuration and secret files')
    args = parser.parse_args()
    return args


def create_password(length=25):
    # create secure password of a given length (https://docs.python.org/3/library/secrets.html#recipes-and-best-practices)
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
                any(c.isdigit() for c in password)):
            break
    return password


def do_initial_setup():
    # input all information from user
    mail_address = input('Please enter your mail address: ')
    domain_name = input('Please enter your domain name (third-level domain will be added automatically, e.g. nicedomain.com): ')
    # handle telegram URL files
    for filename in telegram_url_files:
        filename = Path(*filename)
        with open(filename, 'w') as f:
            bot_id = input('Please enter the Telegram bot id: ')
            bot_id = '[bot_id]' if not bot_id else bot_id
            chat_id = input('Please enter the Telegram chat id: ')
            chat_id = '[chat_id]' if not chat_id else chat_id
            url = f'telegram://{bot_id}@telegram/?channels={chat_id}'
            f.write(url)
            logger.debug(f'Writing Telegram IDs to file: {filename}')
    # handle password files
    for filename in secret_password_files:
        filename = Path(*filename)
        with open(filename, 'w') as f:
            f.write(create_password())
            logger.debug(f'Writing password to secrets file: {filename}')
    # handle SMTP password files
    smtp_password = getpass.getpass('Please enter the SMTP password: ')
    for filename in smtp_password_files:
        filename = Path(*filename)
        with open(filename, 'w') as f:
            f.write(smtp_password)
            logger.debug(f'Writing SMTP password to file: {filename}')
    # replace mail address in files
    for filename in mail_address_files:
        filename = Path(*filename)
        # replacing string in file (https://stackoverflow.com/a/20593644)
        with fileinput.FileInput(filename, inplace=True, backup='.bak') as file:
            for line in file:
                print(line.replace('mail@example.com', mail_address), end='')
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
            parameters[p] = input(f'Please enter parameter "{p}": ')
        filename = Path(app, '.env')
        logger.debug(f'Writing env vars to file: {filename}')
        with open(filename, 'w') as f:
            f.write(env_vars.format(**parameters))


if __name__ == '__main__':
    create_logger()
    args = parse_arguments()
    if args.initial_setup:
        logger.info('Initializing all configuration and secret files...')
        do_initial_setup()
    else:
        print('What would you like to do?')

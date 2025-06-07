# Stalwart - All-in-one Mail & Collaboration server supporting every protocol (IMAP, JMAP, SMTP, CalDAV, CardDAV, WebDAV)

## Debugging
Look at Stalwart log files inside the container:

    docker compose -f stalwart/docker-compose.yml exec mailserver tail -f /opt/stalwart/logs/stalwart.log.2025-05-31

Manually editing config file inside the container:

    docker compose -f stalwart/docker-compose.yml exec mailserver cat /opt/stalwart/etc/config.toml
    nano /var/lib/docker/volumes/stalwart_stalwart_data/_data/etc/config.toml

## Issues

* If resolved consumes a lot of CPU, you can switch resolver inside Stalwart or deactivate systemd-resolved.
  (More information here: https://github.com/stalwartlabs/stalwart/discussions/1569)

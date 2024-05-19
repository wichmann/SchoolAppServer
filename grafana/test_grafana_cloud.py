
"""
Send test data to self hosted Grafana cloud.

Before executing the script, install all necessary requirements:

    pip install prometheus_client, influxdb3-python, python-logging-loki

Alternatively, execute script with pipenv:

    pipenv run python grafana/test_grafana_cloud.py 

"""

import os
import random
import logging
from time import sleep

import logging_loki
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point
from prometheus_client import CollectorRegistry, Gauge, Counter, push_to_gateway


def test_prometheus():
    """
    Push metrics to local PushGateway for collection by Prometheus.

    Source: https://stackoverflow.com/a/60108645
    """
    registry = CollectorRegistry()
    g = Gauge('job_last_success', 'Last time a job successfully finished')
    g.set_to_current_time()
    r = Counter('http_req_total', 'HTTP Requests Total')
    r.inc(42.73)
    m = Gauge('memory_usage_in_bytes', 'System Memory Usage')
    m.set(52.19)
    push_to_gateway('localhost:9091', job='batch', registry=registry)


def test_influx():
    """
    Send some metrics for testing to the InfluxDB server. 
    """
    bucket = os.getenv('INFLUXDB_INIT_BUCKET')
    org = os.getenv('INFLUXDB_INIT_ORG')
    token = os.getenv('INFLUXDB_INIT_ADMIN_TOKEN')
    url = f'https://{os.getenv("INFLUX_DOMAIN")}'
    client = InfluxDBClient3(host=url, token=token, org=org)
    data = {
        'data point': {
            'location': 'Berlin',
            'count': random.randint(0, 100),
        },
    }
    for _, value in data.items():
        point = Point('production').tag('location', value['location']).field('count', value['count'])
        client.write(database=bucket, record=point)


def test_loki():
    """
    Send some logs for testing to the Loki server. 

    Sources:
     - https://medium.com/geekculture/pushing-logs-to-loki-without-using-promtail-fc31dfdde3c6
     - https://pypi.org/project/python-logging-loki/
     - https://github.com/sleleko/devops-kb/blob/master/python/push-to-loki.py 
    """
    logging_loki.emitter.LokiEmitter.level_tag = "level"
    handler = logging_loki.LokiHandler(url=f'https://{os.getenv("LOKI_DOMAIN")}/loki/api/v1/push', version='1')
    logger = logging.getLogger('my-logger')
    logger.addHandler(handler)
    logger.error('Logging a random number for testing: %f...', random.randint(0, 100))


def main():
    """Send test data every 5 seconds."""
    load_dotenv()
    while True:
        try:
            # test_prometheus()
            test_influx()
            test_loki()
            print('Pass complete!')
            sleep(5)
        except KeyboardInterrupt:
            return


main()

#!/usr/bin/env python
"""
A collector that fetches data from an UWSGI Stats Server

A configuration file named UwsgiCollector.conf should contain the following parameters:

enabled = True
path_suffix = ""
measure_collector_time = False
byte_unit = byte,

host = <host>
port = <port>

Testing via the command line:

$ diamond -l -f -r Diamond/src/collectors/uwsgi/uwsgi.py -c Diamond/conf/diamond.conf.example
"""

import diamond.collector

try:
    import json
except ImportError:
    import simplejson as json

import socket

class UwsgiCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(UwsgiCollector, self).get_default_config_help()
        config_help.update({
            'host': "",
            'port': "",
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(UwsgiCollector, self).get_default_config()
        config.update({
            'host':     '127.0.0.1',
            'port':     1717,
        })
        return config

    def _get(self):

        sfamily, addr = (socket.AF_INET, (self.config['host'], int(self.config['port'])) )

        result = ""
        try:
            s = socket.socket(sfamily, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect( addr )

            while True:
                data = s.recv(4096)
                if len(data) < 1:
                    break
                result += data
        except:
            self.log.error("unable to get uWSGI stats")

        try:
            return json.loads(result)
        except (TypeError, ValueError):
            self.log.error("Unable to parse response from uwsgi as a json object")
            return False

    def collect(self):
        """
        Overrides the Collector.collect method
        """

        metric_name = "uwsgi.worker%i.%s"

        if json is None:
            self.log.error('Unable to import json')
            return {}

        result = self._get()
        if not result:
            return

        metrics = {}

        metrics["uwsgi.listen_queue"] = result["listen_queue"]
        metrics["uwsgi.listen_queue_errors"] = result["listen_queue_errors"]
        metrics["uwsgi.signal_queue"] = result["signal_queue"]
        metrics["uwsgi.load"] = result["load"]

        for worker in result["workers"]:
            metrics[metric_name % (worker["id"], "requests")] = worker['requests']
            metrics[metric_name % (worker["id"], "exceptions")] = worker['exceptions']
            metrics[metric_name % (worker["id"], "physical_memory")] = worker['vsz']
            metrics[metric_name % (worker["id"], "avg_response_time")] = worker['avg_rt']
            metrics[metric_name % (worker["id"], "send_bytes")] = worker['tx']
            metrics[metric_name % (worker["id"], "delta_requests")] = worker['delta_requests']
            metrics[metric_name % (worker["id"], "harakiri_count")] = worker['harakiri_count']
            metrics[metric_name % (worker["id"], "signals")] = worker['signals']
            metrics[metric_name % (worker["id"], "signal_queue")] = worker['signal_queue']
            metrics[metric_name % (worker["id"], "running_time")] = worker['running_time']
            metrics[metric_name % (worker["id"], "respawn_count")] = worker['respawn_count']
            metrics[metric_name % (worker["id"], "physical_unshared_memory")] = worker['rss']



        # Publish Metric
        for key in metrics:
            self.publish(key, metrics[key])

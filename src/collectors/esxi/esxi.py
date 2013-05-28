#!/usr/bin/env python
"""
A collector that fetches data from an ESXI vSphere hypervisor

depends on pysphere

A configuration file named EsxiCollector.conf should contain the following parameters:

enabled = True
path = 'esxi'
path_suffix = ''
measure_collector_time = False
byte_unit = byte,
simple = False
percore = True

hosts = <host1>, <host2>, 
username = <username>
password = <password>

An optional "collect_all_stats" parameters can be provided. If the value is false,
you also need to provide counter names with aliases in the following format:

counter1 = cpu.usage, cpu-usage-percent
counter2 = cpu.swapwait, cpu-swapwait-milliseconds
counter3 = datastore.read, datastore-read-kiloBytesPerSecond
counter4 = datastore.write, datastore-write-kiloBytesPerSecond

The only constraint is that the key name begin with "counter"

Testing via the command line:

$ diamond -l -f -r Diamond/src/collectors/esxi/esxi.py -c Diamond/conf/diamond.conf.example
"""
import re

from collections import defaultdict
from threading import Thread

import diamond.collector
from pysphere import VIServer


class EsxiCollector(diamond.collector.Collector):

    def group_stats_by_type_and_generate_averages(self, all_stats):
        """
        Given that for the mast majority of stats exposed via the vSphere python sdk
        we want to get the average, we're going to publish ALL averages via statsd

        We're mostly doing this as a diagnostic to figure out which values we 
        actually carry about.

        There's some complexity here, because we only want to make one http request
        for the complete list of stat objects...and then we inspect the elements
        to group them according to group and counter.

        Returns a tuple of (key, value) where key is formatted "key(unit)x<len_stats>"
        and the value is the average of all strings in the list casted to floats.
        """
        def _avg(vals):
            return sum(vals) / len(vals)

        stats_dict = defaultdict(list)

        for s in all_stats:
            stats_dict['%s.%s' % (s.group, s.counter)].append(s)

        results = []

        for key, stats in stats_dict.items():
            vals = [float(s.value) for s in stats]
            results.append(['%s-%s-x%d' % (key, stats[0].unit, len(stats)),  _avg([float(s.value) for s in stats])])

        return results

    def collect(self):
        """
        A subclass of Diamond's Collector that publishes pysphere metrics
        """
        # We want to speed this up with publishing:
        def _publish(h):

            # Create an instance of VIServer
            server = VIServer()

            # Authenticate using credentials in EsxiCollector.conf
            server.connect(h, self.config['username'], self.config['password'])
            host = server.get_hosts().keys()[0]  # ugg.. this is ugly. keys()[0] is a subclass of str

            # Get a performance managerd instance
            pm = server.get_performance_manager()

            # If collect_all_stats is set to True, get everything:
            if self.config.get('collect_all_stats', True) != 'False':
                mor_ids = []
                for key, mor_id in pm.get_entity_counters(host).items():
                    mor_ids.append(mor_id)
                stats = pm.get_entity_statistic(host, mor_ids)

                # And publish values
                for k, v in self.group_stats_by_type_and_generate_averages(stats):
                    self.publish('%s.%s' % (h, k), v)

            # Otherwise, get all counters and aliases specified
            else:
                counters = dict([v for k, v in self.config.items() if k.startswith('counter')])
                stats = pm.get_entity_statistic(host, counters.keys())

                # And publish values
                for k, v in self.group_stats_by_type_and_generate_averages(stats):
                    k = counters[k.rsplit('-', 2)[0]]
                    self.publish('%s.%s' % (h, k), v)

        # For each host defined in EsxiCollector.conf
        for h in self.config['hosts']:
            _publish(h)


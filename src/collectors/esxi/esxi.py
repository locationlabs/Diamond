#!/usr/bin/env python
"""
A collector that fetches data from an ESXI vSphere hypervisor

depends on pysphere

A configuration file named EsxiCollector.conf should contain the following parameters:

enabled = True
path_suffix = ""
measure_collector_time = False
byte_unit = byte,
simple = False
percore = True

hosts = <host1>, <host2>, 
username = <username>
password = <password>

Testing via the command line:

$ diamond -l -f -r Diamond/src/collectors/esxi/esxi.py -c Diamond/conf/diamond.conf.example
"""

import diamond.collector
from pysphere import VIServer


class EsxiCollector(diamond.collector.Collector):
    def collect(self):
        """
        A subclass of Diamond's Collector that publishes pysphere metrics
        """
        # For each host defined in EsxiCollector.conf
        for h in self.config['hosts']:

             # Create an instance of VIServer
             server = VIServer()

             # Authenticate using credentials in EsxiCollector.conf
             server.connect(h, self.config['username'], self.config['password'])
             host = server.get_hosts().keys()[0]  # ugg.. an ambiguous nested class in dynamically generated code

             # Get a reference to PerformanceManager
             pm = server.get_performance_manager()

             # And publish all values available
             for k, v in pm.get_entity_counters(host).items():
                  self.publish('%s.%s' % (h, k), v)

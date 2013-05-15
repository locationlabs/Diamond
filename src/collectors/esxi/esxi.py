#!/usr/bin/env python
"""
A collector that fetches data from an ESXI vSphere hypervisor

depends on pysphere

Configuration requires additional parameters:

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
        Overrides the Collector.collect method
        """
        for h in self.config['hosts']:
            server = VIServer()
            server.connect(h, self.config['username'], self.config['password'])
            host = server.get_hosts().keys()[0]  # ugg.. an ambiguous nested class in dynamically generated code
            pm = server.get_performance_manager()
            for k, v in pm.get_entity_counters(host).items():
                self.publish('%s.%s' % (h, k), v)

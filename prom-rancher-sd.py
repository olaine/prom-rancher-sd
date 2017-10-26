#!/usr/bin/python3

# Copyright 2016 Daniel Dent (https://www.danieldent.com/)
# Copyright 2016 Virgil Chereches (virgil.chereches@gmx.net)

import time
import urllib.parse
import urllib.request
import json
import shutil


def get_current_metadata_entry(entry):
    headers = {
        'User-Agent': "prom-rancher-sd/0.1",
        'Accept': 'application/json'
    }
    req = urllib.request.Request('http://rancher-metadata.rancher.internal/2015-07-25/%s' % entry, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf8 '))

def is_monitored_service(service):
    return 'labels' in service and 'com.prometheus.monitoring' in service['labels'] and service['labels']['com.prometheus.monitoring'] == 'true'

def is_node_exporter_service(service):
    return service['service_name'] == 'node-exporter'

def monitoring_config(service):
    #change metrics_path label to __metrics_paths__
    return {
        "targets": [service['primary_ip'] + ':' + (service['labels']['com.prometheus.port'] if 'com.prometheus.port' in service['labels'] else '8083')],
        "labels": {
            'instance': None,
            'name': service['name'],
            'service_name': service['service_name'],
            'stack_name': service['stack_name'],
            '__metrics_path__': service['labels']['com.prometheus.metricspath'] if 'com.prometheus.metricspath' in service['labels'] else '/metrics'
        },
       "host-uuid": service['host_uuid']
    }

def node_monitoring_config(service):
    return {
        "targets": [service['primary_ip'] + ':' + '9100' ],
        "labels": {
            'instance': None,
            'name': service['name'],
            'service_name': service['service_name'],
            'stack_name': service['stack_name'],
        },
       "host-uuid": service['host_uuid']
    }

def get_hosts_dict(hosts):
   return { x['uuid']:x['hostname'] for x in hosts }

def get_monitoring_config():
    return list(map(monitoring_config, filter(is_monitored_service, get_current_metadata_entry('containers'))))

def get_node_monitoring_config():
    return list(map(node_monitoring_config, filter(is_node_exporter_service, get_current_metadata_entry('containers'))))

def enrich_dict(dictionary,hostdict):
    assert 'host-uuid' in dictionary
    assert dictionary['host-uuid'] in hostdict
    hostname = hostdict[dictionary['host-uuid']]
    dictionary['labels']['instance']=hostname
    dictionary.pop('host-uuid',None)
    return dictionary

def write_config_file(filename,get_config_function):
    hostdict = get_hosts_dict(get_current_metadata_entry('hosts'))
    configlist = get_config_function()
    newconfiglist = [ enrich_dict(x,hostdict) for x in configlist ]
    tmpfile = filename+'.temp'
    with open(tmpfile, 'w') as config_file:
        print(json.dumps(newconfiglist, indent=2),file=config_file)
    shutil.move(tmpfile,filename)

if __name__ == '__main__':
    while True:
        time.sleep(5)
        write_config_file('/prom-rancher-sd-data/rancher.json',get_monitoring_config)
        write_config_file('/prom-rancher-sd-data/node_exporter.json',get_node_monitoring_config)

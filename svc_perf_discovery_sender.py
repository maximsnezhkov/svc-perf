#!/usr/bin/python
# -*- coding: utf-8 -*- # coding: utf-8
#
# IBM Storwize V7000 volume/mdisk autodiscovery script for Zabbix
#
# 2013 Matvey Marinin
#
# Sends volume/mdisk low-level discovery data to LLD trapper item svc_perf_discovery[<volume-mdisk|volume|mdisk|pool>] in JSON format
# Use with "_Special_Storwize_Perf_sender" Zabbix template:
# (http://www.zabbix.com/documentation/2.0/manual/discovery/low_level_discovery)
#
# Usage:
# svc_perf_discovery.py [--debug] --clusters <svc1>[,<svc2>...] --user <username> --password <pwd> --type <volume-mdisk|volume|mdisk|pool>
#
#   --debug    = Enable debug output
#   --clusters = Comma-separated Storwize node list
#   --user     = Storwize V7000 user account with Administrator role (it seems that Monitor role is not enough)
#   --password = User password
#   --type     = Requested object type, one of <volume-mdisk|volume|mdisk|pool>
#
import pywbem
import getopt, sys
from zbxsend import Metric, send_to_zabbix
import logging

def usage():
  print >> sys.stderr, "Usage: svc_perf_discovery.py [--debug] --clusters <svc1>[,<svc2>...] --user <username> --password <pwd> --type <volume-mdisk|volume|mdisk|pool>"

DISCOVERY_TYPE = ['volume-mdisk','volume','mdisk','pool']

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "clusters=", "user=", "password=", "type=", "debug"])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err)
  usage()
  sys.exit(2)

debug = False
clusters = []
user = None
password = None
objectType = None
for o, a in opts:
  if o == "--clusters" and not a.startswith('--'):
    clusters.extend( a.split(','))
  elif o == "--user" and not a.startswith('--'):
    user = a
  elif o == "--password" and not a.startswith('--'):
    password = a
  elif o == "--type" and not a.startswith('--'):
    objectType = a
  elif o == "--debug":
    debug = True
  elif o in ("-h", "--help"):
    usage()
    sys.exit()

if not clusters:
  print >> sys.stderr, '--clusters option must be set'
  usage()
  sys.exit(2)

if not user or not password:
  print >> sys.stderr, '--user and --password options must be set'
  usage()
  sys.exit(2)

if not objectType or not objectType in DISCOVERY_TYPE:
  print >> sys.stderr, '--type option must be one of %s' % DISCOVERY_TYPE
  usage()
  sys.exit(2)

def debug_print(message):
  if debug:
    print message

for cluster in clusters:
  debug_print('Connecting to: %s' % cluster)
  conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/ibm') 
  conn.debug = True

  for objectType in DISCOVERY_TYPE:
    output = []

    if objectType == 'volume-mdisk' or objectType == 'volume':
      for vol in conn.ExecQuery('WQL', 'select DeviceID, ElementName from IBMTSSVC_StorageVolume'):
        output.append( '{"{#TYPE}":"%s", "{#NAME}":"%s", "{#ID}":"%s"}' % ('volume', vol.properties['ElementName'].value, vol.properties['DeviceID'].value) )

    if objectType == 'volume-mdisk' or objectType == 'mdisk':
      for mdisk in conn.ExecQuery('WQL', 'select DeviceID, ElementName from IBMTSSVC_BackendVolume'):
        output.append( '{"{#TYPE}":"%s", "{#NAME}":"%s", "{#ID}":"%s"}' % ('mdisk', mdisk.properties['ElementName'].value, mdisk.properties['DeviceID'].value) )

    if objectType == 'pool':
      for pool in conn.ExecQuery('WQL', 'select PoolID, ElementName from IBMTSSVC_ConcreteStoragePool'):
        output.append( '{"{#TYPE}":"%s","{#NAME}":"%s","{#ID}":"%s"}' % ('pool', pool.properties['ElementName'].value, pool.properties['PoolID'].value) )

    json = []
    json.append('{"data":[')

    for i, v in enumerate( output ):
      if i < len(output)-1:
        json.append(v+',')
      else:
        json.append(v)
    json.append(']}')

    json_string = ''.join(json)
    debug_print(json_string)

    trapper_key = 'svc.discovery.%s' % objectType
    debug_print('Sending to host=%s, key=%s' % (cluster, trapper_key))

    #send json to LLD trapper item with zbxsend module
    logging.basicConfig(level=logging.INFO)
    send_to_zabbix([Metric(cluster, trapper_key, json_string)], 'localhost', 10051)




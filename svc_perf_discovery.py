#!/usr/bin/python
# -*- coding: utf-8 -*- # coding: utf-8
#
# IBM Storwize V7000 volume/mdisk autodiscovery script for Zabbix
#
# 2012 Matvey Marinin
#
# Returns volume and mdisk list in JSON format for "_Special_Storwize_Perf" Zabbix autodiscovery template:
# (http://www.zabbix.com/documentation/2.0/manual/discovery/low_level_discovery)
#
# Usage:
# svc_perf_discovery.py --cluster <cluster1> --user <username> --password <pwd> --type <volume-mdisk|volume|mdisk|pool>
#
#   --cluster  = Dns name or IP of Storwize V7000 block node  (not Unified mgmt node!). Only one cluster name is allowed.
#   --user     = Storwize V7000 user account with Administrator role (it seems that Monitor role is not enough)
#   --password = User password
#   --type     = Requested object type, one of <volume-mdisk|volume|mdisk|pool>
#
import pywbem
import getopt, sys

def usage():
  print >> sys.stderr, "Usage: svc_perf_discovery.py --cluster <cluster1> --user <username> --password <pwd> --type <volume-mdisk|volume|mdisk|pool>"

TYPE_ARG = ['volume-mdisk','volume','mdisk','pool']

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "cluster=", "user=", "password=", "type="])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err)
  usage()
  sys.exit(2)
  
cluster = None
user = None
password = None
objectType = None
for o, a in opts:
  if o == "--cluster" and not a.startswith('--'):
    cluster = a
  elif o == "--user" and not a.startswith('--'):
    user = a
  elif o == "--password" and not a.startswith('--'):
    password = a
  elif o == "--type" and not a.startswith('--'):
    objectType = a
  elif o in ("-h", "--help"):
    usage()
    sys.exit()

if not cluster:
  print >> sys.stderr, '--cluster must be set'
  usage()
  sys.exit(2)

if not user or not password:
  print >> sys.stderr, '--user and --password options must be set'
  usage()
  sys.exit(2)

if not objectType or not objectType in TYPE_ARG:
  print >> sys.stderr, '--type option must be one of %s' % TYPE_ARG
  usage()
  sys.exit(2)
  
output = []

conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/ibm') 
conn.debug = True

print '{ "data":['
first = True

if objectType == 'volume-mdisk' or objectType == 'volume':
  for vol in conn.ExecQuery('WQL', 'select DeviceID, ElementName from IBMTSSVC_StorageVolume'):
    output.append( '{"{#TYPE}":"%s", "{#NAME}":"%s", "{#ID}":"%s"}' % ('volume', vol.properties['ElementName'].value, vol.properties['DeviceID'].value) )

if objectType == 'volume-mdisk' or objectType == 'mdisk':
  for mdisk in conn.ExecQuery('WQL', 'select DeviceID, ElementName from IBMTSSVC_BackendVolume'):
    output.append( '{"{#TYPE}":"%s", "{#NAME}":"%s", "{#ID}":"%s"}' % ('mdisk', mdisk.properties['ElementName'].value, mdisk.properties['DeviceID'].value) )

if objectType == 'pool':
  for pool in conn.ExecQuery('WQL', 'select PoolID, ElementName from IBMTSSVC_ConcreteStoragePool'):
    output.append( '{"{#TYPE}":"%s", "{#NAME}":"%s", "{#ID}":"%s"}' % ('pool', pool.properties['ElementName'].value, pool.properties['PoolID'].value) )

for i, v in enumerate( output ):
  if i < len(output)-1:
    print v+','
  else:
    print v
  
print '] }'

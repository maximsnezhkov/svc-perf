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
# svc_perf_discovery.py --cluster <cluster1> --user <username> --password <pwd>
#
#   --cluster = Dns name or IP of Storwize V7000 block node  (not Unified mgmt node!). Only one cluster name is allowed.
#   --user    = Storwize V7000 user account with Administrator role (it seems that Monitor role is not enough)
#   --password = User password
#
#
import pywbem
import getopt, sys

def usage():
  print >> sys.stderr, "Usage: svc_perf_discovery.py --cluster <cluster1> --user <username> --password <pwd>"

try:
  opts, args = getopt.getopt(sys.argv[1:], "-h", ["help", "cluster=", "user=", "password="])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err)
  usage()
  sys.exit(2)

cluster = None
user = None
password = None
for o, a in opts:
  if o == "--cluster":
    cluster = a
  elif o == "--user":
    user = a
  elif o == "--password":
    password = a
  elif o in ("-h", "--help"):
    usage()
    sys.exit()

if not cluster:
  print >> sys.stderr, '--cluster must be set'
  usage()
  sys.exit(2)

output = []

conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/ibm') 
conn.debug = True

print '{ "data":['
first = True

volumes = conn.EnumerateInstances('IBMTSSVC_StorageVolume')
for vol in volumes: ## vol is IBMTSSVC_StorageVolume
  output.append( '{"{#TYPE}":"%s",  "{#NAME}":"%s"}' % ('volume', vol.properties['ElementName'].value) )
  
  
mdisks = conn.EnumerateInstances('IBMTSSVC_BackendVolume')
for mdisk in mdisks: ## mdisk is IBMTSSVC_BackendVolume
  output.append( '{"{#TYPE}":"%s",  "{#NAME}":"%s"}' % ('mdisk', mdisk.properties['ElementName'].value) )

for i, v in enumerate( output ):
  if i < len(output)-1:
    print v+','
  else:
    print v


  
print '] }'

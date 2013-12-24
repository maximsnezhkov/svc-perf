#!/usr/bin/python
# -*- coding: utf-8 -*- # coding: utf-8
#
# IBM SVC/Storwize V7000 operational state monitor
#
# 2013 Matvey Marinin
#
# Returns storage pool/volume space stats in zabbix_sender format (http://www.zabbix.com/documentation/2.2/manpages/zabbix_sender):
# <hostname> <key> <timestamp> <value>
#
# Use with template _Special_Storwize_Perf
#
# Data is collected with SVC CIM provider (WBEM):
# http://pic.dhe.ibm.com/infocenter/storwize/unified_ic/index.jsp?topic=%2Fcom.ibm.storwize.v7000.unified.doc%2Fsvc_umlblockprofile.html
# http://pic.dhe.ibm.com/infocenter/storwize/unified_ic/index.jsp?topic=%2Fcom.ibm.storwize.v7000.unified.doc%2Fsvc_cim_main.html
#
# Usage: svc_mon.py [--debug] --clusters <svc1>[,<svc2>...] --user <svc_username> --password <svc_pwd>
#
#   --debug = Enable debug output
#   --clusters = Comma-separated Storwize node list (DNS name/IP)
#   --user    = Storwize V7000 user account
#   --password = Storwize password
#
import pywbem
import getopt, sys
import datetime, time, calendar

def usage():
  print >> sys.stderr, "Usage: svc_mon.py [--debug] --clusters <svc1>[,<svc2>...] --user <svc_username> --password <svc_pwd>"

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "clusters=", "user=", "password=", "debug"])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err)
  usage()
  sys.exit(2)

debug = False
clusters = []
user = None
password = None

for o, a in opts:
  if o == "--clusters" and not a.startswith('--'):
    clusters.extend( a.split(','))
  elif o == "--user" and not a.startswith('--'):
    user = a
  elif o == "--password" and not a.startswith('--'):
    password = a
  elif o == "--debug":
    debug = True
  elif o in ("-h", "--help"):
    usage()
    sys.exit()

if debug:
  print 'clusters:', clusters

if not clusters:
  print >> sys.stderr, '--clusters option must be set'
  usage()
  sys.exit(2)

if not user or not password:
  print >> sys.stderr, '--user and --password options must be set'
  usage()
  sys.exit(2)

     
#####################################################################################################
# main 
#####################################################################################################

for cluster in clusters:
  ''' connect to Storwize CIM provider '''
  conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/ibm') 
  conn.debug = True

  pools = conn.ExecQuery('WQL', 'select * from IBMTSSVC_ConcreteStoragePool')
  for pool in pools:  
    timestamp = int(time.time())
    poolID = pool.properties['PoolID'].value
    
    #<hostname> <key> <timestamp> <value>
    # svc1-blk svc.pool.nativeStatus[8] 1356526942 1
    # svc1-blk svc.pool.overallocation[8] 1356526942 2.2936499048
    # svc1-blk svc.pool.totalSpaceGB[8] 1356526942 1 2232.25
    # svc1-blk svc.pool.virtualCapacityGB[8] 1356526942 1 5120.0
    # svc1-blk svc.pool.usedCapacityGB[8] 1356526942 1 5120.0
    # svc1-blk svc.pool.realCapacityGB[8] 1356526942 1 5120.0

    def printPool(key, value):
      print '%s svc.pool.%s[%s] %d %s' % ( cluster, key, poolID, timestamp, value )

    printPool( 'nativeStatus', pool.properties['nativeStatus'].value)
    printPool( 'overallocation', float(pool.properties['VirtualCapacity'].value)/float(pool.properties['TotalManagedSpace'].value)*100 )
    printPool( 'totalSpace', pool.properties['TotalManagedSpace'].value )
    printPool( 'usedCapacity', pool.properties['UsedCapacity'].value )
    printPool( 'realCapacity', pool.properties['RealCapacity'].value )
    printPool( 'freeCapacity', pool.properties['TotalManagedSpace'].value - pool.properties['RealCapacity'].value )


  #<hostname> <key> <timestamp> <value>
  #svc1-blk svc.volume.nativeStatus[35] 1365594894 1
  for vol in conn.ExecQuery('WQL', 'select DeviceID, NativeStatus from IBMTSSVC_StorageVolume'):
    print '%s svc.volume.%s[%s] %d %s' % ( cluster, 'nativeStatus', vol.properties['DeviceID'].value, timestamp, vol.properties['NativeStatus'].value )

  #<hostname> <key> <timestamp> <value>
  #svc1-blk svc.mdisk.nativeStatus[35] 1365594894 1
  for md in conn.ExecQuery('WQL', 'select DeviceID, NativeStatus from IBMTSSVC_BackendVolume'):
    print '%s svc.mdisk.%s[%s] %d %s' % ( cluster, 'nativeStatus', md.properties['DeviceID'].value, timestamp, md.properties['NativeStatus'].value )
    
   




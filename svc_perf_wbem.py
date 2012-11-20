#!/usr/bin/python
# -*- coding: utf-8 -*- # coding: utf-8
#
# IBM Storwize V7000 performance monitoring script for Zabbix
#
# v3.1
# 2012 Matvey Marinin
#
# Returns statistics in zabbix_sender format (http://www.zabbix.com/documentation/2.2/manpages/zabbix_sender):
# <hostname> <key> <timestamp> <value> 
# svc1-blk svc.volume.back-node.KBytesRead 1350976915 3148
# svc1-blk svc.volume.back-node.KBytesWritten 1350976915 1774572
# svc1-blk svc.volume.back-node.KBytesTransferred 1350976915 1777720
# svc1-blk svc.volume.back-node.ReadIOs 1350976915 2231
# svc1-blk svc.volume.back-node.WriteIOs 1350976915 3619
# svc1-blk svc.volume.back-node.TotalIOs 1350976915 5850
#
# Performance stats is collected with SVC CIM provider (WBEM):
# http://pic.dhe.ibm.com/infocenter/storwize/unified_ic/index.jsp?topic=%2Fcom.ibm.storwize.v7000.unified.doc%2Fsvc_umlblockprofile.html
# http://pic.dhe.ibm.com/infocenter/storwize/unified_ic/index.jsp?topic=%2Fcom.ibm.storwize.v7000.unified.doc%2Fsvc_cim_main.html
# 
# Usage:
# svc_perf_wbem.py --cluster <cluster1> [--cluster <cluster2>...] --user <username> --password <pwd> --cachefile <path>|none
#
#   --cluster = Dns name or IP of Storwize V7000 block node  (not Unified mgmt node!). May be used several times to monitor some clusters.
#   --user    = Storwize V7000 user account with Administrator role (it seems that Monitor role is not enough)
#   --password = User password
#   --cachefile = Path to timestamp cache file or "none" to not use cache. Used to prevent submitting duplicate values to Zabbix.
#                 Duplicates detected by statistics timestamp supplied by Storwize.
#
#
import pywbem
import getopt, sys, datetime, calendar, json

def usage():
  print >> sys.stderr, "Usage: svc_perf_wbem.py --cluster <cluster1> [--cluster <cluster2>...] --user <username> --password <pwd> --cachefile <path>|none"

try:
  opts, args = getopt.getopt(sys.argv[1:], "-h", ["help", "cluster=", "user=", "password=", "cachefile="])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err) # will print something like "option -a not recognized"
  usage()
  sys.exit(2)

cluster = []
user = None
password = None
cachefile = None
for o, a in opts:
  if o == "--cluster":
    cluster.append(a)
  elif o == "--user":
    user = a;
  elif o == "--password":
    password = a;
  elif o == "--cachefile":
    cachefile = a;
  elif o in ("-h", "--help"):
    usage()
    sys.exit()

if not cluster or not user or not password or not cachefile:
  print >> sys.stderr, 'Required argument is not set'
  usage()
  sys.exit(2)

## Loading timestamp cache from file
cachedTimestamps = None
try:
  if 'none' != cachefile:
    cachedTimestamps = json.load( open(cachefile, 'r') )
except Exception, err:
  print >> sys.stderr, "Can't load cached timestamps:", str(err)
  
if cachedTimestamps is None:
  cachedTimestamps = {}

#debug
#print >> sys.stderr, 'Timestamp cache:', cachedTimestamps

def enumNames(cimClass):
  '''Enum storage objects and return dict{id:name}'''
  names = {}
  for obj in conn.EnumerateInstances(cimClass):
    deviceID = obj.properties['DeviceID'].value
    if deviceID:
      names[str(deviceID)] = obj.properties['ElementName'].value
  return names

  
for cluster in cluster:
  #debug
  print >> sys.stderr, 'Connecting to', cluster  
  
  conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/ibm') 
  conn.debug = True

  ##enumerate volumes in cluster
  volumes = enumNames('IBMTSSVC_StorageVolume')

  ##get volume stats
  stats = conn.EnumerateInstances('IBMTSSVC_StorageVolumeStatistics')
  for stat in stats:
    ##parse property InstanceID = "StorageVolumeStats 46" to get volume ID
    statID = stat.properties['InstanceID'].value.split()[1] 
    vol_name = volumes[statID]
    ps = stat.properties
    
    timestamp = calendar.timegm(ps['StatisticTime'].value.datetime.timetuple())
    
    ## check cache and don't output same timestamp values
    cache_key = '%s.%s.%s' % (cluster, 'volume', vol_name)
    if (cache_key in cachedTimestamps) and (timestamp == cachedTimestamps[cache_key]):
      print >> sys.stderr, 'old timestamp: %s = %d' % (cache_key, timestamp)
      continue
      
    cachedTimestamps[cache_key] = timestamp
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'KBytesRead', 'volume', vol_name, timestamp, ps['KBytesRead'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'KBytesWritten', 'volume', vol_name, timestamp, ps['KBytesWritten'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'KBytesTransferred',  'volume', vol_name, timestamp, ps['KBytesTransferred'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'ReadIOs', 'volume', vol_name, timestamp, ps['ReadIOs'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'WriteIOs', 'volume', vol_name, timestamp, ps['WriteIOs'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'TotalIOs', 'volume', vol_name, timestamp, ps['TotalIOs'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'IOTimeCounter', 'volume', vol_name, timestamp, ps['IOTimeCounter'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'ReadIOTimeCounter', 'volume', vol_name, timestamp, ps['ReadIOTimeCounter'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'WriteIOTimeCounter', 'volume', vol_name, timestamp, ps['WriteIOTimeCounter'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'ReadHitIOs', 'volume', vol_name, timestamp, ps['ReadHitIOs'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'WriteHitIOs', 'volume', vol_name, timestamp, ps['WriteHitIOs'].value)


  ##now enumerate mdisks in cluster
  mdisks = enumNames('IBMTSSVC_BackendVolume')

  ##get mdisk stats
  stats = conn.EnumerateInstances('IBMTSSVC_BackendVolumeStatistics')
  for stat in stats:
    statID = stat.properties['InstanceID'].value.split()[1] 
    mdisk_name = mdisks[statID]
    ps = stat.properties
    
    timestamp = calendar.timegm(ps['StatisticTime'].value.datetime.timetuple())
      
    ## check cache and don't output same timestamp values
    cache_key = '%s.%s.%s' % (cluster, 'mdisk', mdisk_name)
    if (cache_key in cachedTimestamps) and (timestamp == cachedTimestamps[cache_key]):
      print >> sys.stderr, 'old timestamp: %s = %d' % (cache_key, timestamp)
      continue
      
    cachedTimestamps[cache_key] = timestamp
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'KBytesRead', 'mdisk', mdisk_name, timestamp, ps['KBytesRead'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'KBytesWritten', 'mdisk', mdisk_name, timestamp, ps['KBytesWritten'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'KBytesTransferred',  'mdisk', mdisk_name, timestamp, ps['KBytesTransferred'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'ReadIOs', 'mdisk', mdisk_name, timestamp, ps['ReadIOs'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'WriteIOs', 'mdisk', mdisk_name, timestamp, ps['WriteIOs'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'TotalIOs', 'mdisk', mdisk_name, timestamp, ps['TotalIOs'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'IOTimeCounter', 'mdisk', mdisk_name, timestamp, ps['IOTimeCounter'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'ReadIOTimeCounter', 'mdisk', mdisk_name, timestamp, ps['ReadIOTimeCounter'].value)
    print '%s svc.%s[%s,%s] %d %s' % (cluster, 'WriteIOTimeCounter', 'mdisk', mdisk_name, timestamp, ps['WriteIOTimeCounter'].value)

try:
  if 'none' != cachefile:
    cachedTimestamps = json.dump( cachedTimestamps, open(cachefile, 'w') )
except Exception, err:
  print >> sys.stderr, "Can't save cached timestamps:", str(err)

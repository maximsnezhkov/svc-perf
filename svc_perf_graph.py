#!/usr/bin/python
# -*- coding: utf-8 -*- # coding: utf-8
#
# IBM SVC/Storwize V7000 graph generation script for Zabbix.
# Generates pool performance summary graphs with Zabbix API.
# Graphs is named:
# "Pool - <pool name> - Volume IOPS"
# "Pool - <pool name> - Volume Throughput"
# "Pool - <pool name> - Volume IO Time"
# "Pool - <pool name> - MDisk IOPS"
# "Pool - <pool name> - MDisk Throughput"
# "Pool - <pool name> - MDisk IO Time"
#
# 2013 Matvey Marinin
#
# Usage: svc_perf_graph.py [--debug] --clusters <svc1>[,<svc2>...] --user <svc_username> --password <svc_pwd> --zabbix_url <http://zabbix.domain.com> --zabbix_user <username> --zabbix_password <password>
#
#   --debug = Enable debug output
#   --clusters = Comma-separated Storwize node list (DNS name/IP)
#   --user    = Storwize V7000 user account
#   --password = Storwize password
#   --zabbix_url = Zabbix API url in <http://zabbix.domain.com> format
#   --zabbix_user = Zabbix account with admin permissions to SVC nodes
#   --zabbix_password = Zabbix password
#
#
import pywbem
import getopt, sys
import itertools
from pyzabbix import ZabbixAPI

def usage():
  print >> sys.stderr, "Usage: svc_perf_graph.py [--debug] --clusters <svc1>[,<svc2>...] --user <svc_username> --password <svc_pwd> --zabbix_url <http://zabbix.domain.com> --zabbix_user <username> --zabbix_password <password>"

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "clusters=", "user=", "password=", "debug", "zabbix_url=", "zabbix_user=", "zabbix_password="])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err)
  usage()
  sys.exit(2)

debug = False
clusters = []
user = None
password = None
zabbix_url = None
zabbix_user = None
zabbix_password = None

for o, a in opts:
  if o == "--clusters" and not a.startswith('--'):
    clusters.extend( a.split(','))
  elif o == "--user" and not a.startswith('--'):
    user = a
  elif o == "--password" and not a.startswith('--'):
    password = a
  elif o == "--debug":
    debug = True
  elif o == "--zabbix_url" and not a.startswith('--'):
    zabbix_url = a
  elif o == "--zabbix_user" and not a.startswith('--'):
    zabbix_user = a
  elif o == "--zabbix_password" and not a.startswith('--'):
    zabbix_password = a
  elif o in ("-h", "--help"):
    usage()
    sys.exit()

def debug_print(message):
  if debug:
    print message


debug_print('clusters: %s' % clusters)

if not clusters:
  print >> sys.stderr, '--clusters option must be set'
  usage()
  sys.exit(2)

if not user or not password:
  print >> sys.stderr, '--user and --password options must be set'
  usage()
  sys.exit(2)

if not zabbix_url or not zabbix_user or not zabbix_password:
  print >> sys.stderr, '--zabbix_url, --zabbix_user and --zabbix_password options must be set'
  usage()
  sys.exit(2)

##############################################################
# Color table from lld_all_graph.pl
# https://www.zabbix.com/forum/showthread.php?t=26678
# 42 total items
# dark colors
COLORS = ( "5299AD", # blue1
           "5D549A", # violet
           "87B457", # green
           "CF545E", # red
           "CDDA13", # lemon
           "5DAE99", # turquise
           "DD844C", # orange
           "AE5C8A", # mauve
           "BD9F83", # ltbrown
           "6B9BD4", # blue2
           "B75F73", #red-brown
           "646560", # kaky
           "335098", # deepblue
           "5FBFDB", # bleu
           "D1CE85", # yellow
           "909090", # grey
           "A16254", # brown
           "E8678D", # pink
           "62B55A", # deepgreen
           "A599AD", # greypurple
           "6A5DD9", # violet2
           # light colors
           "98D6E7", # blue1
           "9E7EDF", # violet
           "BDDA83", # green
           "EF747E", # red
           "EDFA33", # lemon
           "7EC392", # tuquise
           "EDA46C", # orange
           "DF93D7", # mauve
           "E2BB91", # ltbrown
           "A0CBEA", # blue2
           "CB868B", # red-brown
           "77897D", # kaky
           "5370B8", #deepblue
           "76DAF7", # bleu
           "EAD770", # yellow
           "AEAEAE", # grey
           "B97A6F", # brown
           "E8849D", # pink
           "95D36E", # deepgreen
           "B7AACF", # greypurple
           "8A7DF9" # violet2
)
##############################################################

''' Graph layout type '''
GRAPH_LAYOUT_NORMAL = 0
GRAPH_LAYOUT_STACKED = 1
GRAPH_LAYOUT_PIE = 2
GRAPH_LAYOUT_EXPLODED = 3

VOLUME_GRAPHS = (
  {'name':'Volume IOPS', 'graphtype':GRAPH_LAYOUT_STACKED, 'items':['svc.TotalIORate[volume,%s]']},
  {'name':'Volume Throughput', 'graphtype':GRAPH_LAYOUT_STACKED, 'items':['svc.TotalRateKB[volume,%s]']},
  {'name':'Volume IO Time', 'graphtype':GRAPH_LAYOUT_NORMAL, 'items':['svc.ReadIOTime[volume,%s]', 'svc.WriteIOTime[volume,%s]']}
  )
MDISK_GRAPHS = (
  {'name':'MDisk IOPS', 'graphtype':GRAPH_LAYOUT_STACKED, 'items':['svc.TotalIORate[mdisk,%s]']},
  {'name':'MDisk Throughput', 'graphtype':GRAPH_LAYOUT_STACKED, 'items':['svc.TotalRateKB[mdisk,%s]']},
  {'name':'MDisk IO Time', 'graphtype':GRAPH_LAYOUT_NORMAL, 'items':['svc.ReadIOTime[mdisk,%s]', 'svc.WriteIOTime[mdisk,%s]']}
  )

## graph: graphid, name, height, width, graphtype, gitems[]
## graph_item: gitemid, color, itemid, drawtype + item_key

''' create or update graphs for pool '''
def updateGraphs(poolName, pool_elements, graph_templates, zabbix, zabbix_items):
  ''' pool_elements - list of (volume/mdisk_id, name) tuples for use in item_keys. It may be None, if pool has no volumes/mdisks
      graph_templates - one of VOLUME_GRAPHS/MDISK_GRAPHS
      zabbix - instance of ZabbixAPI
      zabbix_items - dict: item_key -> (itemid, item_name)
  '''
  
  ''' sort volumes/mdisks by name '''
  if pool_elements: 
    pool_elements = sorted(pool_elements, key=lambda id_name_tuple: id_name_tuple[1])
    
  for graph_template in graph_templates:
    graph_name = 'Pool - %s - %s' % (poolName, graph_template['name'])
    gitems = []
    gitem_sortorder = 0
    colors = itertools.cycle(COLORS)
    if pool_elements: # if pool has any volumes/mdisks
      for (object_id, object_name) in pool_elements:
        for item_template in graph_template['items']:
          item_key = item_template % object_id
          if item_key in zabbix_items:
            item_id, item_name = zabbix_items[item_key]
            if item_id and item_name:
              gitems.append( dict(color=colors.next(), itemid=item_id, sortorder=gitem_sortorder))
              gitem_sortorder = gitem_sortorder + 1
    graph = dict(name=graph_name, height=200, width=900, graphtype=graph_template['graphtype'], gitems=gitems)

    ## update Zabbix
    result = zabbix.graph.get(filter={'name':graph_name}, output='graphid')
    if len(result)>0:
      ### existing graph found
      graph['graphid'] = result[0].get('graphid')
      if graph['gitems']:
        debug_print('Updating graph %s' % graph_name)
        zabbix.graph.update(graph)         
      else:
        debug_print('Removing empty graph %s' % graph_name)
        zabbix.graph.delete(graph)
    else:
      if graph['gitems']:
        debug_print('Creating graph %s' % graph_name)
        zabbix.graph.create(graph)
            

#####################################################################################################
# main 
#####################################################################################################

## connect to Zabbix API ##
zabbix = ZabbixAPI(zabbix_url)
zabbix.login(zabbix_user, zabbix_password)
debug_print('Connected to Zabbix API Version %s' % zabbix.api_version())

for cluster in clusters:
  zabbix_items = {} # item_key -> (itemid, item_name)
  
  debug_print('Searching zabbix items of host %s' % cluster)
  items = zabbix.item.getObjects(host=cluster)
  if not items:
    print 'WARNING: ZabbixAPI.item.getObjects(host=%s) returned empty list. Check zabbix user permissions' % cluster
         
  for i in items:
    if ('key_' in i) and ('itemid' in i) and ('name' in i):
      zabbix_items[ i['key_'] ] = ( i['itemid'], i['name'] )
  items = None

    
  ''' connect to Storwize CIM provider '''
  conn = pywbem.WBEMConnection('https://'+cluster, (user, password), 'root/ibm') 
  conn.debug = True

  def getStorageObjects(wbemConnection, wbemClass):
    ''' @return array pool_volumes["pool1"] = [ (volume_id1, volume_name1) , (volume_id2, volume_name2), ...] '''
    storage_objects = {}
    for obj in wbemConnection.ExecQuery('WQL', 'select DeviceID, ElementName, PoolName from %s' % wbemClass):
      device_id = obj.properties['DeviceID'].value
      element_name = obj.properties['ElementName'].value
      pool_name = obj.properties['PoolName'].value
      if device_id and pool_name and element_name:
        if pool_name in storage_objects:
          storage_objects[pool_name].append((device_id, element_name))
        else:
          storage_objects[pool_name] = [(device_id, element_name)]
    return storage_objects

  pool_volumes = getStorageObjects(conn, 'IBMTSSVC_StorageVolume')
  pool_mdisks = getStorageObjects(conn, 'IBMTSSVC_BackendVolume')

  for p in conn.ExecQuery('WQL', 'select Caption from IBMTSSVC_ConcreteStoragePool'):
    pool = p.properties['Caption'].value
    if pool:
      updateGraphs(pool, pool_volumes.get(pool), VOLUME_GRAPHS, zabbix, zabbix_items)
      updateGraphs(pool, pool_mdisks.get(pool), MDISK_GRAPHS, zabbix, zabbix_items)


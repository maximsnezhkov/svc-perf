#!/usr/bin/python
# -*- coding: utf-8 -*- # coding: utf-8
#
# Storwize Unified health monitoring script
# Uses GUI XML API
#
# Zabbix items:
#   custom.svc.unified.status.fileServices
#   custom.svc.unified.status.clusterConfig
#   custom.svc.unified.status.network
#   custom.svc.unified.status.unknown
#   custom.svc.unified.status.clusterManagement
#   custom.svc.unified.status.hardware
#   custom.svc.unified.status.fileSystem
#   custom.svc.unified.status.performance
#   custom.svc.unified.status.storageConnection
#   custom.svc.unified.status.nodeState
#   custom.svc.status.externalStorage
#   custom.svc.status.internalStorage
#   custom.svc.status.remotePartnerships
#
# Item values: Normal(0),  Degraded(1),  Error(2);
#
#
# Requirements:
#  requests, zbxsend
#
######################################################################################################
import getopt, sys, logging, pprint, datetime
import requests, json
from zbxsend import Metric, send_to_zabbix

SVC_CONN_STATUS_TMPL='custom.svc.status.%s'
UNIFIED_CONN_STATUS_TMPL='custom.svc.unified.status.%s'

def usage():
  print >> sys.stderr, "Usage: svc_mon2.py [--debug] --svc <Storwize name|IP> [--unified] --user <username> --password <pwd> [--host <Storwize host in Zabbix=svc>]"

def debug_print(message):
  if debug:
    print >> sys.stderr, message

try:
  opts, args = getopt.gnu_getopt(sys.argv[1:], "-h", ["help", "svc=", "unified", "user=", "password=", "host", "debug"])
except getopt.GetoptError, err:
  print >> sys.stderr, str(err)
  usage()
  sys.exit(2)

debug = False
svc = None
unified = False
user = None
password = None
host = None
for o, a in opts:
  if o == "--svc" and not a.startswith('--'):
    svc = a
  elif o == "--unified":
    unified = True
  elif o == "--user" and not a.startswith('--'):
    user = a
  elif o == "--password" and not a.startswith('--'):
    password = a
  elif o == "--host" and not a.startswith('--'):
    host = a
  elif o == "--debug":
    debug = True
  elif o in ("-h", "--help"):
    usage()
    sys.exit()

if not svc:
  print >> sys.stderr, '--svc option must be set'
  usage()
  sys.exit(2)

if not user or not password:
  print >> sys.stderr, '--user and --password options must be set'
  usage()
  sys.exit(2)

#default zabbix host object name = svc name
host = host or svc
  
######################################################################################################

# build API url
if unified:
  svc_url = 'https://%s:1081' % svc
else:
  svc_url = 'https://%s' % svc
debug_print('Connecting to '+svc_url)

# use shared session with auth cookies
s = requests.Session()

# authenticate user
r = s.post(svc_url+'/login', params={'login': user, 'password': password, 'tzoffset': '-240'}, verify=False)
if debug:
  print "Auth request status: ", r.status_code
  
# check authentication response for errors
r.raise_for_status()


# prepare JSON-RPC to "public static com.ibm.evo.events.PollingManager.PollResponse poll(long lastEventId, boolean blocking, long pid)"
rpc_request = {}
if unified:
  #{"clazz":"com.ibm.ifs.gui.rpc.IfsRPCRequest","methodClazz":"com.ibm.evo.events.PollingManager","methodName":"poll","methodArgs":[0,false,0]}
  rpc_request['clazz'] = 'com.ibm.ifs.gui.rpc.IfsRPCRequest'
else:
  #{"clazz":"com.ibm.evo.rpc.RPCRequest","methodClazz":"com.ibm.evo.events.PollingManager","methodName":"poll","methodArgs":[0,false,0]}
  rpc_request['clazz'] = 'com.ibm.evo.rpc.RPCRequest'

rpc_request['methodClazz'] = 'com.ibm.evo.events.PollingManager'
rpc_request['methodName'] = 'poll'
rpc_request['methodArgs'] = (1, False, 0) #lastEventId=1 to get all fresh events every time

# get Storwize status  
r = s.post(svc_url+'/RPCAdapter', headers={'content-type': 'application/json'}, data=json.dumps(rpc_request), verify=False)
  
if debug:
  #print r.request.headers
  #print r.headers
  #pprint.pprint(r.cookies)
  #print r.text
  print "RPC request status: ", r.status_code
  
# check rpc response for errors
r.raise_for_status()

# parse JSON-RPC response into JSON object tree
try:
  #fix non-standard "\<newline>" escapes in JSON-RPC response
  json_text = r.text.replace(u'\\\n',u'')
  
  json_data = json.loads(json_text)

  #if debug:
    #print json.dumps(json_data, sort_keys = True, indent = 4).decode('utf-8')
    
except ValueError as e:
  print >> sys.stderr, 'ERROR: ValueError raised on JSON parsing: %s' % e
  print >> sys.stderr, json_text
  exit(1)

'''
Storwize Unified poll response:
{
    "clazz": "com.ibm.evo.rpc.RPCResponse", 
    "messages": null, 
    "result": {
        "clazz": "com.ibm.evo.events.PollResponse", 
        "events": [
            {
                "arguments": [
                    "12402640704823473333"
                ], 
                "clazz": "com.ibm.sonas.gui.events.pods.ConnectionStatusEvent", 
                "id": 359877, 
                "items": {
                    "clusterConfig": "1", 
                    "clusterManagement": "0", 
                    "fileServices": "0", 
                    "fileSystem": "0", 
                    "hardware": "0", 
                    "network": "0", 
                    "nodeState": "0", 
                    "performance": "0", 
                    "storageConnection": "0", 
                    "unknown": "0"
                }, 
                "timestamp": 1409662691741, 
                "topic": "CONNECTION_STATUS"
            }, 
            {
                "arguments": null, 
                "clazz": "com.ibm.evo.events.ResourceEvent",
                ...
            }...
}

Storwize block module poll response:
{
    "clazz": "com.ibm.evo.rpc.RPCResponse", 
    "messages": null, 
    "result": {
        "clazz": "com.ibm.evo.events.PollResponse", 
        "events": [
            {
                "arguments": null, 
                "ccuInProgress": false, 
                "clazz": "com.ibm.svc.gui.events.ConnectionStatusEvent", 
                "externalStorage": "0", 
                "id": 4202319, 
                "internalStorage": "0", 
                "remotePartnerships": "0", 
                "timestamp": 1409819425770, 
                "topic": "CONNECTION_STATUS", 
                "trials": "0"
            },
            {}...
}
'''
#parse RPCResponse
if json_data.get('clazz') != 'com.ibm.evo.rpc.RPCResponse':
  print >> sys.stderr, 'ERROR: Unexpected class "%s" in RPC response' % json_data.get('clazz')
  print >> sys.stderr, json.dumps(json_data, sort_keys = True, indent = 4).decode('utf-8')
  exit(1)

if not json_data.get('result'):
  print >> sys.stderr, "ERROR: RPC returned no result"
  if json_data.get('messages'): print >> sys.stderr, json_data.get('messages')
  exit(1)

#parse PollResponse  
if json_data['result'].get('clazz') != 'com.ibm.evo.events.PollResponse':
  print >> sys.stderr, 'ERROR: Unexpected class "%s" in RPC response' % json_data['result'].get('clazz')
  print >> sys.stderr, json.dumps(json_data, sort_keys = True, indent = 4).decode('utf-8')
  exit(1)

zabbix_metrics = []
events = json_data['result']['events']
for e in events:
  
  #Storwize Unified cluster status
  if e.get('clazz') == 'com.ibm.sonas.gui.events.pods.ConnectionStatusEvent':
    timestamp = float(e['timestamp'])/1000
    debug_print('%s %s %s' % (e.get('clazz'), e.get('id'), str(datetime.datetime.fromtimestamp(timestamp)) ) )
    for i in e['items'].keys():
      zabbix_item_key = UNIFIED_CONN_STATUS_TMPL % i
      zabbix_item_value = e['items'][i]
      #debug_print('host=%s, key=%s, value=%s, timestamp=%s' % (host, zabbix_item_key, zabbix_item_value, str(datetime.datetime.fromtimestamp(timestamp))))
      zabbix_metrics.append( Metric(host, zabbix_item_key, zabbix_item_value, timestamp))

  #Storwize block cluster status
  if e.get('clazz') == 'com.ibm.svc.gui.events.ConnectionStatusEvent':
    timestamp = float(e['timestamp'])/1000
    debug_print('%s %s %s' % (e.get('clazz'), e.get('id'), str(datetime.datetime.fromtimestamp(timestamp)) ) )
    for i in ['externalStorage', 'internalStorage', 'remotePartnerships']:
      zabbix_item_key = SVC_CONN_STATUS_TMPL % i
      zabbix_item_value = e[i]
      #debug_print('host=%s, key=%s, value=%s, timestamp=%s' % (host, zabbix_item_key, zabbix_item_value, str(datetime.datetime.fromtimestamp(timestamp))))
      zabbix_metrics.append( Metric(host, zabbix_item_key, zabbix_item_value, timestamp))

if debug:
  for m in zabbix_metrics:
    print str(m)

#send data to zabbix with zbxsend module
if len(zabbix_metrics):
  if debug:
    logging.basicConfig(level=logging.INFO)
  else:
    logging.basicConfig(level=logging.WARNING)
  send_to_zabbix(zabbix_metrics, 'localhost', 10051)


  

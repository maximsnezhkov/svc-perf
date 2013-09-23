#!/bin/bash
#
# IBM SVC/Storwize V7000 health status monitor
#
# 2013 Matvey Marinin
#
# Returns number of Storwize alerts or an empty string
#
# Parameters:
#   $1 = Storwize DNS name/IP
#
# Usage:
#   create external check item with key svc_status.sh["{HOST.CONN}"]
#
# For testing purposes script must be run as zabbix user:
#   sudo -u zabbix /etc/zabbix/externalscripts/svc_status.sh dev-svc1
#
# Key-based SSH access to Storwize CLI needs to be configured for zabbix user (see /var/lib/zabbix/.ssh)
#
set -e

SVC_STATUS_AWK=/etc/zabbix/externalscripts/svc_status.awk
ssh -q -o PasswordAuthentication=no $1 lseventlog -expired no -fixed no -monitoring no -message no -order severity | awk -f "$SVC_STATUS_AWK" | wc -l

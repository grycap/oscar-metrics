#!/bin/bash
cluster_auth='{"cluster_id":"'"${CLUSTER_ID}"'","endpoint":"'"${ENDPOINT}"'","user":"'"${USER}"'","password":"'"${PASSW}"'","ssl":"True"}'
python3 prometheus_metric_parser.py $PROMETHEUS_ENDPOINT $VO $cluster_auth
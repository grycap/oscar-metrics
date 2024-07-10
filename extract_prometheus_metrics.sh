#!/bin/bash
cluster_auth='{"cluster_id":'"${CLUSTER_ID}"',"endpoint":'"${ENDPOINT}"',"user":'"${USER}"',"password":'"${PASSW}"',"ssl":"True"}'
python3 metrics_prom.py $ENDPOINT $VO $cluster_auth
aws s3 cp --recursive metrics/prometheus-metrics-* s3://metrics.oscar.grycap.net/"${CLUSTER_ID}/prometheus_csv"
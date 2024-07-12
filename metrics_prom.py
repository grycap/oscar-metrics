from datetime import date
import time
import requests
import json
import csv
import argparse
from oscar_python.client import Client

QUERY_ENDPOINT = "/api/v1/query?query="
TIME = "5d"

parser = argparse.ArgumentParser(description="Command-line to retreive Prometheus metrics from OSCAR", formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument("PROMETHEUS_ENDPOINT", action="store", help="Prometheus endpoint")
parser.add_argument("VO", help="VO from which get the metrics")
parser.add_argument("OSCAR_AUTH", help="JSON string with the OSCAR cluster authentication info (BasicAuth/oidc-token)")
parser.add_argument("-t", "--time", dest=TIME, help="")

args = parser.parse_args()

PROMETHEUS_ENDPOINT = args.PROMETHEUS_ENDPOINT
VO = args.VO
OSCAR_CLUSTER_AUTH = args.OSCAR_AUTH

PROMETHEUS_ENDPOINT = PROMETHEUS_ENDPOINT+QUERY_ENDPOINT

try:
    OSCAR_CLUSTER_AUTH = json.loads(OSCAR_CLUSTER_AUTH)
except TypeError: 
    print("Error parsing OSCAR cluster authentication!")
    exit(0)

def get_sync_query(svc_name):
    return "sum(rate(container_cpu_usage_seconds_total{pod=~'"+svc_name+".*', container='oscar-container'}["+TIME+"]))"

def get_exposed_query(svc_name):
    return "sum(rate(container_cpu_usage_seconds_total{pod=~'"+svc_name+".*', container='"+svc_name+"'}["+TIME+"]))"

def get_async_query():
    return "sum by (pod) (rate(container_cpu_usage_seconds_total{namespace='oscar-svc'}["+TIME+"])) * on (pod) group_left () kube_pod_status_phase{phase='Succeeded'}"

def get_cluster_services(oscar_client):
    cluster_services_response = oscar_client.list_services()
    return json.loads(cluster_services_response.text)

def has_jobs(svc_name):
    res = oscar_client.list_jobs(svc_name)
    if json.loads(res.text) == {}:
        return False, None
    return True, json.loads(res.text)

def query(cpu_usage_query):
    send_url=PROMETHEUS_ENDPOINT+cpu_usage_query
    response = requests.request("GET", send_url)
    return json.loads(response.text)
    
def generate_file_name():
    return f"/app/metrics/prometheus-metrics/metric-{str(int(time.time()))}.csv"

def extract_metrics(cluster_services):
    with open(generate_file_name(), 'w', newline='') as file:
        writer = csv.writer(file)
        fields = ["service_name", "pod_name", "cpu_usage_seconds", "vo"]
        writer.writerow(fields)

        for svc in cluster_services:
            svc_vo = svc["vo"]
            svc_name = svc["name"]
            if svc_vo!="" and svc_vo == VO:

                result = {}
                jobs, job_list = has_jobs(svc_name)
                if jobs and job_list is not None:
                    cpu_usage_query = get_async_query()
                    result = query(cpu_usage_query)
                    metrics = result["data"]["result"]
                    for (k,v) in job_list.items():
                        if len(metrics) > 0:
                            for m in metrics:
                                pod_name = m["metric"]["pod"]
                                if k in pod_name:
                                    value = m["value"][1]
                                    writer.writerow([svc_name,pod_name, value, svc_vo])
                else:
                    if "expose" in svc_name:
                        cpu_usage_query = get_exposed_query(svc_name)
                    else:
                        cpu_usage_query = get_sync_query(svc_name)
                    result = query(cpu_usage_query)
                    metrics = result["data"]["result"]
                    if len(metrics) > 0:
                        for m in metrics:
                            #pod_name =  m["metric"]["pod"]
                            value = m["value"][1]
                            writer.writerow([svc_name,svc_name, value, svc_vo])

######## MAIN ##########                       
if __name__ == "__main__":
    print("[*] Getting metrics from Prometheus DB")
    try:
        oscar_client = Client(OSCAR_CLUSTER_AUTH)
    except:
        print("Error creating OSCAR client")
        exit(0)

    cluster_services = get_cluster_services(oscar_client)
    extract_metrics(cluster_services)
    print("Success!")

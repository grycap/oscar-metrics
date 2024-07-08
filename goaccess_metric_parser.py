
from posixpath import split
import argparse
import csv
import json
import time
import os

CREATE_PATH = "/system/services"
RUN_PATH = "/run"
JOB_PATH = "/job"

TIMESTAMP = str(int(time.time()))

OUTPUT_PATH = "/app/metrics"

parser = argparse.ArgumentParser(description="Command-line to retreive Prometheus metrics from OSCAR", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-f", "--file_path", type=str, help="Logfile path/name")
parser.add_argument("-g", "--general", action="store_true", help="Complete logfile")
parser.add_argument("-u", "--use_existing", action="store_true", required=False, help="Use existing output file")
parser.add_argument("-p", "--partial", action="store_true", help="Filtered by status code logfile")
parser.add_argument("status_code", type=int, help="Complete logfile")


args = parser.parse_args()

with open(args.file_path, 'r') as rawfile:
    metrics = json.loads(rawfile.read())
    START_DATE = metrics["general"]["start_date"]
    END_DATE = metrics["general"]["end_date"]

"""
 > Countries reached 
 > Output format: {continent, country, total_visits, unique_visits, start_date, end_date}
"""
def parse_geolocation_info():

    with open(f'{OUTPUT_PATH}/{TIMESTAMP}_geolocation_metrics.csv', 'w', newline='') as gfile:
        writer = csv.writer(gfile)
        fields = ["continent", "country", "total_visits", "unique_visits", "start_metric_date", "end_metric_date"]
        writer.writerow(fields)

        geolocation = metrics["geolocation"]["data"]

        for d in geolocation:
            continent = d["data"]
            for item in d["items"]:
                writer.writerow([continent, item["data"], item["hits"]["count"] ,item["visitors"]["count"], START_DATE, END_DATE])
    
        gfile.close()
    
""" 
 > Number of AI applications (created services -> POST requests to /system/services)
 > Output format: {num_created, start_date, end_date}

 > Processed inference executions (POST requests to /run or /job)
 > Output format: {service, executions, type, successfull, failed, start_date, end_date}
"""

def parse_requests_info(status_code, write_type):

    inference = dict()
    requests = metrics["requests"]["data"]
    create_count = 0
    exec_count = 0
    
    for r in requests:
        if r["method"] == "POST":
            path = r["data"]
            if path == CREATE_PATH:
                create_count+=1
            elif RUN_PATH in path or JOB_PATH in path:
                sum_requests = r["hits"]["count"]
                split_path = split(path)
                service = split_path[1]
                if service in inference.keys():
                    inference[service].append({"exec_type": split_path[0], "status_code": status_code, "count": sum_requests})
                else:
                    inference[service] = [{"exec_type": split_path[0], "status_code": status_code, "count": sum_requests}]
                exec_count+=sum_requests

    if create_count != 0:
        with open(f'{OUTPUT_PATH}/{TIMESTAMP}_created_apps_metrics.csv', write_type, newline='') as cfile:
            writer = csv.writer(cfile)
            if write_type == "w": writer.writerow(["application_count", "status_code", "start_metric_date", "end_metric_date"])
            writer.writerow([create_count, status_code, START_DATE, END_DATE])

            cfile.close()

    if exec_count != 0:
       with open(f'{OUTPUT_PATH}/{TIMESTAMP}_total_inference_metrics.csv', write_type, newline='') as efile:
            writer = csv.writer(efile)
            if write_type == "w": writer.writerow(["inference_count", "status_code", "start_metric_date", "end_metric_date"])
            writer.writerow([exec_count, status_code, START_DATE, END_DATE])
            
            efile.close()

       with open(f'{OUTPUT_PATH}/{TIMESTAMP}_services_inference_metrics.csv', write_type, newline='') as sfile:
            writer = csv.writer(sfile)
            if write_type == "w": writer.writerow(["service_name", "exec_type", "status_code", "inference_count" , "start_metric_date", "end_metric_date"])
            for k in inference.keys():
                for item in inference[k]:
                    writer.writerow([k, item["exec_type"], item["status_code"], item["count"], START_DATE, END_DATE])
                
            sfile.close()        


if args.general:
    parse_geolocation_info()
elif args.partial:
    if args.use_existing:
        parse_requests_info(args.status_code, "a")
    else:
        parse_requests_info(args.status_code, "w")








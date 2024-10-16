
from posixpath import split
import argparse
import csv
import json
import time
import os
import re

CREATE_PATH = "/system/services"
RUN_PATH = "/run"
JOB_PATH = "/job"

TIMESTAMP = str(int(time.time()))

OUTPUT_PATH = "/app/metrics/goaccess-metrics"

parser = argparse.ArgumentParser(description="Command-line to retreive Prometheus metrics from OSCAR", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-f", "--file_path", type=str, help="Logfile path/name")
parser.add_argument("-g", "--general", action="store_true", help="Complete logfile")
parser.add_argument("-u", "--use_existing", action="store_true", required=False, help="Use existing output file")
parser.add_argument("-p", "--partial", action="store_true", help="Filtered by status code logfile")
parser.add_argument("-c", "--create", action="store_true", help="Using as input created services log format file")
parser.add_argument("status_code", type=int, help="Complete logfile")


args = parser.parse_args()

"""
 > Countries reached 
 > Output format: {continent, country, total_visits, unique_visits, start_date, end_date}
"""
def parse_geolocation_info(write_type):
    with open(f'{OUTPUT_PATH}/geolocation_metrics.csv', write_type, newline='') as gfile:
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

def parse_inference_info(status_code, write_type):

    inference = dict()
    requests = metrics["requests"]["data"]
    exec_count = 0
    
    for r in requests:
        if r["method"] == "POST":
            path = r["data"]
            if RUN_PATH in path or JOB_PATH in path:
                sum_requests = r["hits"]["count"]
                split_path = split(path)
                service = split_path[1]
                if service in inference.keys():
                    inference[service].append({"exec_type": split_path[0], "status_code": status_code, "count": sum_requests})
                else:
                    inference[service] = [{"exec_type": split_path[0], "status_code": status_code, "count": sum_requests}]
                exec_count+=sum_requests

    if exec_count != 0:
       with open(f'{OUTPUT_PATH}/total_inference_metrics.csv', write_type, newline='') as efile:
            writer = csv.writer(efile)
            if write_type == "w": writer.writerow(["inference_count", "status_code", "start_metric_date", "end_metric_date"])
            writer.writerow([exec_count, status_code, START_DATE, END_DATE])
            
            efile.close()

       with open(f'{OUTPUT_PATH}/services_inference_metrics.csv', write_type, newline='') as sfile:
            writer = csv.writer(sfile)
            if write_type == "w": writer.writerow(["service_name", "exec_type", "status_code", "inference_count" , "start_metric_date", "end_metric_date"])
            for k in inference.keys():
                for item in inference[k]:
                    writer.writerow([k, item["exec_type"], item["status_code"], item["count"], START_DATE, END_DATE])
                
            sfile.close()        

def parse_create_info(write_type):
    with open(args.file_path, 'r') as rawfile:
        for log in rawfile:
            match = re.match(r'\[CREATE-HANDLER\] (\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) (\w+) \| (\d{3}) \| (\/\S+) \| ([\w-]+) \| ([\w\d]+@[a-zA-Z]+\.[a-zA-Z]+)', log)
            if match:
                creation_time = match.group(1)
                service_name = match.group(5)
                owner_uid = match.group(6)
            with open(f'{OUTPUT_PATH}/created_services_info.csv', write_type, newline='') as cfile:
                if write_type == "w": writer.writerow(["service_name", "owner_uid", "creation_time"])
                writer.writerow([service_name, owner_uid, creation_time])
                cfile.close()
        rawfile.close()

wr="w"
if args.use_existing:
    wr="a"

if args.create:
    parse_create_info(wr)
else:
    with open(args.file_path, 'r') as rawfile:
        metrics = json.loads(rawfile.read())
        try:
            START_DATE = metrics["general"]["start_date"]
            END_DATE = metrics["general"]["end_date"]
        except:
            START_DATE = metrics["general"]["date_time"]
            END_DATE = metrics["general"]["date_time"]

if args.general:
    parse_geolocation_info(wr)
if args.partial:
    parse_inference_info(args.status_code, wr)
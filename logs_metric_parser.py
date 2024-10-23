
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

OUTPUT_PATH = "/app/metrics/logs-metrics"

parser = argparse.ArgumentParser(description="Command-line to retreive Prometheus metrics from OSCAR", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-f", "--file_path", type=str, help="Logfile path/name")
parser.add_argument("-g", "--geolocation", action="store_true", help="Using as input complete generated GoAccess json")
parser.add_argument("-u", "--use_existing", action="store_true", required=False, help="Use existing output file")
parser.add_argument("-i", "--inference", action="store_true", help="Using as input inference log format file")
parser.add_argument("-c", "--create", action="store_true", help="Using as input created services log format file")
parser.add_argument("-a", "--goaccess", action="store_true", help="Using as input generated GoAccess json filtered")
parser.add_argument("status_code", type=int, help="Complete logfile")


args = parser.parse_args()

if not args.create and not args.inference:
    with open(args.file_path, 'r') as rawfile:
        metrics = json.loads(rawfile.read())
        try:
            START_DATE = metrics["general"]["start_date"]
            END_DATE = metrics["general"]["end_date"]
        except:
            START_DATE = metrics["general"]["date_time"]
            END_DATE = metrics["general"]["date_time"]

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
 > Processed inference executions (POST requests to /run or /job)
 > Output format: {service_name, status_code, total_visits, unique_visits, start_date, end_date}
"""

def parse_inference_goaccess(status_code, write_type):
    requests = metrics["requests"]["data"]

    with open(f'{OUTPUT_PATH}/total_inference_metrics.csv', write_type, newline='') as efile:
        writer = csv.writer(efile)
        if write_type == "w": writer.writerow(["service_name", "status_code", "total_visits", "unique_visits", "start_metric_date", "end_metric_date"])
        for r in requests:
            path = r["data"]
            if RUN_PATH in path or JOB_PATH in path:
                total_visits = r["hits"]["count"]
                unique_visits = r["visitors"]["count"]
                split_path = split(path)
                service_name = split_path[1]

                writer.writerow([service_name, status_code, total_visits, unique_visits, START_DATE, END_DATE])

"""
 > Info about all inference executions
 > Output format: {service_name, exec_type, status_code, owner_uid, request_date, request_time}
"""
def parse_inference_log(write_type):
    with open(f'{OUTPUT_PATH}/services_inference_metrics.csv', write_type, newline='') as sfile:
        writer = csv.writer(sfile)
        if write_type == "w": writer.writerow(["service_name", "exec_type", "status_code", "owner_uid", "request_datetime"])
        with open(args.file_path, 'r') as rawfile:
            for log in rawfile:
                pattern = re.compile(
                    r'\[GIN-EXECUTIONS-LOGGER\]\s'  # Literal text "[GIN-EXECUTIONS-LOGGER]"
                    r'(?P<date>\d{4}/\d{2}/\d{2})\s-\s(?P<time>\d{2}:\d{2}:\d{2})\s\|\s+'  # Date and time
                    r'(?P<status>\d{3})\s+\|\s+'  # HTTP status code
                    r'(?P<latency>\S+)\s+\|\s+'  # Latency (can be in ms or s)
                    r'(?P<client_ip>\S+)\s+\|\s+'  # Client IP
                    r'(?P<method>[A-Z]+)\s+'  # HTTP method (e.g., POST)
                    r'(?P<path>\S+)\s+\|\s+'  # Request path
                    r'(?P<user>\S*)'  # User (can be empty)
                )
                match = pattern.search(log)
                if match:
                    path = match.group('path')
                    split_path = split(path)
                    exec_type = split_path[0]
                    service_name = split_path[1]

                    status_code = match.group('status')
                    request_date = match.group('date')
                    request_time = match.group('time')

                    request_datetime = request_date+" "+"request_time"
                    owner_uid = match.group('user')
                    writer.writerow([service_name, exec_type, status_code, owner_uid, request_datetime]) 

"""
 > Number of AI applications (created services -> POST requests to /system/services)
 > Output format: {service_name, owner_uid, creation_date, creation_time}
"""
def parse_create_log(write_type):
    with open(f'{OUTPUT_PATH}/created_services_info.csv', write_type, newline='') as cfile:
        writer = csv.writer(cfile)
        if write_type == "w": writer.writerow(["service_name", "owner_uid", "creation_datetime"])
        with open(args.file_path, 'r') as rawfile:
            for log in rawfile:
                pattern = re.compile(
                    r'\[CREATE-HANDLER\]\s'  # Skip the first part
                    r'(?P<date>\d{4}/\d{2}/\d{2})\s'  # Date (e.g., 2024/10/16)
                    r'(?P<time>\d{2}:\d{2}:\d{2})\s'  # Time (e.g., 10:41:49)
                    r'(?P<method>\w+)\s\|\s'  # HTTP method (e.g., POST)
                    r'(?P<status>\d{3})\s\|\s'  # Status code (e.g., 200)
                    r'(?P<path>\S+)\s\|\s'  # Request path (e.g., /system/services)
                    r'(?P<service_name>\S+)\s\|\s'  # Service name (e.g., cowsay-fsdg9)
                    r'(?P<user>\S+)'  # User identifier (e.g., <uid>@egi.eu)
                )
                match = pattern.search(log)
                if match:
                    creation_date = match.group('date')
                    creation_time = match.group('time')
                    creation_datetime = creation_date+" "+"creation_time"

                    service_name = match.group('service_name')
                    owner_uid = match.group('user')
                    writer.writerow([service_name, owner_uid, creation_date, creation_datetime])

wr="w"
if args.use_existing:
    wr="a"

if args.create:
    parse_create_log(wr)
if args.inference:
    parse_inference_log(wr)
if args.geolocation:
    parse_geolocation_info(wr)
if args.goaccess:
    parse_inference_goaccess(args.status_code, wr)
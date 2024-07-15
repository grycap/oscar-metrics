# Container paths
OUTPUTS_PATH="/app/metrics/rawmetrics"
FILTERED_PATH="$OUTPUTS_PATH/filtered_by_status_code"
OUTPUT_FILE="output"

# Path to the readonly volume with the cluster's ingress logs
CLUSTER_LOGS_DIR="/var/log/clusterlogs"
LOCAL_LOGS_DIR="/var/log/ingresslogs"
OSCAR_LOGS_DIR="$LOCAL_LOGS_DIR/oscar"

FULL_REPORT_FILE="$OSCAR_LOGS_DIR/oscar.log"
mkdir -p $OSCAR_LOGS_DIR

# Log format for goaccess
LOG_FORMAT='%^ %^ %^ %h - - [%d:%t] %~ %m %U %^ %s %b %R %u %^'

metrics(){
    oscar_logfile="oscar_execlog_"
    ingress_logfile=$1
    metric_date=$(echo $ingress_logfile | awk -F. '{print $3}')

    if [ -z $metric_date ]; then
        metric_date="current_"$(date +"%s")
    fi

    # Filter the ingress logs to get the OSCAR ones
    oscar_logfile=$oscar_logfile$metric_date.log
    cat $ingress_logfile | grep -a 'oscar-oscar' | grep -a '/job\|/run' > $OSCAR_LOGS_DIR/$oscar_logfile
    # Ensure the filtered log file is created and not empty 
    if [ ! -f "$OSCAR_LOGS_DIR/$oscar_logfile" ] || [ ! -s "$OSCAR_LOGS_DIR/$oscar_logfile" ]; then
        echo "[*] Warning: Failed to create log file or no OSCAR execution logs found for $OSCAR_LOGS_DIR/$oscar_logfile"
        return
    fi

    cat $OSCAR_LOGS_DIR/$oscar_logfile | tee -a $FULL_REPORT_FILE >/dev/null

    geo_err=$( { cat "$OSCAR_LOGS_DIR/$oscar_logfile" | goaccess - --log-format="${LOG_FORMAT}" -o "${OUTPUTS_PATH}/${OUTPUT_FILE}_${oscar_logfile}.json" --json-pretty-print; } 2>&1 )
    if [ ! -f "${OUTPUTS_PATH}/${OUTPUT_FILE}_${oscar_logfile}.json" ]; then
        echo "[*] Warning: Couldn't process file $oscar_logfile"
    else
        python3 goaccess_metric_parser.py -f "${OUTPUTS_PATH}/${OUTPUT_FILE}_${oscar_logfile}.json" -g 0
    fi

    status_codes=('200' '204' '404' '500')
    init="t"

    out="${FILTERED_PATH}/${OUTPUT_FILE}_${oscar_logfile}"

    for code in "${status_codes[@]}"; do
    code_logs=$(cat $OSCAR_LOGS_DIR/$oscar_logfile | grep -e 'HTTP/[0-9].[0-9]" '${code}' ')
    if [ ! -z "$code_logs" ]; then
        app_err=$( { cat $OSCAR_LOGS_DIR/$oscar_logfile | grep -e 'HTTP/[0-9].[0-9]" '${code}' ' | goaccess - -o  "${out}_f${code}.json" --json-pretty-print --log-format="${LOG_FORMAT}" --enable-panel=REQUESTS --enable-panel=STATUS_CODES; } 2>&1 )
        if [ ! -f "${out}_f${code}.json" ]; then
            echo "[*] Warning: Couldn't process file $oscar_logfile for status code '$code'"
        else
            if [ $init == 't' ]; then
                python3 goaccess_metric_parser.py -f "${out}_f${code}.json" -p $code
                init="f"
            else
            python3 goaccess_metric_parser.py -f "${out}_f${code}.json" -p $code -u
            fi
        fi
    fi
    done
}

for log in "$CLUSTER_LOGS_DIR"/*;
do
    if [[ $log == *"ingress"* ]]; then
        cp -r $log $LOCAL_LOGS_DIR
        # remove total path
        log=$(echo $log | sed 's/\/var\/log\/clusterlogs\///')
        for logfile in "$LOCAL_LOGS_DIR/$log/controller/"*;
        do
            if [[ $logfile == *".gz" ]]; then
                # upload a backup of the ingress logs to s3
                aws s3 cp $logfile s3://metrics.oscar.grycap.net/"${CLUSTER_ID}"/ingresslogs
                # unzip all log files
                gzip -d $logfile
            fi
        done
        break
    fi
done

for logfile in "$LOCAL_LOGS_DIR/$log/controller/"*;
do
    if [[ $logfile == *".log"* ]]; then
    metrics $logfile
    fi
done

# Generate the html file
if [ ! -f "${FULL_REPORT_FILE}" ] || [ ! -s "${FULL_REPORT_FILE}" ]; then
    echo "Error: Failed to create html report."
    exit 1
fi
goaccess "${FULL_REPORT_FILE}" --log-format="${LOG_FORMAT}" -o "/app/metrics/dashboard.html"
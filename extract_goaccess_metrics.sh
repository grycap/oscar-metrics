# Container paths
OUTPUTS_PATH="/app/metrics/rawmetrics"
FILTERED_PATH="$OUTPUTS_PATH/filtered_by_status_code"
OUTPUT_FILE="output_OSCAR_goaccess"
# Path to the readonly volume with the cluster's ingress logs
CLUSTER_LOGS_DIR="/var/log/clusterlogs"
LOCAL_LOGS_DIR="/var/log/ingresslogs"
OSCAR_LOGS_DIR="$LOCAL_LOGS_DIR/oscar"

HISTORY_LOGS="$OSCAR_LOGS_DIR/oscar.log"
LATEST_LOGS="$OSCAR_LOGS_DIR/latest_oscar.log"
mkdir -p $OSCAR_LOGS_DIR

# Log format for goaccess
LOG_FORMAT='%^ %^ %^ %^ [%^] %d - %t | %s | %Ts | %h | %m %~ %U | %u'

addLog(){
    ingress_logfile=$1
    cat $ingress_logfile | grep GIN-EXECUTIONS-LOGGER | grep -a '/job\|/run' | tee -a $HISTORY_LOGS >/dev/null
}

metrics(){
    LOG_FILE=$1
    filename=`basename "$LOG_FILE"`
    geo_err=$( { goaccess "${LOG_FILE}" --log-format="${LOG_FORMAT}" -o "${OUTPUTS_PATH}/${filename}_full.json" --json-pretty-print; } 2>&1 )
    if [[ $filename == "latest"* ]]; then
        python3 goaccess_metric_parser.py -f "${OUTPUTS_PATH}/${filename}_full.json" -g 0
    else
        python3 goaccess_metric_parser.py -f "${OUTPUTS_PATH}/${filename}_full.json" -g 0 -u
    fi
    
    status_codes=('200' '204' '404' '500')
    init="t"

    out="${FILTERED_PATH}/${filename}"

    for code in "${status_codes[@]}"; do
    code_logs=$(cat $LOG_FILE| grep -e 'HTTP/[0-9].[0-9]" '${code}' ')
    if [ ! -z "$code_logs" ]; then
        app_err=$( { cat $LOG_FILE | grep -e 'HTTP/[0-9].[0-9]" '${code}' ' | goaccess - -o  "${out}_f${code}.json" --json-pretty-print --log-format="${LOG_FORMAT}"; } 2>&1 )
        if [ ! -f "${out}_f${code}.json" ]; then
            echo "[*] Warning: Couldn't process file $LOG_FILE for status code '$code'"
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
    if [[ $log == *"oscar_oscar"* ]]; then
        cp -r $log $LOCAL_LOGS_DIR
        # remove total path
        log=$(echo $log | sed 's/\/var\/log\/clusterlogs\///')
        for logfile in "$LOCAL_LOGS_DIR/$log/oscar/"*;
        do
            if [[ $logfile == *".gz" ]]; then
                # upload a backup of the ingress logs to s3
                aws s3 cp $logfile s3://metrics.oscar.grycap.net/"${CLUSTER_ID}"/ingresslogs/
                # unzip all log files
                gzip -d $logfile
            fi
        done
        break
    fi
done

for logfile in "$LOCAL_LOGS_DIR/$log/oscar/"*;
do
    if [[ $logfile == *".log"* ]]; then
        if [[ $logfile == *".log" ]]; then
            aws s3 cp $logfile s3://metrics.oscar.grycap.net/"${CLUSTER_ID}"/ingresslogs/
            cat $logfile | grep GIN-EXECUTIONS-LOGGER | grep -a '/job\|/run' | tee -a $LATEST_LOGS >/dev/null
            metrics $LATEST_LOGS
        else
            addLog $logfile
        fi
    fi
done

# Generate the html file
if [ ! -f "${HISTORY_LOGS}" ] || [ ! -s "${HISTORY_LOGS}" ]; then
    goaccess "${LATEST_LOGS}" --log-format="${LOG_FORMAT}" -o "/app/metrics/dashboard.html"
else
    metrics $HISTORY_LOGS

    cat $LATEST_LOGS | tee -a $HISTORY_LOGS >/dev/null
    goaccess "${HISTORY_LOGS}" --log-format="${LOG_FORMAT}" -o "/app/metrics/dashboard.html"
fi

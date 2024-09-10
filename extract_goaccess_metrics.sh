# Container paths
OUTPUTS_PATH="/app/metrics/rawmetrics"
FILTERED_PATH="$OUTPUTS_PATH/filtered_by_status_code"
OUTPUT_FILE="output_OSCAR_goaccess"
# Path to the readonly volume with the cluster's ingress logs
CLUSTER_LOGS_DIR="/var/log/clusterlogs"
LOCAL_LOGS_DIR="/var/log/ingresslogs"
OSCAR_LOGS_DIR="$LOCAL_LOGS_DIR/oscar"

FULL_LOGS="$OSCAR_LOGS_DIR/oscar.log"
LATEST_LOGS="$OSCAR_LOGS_DIR/latest_oscar.log"
mkdir -p $OSCAR_LOGS_DIR

# Log format for goaccess
LOG_FORMAT='%^ %^ %^ %h - - [%d:%t] %~ %m %U %^ %s %^ %R %^ %^'

addLog(){
    ingress_logfile=$1
    cat $ingress_logfile | grep -a 'oscar-oscar' | grep -a '/job\|/run' | tee -a $FULL_LOGS >/dev/null
}

metrics(){
    LOG_FILE=$1
    geo_err=$( { goaccess "${LOG_FILE}" --log-format="${LOG_FORMAT}" -o "${OUTPUTS_PATH}/${LOG_FILE}_full.json" --json-pretty-print; } 2>&1 )
    python3 goaccess_metric_parser.py -f "${OUTPUTS_PATH}/${LOG_FILE}_full.json" -g 0

    status_codes=('200' '204' '404' '500')
    init="t"

    out="${FILTERED_PATH}/${LOG_FILE}"

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
    if [[ $log == *"ingress"* ]]; then
        cp -r $log $LOCAL_LOGS_DIR
        # remove total path
        log=$(echo $log | sed 's/\/var\/log\/clusterlogs\///')
        for logfile in "$LOCAL_LOGS_DIR/$log/controller/"*;
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

for logfile in "$LOCAL_LOGS_DIR/$log/controller/"*;
do
    if [[ $logfile == *".log"* ]]; then
        if [[ $logfile == *".log"]]; then
            cat $logfile | grep -a 'oscar-oscar' | grep -a '/job\|/run' | tee -a $LATEST_LOGS >/dev/null
            metrics $LATEST_LOGS
        else
            addLog $logfile
        fi
    fi
done

# Generate the html file
if [ ! -f "${FULL_LOGS}" ] || [ ! -s "${FULL_LOGS}" ]; then
    echo "Error: Failed to create html report."
    exit 1
fi

metrics $FULL_LOGS

cat $LATEST_LOGS | tee -a $FULL_LOGS >/dev/null
goaccess "${FULL_LOGS}" --log-format="${LOG_FORMAT}" -o "/app/metrics/dashboard.html"
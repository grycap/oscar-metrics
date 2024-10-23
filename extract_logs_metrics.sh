# Container paths
OUTPUTS_PATH="/app/metrics/rawmetrics"
FILTERED_PATH="$OUTPUTS_PATH/filtered_by_status_code"

# Path to the readonly volume with the cluster's ingress logs
CLUSTER_LOGS_DIR="/var/log/clusterlogs"
LOCAL_LOGS_DIR="/var/log/ingresslogs"
OSCAR_LOGS_DIR="$LOCAL_LOGS_DIR/oscar"

HISTORY_LOGS_INFERENCE="$OSCAR_LOGS_DIR/inference/oscar.log"
HISTORY_LOGS_CREATE="$OSCAR_LOGS_DIR/create/oscar.log"

mkdir -p $OSCAR_LOGS_DIR/inference
mkdir -p $OSCAR_LOGS_DIR/create

# Log format for goaccess
LOG_FORMAT='%^ %^ %^ %^ [%^] %d - %t | %s | %Ts | %h | %m %~ %U | %u'

addLog(){
    ingress_logfile=$1
    cat $ingress_logfile | grep GIN-EXECUTIONS-LOGGER | grep -a '/job\|/run' | tee -a $HISTORY_LOGS_INFERENCE >/dev/null
    cat $logfile | grep CREATE-HANDLER | grep '/system/services' | tee -a $HISTORY_LOGS_CREATE >/dev/null
}

metrics(){
    LOG_FILE=$1
    filename=`basename "$LOG_FILE"`
    geo_err=$( { goaccess "${LOG_FILE}" --log-format="${LOG_FORMAT}" -o "${OUTPUTS_PATH}/${filename}_full.json" --json-pretty-print; } 2>&1 )
    python3 logs_metric_parser.py -f "${OUTPUTS_PATH}/${filename}_full.json" -g 0
    
    status_codes=('200' '201' '204' '404' '500')
    init="t"

    out="${FILTERED_PATH}/${filename}"

    for code in "${status_codes[@]}"; do
    code_logs=$(cat $LOG_FILE| grep -E '\|[ ]*'${code}'[ ]*\|')
    if [ ! -z "$code_logs" ]; then
        app_err=$( { cat $LOG_FILE | grep -E '\|[ ]*'${code}'[ ]*\|' | goaccess - -o  "${out}_f${code}.json" --json-pretty-print --log-format="${LOG_FORMAT}"; } 2>&1 )
        if [ ! -f "${out}_f${code}.json" ]; then
            echo "[*] Warning: Couldn't process file $LOG_FILE for status code '$code'"
        else
            if [ $init == 't' ]; then
                python3 logs_metric_parser.py -f "${out}_f${code}.json" -a $code
                init="f"
            else
            python3 logs_metric_parser.py -f "${out}_f${code}.json" -a $code -u
            fi
        fi
    fi
    done
}


# Read current logs and upload backup to s3 
for log_path in "$CLUSTER_LOGS_DIR"/*;
do
    if [[ $log_path == *"oscar_oscar"* ]]; then
        cp -r $log_path $LOCAL_LOGS_DIR
        # Remove total path
        relative_log_path=$(echo $log_path | sed 's/\/var\/log\/clusterlogs\///')
        # Upload current logs to s3
        aws s3 cp --recursive $log_path s3://metrics.oscar.grycap.net/"${CLUSTER_ID}"/ingresslogs/"${relative_log_path}"
        break
    fi
done

# Download from s3 all past logs from previous OSCAR pods
aws s3 cp s3://metrics.oscar.grycap.net/"${CLUSTER_ID}"/ingresslogs $LOCAL_LOGS_DIR --recursive --exclude "oscar/*" --exclude "${relative_log_path}"

# /var/log/ingresslogs/oscar_oscar-7499cd/oscar
for logfile in "$LOCAL_LOGS_DIR/oscar_oscar"*"/oscar/"*;
do
    if [[ $logfile == *".gz" &&  ]]; then
        # unzip all log files
        gzip -d $logfile
        logfile=$(echo $logfile | sed 's/\.gz//')
    fi

    if [[ $logfile == *".log"* || $logfile == *".log" ]]; then
            echo ">> Adding logfile '$logfile'"
            addLog $logfile
    fi
done

awk '!seen[$0]++' $HISTORY_LOGS_INFERENCE > tmp_inference.log
mv tmp_inference.log $HISTORY_LOGS_INFERENCE

awk '!seen[$0]++' $HISTORY_LOGS_CREATE > tmp_create.log
mv tmp_create.log $HISTORY_LOGS_CREATE

metrics $HISTORY_LOGS_INFERENCE
python3 logs_metric_parser.py -f $HISTORY_LOGS_INFERENCE -i 0
python3 logs_metric_parser.py -f $HISTORY_LOGS_CREATE -c 0

rm tmp_*.log

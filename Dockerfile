FROM bitnami/python

# Install goaccess tool
RUN apt-get update && \
    apt-get install nano goaccess -y

# Install aws-cli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Verify the installation
RUN aws --version

# Install python dependencies
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

# Create the directory structure for the metrics
RUN mkdir -p /app/metrics/rawmetrics/filtered_by_status_code && \
    mkdir -p /app/metrics/goaccess-metrics && \
    mkdir -p /app/metrics/prometheus-metrics && \
    mkdir -p /app/ui && \
    mkdir -p /var/log/ingresslogs

# Copy required files
COPY extract_goaccess_metrics.sh /app/
COPY goaccess_metric_parser.py /app/

COPY extract_prometheus_metrics.sh /app/
COPY metrics_prom.py /app/

COPY create_index.py /app/

COPY dbip-country-lite-2024.mmdb /app/
COPY goaccess.conf /etc/goaccess/
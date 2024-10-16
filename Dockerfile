FROM bitnami/python

# Install goaccess tool
RUN apt-get update && \
    apt-get install vim libncursesw5-dev libmaxminddb-dev -y

# Install aws-cli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Verify the installation
RUN aws --version

RUN curl "https://tar.goaccess.io/goaccess-1.5.5.tar.gz" -o "goaccess-1.5.5.tar.gz" && \
    tar -xzvf goaccess-1.5.5.tar.gz && \
    cd goaccess-1.5.5/ && \
    ./configure --enable-utf8 --enable-geoip=mmdb --with-openssl && \ 
    make && \
    make install

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
COPY extract_logs_metrics.sh /app/
COPY logs_metric_parser.py /app/

COPY extract_prometheus_metrics.sh /app/
COPY prometheus_metric_parser.py /app/

COPY create_index.py /app/

COPY dbip-country-lite-2024.mmdb /app/
COPY goaccess.conf /usr/local/etc/goaccess/goaccess.conf 
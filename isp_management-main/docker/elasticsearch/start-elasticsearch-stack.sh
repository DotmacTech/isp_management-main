#!/bin/bash
# Script to start the Elasticsearch stack and initialize it

# Create necessary directories
mkdir -p ./logstash/pipeline
mkdir -p ./logstash/config
mkdir -p ./filebeat
mkdir -p ./init
mkdir -p ./kibana/dashboards

# Copy configuration files if they don't exist
if [ ! -f ./logstash/config/logstash.yml ]; then
    cp ../logstash/config/logstash.yml ./logstash/config/
fi

if [ ! -f ./logstash/pipeline/isp-logs.conf ]; then
    cp ../logstash/pipeline/isp-logs.conf ./logstash/pipeline/
fi

if [ ! -f ./filebeat/filebeat.yml ]; then
    cp ../filebeat/filebeat.yml ./filebeat/
fi

if [ ! -f ./init/init-elasticsearch.sh ]; then
    cp ../init/init-elasticsearch.sh ./init/
    chmod +x ./init/init-elasticsearch.sh
fi

if [ ! -f ./init/import-kibana-dashboards.sh ]; then
    cp ../init/import-kibana-dashboards.sh ./init/
    chmod +x ./init/import-kibana-dashboards.sh
fi

# Copy dashboard files
cp ../kibana/dashboards/*.ndjson ./kibana/dashboards/

# Start the Elasticsearch stack
echo "Starting Elasticsearch stack..."
docker-compose up -d

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s http://localhost:9200 >/dev/null; do
    sleep 5
    echo "Still waiting..."
done
echo "Elasticsearch is ready!"

# Initialize Elasticsearch
echo "Initializing Elasticsearch..."
docker exec -it isp-elasticsearch /bin/bash -c "/usr/share/elasticsearch/init/init-elasticsearch.sh"

# Wait for Kibana to be ready
echo "Waiting for Kibana to be ready..."
until curl -s http://localhost:5601/api/status >/dev/null; do
    sleep 5
    echo "Still waiting..."
done
echo "Kibana is ready!"

# Import Kibana dashboards
echo "Importing Kibana dashboards..."
docker exec -it isp-kibana /bin/bash -c "/usr/share/kibana/init/import-kibana-dashboards.sh"

echo "Elasticsearch stack is up and running!"
echo "Elasticsearch: http://localhost:9200"
echo "Kibana: http://localhost:5601"

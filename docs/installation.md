# Installation Guide

This document provides detailed instructions for installing, configuring, and running the Kafka Pub/Sub System.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Scaling](#scaling)
- [Upgrading](#upgrading)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware Requirements

- **Minimum**:
  - 2 CPU cores
  - 4GB RAM
  - 20GB storage
- **Recommended**:
  - 4+ CPU cores
  - 8GB+ RAM
  - 50GB+ SSD storage

### Software Requirements

- Docker Engine 20.10.0+
- Docker Compose 2.0.0+
- Network connectivity for Docker images

## Installation

### Step 1: Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit the `.env` file to set environment-specific variables:

```
# Kafka Configuration
KAFKA_BROKER_ID=1
KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1

# MongoDB Configuration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password
MONGO_INITDB_DATABASE=pubsub_data

# Producer Configuration
PRODUCER_INTERVAL_MS=100
PRODUCER_BATCH_SIZE=100
KAFKA_TOPIC=data-topic

# Consumer Configuration
CONSUMER_GROUP_ID=data-consumer-group
CONSUMER_AUTO_OFFSET_RESET=earliest

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

### Step 2: Build and Start the System

```bash
docker-compose up -d
```

This command builds and starts all services defined in the docker-compose.yml file:

- Zookeeper
- Kafka
- MongoDB
- Producer
- Consumer
- Prometheus
- Grafana

### Step 3: Verify Installation

Check if all containers are running:

```bash
docker-compose ps
```

All services should be in the "Up" state.

## Configuration

### Kafka Configuration

Kafka can be configured by modifying the environment variables in the `.env` file. Key configuration parameters include:

| Parameter                              | Description                              | Default                |
| -------------------------------------- | ---------------------------------------- | ---------------------- |
| KAFKA_BROKER_ID                        | Unique ID for the Kafka broker           | 1                      |
| KAFKA_ZOOKEEPER_CONNECT                | Zookeeper connection string              | zookeeper:2181         |
| KAFKA_ADVERTISED_LISTENERS             | Listeners for clients                    | PLAINTEXT://kafka:9092 |
| KAFKA_AUTO_CREATE_TOPICS_ENABLE        | Whether topics are created automatically | true                   |
| KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR | Replication factor for the offsets topic | 1                      |

For production, it's recommended to:

- Set a higher replication factor (at least 3)
- Configure proper authentication and authorization
- Set appropriate retention policies

### Producer Configuration

The producer can be configured by modifying its configuration file or environment variables:

| Parameter               | Description                           | Default    |
| ----------------------- | ------------------------------------- | ---------- |
| KAFKA_BOOTSTRAP_SERVERS | Kafka broker addresses                | kafka:9092 |
| KAFKA_TOPIC             | Topic to publish messages to          | data-topic |
| PRODUCER_INTERVAL_MS    | Interval between message batches (ms) | 100        |
| PRODUCER_BATCH_SIZE     | Number of messages per batch          | 100        |

### Consumer Configuration

The consumer can be configured similarly:

| Parameter                  | Description                        | Default                                |
| -------------------------- | ---------------------------------- | -------------------------------------- |
| KAFKA_BOOTSTRAP_SERVERS    | Kafka broker addresses             | kafka:9092                             |
| KAFKA_TOPIC                | Topic to subscribe to              | data-topic                             |
| CONSUMER_GROUP_ID          | Consumer group identifier          | data-consumer-group                    |
| CONSUMER_AUTO_OFFSET_RESET | What to do when no offset is found | earliest                               |
| MONGODB_URI                | MongoDB connection URI             | mongodb://admin:password@mongodb:27017 |
| MONGODB_DATABASE           | MongoDB database name              | pubsub_data                            |
| MONGODB_COLLECTION         | MongoDB collection name            | messages                               |

### Monitoring Configuration

Monitoring tools can be configured as follows:

#### Prometheus

Edit the Prometheus configuration file at `monitoring/prometheus/prometheus.yml` to:

- Add/modify targets
- Adjust scrape intervals
- Configure alerting rules

#### Grafana

Grafana is accessible at http://localhost:3000 (default credentials: admin/admin).

To configure:

1. Log in to the Grafana UI
2. Go to Configuration > Data Sources to verify the Prometheus data source
3. Import dashboards from `monitoring/grafana/dashboards/`

## Running the System

### Starting the System

```bash
docker-compose up -d
```

### Stopping the System

```bash
docker-compose down
```

### Viewing Logs

```bash
# View logs for all services
docker-compose logs

# View logs for a specific service
docker-compose logs producer
docker-compose logs consumer

# Follow logs in real-time
docker-compose logs -f
```

### Monitoring the System

1. Access Prometheus at http://localhost:9090
2. Access Grafana at http://localhost:3000

The following dashboards are available in Grafana:

- Kafka Overview
- Producer Metrics
- Consumer Metrics
- MongoDB Metrics

## Scaling

### Scaling Consumers

To handle higher message volumes, you can scale the number of consumer instances:

```bash
docker-compose up -d --scale consumer=3
```

This creates three consumer instances that share the workload within the same consumer group.

### Scaling Producers

Similarly, you can scale producer instances:

```bash
docker-compose up -d --scale producer=2
```

### Scaling Kafka

For a production deployment, consider:

1. Increasing the number of Kafka brokers by modifying the docker-compose.yml
2. Increasing the number of partitions for the topic:

```bash
docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --alter --topic data-topic --partitions 6
```

## Upgrading

### Upgrading Components

To rebuild and restart specific components after making changes:

```bash
# Rebuild and restart a specific component
docker-compose build producer
docker-compose up -d producer

# Rebuild and restart the entire system
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Common Issues

#### System Won't Start

**Symptom**: `docker-compose up` fails or containers exit immediately

**Solution**:

1. Check if ports are already in use:

```bash
netstat -tulpn | grep <port>
```

2. Check container logs:

```bash
docker-compose logs
```

3. Verify that Docker has enough resources allocated
4. Try resetting Docker Compose:

```bash
docker-compose down -v
docker-compose up -d
```

#### Kafka Connection Issues

**Symptom**: Services can't connect to Kafka

**Solution**:

1. Verify Kafka is running:

```bash
docker-compose ps kafka
```

2. Check Kafka logs:

```bash
docker-compose logs kafka
```

3. Verify network connectivity:

```bash
docker exec -it producer ping kafka
```

4. Check if the topic exists:

```bash
docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --list
```

#### Data Not Being Stored in MongoDB

**Symptom**: Messages are produced but not appearing in MongoDB

**Solution**:

1. Check consumer logs:

```bash
docker-compose logs consumer
```

2. Verify MongoDB connection:

```bash
docker exec -it consumer ping mongodb
```

3. Check MongoDB directly:

```bash
docker exec -it mongodb mongosh --username admin --password password
use pubsub_data
db.messages.find()
```

#### Monitoring Not Working

**Symptom**: Prometheus or Grafana dashboards not showing data

**Solution**:

1. Check if services are exposing metrics:

```bash
curl http://localhost:8080/metrics  # Replace with actual metrics endpoint
```

2. Verify Prometheus targets:
   - Access http://localhost:9090/targets
3. Check Prometheus configuration:

```bash
docker-compose logs prometheus
```

4. Verify Grafana data source configuration

### Getting Support

If you continue to experience issues:

1. Collect logs from all services:

```bash
docker-compose logs > system-logs.txt
```

2. Document the issue with:
   - Description of the problem
   - Steps to reproduce
   - System information
   - Attached logs

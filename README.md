# Kafka Pub/Sub System

A scalable, containerized publish/subscribe system built with Kafka and Python, featuring data persistence, error handling, and comprehensive monitoring.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Key Components](#key-components)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Module Design](#module-design)
- [Error Handling](#error-handling)
- [Monitoring and Logging](#monitoring-and-logging)
- [Performance Considerations](#performance-considerations)

## System Overview

This project implements a robust Kafka-based publish/subscribe system with the following features:

- JSON data production and consumption
- MongoDB persistence layer
- Containerized microservices architecture
- Comprehensive error handling with retry mechanisms
- Multi-consumer group support
- Prometheus/Grafana monitoring and logging

The system is designed to handle up to 100,000 messages per hour with built-in scalability.

## Architecture

```
┌───────────────┐     ┌────────────────┐     ┌───────────────────┐
│  Data Producer│     │                │     │  Data Consumer    │
│(Containerized)|-───▶│    Kafka       │────▶│  (Containerized)  │
│               │     │ (Containerized)│     │                   │
└───────────────┘     └────────────────┘     └───────────────────┘
        │                                              │
        │                                              │
        ▼                                              ▼
┌───────────────┐                           ┌───────────────────┐
│  Logging      │                           │     Persistence   │
│  (ELK Stack)  │                           │     MongoDB       │
└───────────────┘                           └───────────────────┘
        ▲                                             ▲
        │                                             │
        └──────────────────┐      ┌───────────────────┘
                           │      │
                     ┌─────────────────┐
                     │   Monitoring    │
                     │   Prometheus    │
                     │   + Grafana     │
                     └─────────────────┘
```

## Key Components

### 1. Kafka Environment

- **Kafka Broker**: Handles message storage and distribution
- **Zookeeper**: Manages the Kafka cluster
- **Configuration**: Multiple partitions to support parallel processing and multiple consumers

### 2. Data Producer

- Generates simple JSON data with UUID keys
- Uses format: `(key, value, headers)` for Kafka messages
- Publishes messages to Kafka topics
- Implements error handling and retry mechanisms
- Collects metrics and logs for monitoring

### 3. Data Consumer

- Subscribes to Kafka topics
- Processes received JSON data
- Persists data to MongoDB
- Handles consumer group management for parallel processing
- Implements error handling with retry logic

### 4. Persistence Layer

- MongoDB for JSON data storage
- Simple data models and indexes to support future queries

### 5. Monitoring and Logging

- Prometheus for metrics collection
- Grafana for visualization
- ELK Stack (optional) for log collection and analysis

## Project Structure

The repository is organized with the following structure:

```
/
├── docker-compose.yml           # Main Docker Compose configuration
├── .env                         # Environment variables
├── README.md                    # Project documentation
├── scripts/                     # Helper scripts
│   ├── setup.sh                 # Setup script
│   └── teardown.sh              # Cleanup script
├── producer/                    # Producer application
│   ├── Dockerfile               # Producer Docker configuration
│   ├── requirements.txt         # Python dependencies
│   ├── src/                     # Source code
│   │   ├── __init__.py
│   │   ├── producer.py          # Main producer class
│   │   ├── data_generator.py    # Data generation module
│   │   └── utils/               # Utility functions
│   │       ├── __init__.py
│   │       ├── config.py        # Configuration loading
│   │       ├── logging.py       # Logging setup
│   │       └── metrics.py       # Metrics collection
│   ├── config/                  # Configuration files
│   │   └── config.json          # Producer configuration
│   └── tests/                   # Tests
│       ├── __init__.py
│       └── test_producer.py     # Producer tests
├── consumer/                    # Consumer application
│   ├── Dockerfile               # Consumer Docker configuration
│   ├── requirements.txt         # Python dependencies
│   ├── src/                     # Source code
│   │   ├── __init__.py
│   │   ├── consumer.py          # Main consumer class
│   │   ├── data_processor.py    # Data processing module
│   │   ├── storage.py           # Persistence module
│   │   └── utils/               # Utility functions
│   │       ├── __init__.py
│   │       ├── config.py        # Configuration loading
│   │       ├── logging.py       # Logging setup
│   │       └── metrics.py       # Metrics collection
│   └── tests/                   # Tests
│       ├── __init__.py
│       └── test_consumer.py     # Consumer tests
├── monitoring/                  # Monitoring configuration
│   ├── prometheus/              # Prometheus configuration
│   │   └── prometheus.yml       # Prometheus config file
│   └── grafana/                 # Grafana configuration
│       ├── datasource.yml       # Data source configuration
│       └── dashboards/          # Dashboard configurations
│           ├── kafka.json       # Kafka monitoring dashboard
│           ├── producer.json    # Producer monitoring dashboard
│           └── consumer.json    # Consumer monitoring dashboard
└── docs/                        # Additional documentation
    ├── architecture.md          # Detailed architecture description
    ├── installation.md          # Installation guide
    └── development.md           # Development guide
```

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- Git
- Python 3.9 or higher (for local development)

### Installation Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/planetree12/kafka-pubsub-system.git
   cd kafka-pubsub-system
   ```

2. Start the system using Docker Compose:
   ```bash
   docker compose up -d --build
   ```

This will start:

- Zookeeper
- Kafka
- MongoDB
- Producer service
- Consumer service
- Prometheus
- Grafana

3. Access the monitoring dashboard:
   - Grafana: http://localhost:3000 (default credentials: admin/admin)

### Local Development Setup

For local development without Docker:

1. Set up a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the producer dependencies:

   ```bash
   cd producer
   pip install -r requirements.txt
   ```

3. Run the producer:
   ```bash
   python -m src.producer
   ```

## Usage

### Configuration

The system can be configured using JSON configuration files or environment variables:

#### Producer Configuration

The producer is configured through a JSON file located at `producer/config/config.json`:

```json
{
  "kafka": {
    "bootstrap_servers": "kafka:9092",
    "topic": "data-topic",
    "compression_type": "snappy"
  },
  "producer": {
    "interval_ms": 36,
    "batch_size": 100,
    "max_retries": 3,
    "initial_retry_delay_ms": 3000
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "metrics": {
    "enabled": true,
    "port": 8000
  }
}
```

The producer service continuously generates and sends messages to Kafka based on these configuration parameters:

- `interval_ms`: Controls how frequently batches of messages are sent (e.g., 36ms means approximately 100,000 messages per hour)
- `batch_size`: Number of messages in each batch

With the default configuration, the producer will generate and send approximately 100,000 messages per hour to Kafka in a continuous stream.

Environment variables can also be used to override configuration:

- `KAFKA_BOOTSTRAP_SERVERS`: Comma-separated list of Kafka broker addresses
- `KAFKA_TOPIC`: The Kafka topic to publish to
- `PRODUCER_INTERVAL_MS`: Interval between batches in milliseconds
- `PRODUCER_BATCH_SIZE`: Number of messages to send in each batch

#### Consumer Configuration

The consumer is configured through a JSON file located at `consumer/config/config.json`:

```json
{
  "kafka": {
    "bootstrap_servers": "kafka:9092",
    "topic": "data-topic",
    "group_id": "data-consumer-group"
  },
  "consumer": {
    "offset_commit_frequency_ms": 1000
  },
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "metrics": {
    "enabled": true,
    "port": 8001
  }
}
```

Environment variables can also be used to override configuration:

- `CONSUMER_GROUP_ID`: The Kafka consumer group ID
- `MONGODB_URI`: The MongoDB connection string
- `MONGODB_DATABASE`: The MongoDB database name

### Scaling

To scale the number of consumers:

```bash
docker-compose up -d --scale consumer=3
```

### Running Tests

To run the tests for the producer:

```bash
cd producer
pytest
```

To run tests with coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

## Module Design

### Data Format

#### Kafka Message Format

The producer generates Kafka messages with the following format:

- **Key**: UUID string (serves as the unique message identifier)
- **Value**: JSON object with the following structure:

  ```json
  {
    "id": "uuid-string",
    "name": "item_12345678",
    "created_at": "2023-07-15T12:34:56.789Z",
    "metadata": {
      "source": "system-a",
      "version": "1.0.0"
    }
  }
  ```

  Where:

  - `id`: UUID string that uniquely identifies the message
  - `name`: Item identifier with pattern "item\_" followed by 8 digits
  - `created_at`: ISO 8601 formatted timestamp with UTC timezone
  - `metadata`: Optional object containing additional information:
    - `source`: Identifies the source system
    - `version`: Version information in semantic format

- **Headers**: Message metadata
  ```json
  {
    "content-type": "application/json",
    "created_at": "2023-07-15T12:34:56.789Z"
  }
  ```

**Note**: This message format is hardcoded in the `producer/src/data_generator.py` file. To modify the structure or content of produced messages, you need to modify this file directly.

### Producer Interface

```python
class DataProducer:
    def __init__(self):
        """
        Initialize the producer.

        Loads configuration, sets up logging and metrics,
        and initializes the Kafka producer connection.
        """
        pass

    def generate_data(self, batch_size):
        """
        Generate a batch of data.

        Args:
            batch_size: The number of messages to generate.

        Returns:
            List of (key, value, headers) tuples.
        """
        pass

    def send_message(self, key, value, headers):
        """
        Send a message to Kafka with retry logic.

        Args:
            key: The message key.
            value: (dict) JSON data to send.
            headers: Optional message headers.

        Returns:
            bool: True if successful, False otherwise.
        """
        pass

    def send_batch(self, batch):
        """Send a batch of messages to Kafka

        Args:
            batch: List of (key, value, headers) tuples

        Returns:
            int: Number of successfully sent messages
        """
        pass

    def run(self, interval=0.1, batch_size=100):
        """Run the producer main loop

        This method starts a continuous loop that will:
        1. Generate batches of data messages at regular intervals
        2. Send each batch to Kafka
        3. Control the sending rate based on the configured interval
        4. Perform periodic health checks
        5. Continue running until explicitly stopped (via SIGTERM/SIGINT)

        Args:
            interval (float): Send interval in seconds
            batch_size (int): Number of messages to send in batch
        """
        pass
```

The producer runs as a continuous service that constantly generates and sends data to Kafka at the configured rate. It doesn't stop after sending a batch of messages, but continues to generate and send new messages until the service is explicitly terminated.

### Consumer Interface

```python
class DataConsumer:
    def __init__(self, config):
        """Initialize the consumer

        Args:
            config (dict): Configuration parameters including Kafka connection info, consumer group ID, etc.
        """
        pass

    def process_message(self, message):
        """Process message received from Kafka

        Args:
            message (dict): Received JSON message

        Returns:
            bool: Whether processing was successful
        """
        pass

    def persist_data(self, processed_data):
        """Save processed data to MongoDB

        Args:
            processed_data (dict): Processed data

        Returns:
            bool: Whether saving was successful
        """
        pass

    def run(self):
        """Run the consumer main loop"""
        pass
```

### Persistence Interface

```python
class DataStorage:
    def __init__(self, config):
        """Initialize data storage

        Args:
            config (dict): MongoDB connection information
        """
        pass

    def save(self, data):
        """Save data

        Args:
            data (dict): Data to save

        Returns:
            bool: Whether saving was successful
        """
        pass

    def get(self, query):
        """Query data

        Args:
            query (dict): Query conditions

        Returns:
            list: Data matching the conditions
        """
        pass
```

## Error Handling

### Producer Side

- Exponential backoff retry strategy
- Configurable maximum retry attempts and timeout
- Failed message logging for later analysis

### Consumer Side

- Idempotent message processing to ensure safety with repeated processing
- Configurable offset commit frequency to prevent message loss on consumer crashes
- Dead-letter queue for messages that repeatedly fail to process

## Monitoring and Logging

### Metrics Collection

The system uses Prometheus for comprehensive metrics collection across all components:

#### Kafka Metrics

- **Broker Health**: Online status and response times of brokers
- **Topic Partitions**: Number of partitions per topic
- **Partition State**: Distribution of leaders and followers
- **Replication Status**: Replication factor and number of in-sync replicas
- **Message Processing Rate**: Messages processed per second (produced/consumed)
- **Byte Processing Rate**: Bytes processed per second (in/out)
- **Consumer Lag**: Number of messages by which consumers lag behind producers
- **Consumer Group Members**: Number of active consumers in groups

#### Zookeeper Metrics

- **Service Health**: Online status and response times
- **Node Status**: Leader/follower state
- **Connection Count**: Number of client connections
- **Request Rate**: Requests processed per second

#### Producer Metrics

- **Operational Status**: Online status and health checks
- **Message Production Rate**: Messages produced per second
- **Batch Size**: Average batch size
- **Error Rate**: Percentage of failed message deliveries
- **Latency**: Time taken to send messages to Kafka

The producer metrics are collected using Prometheus and can be visualized using Grafana dashboards. The metrics provide insights into the performance and health of the producer component.

#### Consumer Metrics

- **Operational Status**: Online status and health checks
- **Message Consumption Rate**: Messages processed per second
- **Offset Commit Frequency**: Rate of consumption position commits
- **Error Rate**: Percentage of message processing failures

#### MongoDB Metrics

- **Service Health**: Online status and response times
- **Connection Count**: Number of active connections
- **Operation Counters**: Read/write/update/delete operation counts
- **Collection Size**: Data collection growth rate

#### System-level Metrics

- **Container Status**: Running state of all Docker containers
- **Service Restart Count**: Frequency of container restarts
- **Resource Usage**: Basic CPU, memory, and disk usage percentages

### Prometheus Configuration

Basic Prometheus configuration includes appropriate scrape intervals and targets for all monitored components. The actual configuration can be found in:

```
monitoring/prometheus/prometheus.yml
```

### Dashboards

The monitoring system includes the following Grafana dashboards:

- **System Overview**: Health status of all components and key metrics
- **Kafka Monitoring**: Broker status, topic partition state, consumer lag
- **Application Monitoring**: Producer and consumer status, error rates
- **Persistence Monitoring**: MongoDB connection state, operation counts

### Alerts

Basic alert rules configured in Prometheus:

- **Service Unavailability**: When any critical service is unreachable for 1 minute
- **High Consumer Lag**: When consumer lag exceeds 10,000 messages for 5 minutes
- **Disk Space Low**: When remaining space is below 20%

### Logging

- Structured logging in JSON format
- Logs for critical operations and errors
- Configurable log levels

## Performance Considerations

The system is designed to handle approximately 100,000 messages per hour with the following optimizations:

- Batch message production for higher throughput
- Multiple partitions for parallel processing
- Consumer groups for load distribution
- MongoDB indexes for efficient data retrieval
- Configurable parameters to adjust performance based on workload

## Using Custom Configuration

You can customize the system behavior by modifying the configuration files:

1. Modify the producer configuration: Edit `producer/config/config.json` to change Kafka connection details, message production rate, etc.
2. Modify the consumer configuration: Edit `consumer/config/config.json` to change consumer group settings, MongoDB connection details, etc.

For certain types of changes, modifying configuration files alone is not sufficient:

- To change the structure or content of produced messages: Modify the code in `producer/src/data_generator.py`
- To change the message processing logic: Modify the code in `consumer/src/consumer.py`
- To add new metrics or change monitoring behavior: Modify the code in `producer/src/utils/metrics.py` or `consumer/src/utils/metrics.py`

After making configuration or code changes, start the system to apply them:

```bash
python -m src.producer
```

The system will automatically read from the configuration files and use the updated code.

---

This project is part of a coding assignment demonstrating Kafka, Python, and containerization skills.

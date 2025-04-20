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
├── README.md                    # Project documentation
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

   This will automatically start all services including multiple consumer instances (consumer-1 and consumer-2) as configured in the `docker-compose.yml` file.

This will start:

- Zookeeper
- Kafka
- MongoDB
- Producer service
- Multiple Consumer instances (consumer-1, consumer-2)
- Prometheus
- Grafana

3. Access the monitoring dashboard:
   - Grafana: http://localhost:3000 (default credentials: admin/admin)
   - Kafka UI: http://localhost:8080

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

The system is configured using JSON configuration files:

#### Producer Configuration

The producer is configured through a JSON file located at `producer/config/config.json`:

```json
{
  "kafka": {
    "bootstrap_servers": "kafka:29092",
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

### Accessing MongoDB Data

To access and inspect the data stored in MongoDB, you can use the `docker exec` command to enter the MongoDB container:

```bash
# Access the MongoDB container
docker exec -it <container name or id> mongosh
```

Once inside the MongoDB shell, you can run various commands to explore the data:

```bash
# List all databases
show dbs

# Switch to the database used by the application
use pubsub_data

# List all collections in the current database
db.getCollectionNames()

# View data in a collection (we use the collection name "messages" in this project)
db.messages.find()
```

To exit the MongoDB shell, type `exit` or press Ctrl+D.

For more advanced queries, refer to the [MongoDB documentation](https://docs.mongodb.com/manual/reference/method/db.collection.find/).

### Scaling

To add more consumer instances, you can modify the docker-compose.yml file by adding new consumer services with unique names:

```yaml
# Example of adding a new consumer instance
consumer-3:
  build:
    context: ./consumer
  depends_on:
    kafka:
      condition: service_healthy
    mongodb:
      condition: service_healthy
  ports:
    - "8003:8001"
  restart: on-failure
```

After updating the docker-compose.yml file, you can apply the changes with:

```bash
docker compose up -d
```

Make sure to also update the Prometheus configuration in `monitoring/prometheus/prometheus.yml` to monitor the new consumer instance:

```yaml
- job_name: "consumer-3"
  static_configs:
    - targets: ["consumer-3:8001"]
  metrics_path: "/metrics"
  scrape_interval: 15s
```

Additionally, you may want to update the Grafana dashboard to include the new consumer instance monitoring panels.

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

### Consumer Specifications

The Consumer module implements the following specific requirements:

1. **Direct Persistence**: Messages from Kafka are stored directly in MongoDB without additional processing or filtering.

2. **Data Model**:

   - MongoDB collection with fields: `message_id`, `name`, `created_at`
   - Index on `created_at` field for efficient time-based queries

3. **Error Handling**:

   - Failed MongoDB connections result in messages being redirected to a Kafka dead letter topic
   - Retry mechanisms with configurable attempts and backoff strategy

4. **Performance Optimization**:

   - Batch processing for MongoDB writes to improve throughput
   - Number of consumer instances equals the number of Kafka partitions
   - Internal parallel processing for message handling

5. **Monitoring Metrics**:

   - Message consumption rate (messages processed per second)
   - Processing error rate
   - MongoDB write latency
   - Consumer lag (messages pending in Kafka)

6. **Multiple Consumer Instances**:

   - MongoDB initialization (particularly index creation) is implemented in an idempotent manner to handle multiple concurrent consumer instances
   - Each consumer instance checks if required indexes exist before creating them
   - This approach prevents errors when scaling to multiple consumer instances

7. **Dead Letter Queue**:

   - Dead letter topic ("dead-letter-topic") is automatically created by Kafka when needed
   - Kafka is configured with `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"` which creates topics on demand
   - Consumer sends failed messages to the dead letter topic when MongoDB connections fail
   - No explicit topic creation is needed as topics are created on first use

8. **Scaling Configuration**:
   - The system is pre-configured to run multiple named consumer instances (consumer-1, consumer-2)
   - Each consumer instance is defined as a separate service in `docker-compose.yml`
   - Each instance has its own dedicated monitoring in Prometheus and Grafana
   - To add more consumers, add new service definitions to docker-compose.yml with appropriate port mappings
   - Make corresponding changes to monitoring configurations for new consumer instances

The number of consumer instances should ideally match the number of Kafka topic partitions for optimal performance. Currently, the system is configured with 6 partitions as specified in the docker-compose.yml file under the Kafka service configuration.

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

The system uses Prometheus for comprehensive metrics collection across all components. The `Application Monitoring` dashboard provides a consolidated view:

#### Kafka Metrics

- **Broker Health**: Basic `up` status shown in the Application Monitoring dashboard.
- **Message Processing Rate**: Messages processed per second, shown _per consumer instance_.
- **Consumer Lag**: Number of messages by which consumers lag behind producers, shown _per consumer instance_.
  _Note: More detailed Kafka metrics (like partition details) can be found in the dedicated `Kafka Monitoring` dashboard._

#### Zookeeper Metrics

- **Service Health**: Basic `up` status shown in the Application Monitoring dashboard.

#### Producer Metrics

- **Message Production Rate**: Messages produced per second.
- **Batch Size**: Average batch size.
- **Error Rate**: Rate of failed message deliveries.
- **Latency**: Time taken to send messages to Kafka.

#### Consumer Metrics

- **Message Consumption Rate**: Messages processed per second, shown _per consumer instance_.
- **Error Rate**: Rate of message processing failures, shown _per consumer instance_.
- **Processing Time**: Time spent processing messages, including MongoDB write latency, shown _per consumer instance_.

#### MongoDB Metrics

- **Service Health**: Basic `up` status shown in the Application Monitoring dashboard.

#### System-level Metrics

- **Basic Service Health**: `up` status for core infrastructure components.
- **Resource Usage**: CPU Usage and Network I/O are displayed.

### Prometheus Configuration

Basic Prometheus configuration includes appropriate scrape intervals and targets for all monitored components. The actual configuration can be found in:

```
monitoring/prometheus/prometheus.yml
```

### Dashboards

The monitoring system includes the following Grafana dashboards:

- **System Overview**: High-level health status of infrastructure components and key system metrics (CPU, Network). _(This dashboard seems to have overlapping information with Application Monitoring)_
- **Kafka Monitoring**: Detailed Kafka-specific metrics like broker status, topic partition state, consumer lag.
- **Application Monitoring**: Consolidated view of producer and consumer application-level metrics (rates, errors, latency, lag, processing time) along with basic infrastructure health.

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

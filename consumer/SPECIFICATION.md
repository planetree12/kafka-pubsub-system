# Consumer Module Specification

## Overview

The Consumer module is responsible for subscribing to the Kafka topic, processing messages, and storing them in MongoDB. This module implements the consumer component of the Kafka Pub/Sub System.

## Key Features

- Direct persistence to MongoDB without message transformation
- Batch processing for optimized performance
- Error handling with dead letter topic redirection
- Prometheus metrics for monitoring

## Table of Contents

- [Functional Requirements](#functional-requirements)
- [Technical Specifications](#technical-specifications)
- [Component Design](#component-design)
- [Data Flow](#data-flow)
- [MongoDB Integration](#mongodb-integration)
- [Error Handling](#error-handling)
- [Metrics and Monitoring](#metrics-and-monitoring)
- [Configuration](#configuration)
- [Performance Considerations](#performance-considerations)
- [Scaling](#scaling)

## Functional Requirements

1. Subscribe to and consume messages from the Kafka topic (`data-topic`)
2. Store consumed messages directly in MongoDB without additional processing
3. Implement error handling with redirection to a dead letter topic
4. Use batch processing for MongoDB writes to optimize performance
5. Support consumer group scaling with partition-based message distribution
6. Provide monitoring metrics for system health and performance tracking

## Technical Specifications

### Kafka Consumer Configuration

- **Bootstrap Servers**: `kafka:9092`
- **Consumer Group ID**: `data-consumer-group`
- **Topic**: `data-topic`
- **Dead Letter Topic**: `dead-letter-topic`
- **Auto Commit**: `false` (manual offset commit for better control)
- **Poll Timeout**: 1000ms
- **Offset Commit Frequency**: Every batch or every 1000 messages

**Important Note**: The `dead_letter_topic` is automatically created by Kafka when first used, due to the `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"` setting in the Kafka configuration. The consumer simply sends failed messages to this topic name without needing to create it explicitly.

### MongoDB Configuration

- **Connection**: `mongodb://mongodb:27017`
- **Database**: `pubsub_data`
- **Collection**: `messages`
- **Index**: `created_at` (ascending)
- **Write Concern**: `w: 1` (acknowledgment from primary only)
- **Batch Size**: 100 messages (configurable)

**Important Note**: Similar to Kafka auto-creating topics, MongoDB will automatically create collections when they are first used. The consumer does not need to explicitly create the collection; it will be created on the first insert operation. However, the consumer is responsible for creating necessary indexes.

### Scaling

- Number of consumer instances should equal the number of Kafka partitions
- Each consumer instance handles messages from assigned partitions
- Internal parallel processing of batches using Python threading or concurrent.futures

## MongoDB Initialization

Since multiple consumer instances may run simultaneously, MongoDB initialization (particularly index creation) is implemented in an idempotent manner:

```python
def create_indexes_if_not_exist(db, collection_name):
    # Check if index already exists
    existing_indexes = db[collection_name].list_indexes()
    existing_index_names = [idx['name'] for idx in existing_indexes]

    # Create index only if it doesn't exist
    if 'created_at_1' not in existing_index_names:
        db[collection_name].create_index([('created_at', 1)], background=True)
```

This approach ensures that even if multiple consumer instances attempt to create the same index simultaneously, no errors will occur since MongoDB's index creation is idempotent.

## Component Design

### Core Components

1. **Kafka Client**: Manages connection to Kafka, message consumption, and offset management
2. **Message Processor**: Handles JSON message parsing and validation
3. **MongoDB Client**: Manages database connection and batch write operations
4. **Error Handler**: Implements retry logic and dead letter topic publishing
5. **Metrics Collector**: Gathers and exposes performance metrics

### Class Structure

```python
class DataConsumer:
    """Main consumer class that orchestrates the message consumption and storage process"""

    def __init__(self, config):
        """Initialize the consumer with configuration

        Args:
            config (dict): Configuration dictionary
        """
        pass

    def connect_kafka(self):
        """Establish connection to Kafka"""
        pass

    def connect_mongodb(self):
        """Establish connection to MongoDB"""
        pass

    def consume_messages(self, batch_size=100, timeout_ms=1000):
        """Consume a batch of messages from Kafka

        Args:
            batch_size (int): Maximum number of messages to consume
            timeout_ms (int): Poll timeout in milliseconds

        Returns:
            list: List of consumed messages
        """
        pass

    def store_batch(self, messages):
        """Store a batch of messages in MongoDB

        Args:
            messages (list): List of messages to store

        Returns:
            bool: Whether the operation was successful
        """
        pass

    def send_to_dead_letter(self, message, error):
        """Send a message to the dead letter topic

        Args:
            message (dict): Original message
            error (Exception): Error that occurred

        Returns:
            bool: Whether sending was successful
        """
        pass

    def commit_offsets(self):
        """Commit current offsets to Kafka"""
        pass

    def run(self):
        """Main execution loop"""
        pass


class MongoDBHandler:
    """Handles MongoDB operations"""

    def __init__(self, config):
        """Initialize MongoDB handler

        Args:
            config (dict): MongoDB configuration
        """
        pass

    def connect(self):
        """Establish connection to MongoDB"""
        pass

    def create_indexes(self):
        """Create necessary indexes in the MongoDB collection"""
        pass

    def insert_batch(self, documents):
        """Insert a batch of documents

        Args:
            documents (list): List of documents to insert

        Returns:
            bool: Whether the operation was successful
        """
        pass


class MetricsCollector:
    """Collects and exposes metrics"""

    def __init__(self, port=8001):
        """Initialize metrics collector

        Args:
            port (int): Port to expose metrics on
        """
        pass

    def increment_messages_processed(self, count=1):
        """Increment processed messages counter

        Args:
            count (int): Number to increment by
        """
        pass

    def increment_processing_errors(self, count=1):
        """Increment processing errors counter

        Args:
            count (int): Number to increment by
        """
        pass

    def observe_processing_time(self, seconds):
        """Record message processing time

        Args:
            seconds (float): Processing time in seconds
        """
        pass

    def observe_batch_size(self, size):
        """Record batch size

        Args:
            size (int): Batch size
        """
        pass
```

## Data Flow

1. **Message Consumption**:

   - The consumer polls messages from Kafka in batches
   - Messages are validated for format and structure
   - A batch of valid messages is collected

2. **Batch Processing**:

   - Collected messages are transformed into MongoDB documents
   - Batch insert operation is performed (automatically creates collection if needed)
   - Success/failure status is tracked

3. **Commit Management**:

   - Offsets are committed after successful batch processing
   - In case of failures, offset commitment is skipped (will retry in next poll)

4. **Error Handling**:
   - Database connection issues trigger dead letter topic publishing
   - Individual message processing errors are logged and counted

## MongoDB Integration

### Document Structure

Each message will be stored in MongoDB with the following structure:

```json
{
  "_id": "msg-uuid-string",
  "message_id": "msg-uuid-string",
  "name": "item_12345678",
  "created_at": "2023-07-15T12:34:56.789Z",
  "metadata": {
    "source": "system-a",
    "version": "1.0.0"
  },
  "received_at": "2023-07-15T12:35:01.234Z"
}
```

The `_id` field will use the message's UUID to ensure idempotency.

### Collections

MongoDB collections are created automatically when documents are first inserted. The consumer doesn't need to explicitly create the collection. The insertion code might look like:

```python
def store_batch(self, messages):
    """Store a batch of messages in MongoDB"""
    try:
        # MongoDB will automatically create the collection if it doesn't exist
        result = self.db[self.collection_name].insert_many(messages)
        return len(result.inserted_ids) == len(messages)
    except Exception as e:
        self.logger.error("Failed to store batch", error=str(e))
        return False
```

### Indexes

After connecting to MongoDB, the consumer creates the necessary indexes:

```javascript
db.messages.createIndex({ created_at: 1 });
```

This index supports efficient time-based queries and report generation.

## Error Handling

### Connection Failures

1. **MongoDB Connection Failures**:

   - Retry connection with exponential backoff (max 3 attempts)
   - If connection fails after retries, redirect messages to dead letter topic
   - Dead letter topic is automatically created by Kafka when first used (due to `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"`)
   - Periodically attempt to reconnect to MongoDB

2. **Kafka Connection Failures**:
   - Retry connection with exponential backoff (max 3 attempts)
   - If connection fails, log error and exit (rely on container restart policy)

### Message Processing Failures

1. **Invalid Message Format**:

   - Log error with message details
   - Send to dead letter topic with reason code
   - Continue processing other messages

2. **MongoDB Write Failures**:
   - Retry batch operation (max 3 attempts)
   - If still failing, break batch into smaller chunks
   - For persistent failures, send to dead letter topic

## Metrics and Monitoring

### Key Metrics

1. **Operational Metrics**:

   - `consumer_messages_processed_total`: Counter for total processed messages
   - `consumer_processing_errors_total`: Counter for processing errors
   - `consumer_active_connections`: Gauge for active connections (Kafka and MongoDB)
   - `consumer_batch_size`: Histogram of batch sizes
   - `consumer_processing_time_seconds`: Histogram of message processing time

2. **Performance Metrics**:
   - `consumer_lag`: Gauge for consumer lag (messages waiting to be processed)
   - `consumer_mongodb_write_time_seconds`: Histogram of MongoDB write times
   - `consumer_offset_commit_time_seconds`: Histogram of offset commit times

The consumer exposes Prometheus metrics on port 8001. These metrics include:

- Message consumption rate
- Error rate
- MongoDB write latency
- Consumer lag

### Prometheus Integration

Metrics will be exposed on the `/metrics` endpoint on port 8001, ready for Prometheus scraping.

## Configuration

### Configuration File Structure

```json
{
  "kafka": {
    "bootstrap_servers": "kafka:9092",
    "topic": "data-topic",
    "group_id": "data-consumer-group",
    "dead_letter_topic": "dead-letter-topic",
    "auto_offset_reset": "earliest",
    "enable_auto_commit": false,
    "poll_timeout_ms": 1000
  },
  "mongodb": {
    "uri": "mongodb://mongodb:27017",
    "database": "pubsub_data",
    "collection": "messages"
  },
  "consumer": {
    "batch_size": 100,
    "offset_commit_frequency": 1000,
    "max_retries": 3,
    "retry_backoff_ms": 1000
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

## Performance Considerations

### Optimizations

1. **Batch Processing**:

   - Group messages into batches (default 100) to reduce MongoDB roundtrips
   - Adjust batch size based on message size and system capacity

2. **Connection Pooling**:

   - Use connection pooling for MongoDB to reduce connection overhead
   - Configure appropriate pool size based on expected load

3. **Parallel Processing**:

   - Process multiple batches in parallel using threads or concurrent.futures
   - Number of parallel workers should be tuned based on available resources

4. **Resource Management**:
   - Monitor and limit memory usage to prevent OOM issues
   - Implement graceful degradation under heavy load

## Scaling

The number of consumer instances should match the number of Kafka partitions for optimal performance. The system is pre-configured in the `docker-compose.yml` file to automatically start 6 consumer instances to match the 6 Kafka partitions:

```yaml
# From docker-compose.yml
consumer:
  # ... other configuration ...
  deploy:
    replicas: 6 # Match the number of Kafka partitions (KAFKA_NUM_PARTITIONS)
```

With this configuration, simply running `docker compose up -d` will automatically start the correct number of consumer instances. If you need to change the number of partitions, remember to update both the `KAFKA_NUM_PARTITIONS` value and the consumer `replicas` value to keep them in sync.

### Scaling Strategy

1. **Horizontal Scaling**:

   - The system uses Docker Compose's `deploy: replicas` feature for horizontal scaling
   - Ensure the number of consumer instances matches the number of Kafka partitions
   - For advanced deployments, Kubernetes can be used with similar replica configurations

2. **Vertical Scaling**:
   - Increase resources (CPU, memory) allocated to consumer containers
   - Tune batch size and parallel processing parameters

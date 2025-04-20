# Architecture Overview

This document provides a detailed description of the Kafka Pub/Sub System architecture, design decisions, and implementation details.

## Table of Contents

- [System Architecture Overview](#system-architecture-overview)
- [Data Model](#data-model)
- [Component Details](#component-details)
  - [Kafka Environment](#kafka-environment)
  - [Producer](#producer)
  - [Consumer](#consumer)
  - [Persistence Layer](#persistence-layer)
  - [Monitoring and Logging](#monitoring-and-logging)
- [Data Flow](#data-flow)
- [Performance Considerations](#performance-considerations)

## System Architecture Overview

The Kafka Pub/Sub System is designed as a scalable, containerized microservices architecture centered around Apache Kafka as the message broker. The system is optimized to handle at least 100,000 messages per hour (approximately 28 messages per second) with built-in scalability to accommodate higher volumes when needed.

### Architecture Diagram

```
┌───────────────┐     ┌────────────────┐     ┌───────────────────┐
│  Data Producer│     │                │     │  Data Consumer    │
│  (Containerized)───▶│    Kafka       │────▶│  (Containerized)  │
│                │     │ (Containerized)│     │                   │
└───────────────┘     └────────────────┘     └───────────────────┘
        │                                              │
        │                                              │
        ▼                                              ▼
┌───────────────┐                           ┌───────────────────┐
│  Logging      │                           │     Persistence   │
│  (ELK Stack)  │                           │     MongoDB       │
└───────────────┘                           └───────────────────┘
        ▲                                              ▲
        │                                              │
        └──────────────────┐      ┌───────────────────┘
                           │      │
                     ┌─────────────────┐
                     │   Monitoring    │
                     │   Prometheus   │
                     │   + Grafana    │
                     └─────────────────┘
```

### Design Principles

The architecture follows these key design principles:

1. **Decoupling**: Producer and consumer services are completely decoupled, allowing independent scaling and deployment.
2. **Fault Tolerance**: The system includes comprehensive error handling and retry mechanisms.
3. **Scalability**: All components can be scaled horizontally to handle increased load.
4. **Observability**: Extensive monitoring and logging are integrated into the system.
5. **Containerization**: All components are containerized for consistent deployment and isolation.
6. **Extensibility**: The modular design allows for easy extension and modification.

## Data Model

### JSON Message Structure

The system processes JSON messages with a flexible schema. A typical message structure might include:

```json
{
  "id": "msg-123456",
  "timestamp": "2023-06-15T08:30:45.123Z",
  "source": "producer-1",
  "type": "data_event",
  "payload": {
    "field1": "value1",
    "field2": 12345,
    "field3": {
      "nested_field": "nested_value"
    }
  },
  "metadata": {
    "version": "1.0",
    "priority": "normal"
  }
}
```

### Data Lifecycle

1. **Generation**: The producer generates JSON data according to configured templates or patterns.
2. **Publication**: Data is serialized and published to a Kafka topic.
3. **Consumption**: Consumers read the data from Kafka topics.
4. **Processing**: Optional transformations or validations are applied.
5. **Persistence**: Processed data is stored in MongoDB.
6. **Monitoring**: Metrics are collected at each stage for monitoring.

## Component Details

### Kafka Environment

The Kafka environment is the central component of the pub/sub system, responsible for reliable message delivery between producers and consumers.

#### Configuration

- **Multiple Partitions**: The Kafka topic is configured with multiple partitions (minimum 6 for a system handling 100,000 messages/hour) to enable parallel processing.
- **Replication Factor**: For development, a replication factor of 1 is used. For production, a higher replication factor (3+) is recommended.
- **Retention Policy**: Messages are retained for a configurable period (default: 7 days).
- **Topic Configuration**:
  - `data-topic`: Main topic for data messages
  - Additional topics can be configured for specific use cases

#### Performance Tuning

- **Batch Size**: Producers use batching to improve throughput.
- **Compression**: Messages are compressed to reduce network bandwidth.
- **Partition Assignment Strategy**: Round-robin or range strategies depending on the consumption pattern.

### Producer

The producer service is responsible for generating data and publishing it to Kafka topics.

#### Key Components

1. **Data Generator**: Creates simulated JSON data based on configurable patterns.
2. **Kafka Client**: Handles the connection to Kafka and message publishing.
3. **Retry Mechanism**: Implements exponential backoff for failed publish attempts.
4. **Metrics Collector**: Gathers metrics about message generation and publishing rates.

#### Design Considerations

- **Batching Strategy**: To achieve the target of 100,000 messages per hour, the producer batches messages (default batch size: 100) to reduce network overhead and increase throughput.
- **Rate Limiting**: The producer includes configurable rate limiting to prevent overwhelming the system.
- **Error Handling**: Failed publish attempts are retried with exponential backoff, with configurable maximum retry attempts.

### Consumer

The consumer service subscribes to Kafka topics, processes received messages, and persists the data to MongoDB.

#### Key Components

1. **Kafka Consumer Client**: Manages the connection to Kafka and message consumption.
2. **Message Processor**: Processes and potentially transforms the received JSON data.
3. **Persistence Client**: Handles storing the processed data in MongoDB.
4. **Error Handler**: Manages failed processing attempts and retries.

#### Design Considerations

- **Consumer Groups**: Multiple consumer instances can be grouped to distribute the processing load. For handling 100,000 messages/hour, a minimum of 3 consumer instances is recommended.
- **Partition Assignment**: Ensures balanced distribution of partitions across consumer instances.
- **Offset Management**: Configurable offset commit strategy to balance between performance and message delivery guarantees.
- **Idempotent Processing**: Ensures that messages can be safely reprocessed without side effects.

### Persistence Layer

MongoDB is used as the persistence layer due to its natural fit for JSON data and scalability characteristics.

#### Schema Design

- **Collections**: Messages are stored in collections based on their type or other criteria.
- **Indexing Strategy**: Indexes on frequently queried fields improve query performance.
- **Sharding**: For production deployments with very high volumes, consider MongoDB sharding.

#### Performance Optimization

- **Write Concern**: Configurable write concern balances between durability and performance.
- **Connection Pooling**: Optimized connection pooling reduces connection overhead.
- **Bulk Operations**: Batch inserts for higher throughput.

### Monitoring and Logging

The monitoring and logging components provide visibility into the system's operation and performance.

#### Metrics Collection

- **Producer Metrics**: Message generation rate, publishing rate, error rate, latency.
- **Kafka Metrics**: Topic metrics, consumer lag, broker health.
- **Consumer Metrics**: Message consumption rate, processing time, error rate.
- **MongoDB Metrics**: Query performance, write performance, storage usage.

#### Dashboards

- **Operational Dashboard**: Real-time view of system operation.
- **Performance Dashboard**: Metrics related to throughput and latency.
- **Error Dashboard**: View of error rates and types.

#### Logging

- **Structured Logging**: JSON-formatted logs for easier parsing and analysis.
- **Log Levels**: Configurable log levels (INFO, DEBUG, ERROR, etc.).
- **Centralized Collection**: Logs from all components are centrally collected and indexed.

## Data Flow

### Normal Operation

1. The producer generates JSON data at a rate adjusted to meet the target of 100,000 messages per hour.
2. Messages are batched and published to the Kafka topic.
3. The consumer group consumes messages from the topic, with each consumer instance handling a subset of partitions.
4. Consumed messages are processed and stored in MongoDB.
5. Metrics are collected at each stage and sent to Prometheus.
6. Logs are generated and centrally collected.

### Error Handling

1. **Producer Errors**: Failed publish attempts are retried with exponential backoff.
2. **Consumer Errors**: Failed processing attempts are retried. Messages that consistently fail can be sent to a dead-letter queue.
3. **Kafka Failures**: The system is designed to recover automatically from temporary Kafka unavailability.
4. **MongoDB Failures**: Failed database operations are retried. If persistence fails persistently, the system can be configured to buffer messages.

## Performance Considerations

### Throughput Optimization

To achieve and exceed the target of 100,000 messages per hour:

1. **Producer Optimization**:

   - Batched message production (100 messages per batch)
   - Asynchronous sending with callbacks
   - Configurable message generation rate (default: 28 messages/second)

2. **Kafka Optimization**:

   - Multiple partitions (6+) to enable parallel processing
   - Compression to reduce network bandwidth
   - Appropriate retention and segment settings

3. **Consumer Optimization**:
   - Multiple consumer instances (3+) in a consumer group
   - Batched processing where appropriate
   - Optimized MongoDB writes using bulk operations

### Scalability Strategy

The system can scale to handle higher message volumes through:

1. **Horizontal Scaling**:

   - Adding more producer instances
   - Adding more consumer instances
   - Adding more Kafka brokers and partitions

2. **Vertical Scaling**:

   - Increasing resources (CPU, memory) for existing instances
   - Optimizing configurations for higher performance

3. **Monitoring-Driven Scaling**:
   - Automated scaling based on metrics like consumer lag
   - Alerts for performance thresholds to trigger manual scaling

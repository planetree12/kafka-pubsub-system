# Development Guide

This document provides guidelines and instructions for developers contributing to the Kafka Pub/Sub System project.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Module Extension Guidelines](#module-extension-guidelines)
- [Troubleshooting](#troubleshooting)

## Development Environment Setup

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Git

### Local Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/kafka-pubsub-system.git
   cd kafka-pubsub-system
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:

   ```bash
   pip install -r producer/requirements.txt
   pip install -r consumer/requirements.txt
   pip install pytest pytest-cov flake8 black isort mypy
   ```

4. Setup pre-commit hooks (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Running Components Locally

To run components locally during development:

1. Start Kafka and other dependencies using Docker Compose:

   ```bash
   docker-compose up -d kafka zookeeper mongodb
   ```

2. Run the producer in development mode:

   ```bash
   cd producer
   python -m src.producer --config=config/dev.json
   ```

3. Run the consumer in development mode:
   ```bash
   cd consumer
   python -m src.consumer --config=config/dev.json
   ```

## Code Style Guidelines

This project follows PEP 8 style guidelines with some modifications.

### Style Rules

- Line length: 88 characters (Black default)
- Use 4 spaces for indentation (no tabs)
- Use docstrings for all public modules, functions, classes, and methods
- Type hints are required for all function parameters and return values

### Automated Formatting

We use the following tools to enforce code style:

- **Black**: For code formatting

  ```bash
  black producer/ consumer/
  ```

- **isort**: For import sorting

  ```bash
  isort producer/ consumer/
  ```

- **Flake8**: For style guide enforcement

  ```bash
  flake8 producer/ consumer/
  ```

- **MyPy**: For type checking
  ```bash
  mypy producer/ consumer/
  ```

## Testing

### Testing Strategy

The project uses pytest for unit and integration tests. Tests are organized as follows:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interaction between components
- **End-to-End Tests**: Test complete flow from producer to consumer

### Running Tests

To run tests:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=producer --cov=consumer --cov-report=term-missing

# Run specific test modules
pytest producer/tests/
pytest consumer/tests/test_consumer.py
```

### Test Writing Guidelines

- Each test function should test a single functionality
- Use descriptive test names (`test_<function_name>_<scenario>`)
- Use fixtures for common test setup
- Mock external dependencies (Kafka, MongoDB) for unit tests
- Use parameterized tests for testing multiple inputs

Example test:

```python
import pytest
from producer.src.producer import DataProducer

def test_send_message_success(mocker):
    # Arrange
    mock_kafka = mocker.patch('producer.src.producer.KafkaProducer')
    mock_kafka.return_value.send.return_value.get.return_value = None
    config = {"bootstrap_servers": "localhost:9092", "topic": "test-topic"}
    producer = DataProducer(config)

    # Act
    result = producer.send_message({"key": "value"})

    # Assert
    assert result is True
    mock_kafka.return_value.send.assert_called_once()
```

## Module Extension Guidelines

### Adding a New Producer

1. Create a new class that extends `BaseProducer` in `producer/src/`
2. Implement the required methods:
   - `generate_data()`
   - `send_message()`
   - `run()`
3. Add configuration options to the config schema
4. Add tests for the new producer

Example:

```python
from producer.src.base_producer import BaseProducer

class CustomProducer(BaseProducer):
    def __init__(self, config):
        super().__init__(config)
        # Custom initialization

    def generate_data(self):
        # Custom data generation
        return {"custom_field": "value"}

    def send_message(self, data):
        # Custom send logic
        return super().send_message(data)
```

### Adding a New Consumer

1. Create a new class that extends `BaseConsumer` in `consumer/src/`
2. Implement the required methods:
   - `process_message()`
   - `persist_data()`
   - `run()`
3. Add configuration options to the config schema
4. Add tests for the new consumer

### Adding New Metrics

1. Define new metrics in the appropriate module (`producer/src/utils/metrics.py` or `consumer/src/utils/metrics.py`)
2. Update the Prometheus configuration in `monitoring/prometheus/prometheus.yml`
3. Create a new dashboard or update existing dashboards in `monitoring/grafana/dashboards/`

## Troubleshooting

### Common Issues

#### Kafka Connection Issues

**Symptom**: Producer or consumer can't connect to Kafka
**Solution**:

- Check if Kafka container is running: `docker ps`
- Verify network settings in Docker Compose file
- Check logs: `docker logs kafka`

#### MongoDB Connection Issues

**Symptom**: Consumer can't connect to MongoDB
**Solution**:

- Check if MongoDB container is running
- Verify connection string and credentials
- Check MongoDB logs: `docker logs mongodb`

#### Slow Performance

**Symptom**: Message processing is slow
**Solution**:

- Check consumer lag using Kafka tools
- Review batch size settings
- Check resource usage (CPU, memory)
- Look at the monitoring dashboard for bottlenecks

### Debugging Tips

1. Enable debug logging by setting the environment variable:

   ```bash
   export LOG_LEVEL=DEBUG
   ```

2. Use the `kafka-console-consumer` tool to check raw messages:

   ```bash
   docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic data-topic --from-beginning
   ```

3. Use MongoDB client to inspect stored data:

   ```bash
   docker exec -it mongodb mongosh
   ```

4. Check metrics in Grafana for performance issues

For more complex issues, please open an issue on GitHub with:

- Detailed description of the problem
- Steps to reproduce
- System information
- Relevant logs and error messages

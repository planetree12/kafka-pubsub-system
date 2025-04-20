"""Configuration management for the Kafka Producer."""

import json
import os
import pathlib
from jsonschema import validate
from typing import Dict, Any, Optional

# Configuration schema (updated to match config.json)
CONFIG_SCHEMA = {
    "type": "object",
    "required": ["kafka", "producer", "logging", "metrics"],
    "properties": {
        "kafka": {
            "type": "object",
            "required": ["bootstrap_servers", "topic", "compression_type"],
            "properties": {
                "bootstrap_servers": {"type": "string"},
                "topic": {"type": "string"},
                "compression_type": {"type": "string"}
            }
        },
        "producer": {
            "type": "object",
            "required": ["interval_ms", "batch_size", "max_retries", "initial_retry_delay_ms"],
            "properties": {
                "interval_ms": {"type": "number"},
                "batch_size": {"type": "number"},
                "max_retries": {"type": "number"},
                "initial_retry_delay_ms": {"type": "number"}
            }
        },
        "logging": {
            "type": "object",
            "required": ["level", "format"],
            "properties": {
                "level": {"type": "string"},
                "format": {"type": "string"}
            }
        },
        "metrics": {
            "type": "object",
            "required": ["enabled", "port"],
            "properties": {
                "enabled": {"type": "boolean"},
                "port": {"type": "number"}
            }
        }
    }
}

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from the specified JSON file and environment variables.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Dict containing the configuration.
    """
    # Default configuration matching the schema
    default_config = {
        "kafka": {
            "bootstrap_servers": "kafka:9092",
            "topic": "data-topic",
            "compression_type": "snappy"
        },
        "producer": {
            "interval_ms": 100,
            "batch_size": 100,
            "max_retries": 3,
            "initial_retry_delay_ms": 3000
        },
        "logging": {
            "level": "INFO",
            "format": "json"
        },
        "metrics": {
            "enabled": True,
            "port": 8000
        }
    }

    # Load from file if it exists
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            file_config = json.load(f)
            # Merge with default config
            default_config["kafka"].update(file_config.get("kafka", {}))
            default_config["producer"].update(file_config.get("producer", {}))
            default_config["logging"].update(file_config.get("logging", {}))
            default_config["metrics"].update(file_config.get("metrics", {}))

    # Override with environment variables if present
    if os.getenv("KAFKA_BOOTSTRAP_SERVERS"):
        default_config["kafka"]["bootstrap_servers"] = os.getenv("KAFKA_BOOTSTRAP_SERVERS")

    if os.getenv("KAFKA_TOPIC"):
        default_config["kafka"]["topic"] = os.getenv("KAFKA_TOPIC")

    if os.getenv("PRODUCER_INTERVAL_MS"):
        default_config["producer"]["interval_ms"] = int(os.getenv("PRODUCER_INTERVAL_MS"))

    if os.getenv("PRODUCER_BATCH_SIZE"):
        default_config["producer"]["batch_size"] = int(os.getenv("PRODUCER_BATCH_SIZE"))

    # Validate configuration
    validate(instance=default_config, schema=CONFIG_SCHEMA)

    return default_config

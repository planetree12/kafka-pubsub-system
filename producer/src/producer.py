"""Main producer module for the Kafka pub/sub system."""

import json
import time
import signal
import threading
import sys
import os
import pathlib
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
from retry import retry

from .data_generator import DataGenerator
from .utils.config import load_config
from .utils.logging import configure_logging, get_logger
from .utils.metrics import ProducerMetrics

class DataProducer:
    """
    Main producer class for generating and publishing data to Kafka.

    This producer generates event data and publishes it to a Kafka topic.
    It supports batch processing, retries with exponential backoff, and metrics collection.
    """

    def __init__(self):
        """Initialize the producer."""
        # Get the base directory of the project
        base_dir = pathlib.Path(__file__).parent.parent.parent.absolute()

        # Hardcoded configuration file path
        config_path = os.path.join(base_dir, "producer", "config", "config.json")

        # Load configuration
        self.config = load_config(config_path)

        # Configure logging
        self.logger = configure_logging(self.config)

        # Initialize metrics
        self.metrics = ProducerMetrics(self.config)

        # Initialize data generator with config
        self.data_generator = DataGenerator(self.config)

        # Initialize Kafka producer
        self._init_kafka_producer()

        # Initialize state
        self.running = False
        self.last_health_check_time = 0
        self.health_check_interval = 60  # seconds

        # Set up signal handling
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

        self.logger.info(
            "Producer initialized",
            kafka_topic=self.config["kafka"]["topic"],
            bootstrap_servers=self.config["kafka"]["bootstrap_servers"]
        )

    def _init_kafka_producer(self) -> None:
        """Initialize the Kafka producer."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.config["kafka"]["bootstrap_servers"],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                compression_type=self.config["kafka"]["compression_type"],
                acks='all',  # Wait for all replicas to acknowledge
                retries=self.config["producer"]["max_retries"],
                retry_backoff_ms=100,
                batch_size=16384,  # 16KB batch size
                linger_ms=5,  # Wait 5ms for batches
                buffer_memory=33554432,  # 32MB buffer
            )
            self.metrics.record_operational_status(True)
            self.logger.info("Connected to Kafka")
        except Exception as e:
            self.metrics.record_operational_status(False)
            self.logger.error("Failed to connect to Kafka", error=str(e))
            raise

    @retry(exceptions=KafkaError, tries=3, delay=3, backoff=2, logger=None)
    def send_message(self, key: str, value: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        """
        Send a message to Kafka with retry logic.

        Args:
            key: The message key.
            value: The message value.
            headers: Optional message headers.

        Returns:
            bool: True if successful, False otherwise.
        """
        with self.metrics.time_send_operation():
            try:
                # 轉換 headers 為 Kafka 格式 (list of tuples)
                kafka_headers = None
                if headers:
                    kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]

                future = self.producer.send(
                    self.config["kafka"]["topic"],
                    key=key,
                    value=value,
                    headers=kafka_headers
                )
                # Wait for the send to complete to catch immediate errors
                future.get(timeout=10)
                self.metrics.record_message_sent()
                return True
            except KafkaError as e:
                # This will be retried by the retry decorator
                error_type = type(e).__name__
                self.logger.warning(
                    "Failed to send message, retrying",
                    error=str(e),
                    error_type=error_type
                )
                self.metrics.record_send_failure(error_type)
                raise
            except Exception as e:
                # Non-Kafka errors won't be retried
                error_type = type(e).__name__
                self.logger.error(
                    "Unexpected error sending message",
                    error=str(e),
                    error_type=error_type
                )
                self.metrics.record_send_failure(error_type)
                return False

    def send_batch(self, batch: List[Tuple[str, Dict[str, Any], Dict[str, str]]]) -> int:
        """
        Send a batch of messages to Kafka.

        Args:
            batch: List of (key, value, headers) tuples.

        Returns:
            int: Number of successfully sent messages.
        """
        if not batch:
            return 0

        batch_size = len(batch)
        successful = 0

        for key, value, headers in batch:
            if self.send_message(key, value, headers):
                successful += 1

        self.metrics.record_batch_sent(batch_size)
        if successful != batch_size:
            self.logger.warning(
                "Some messages failed to send",
                batch_size=batch_size,
                successful=successful
            )

        return successful

    def generate_data(self, batch_size: int = None) -> List[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        """
        Generate a batch of data.

        Args:
            batch_size: The number of messages to generate.

        Returns:
            List of (key, value, headers) tuples.
        """
        if batch_size is None:
            batch_size = self.config["producer"]["batch_size"]

        self.logger.debug(f"Generating batch of {batch_size} messages")
        return self.data_generator.generate_batch(batch_size)

    def health_check(self) -> bool:
        """
        Perform a health check.

        Returns:
            bool: True if the producer is healthy, False otherwise.
        """
        current_time = time.time()

        # Only perform health check at certain intervals
        if current_time - self.last_health_check_time < self.health_check_interval:
            return True

        self.last_health_check_time = current_time

        # Check Kafka connection
        try:
            # Try to send a small test message
            key = "health-check"
            value = {
                "id": "health-check",
                "name": "health_check",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            headers = {"type": "health-check"}
            result = self.send_message(key, value, headers)

            if result:
                self.logger.info("Health check passed")
                self.metrics.record_operational_status(True)
                return True
            else:
                self.logger.warning("Health check failed")
                self.metrics.record_operational_status(False)
                return False
        except Exception as e:
            self.logger.error("Health check failed with error", error=str(e))
            self.metrics.record_operational_status(False)
            return False

    def run(self, interval_ms: int = None) -> None:
        """
        Run the producer main loop.

        Args:
            interval_ms: The interval between batches in milliseconds.
        """
        if interval_ms is None:
            interval_ms = self.config["producer"]["interval_ms"]

        interval_sec = interval_ms / 1000.0
        batch_size = self.config["producer"]["batch_size"]

        self.running = True
        self.logger.info(
            "Starting producer",
            interval_ms=interval_ms,
            batch_size=batch_size
        )

        try:
            while self.running:
                start_time = time.time()

                # Perform health check
                healthy = self.health_check()
                if not healthy:
                    # Try to reinitialize the producer
                    try:
                        self._init_kafka_producer()
                    except Exception as e:
                        self.logger.error(
                            "Failed to reinitialize Kafka producer",
                            error=str(e)
                        )
                        # Sleep to avoid tight loop
                        time.sleep(5)
                        continue

                # Generate and send a batch of data
                batch = self.generate_data(batch_size)
                sent = self.send_batch(batch)

                # Control the sending rate
                elapsed = time.time() - start_time
                sleep_time = max(0, interval_sec - elapsed)

                if sleep_time > 0:
                    time.sleep(sleep_time)
        except Exception as e:
            self.logger.error("Unexpected error in producer main loop", error=str(e))
            self.metrics.record_operational_status(False)
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        self.logger.info("Shutting down producer")
        if hasattr(self, 'producer'):
            self.producer.close(timeout=5)
        self.metrics.record_operational_status(False)

    def _handle_exit(self, signum, frame) -> None:
        """
        Handle exit signals.

        Args:
            signum: The signal number.
            frame: The current stack frame.
        """
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

def main():
    """Main entry point."""
    try:
        producer = DataProducer()
        producer.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

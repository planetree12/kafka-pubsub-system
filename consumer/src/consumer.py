"""
Main Kafka consumer module for processing messages and persisting to MongoDB.
"""
import json
import logging
import signal
import sys
import time
from typing import Dict, Any, List

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
import pymongo

from src.data_processor import DataProcessor
from src.storage import MongoDBHandler
from src.utils.config import load_config
from src.utils.logging import setup_logging
from src.utils.metrics import MetricsCollector


class DataConsumer:
    """
    Main consumer class for Kafka message consumption and MongoDB persistence.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the consumer with configuration.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)

        # Set up logging
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.metrics = MetricsCollector(self.config)
        self.processor = DataProcessor()
        self.storage = MongoDBHandler(self.config)

        # Kafka configuration
        self.bootstrap_servers = self.config.get('kafka', {}).get('bootstrap_servers', 'kafka:29092')
        self.topic = self.config.get('kafka', {}).get('topic', 'data-topic')
        self.group_id = self.config.get('kafka', {}).get('group_id', 'data-consumer-group')
        self.dead_letter_topic = self.config.get('kafka', {}).get('dead_letter_topic', 'dead-letter-topic')
        self.auto_offset_reset = self.config.get('kafka', {}).get('auto_offset_reset', 'earliest')
        self.enable_auto_commit = self.config.get('kafka', {}).get('enable_auto_commit', False)
        self.poll_timeout_ms = self.config.get('kafka', {}).get('poll_timeout_ms', 1000)

        # Consumer configuration
        self.batch_size = self.config.get('consumer', {}).get('batch_size', 100)
        self.offset_commit_frequency = self.config.get('consumer', {}).get('offset_commit_frequency', 1000)
        self.max_retries = self.config.get('consumer', {}).get('max_retries', 3)
        self.retry_backoff_ms = self.config.get('consumer', {}).get('retry_backoff_ms', 1000)

        # Initialize Kafka consumer and producer (for dead letter)
        self.consumer = None
        self.producer = None
        self.running = False
        self.messages_since_commit = 0

        # Set up signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, sig, frame):
        """
        Handle termination signals for graceful shutdown.

        Args:
            sig: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {sig}, shutting down...")
        self.running = False

    def connect_kafka(self) -> bool:
        """
        Connect to Kafka broker with retry logic.

        Returns:
            bool: True if connection successful, False otherwise
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.logger.info(f"Connecting to Kafka at {self.bootstrap_servers}")

                # Configure Kafka consumer
                consumer_config = {
                    'bootstrap.servers': self.bootstrap_servers,
                    'group.id': self.group_id,
                    'auto.offset.reset': self.auto_offset_reset,
                    'enable.auto.commit': self.enable_auto_commit,
                    'max.poll.interval.ms': 300000,  # 5 minutes
                    'session.timeout.ms': 30000,     # 30 seconds
                }

                # Create consumer
                self.consumer = Consumer(consumer_config)

                # Subscribe to topic
                self.consumer.subscribe([self.topic])
                self.logger.info(f"Successfully subscribed to topic: {self.topic}")

                # Configure Kafka producer (for dead letter topic)
                producer_config = {
                    'bootstrap.servers': self.bootstrap_servers,
                }
                self.producer = Producer(producer_config)

                # Update metrics
                self.metrics.set_active_connections('kafka', 1)

                return True

            except KafkaException as e:
                retry_count += 1
                backoff_time = (self.retry_backoff_ms / 1000) * (2 ** (retry_count - 1))
                self.logger.error(f"Failed to connect to Kafka (attempt {retry_count}/{self.max_retries}): {str(e)}")

                if retry_count < self.max_retries:
                    self.logger.info(f"Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
                else:
                    self.logger.error("Maximum retries reached. Could not connect to Kafka.")
                    return False

    def consume_batch(self) -> List[Dict[str, Any]]:
        """
        Consume a batch of messages from Kafka.

        Returns:
            List[Dict]: List of consumed messages
        """
        messages = []
        message_count = 0
        start_time = time.time()

        # Poll for messages until batch size is reached or timeout occurs
        while message_count < self.batch_size:
            # Check if we should stop
            if not self.running:
                break

            # Poll for message
            msg = self.consumer.poll(timeout=self.poll_timeout_ms / 1000)

            if msg is None:
                # No message received
                break

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition, not an error
                    self.logger.debug(f"Reached end of partition {msg.partition()}")
                else:
                    self.logger.error(f"Kafka error: {msg.error()}")
                    self.metrics.increment_processing_errors()
                continue

            # Valid message received
            messages.append(msg)
            message_count += 1

        elapsed_time = time.time() - start_time

        if messages:
            self.logger.info(f"Consumed {len(messages)} messages in {elapsed_time:.3f} seconds")
            # Record metrics
            self.metrics.observe_batch_size(len(messages))

        return messages

    def process_and_store_batch(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Process and store a batch of messages.

        Args:
            messages: List of Kafka messages

        Returns:
            bool: True if processing and storage successful, False otherwise
        """
        if not messages:
            return True

        start_time = time.time()

        # Process messages
        processed_messages = self.processor.process_batch(messages)

        # Store processed messages in MongoDB
        if processed_messages:
            storage_success = self.storage.insert_batch(processed_messages)
            if not storage_success:
                self.logger.error("Failed to store messages in MongoDB")
                # Send failed messages to dead letter topic
                for message in messages:
                    self.send_to_dead_letter(message, "MongoDB storage failure")
                return False

            # Update metrics
            self.metrics.increment_messages_processed(len(processed_messages))
            self.metrics.observe_mongodb_write_time(time.time() - start_time)

            # Update commit counter
            self.messages_since_commit += len(messages)

            # Commit offsets if needed
            if self.messages_since_commit >= self.offset_commit_frequency:
                self.commit_offsets()

        return True

    def send_to_dead_letter(self, message: Dict[str, Any], error: str) -> bool:
        """
        Send a message to the dead letter topic.

        Args:
            message: Original Kafka message
            error: Error description

        Returns:
            bool: True if sending was successful, False otherwise
        """
        try:
            # Ensure we have a producer
            if self.producer is None:
                self.logger.error("Cannot send to dead letter topic: producer not initialized")
                return False

            # Create dead letter message with original message and error info
            dead_letter_message = {
                'original_message': message.value().decode('utf-8') if message.value() else None,
                'error': error,
                'topic': message.topic(),
                'partition': message.partition(),
                'offset': message.offset(),
                'timestamp': time.time()
            }

            # Serialize to JSON
            message_json = json.dumps(dead_letter_message).encode('utf-8')

            # Send to dead letter topic
            self.producer.produce(
                self.dead_letter_topic,
                key=message.key(),
                value=message_json
            )
            self.producer.poll(0)  # Trigger any callbacks

            self.logger.info(f"Sent message to dead letter topic: {self.dead_letter_topic}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send message to dead letter topic: {str(e)}")
            return False

    def commit_offsets(self) -> None:
        """Commit current offsets to Kafka."""
        if self.consumer and not self.enable_auto_commit:
            try:
                start_time = time.time()
                self.consumer.commit(asynchronous=False)
                elapsed_time = time.time() - start_time

                self.logger.info(f"Committed offsets for {self.messages_since_commit} messages")
                self.messages_since_commit = 0

                # Record metrics
                self.metrics.observe_offset_commit_time(elapsed_time)

            except KafkaException as e:
                self.logger.error(f"Failed to commit offsets: {str(e)}")

    def calculate_lag(self) -> None:
        """Calculate and record consumer lag."""
        try:
            if not self.consumer:
                return

            # Get consumer lag from assignment
            assignments = self.consumer.assignment()
            total_lag = 0

            # For each assigned partition, get lag
            for partition in assignments:
                # Get low and high watermarks
                low, high = self.consumer.get_watermark_offsets(partition)
                # Get current position
                position = self.consumer.position([partition])[0]
                # Calculate lag
                if position is not None and high is not None:
                    lag = high - position
                    total_lag += lag

            self.metrics.set_consumer_lag(total_lag)
            self.logger.debug(f"Current consumer lag: {total_lag} messages")

        except Exception as e:
            self.logger.error(f"Failed to calculate consumer lag: {str(e)}")

    def run(self) -> None:
        """
        Main execution loop for the consumer.

        This method:
        1. Connects to Kafka and MongoDB
        2. Consumes messages in batches
        3. Processes and stores messages
        4. Handles errors and commits offsets
        5. Continues until interrupted
        """
        # Initialize connections
        if not self.connect_kafka():
            self.logger.error("Failed to connect to Kafka, exiting")
            return

        if not self.storage.connect():
            self.logger.error("Failed to connect to MongoDB, messages will be sent to dead letter topic")

        # Start main processing loop
        self.running = True
        self.logger.info("Consumer started and ready to process messages")

        while self.running:
            try:
                # Consume batch of messages
                messages = self.consume_batch()

                # If we got messages, process and store them
                if messages:
                    self.process_and_store_batch(messages)

                # Calculate and record consumer lag periodically
                self.calculate_lag()

            except Exception as e:
                self.logger.error(f"Error in consumer loop: {str(e)}")
                self.metrics.increment_processing_errors()
                # Brief pause to prevent tight error loop
                time.sleep(1)

        # Cleanup on shutdown
        self.logger.info("Consumer shutting down...")

        # Final offset commit
        if self.messages_since_commit > 0:
            self.commit_offsets()

        # Close connections
        if self.consumer:
            self.consumer.close()

        if self.producer:
            self.producer.flush()

        self.storage.close()
        self.logger.info("Consumer shut down successfully")


def main():
    """Command line entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Kafka Consumer for MongoDB storage')
    parser.add_argument('--config', dest='config_path', help='Path to configuration file')
    args = parser.parse_args()

    # Initialize and run consumer
    consumer = DataConsumer(args.config_path)
    consumer.run()


if __name__ == "__main__":
    main()

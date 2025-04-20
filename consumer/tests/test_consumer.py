"""Tests for the consumer module."""

import unittest
import json
import time
import os
from unittest.mock import patch, MagicMock, call

from src.consumer import DataConsumer


class TestDataConsumer(unittest.TestCase):
    """Test cases for the DataConsumer class."""

    @patch('src.consumer.Consumer')
    @patch('src.consumer.Producer')
    @patch('src.consumer.DataProcessor')
    @patch('src.consumer.MongoDBHandler')
    @patch('src.consumer.MetricsCollector')
    @patch('src.consumer.setup_logging')
    @patch('src.consumer.load_config')
    def setUp(self, mock_load_config, mock_setup_logging, mock_metrics, mock_mongodb,
              mock_processor, mock_producer, mock_consumer):
        """Set up test fixtures."""
        # Create a test config
        self.test_config = {
            "kafka": {
                "bootstrap_servers": "kafka:9092",
                "topic": "data-topic",
                "group_id": "data-consumer-group",
                "dead_letter_topic": "dead-letter-topic",
                "auto_offset_reset": "earliest",
                "enable_auto_commit": False,
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
                "enabled": True,
                "port": 8001
            }
        }

        # Mock the load_config function to return our test config
        mock_load_config.return_value = self.test_config

        # Set up mocks
        self.mock_metrics_instance = mock_metrics.return_value
        self.mock_storage_instance = mock_mongodb.return_value
        self.mock_processor_instance = mock_processor.return_value
        self.mock_kafka_producer = mock_producer.return_value
        self.mock_kafka_consumer = mock_consumer.return_value

        # Initialize consumer
        self.consumer = DataConsumer()

        # Verify load_config was called
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once_with(self.test_config)

    def test_initialization(self):
        """Test that the consumer initializes correctly."""
        # Check that the consumer has the expected attributes
        self.assertEqual(self.consumer.config, self.test_config)
        self.assertEqual(self.consumer.bootstrap_servers, "kafka:9092")
        self.assertEqual(self.consumer.topic, "data-topic")
        self.assertEqual(self.consumer.group_id, "data-consumer-group")
        self.assertEqual(self.consumer.dead_letter_topic, "dead-letter-topic")
        self.assertEqual(self.consumer.batch_size, 100)
        self.assertEqual(self.consumer.offset_commit_frequency, 1000)
        self.assertEqual(self.consumer.max_retries, 3)
        self.assertEqual(self.consumer.retry_backoff_ms, 1000)
        self.assertFalse(self.consumer.running)

    @patch('src.consumer.Consumer')
    @patch('src.consumer.time.time')
    def test_connect_kafka_success(self, mock_time, mock_consumer_class):
        """Test successful Kafka connection."""
        # Configure mocks
        mock_time.return_value = 1234567890.0
        mock_consumer_instance = MagicMock()
        mock_consumer_class.return_value = mock_consumer_instance

        # Make sure consumer and producer are not already initialized
        self.consumer.consumer = None
        self.consumer.producer = None

        # Call the method
        result = self.consumer.connect_kafka()

        # Check the result
        self.assertTrue(result)

        # Verify Kafka consumer was initialized with correct config
        mock_consumer_class.assert_called_once()

        # Verify subscribe was called
        mock_consumer_instance.subscribe.assert_called_once_with([self.consumer.topic])

        # Verify metrics were updated
        self.mock_metrics_instance.set_active_connections.assert_called_once_with('kafka', 1)

    @patch('src.consumer.time.time')
    @patch('src.consumer.time.sleep')
    @patch('src.consumer.Consumer')
    def test_connect_kafka_failure(self, mock_consumer_class, mock_sleep, mock_time):
        """Test handling of Kafka connection failure."""
        from confluent_kafka import KafkaException

        # Configure mocks
        mock_time.return_value = 1234567890.0
        mock_consumer_class.side_effect = KafkaException("Test Kafka error")

        # Call the method
        result = self.consumer.connect_kafka()

        # Check the result
        self.assertFalse(result)

        # Verify retry logic was followed
        self.assertEqual(mock_sleep.call_count, self.consumer.max_retries - 1)

    def test_consume_batch_empty(self):
        """Test consuming an empty batch."""
        # Configure mock to return None (no messages)
        self.mock_kafka_consumer.poll.return_value = None
        self.consumer.running = True
        self.consumer.consumer = self.mock_kafka_consumer

        # Call the method
        result = self.consumer.consume_batch()

        # Check the result
        self.assertEqual(result, [])

        # Verify poll was called
        self.mock_kafka_consumer.poll.assert_called_once()

    def test_consume_batch_with_messages(self):
        """Test consuming a batch with messages."""
        # Create mock messages
        mock_messages = []
        for i in range(3):
            mock_msg = MagicMock()
            mock_msg.error.return_value = None
            mock_messages.append(mock_msg)

        # Configure consumer mock to return messages then None
        self.mock_kafka_consumer.poll.side_effect = mock_messages + [None]
        self.consumer.running = True
        self.consumer.consumer = self.mock_kafka_consumer

        # Call the method
        result = self.consumer.consume_batch()

        # Check the result
        self.assertEqual(result, mock_messages)
        self.assertEqual(len(result), 3)

        # Verify poll was called multiple times
        self.assertEqual(self.mock_kafka_consumer.poll.call_count, 4)

        # Verify batch size metric was recorded
        self.mock_metrics_instance.observe_batch_size.assert_called_once_with(3)

    def test_consume_batch_with_errors(self):
        """Test consuming a batch with some error messages."""
        from confluent_kafka import KafkaError

        # Create mock messages with errors
        error_msg = MagicMock()
        error_msg.error.return_value = MagicMock(code=lambda: 123)  # Generic error

        eof_msg = MagicMock()
        eof_msg.error.return_value = MagicMock(code=lambda: KafkaError._PARTITION_EOF)
        eof_msg.partition.return_value = 1

        good_msg = MagicMock()
        good_msg.error.return_value = None

        # Configure consumer mock
        self.mock_kafka_consumer.poll.side_effect = [error_msg, eof_msg, good_msg, None]
        self.consumer.running = True
        self.consumer.consumer = self.mock_kafka_consumer

        # Call the method
        result = self.consumer.consume_batch()

        # Check the result - only good messages should be included
        self.assertEqual(result, [good_msg])

        # Verify error metrics were recorded
        self.mock_metrics_instance.increment_processing_errors.assert_called_once()

    def test_process_and_store_batch_empty(self):
        """Test processing an empty batch."""
        # Call the method
        result = self.consumer.process_and_store_batch([])

        # Check the result
        self.assertTrue(result)

        # Verify no further calls were made
        self.mock_processor_instance.process_batch.assert_not_called()
        self.mock_storage_instance.insert_batch.assert_not_called()

    def test_process_and_store_batch_success(self):
        """Test successful processing and storing of a batch."""
        # Create mock messages
        mock_messages = [MagicMock() for _ in range(3)]

        # Configure processor mock
        processed_messages = [{"id": f"msg-{i}", "data": f"value-{i}"} for i in range(3)]
        self.mock_processor_instance.process_batch.return_value = processed_messages

        # Configure storage mock
        self.mock_storage_instance.insert_batch.return_value = True

        # Call the method
        result = self.consumer.process_and_store_batch(mock_messages)

        # Check the result
        self.assertTrue(result)

        # Verify processor was called
        self.mock_processor_instance.process_batch.assert_called_once_with(mock_messages)

        # Verify storage was called
        self.mock_storage_instance.insert_batch.assert_called_once_with(processed_messages)

        # Verify metrics were recorded
        self.mock_metrics_instance.increment_messages_processed.assert_called_once_with(3)
        self.mock_metrics_instance.observe_mongodb_write_time.assert_called_once()

    def test_process_and_store_batch_storage_failure(self):
        """Test handling storage failure during batch processing."""
        # Create mock messages
        mock_messages = [MagicMock() for _ in range(3)]

        # Configure processor mock
        processed_messages = [{"id": f"msg-{i}", "data": f"value-{i}"} for i in range(3)]
        self.mock_processor_instance.process_batch.return_value = processed_messages

        # Configure storage mock to fail
        self.mock_storage_instance.insert_batch.return_value = False

        # Mock send_to_dead_letter
        with patch.object(self.consumer, 'send_to_dead_letter', return_value=True) as mock_send_dlq:
            # Call the method
            result = self.consumer.process_and_store_batch(mock_messages)

            # Check the result
            self.assertFalse(result)

            # Verify send_to_dead_letter was called for each message
            self.assertEqual(mock_send_dlq.call_count, 3)

    def test_commit_offsets(self):
        """Test committing offsets."""
        # Set up mock
        self.consumer.consumer = self.mock_kafka_consumer
        self.consumer.messages_since_commit = 50

        # Call the method
        self.consumer.commit_offsets()

        # Verify offset commit was called
        self.mock_kafka_consumer.commit.assert_called_once_with(asynchronous=False)

        # Verify messages counter was reset
        self.assertEqual(self.consumer.messages_since_commit, 0)

        # Verify metrics were recorded
        self.mock_metrics_instance.observe_offset_commit_time.assert_called_once()

    def test_send_to_dead_letter(self):
        """Test sending a message to the dead letter topic."""
        # Create mock message
        mock_message = MagicMock()
        mock_message.value.return_value = b'{"test": "data"}'
        mock_message.key.return_value = b"test-key"
        mock_message.topic.return_value = "data-topic"
        mock_message.partition.return_value = 0
        mock_message.offset.return_value = 123

        # Make sure producer is set
        self.consumer.producer = self.mock_kafka_producer

        # Call the method
        result = self.consumer.send_to_dead_letter(mock_message, "Test error")

        # Check the result
        self.assertTrue(result)

        # Verify producer was called
        self.mock_kafka_producer.produce.assert_called_once()
        self.mock_kafka_producer.poll.assert_called_once_with(0)

        # Check the dead letter message format
        call_args = self.mock_kafka_producer.produce.call_args[0]
        self.assertEqual(call_args[0], "dead-letter-topic")

        kwargs = self.mock_kafka_producer.produce.call_args[1]
        self.assertEqual(kwargs["key"], b"test-key")

        # Verify the value is a valid JSON with expected fields
        value_json = json.loads(kwargs["value"].decode('utf-8'))
        self.assertIn("original_message", value_json)
        self.assertIn("error", value_json)
        self.assertEqual(value_json["error"], "Test error")
        self.assertEqual(value_json["topic"], "data-topic")
        self.assertEqual(value_json["partition"], 0)
        self.assertEqual(value_json["offset"], 123)

    @patch('src.consumer.time.time')
    @patch('src.consumer.time.sleep')
    def test_run_method(self, mock_sleep, mock_time):
        """Test the main run loop."""
        # Set up mocks
        mock_time.return_value = 1234567890.0

        # Mock connect methods to succeed
        with patch.object(self.consumer, 'connect_kafka', return_value=True) as mock_connect_kafka:
            with patch.object(self.consumer, 'consume_batch') as mock_consume_batch:
                with patch.object(self.consumer, 'process_and_store_batch', return_value=True) as mock_process:
                    with patch.object(self.consumer, 'calculate_lag') as mock_calc_lag:
                        # Make the run loop execute only once
                        def set_running_false(*args, **kwargs):
                            self.consumer.running = False
                            return [MagicMock()]

                        mock_consume_batch.side_effect = set_running_false

                        # Configure storage mock
                        self.mock_storage_instance.connect.return_value = True

                        # Call the method
                        self.consumer.run()

                        # Verify methods were called
                        mock_connect_kafka.assert_called_once()
                        mock_consume_batch.assert_called_once()
                        mock_process.assert_called_once()
                        mock_calc_lag.assert_called_once()

    def test_calculate_lag(self):
        """Test calculating consumer lag."""
        # Create mock for assignment and watermark offsets
        mock_assignment = [MagicMock(), MagicMock()]
        self.mock_kafka_consumer.assignment.return_value = mock_assignment

        # Configure watermark offsets
        self.mock_kafka_consumer.get_watermark_offsets.side_effect = [
            (100, 200),  # (low, high) for partition 1
            (200, 350)   # (low, high) for partition 2
        ]

        # Configure positions
        self.mock_kafka_consumer.position.side_effect = [
            [150],  # position for partition 1
            [300]   # position for partition 2
        ]

        # Call the method
        self.consumer.consumer = self.mock_kafka_consumer
        self.consumer.calculate_lag()

        # Verify lag calculation (200-150 + 350-300 = 100)
        self.mock_metrics_instance.set_consumer_lag.assert_called_once_with(100)

if __name__ == '__main__':
    unittest.main()

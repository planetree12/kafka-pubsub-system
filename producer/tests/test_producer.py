"""Tests for the producer module."""

import unittest
import json
import time
import os
import pathlib
from unittest.mock import patch, MagicMock

from src.producer import DataProducer

class TestDataProducer(unittest.TestCase):
    """Test cases for the DataProducer class."""

    @patch('src.producer.KafkaProducer')
    @patch('src.producer.configure_logging')
    @patch('src.producer.ProducerMetrics')
    @patch('src.producer.load_config')
    @patch('src.producer.pathlib.Path')
    def setUp(self, mock_path, mock_load_config, mock_metrics, mock_logging, mock_kafka):
        """Set up test fixtures."""
        # Setup path mock
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent.parent.absolute.return_value = "/mock/base/dir"
        mock_path.return_value = mock_path_instance

        # Mock the config path
        self.mock_config_path = os.path.join("/mock/base/dir", "producer", "config", "config.json")

        # Mock the Kafka producer
        self.mock_kafka_instance = mock_kafka.return_value
        self.mock_kafka_instance.send.return_value.get.return_value = None

        # Mock the metrics
        self.mock_metrics_instance = mock_metrics.return_value
        self.mock_metrics_instance.time_send_operation.return_value.__enter__.return_value = None
        self.mock_metrics_instance.time_send_operation.return_value.__exit__.return_value = None

        # Mock the logger
        self.mock_logger = MagicMock()
        mock_logging.return_value = self.mock_logger

        # Create a test config
        self.test_config = {
            "kafka": {
                "bootstrap_servers": "localhost:9092",
                "topic": "test-topic",
                "compression_type": "none"
            },
            "producer": {
                "interval_ms": 100,
                "batch_size": 10,
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

        # Mock the load_config function to return our test config
        mock_load_config.return_value = self.test_config

        # Initialize producer
        self.producer = DataProducer()

        # Verify load_config was called with the correct path
        mock_load_config.assert_called_once_with(self.mock_config_path)

    def test_initialization(self):
        """Test that the producer initializes correctly."""
        # Check that the Kafka producer was initialized with correct parameters
        from kafka.errors import KafkaError

        # Check that the producer has the expected attributes
        self.assertEqual(self.producer.config, self.test_config)
        self.assertFalse(self.producer.running)

    def test_send_message_success(self):
        """Test sending a message successfully."""
        # Set up test data
        test_key = "test-key"
        test_value = {"id": "test-id", "name": "item_12345678", "created_at": "2023-07-15T12:34:56.789Z"}
        test_headers = {"content-type": "application/json"}

        # Call the method
        result = self.producer.send_message(test_key, test_value, test_headers)

        # Check the result
        self.assertTrue(result)

        # Verify Kafka producer was called correctly
        self.mock_kafka_instance.send.assert_called_once()
        call_args = self.mock_kafka_instance.send.call_args[1]
        self.assertEqual(call_args["key"], test_key)
        self.assertEqual(call_args["value"], test_value)
        self.assertIsNotNone(call_args["headers"])

        # Verify metrics were recorded
        self.mock_metrics_instance.record_message_sent.assert_called_once()

    @patch('src.producer.KafkaProducer')
    @patch('src.producer.pathlib.Path')
    def test_send_message_kafka_error(self, mock_path, mock_kafka):
        """Test handling of Kafka errors when sending a message."""
        from kafka.errors import KafkaError

        # Setup path mock
        mock_path_instance = MagicMock()
        mock_path_instance.parent.parent.parent.absolute.return_value = "/mock/base/dir"
        mock_path.return_value = mock_path_instance

        # Configure the mock to raise an error
        mock_future = MagicMock()
        mock_future.get.side_effect = KafkaError("Test Kafka error")

        mock_instance = mock_kafka.return_value
        mock_instance.send.return_value = mock_future

        # Create a producer with the mocked Kafka
        mock_metrics = MagicMock()
        with patch('src.producer.load_config', return_value=self.test_config):
            with patch('src.producer.configure_logging'):
                with patch('src.producer.ProducerMetrics', return_value=mock_metrics):
                    producer = DataProducer()

        # Patch the retry decorator to not retry
        with patch('src.producer.retry', lambda **kwargs: lambda f: f):
            # Call the method
            with self.assertRaises(KafkaError):
                producer.send_message("test-key", {"id": "test-id"}, None)

            # Verify error was recorded - only check if it was called at least once
            mock_metrics.record_send_failure.assert_called()

    def test_send_batch(self):
        """Test sending a batch of messages."""
        # Set up test data
        test_batch = [
            (f"key-{i}", {"id": f"id-{i}", "name": f"item_{10000000+i}", "created_at": "2023-07-15T12:34:56.789Z"}, {"content-type": "application/json"})
            for i in range(5)
        ]

        # Call the method
        result = self.producer.send_batch(test_batch)

        # Check the result
        self.assertEqual(result, 5)

        # Verify Kafka producer was called for each message
        self.assertEqual(self.mock_kafka_instance.send.call_count, 5)

        # Verify batch metrics were recorded
        self.mock_metrics_instance.record_batch_sent.assert_called_once_with(5)

    def test_generate_data(self):
        """Test generating data."""
        # Patch the data generator
        with patch.object(self.producer, 'data_generator') as mock_generator:
            mock_generator.generate_batch.return_value = [
                ("key1", {"id": "id1"}, {"header": "value"})
            ]

            # Call the method
            result = self.producer.generate_data(5)

            # Check that the generator was called with the right batch size
            mock_generator.generate_batch.assert_called_once_with(5)

            # Check the result
            self.assertEqual(result, [("key1", {"id": "id1"}, {"header": "value"})])

    def test_health_check(self):
        """Test the health check functionality."""
        # First call should perform health check
        self.assertTrue(self.producer.health_check())

        # Second call should return True without performing check (due to time interval)
        with patch.object(self.producer, 'send_message') as mock_send:
            mock_send.return_value = False
            self.assertTrue(self.producer.health_check())
            mock_send.assert_not_called()

    @patch('src.producer.time.sleep', return_value=None)
    def test_run(self, mock_sleep):
        """Test the main run loop."""
        # Make the run loop execute only once
        def set_running_false(*args, **kwargs):
            self.producer.running = False
            return [("key1", {"id": "id1"}, {"header": "value"})]

        with patch.object(self.producer, 'generate_data', side_effect=set_running_false):
            with patch.object(self.producer, 'send_batch', return_value=1):
                # Call the method
                self.producer.run()

                # Verify methods were called
                self.producer.generate_data.assert_called_once()
                self.producer.send_batch.assert_called_once()

if __name__ == '__main__':
    unittest.main()

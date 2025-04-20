"""Tests for the utility modules."""

import unittest
import json
import logging
import os
import tempfile
from unittest.mock import patch, MagicMock, call

import prometheus_client

from src.utils.config import load_config
from src.utils.logging import setup_logging, JsonFormatter
from src.utils.metrics import MetricsCollector


class TestConfig(unittest.TestCase):
    """Test cases for the config module."""

    def test_load_config_default_path(self):
        """Test loading configuration with default path."""
        # Create a mock config data
        config_data = {
            "test": "data",
            "nested": {"key": "value"}
        }

        # Mock open to return our test config
        mock_open = unittest.mock.mock_open(read_data=json.dumps(config_data))

        # Mock os.path functions
        with patch('os.path.dirname', return_value='/mock/dir'):
            with patch('os.path.abspath', return_value='/mock/dir/utils'):
                with patch('os.path.join', return_value='/mock/config/path.json'):
                    with patch('builtins.open', mock_open):
                        # Call the function
                        result = load_config()

                        # Check the result
                        self.assertEqual(result, config_data)

                        # Verify open was called with the expected path
                        mock_open.assert_called_once_with('/mock/config/path.json', 'r')

    def test_load_config_custom_path(self):
        """Test loading configuration with a custom path."""
        # Create a mock config data
        config_data = {
            "test": "data",
            "nested": {"key": "value"}
        }

        # Create a temporary file with test config
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            json.dump(config_data, temp_file)
            config_path = temp_file.name

        try:
            # Call the function with the temp file path
            result = load_config(config_path)

            # Check the result
            self.assertEqual(result, config_data)

        finally:
            # Clean up
            os.unlink(config_path)

    def test_load_config_file_not_found(self):
        """Test handling of FileNotFoundError."""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            with self.assertRaises(FileNotFoundError):
                load_config('/nonexistent/path')

    def test_load_config_invalid_json(self):
        """Test handling of invalid JSON."""
        # Mock open to return invalid JSON
        mock_open = unittest.mock.mock_open(read_data='not a valid json')

        with patch('builtins.open', mock_open):
            with self.assertRaises(json.JSONDecodeError):
                load_config('/mock/path')


class TestLogging(unittest.TestCase):
    """Test cases for the logging module."""

    def test_json_formatter(self):
        """Test the JSON formatter."""
        # Create a record with test data
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Add custom properties
        record.props = {
            'custom_key': 'custom_value',
            'another_key': 123
        }

        # Format the record
        formatter = JsonFormatter()
        result = formatter.format(record)

        # Parse the result back to a dict for verification
        result_dict = json.loads(result)

        # Check required fields
        self.assertEqual(result_dict['level'], 'INFO')
        self.assertIn('time', result_dict)
        self.assertEqual(result_dict['message'], 'Test message')

        # Check custom properties
        self.assertEqual(result_dict['custom_key'], 'custom_value')
        self.assertEqual(result_dict['another_key'], 123)

    @patch('src.utils.logging.logging.StreamHandler')
    @patch('src.utils.logging.logging.getLogger')
    def test_setup_logging_json(self, mock_get_logger, mock_stream_handler):
        """Test setting up logging with JSON format."""
        # Set up mocks
        mock_root_logger = MagicMock()
        mock_get_logger.return_value = mock_root_logger

        mock_handler = MagicMock()
        mock_stream_handler.return_value = mock_handler

        # Test config with JSON format
        test_config = {
            "logging": {
                "level": "DEBUG",
                "format": "json"
            }
        }

        # Call the function
        setup_logging(test_config)

        # Verify logger was configured correctly
        mock_root_logger.setLevel.assert_any_call(logging.DEBUG)
        mock_root_logger.addHandler.assert_called_once_with(mock_handler)

        # Verify formatter was set to JsonFormatter
        mock_handler.setFormatter.assert_called_once()
        formatter = mock_handler.setFormatter.call_args[0][0]
        self.assertIsInstance(formatter, JsonFormatter)

    @patch('src.utils.logging.logging.StreamHandler')
    @patch('src.utils.logging.logging.getLogger')
    def test_setup_logging_text(self, mock_get_logger, mock_stream_handler):
        """Test setting up logging with text format."""
        # Set up mocks
        mock_root_logger = MagicMock()
        mock_get_logger.return_value = mock_root_logger

        mock_handler = MagicMock()
        mock_stream_handler.return_value = mock_handler

        # Test config with text format
        test_config = {
            "logging": {
                "level": "INFO",
                "format": "text"
            }
        }

        # Call the function
        setup_logging(test_config)

        # Verify logger was configured correctly
        mock_root_logger.setLevel.assert_any_call(logging.INFO)
        mock_root_logger.addHandler.assert_called_once_with(mock_handler)

        # Verify formatter was set to regular Formatter
        mock_handler.setFormatter.assert_called_once()
        formatter = mock_handler.setFormatter.call_args[0][0]
        self.assertIsInstance(formatter, logging.Formatter)


class TestMetrics(unittest.TestCase):
    """Test cases for the metrics module."""

    @patch('src.utils.metrics.start_http_server')
    def test_metrics_initialization_enabled(self, mock_start_http_server):
        """Test initialization with metrics enabled."""
        # Test config with metrics enabled
        test_config = {
            "metrics": {
                "enabled": True,
                "port": 8001
            }
        }

        # Call the constructor
        metrics = MetricsCollector(test_config)

        # Verify server was started
        self.assertTrue(metrics.enabled)
        self.assertEqual(metrics.port, 8001)
        mock_start_http_server.assert_called_once_with(8001)

    @patch('src.utils.metrics.start_http_server')
    def test_metrics_initialization_disabled(self, mock_start_http_server):
        """Test initialization with metrics disabled."""
        # Test config with metrics disabled
        test_config = {
            "metrics": {
                "enabled": False,
                "port": 8001
            }
        }

        # Call the constructor
        metrics = MetricsCollector(test_config)

        # Verify server was not started
        self.assertFalse(metrics.enabled)
        mock_start_http_server.assert_not_called()

    @patch('src.utils.metrics.MESSAGES_PROCESSED')
    def test_increment_messages_processed(self, mock_counter):
        """Test incrementing the messages processed counter."""
        # Create metrics collector with metrics enabled
        metrics = MetricsCollector({"metrics": {"enabled": True}})

        # Call the method
        metrics.increment_messages_processed(5)

        # Verify counter was incremented
        mock_counter.inc.assert_called_once_with(5)

    @patch('src.utils.metrics.MESSAGES_PROCESSED')
    def test_increment_messages_processed_disabled(self, mock_counter):
        """Test that counter is not incremented when metrics are disabled."""
        # Create metrics collector with metrics disabled
        metrics = MetricsCollector({"metrics": {"enabled": False}})

        # Call the method
        metrics.increment_messages_processed(5)

        # Verify counter was not incremented
        mock_counter.inc.assert_not_called()

    @patch('src.utils.metrics.PROCESSING_ERRORS')
    def test_increment_processing_errors(self, mock_counter):
        """Test incrementing the processing errors counter."""
        # Create metrics collector with metrics enabled
        metrics = MetricsCollector({"metrics": {"enabled": True}})

        # Call the method
        metrics.increment_processing_errors(3)

        # Verify counter was incremented
        mock_counter.inc.assert_called_once_with(3)

    @patch('src.utils.metrics.BATCH_SIZE')
    def test_observe_batch_size(self, mock_histogram):
        """Test observing batch size."""
        # Create metrics collector with metrics enabled
        metrics = MetricsCollector({"metrics": {"enabled": True}})

        # Call the method
        metrics.observe_batch_size(100)

        # Verify histogram was updated
        mock_histogram.observe.assert_called_once_with(100)

    @patch('src.utils.metrics.CONSUMER_LAG')
    def test_set_consumer_lag(self, mock_gauge):
        """Test setting consumer lag gauge."""
        # Create metrics collector with metrics enabled
        metrics = MetricsCollector({"metrics": {"enabled": True}})

        # Call the method
        metrics.set_consumer_lag(50)

        # Verify gauge was set
        mock_gauge.set.assert_called_once_with(50)

    @patch('src.utils.metrics.ACTIVE_CONNECTIONS')
    def test_set_active_connections(self, mock_gauge):
        """Test setting active connections gauge."""
        # Mock the labels method
        mock_label_gauge = MagicMock()
        mock_gauge.labels.return_value = mock_label_gauge

        # Create metrics collector with metrics enabled
        metrics = MetricsCollector({"metrics": {"enabled": True}})

        # Call the method
        metrics.set_active_connections('kafka', 3)

        # Verify gauge was set with the correct label
        mock_gauge.labels.assert_called_once_with(connection_type='kafka')
        mock_label_gauge.set.assert_called_once_with(3)


if __name__ == '__main__':
    unittest.main()

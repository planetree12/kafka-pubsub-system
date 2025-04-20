"""Tests for the data processor module."""

import unittest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.data_processor import DataProcessor


class TestDataProcessor(unittest.TestCase):
    """Test cases for the DataProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = DataProcessor()

    def test_process_message_valid(self):
        """Test processing a valid message."""
        # Create a mock message
        mock_message = MagicMock()
        mock_message.value.return_value = json.dumps({
            "id": "test-id",
            "name": "item_12345678",
            "created_at": "2023-07-15T12:34:56.789Z",
            "metadata": {
                "source": "system-a",
                "version": "1.0.0"
            }
        }).encode('utf-8')

        # Call the method
        success, processed_message = self.processor.process_message(mock_message)

        # Check the result
        self.assertTrue(success)
        self.assertIsNotNone(processed_message)
        self.assertEqual(processed_message["id"], "test-id")
        self.assertEqual(processed_message["name"], "item_12345678")
        self.assertEqual(processed_message["created_at"], "2023-07-15T12:34:56.789Z")
        self.assertIn("received_at", processed_message)
        # Verify received_at is in the expected format (ISO 8601)
        self.assertRegex(processed_message["received_at"], r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z")

    def test_process_message_none(self):
        """Test processing a None message."""
        # Call the method with None
        success, processed_message = self.processor.process_message(None)

        # Check the result
        self.assertFalse(success)
        self.assertIsNone(processed_message)

    def test_process_message_empty_value(self):
        """Test processing a message with empty value."""
        # Create a mock message with empty value
        mock_message = MagicMock()
        mock_message.value.return_value = None

        # Call the method
        success, processed_message = self.processor.process_message(mock_message)

        # Check the result
        self.assertFalse(success)
        self.assertIsNone(processed_message)

    def test_process_message_invalid_json(self):
        """Test processing a message with invalid JSON."""
        # Create a mock message with invalid JSON
        mock_message = MagicMock()
        mock_message.value.return_value = b'not a valid json'

        # Call the method
        success, processed_message = self.processor.process_message(mock_message)

        # Check the result
        self.assertFalse(success)
        self.assertIsNone(processed_message)

    def test_process_message_not_dict(self):
        """Test processing a message that doesn't contain a JSON object."""
        # Create a mock message with an array instead of an object
        mock_message = MagicMock()
        mock_message.value.return_value = json.dumps(["item1", "item2"]).encode('utf-8')

        # Call the method
        success, processed_message = self.processor.process_message(mock_message)

        # Check the result
        self.assertFalse(success)
        self.assertIsNone(processed_message)

    @patch('src.data_processor.datetime')
    def test_process_message_received_at(self, mock_datetime):
        """Test that received_at timestamp is added."""
        # Mock datetime.utcnow to return a fixed value
        mock_now = datetime(2023, 7, 15, 12, 34, 56, 789000)
        mock_datetime.utcnow.return_value = mock_now

        # Create a mock message
        mock_message = MagicMock()
        mock_message.value.return_value = json.dumps({
            "id": "test-id",
            "data": "test-data"
        }).encode('utf-8')

        # Call the method
        success, processed_message = self.processor.process_message(mock_message)

        # Check the result
        self.assertTrue(success)
        self.assertIn("received_at", processed_message)
        self.assertEqual(processed_message["received_at"], "2023-07-15T12:34:56.789000Z")

    def test_process_batch_empty(self):
        """Test processing an empty batch."""
        # Call the method with an empty list
        result = self.processor.process_batch([])

        # Check the result
        self.assertEqual(result, [])

    def test_process_batch_mixed(self):
        """Test processing a batch with mixed valid and invalid messages."""
        # Create mock messages
        valid_message1 = MagicMock()
        valid_message1.value.return_value = json.dumps({"id": "id1", "data": "value1"}).encode('utf-8')

        valid_message2 = MagicMock()
        valid_message2.value.return_value = json.dumps({"id": "id2", "data": "value2"}).encode('utf-8')

        invalid_message = MagicMock()
        invalid_message.value.return_value = b'not a json'

        # Call the method
        result = self.processor.process_batch([valid_message1, invalid_message, valid_message2])

        # Check the result - should only include valid messages
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "id1")
        self.assertEqual(result[1]["id"], "id2")

if __name__ == '__main__':
    unittest.main()

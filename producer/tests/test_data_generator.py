"""Tests for the data generator module."""

import unittest
from unittest.mock import patch, MagicMock
from src.data_generator import DataGenerator

class TestDataGenerator(unittest.TestCase):
    """Test cases for the DataGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "kafka": {
                "bootstrap_servers": "localhost:9092",
                "topic": "test-topic"
            },
            "producer": {
                "interval_ms": 100,
                "batch_size": 10
            }
        }
        self.generator = DataGenerator(self.test_config)

    def test_generate_event(self):
        """Test that an event can be generated."""
        key, value, headers = self.generator.generate_event()

        # Check key is a UUID string
        self.assertIsInstance(key, str)
        self.assertTrue(len(key) > 0)

        # Check value has expected structure
        self.assertIsInstance(value, dict)
        self.assertIn('id', value)
        self.assertIn('name', value)
        self.assertIn('created_at', value)
        self.assertIn('metadata', value)

        # Check value data types
        self.assertIsInstance(value['id'], str)
        self.assertIsInstance(value['name'], str)
        self.assertIsInstance(value['created_at'], str)
        self.assertIsInstance(value['metadata'], dict)

        # Check metadata structure
        self.assertIn('source', value['metadata'])
        self.assertIn('version', value['metadata'])

        # Check name format
        self.assertTrue(value['name'].startswith('item_'))
        self.assertEqual(len(value['name']), 13)  # "item_" + 8 digits

        # Check headers
        self.assertIsInstance(headers, dict)
        self.assertIn('content-type', headers)
        self.assertIn('created_at', headers)
        self.assertEqual(headers['content-type'], 'application/json')

    def test_generate_batch(self):
        """Test that a batch of events can be generated."""
        batch_size = 10
        batch = self.generator.generate_batch(batch_size)

        # Check batch size
        self.assertEqual(len(batch), batch_size)

        # Check each event format
        for key, value, headers in batch:
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, dict)
            self.assertIn('id', value)
            self.assertIn('name', value)
            self.assertIn('created_at', value)
            self.assertIn('metadata', value)
            self.assertIsInstance(headers, dict)

        # Check all event IDs are unique
        ids = [event[1]['id'] for event in batch]
        self.assertEqual(len(ids), len(set(ids)))

        # Check all keys are unique
        keys = [event[0] for event in batch]
        self.assertEqual(len(keys), len(set(keys)))

if __name__ == '__main__':
    unittest.main()

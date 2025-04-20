"""Tests for the MongoDB storage module."""

import unittest
import time
from unittest.mock import patch, MagicMock, call

import pymongo
from pymongo.errors import PyMongoError, BulkWriteError

from src.storage import MongoDBHandler


class TestMongoDBHandler(unittest.TestCase):
    """Test cases for the MongoDBHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "mongodb": {
                "uri": "mongodb://mongodb:27017",
                "database": "pubsub_data",
                "collection": "messages"
            },
            "consumer": {
                "max_retries": 3,
                "retry_backoff_ms": 1000
            }
        }

        # Set up mock for pymongo.MongoClient
        self.mongo_client_patcher = patch('src.storage.pymongo.MongoClient')
        self.mock_mongo_client = self.mongo_client_patcher.start()

        # Mock the MongoClient instance
        self.mock_client_instance = MagicMock()
        self.mock_mongo_client.return_value = self.mock_client_instance

        # Mock the admin property and command method
        self.mock_admin = MagicMock()
        self.mock_client_instance.admin = self.mock_admin
        self.mock_admin.command.return_value = {"ok": 1}

        # Mock the database and collection
        self.mock_db = MagicMock()
        self.mock_collection = MagicMock()
        self.mock_client_instance.__getitem__.return_value = self.mock_db
        self.mock_db.__getitem__.return_value = self.mock_collection

        # Create the handler
        self.storage = MongoDBHandler(self.test_config)

    def tearDown(self):
        """Clean up after test."""
        self.mongo_client_patcher.stop()

    def test_initialization(self):
        """Test that the handler initializes correctly."""
        self.assertEqual(self.storage.uri, "mongodb://mongodb:27017")
        self.assertEqual(self.storage.database_name, "pubsub_data")
        self.assertEqual(self.storage.collection_name, "messages")
        self.assertEqual(self.storage.max_retries, 3)
        self.assertEqual(self.storage.retry_backoff_ms, 1000)

        # Client and DB should be None initially
        self.assertIsNone(self.storage.client)
        self.assertIsNone(self.storage.db)
        self.assertIsNone(self.storage.collection)

    def test_connect_success(self):
        """Test successful MongoDB connection."""
        # Call the method
        result = self.storage.connect()

        # Check the result
        self.assertTrue(result)

        # Verify that MongoDB client was created with the correct URI
        self.mock_mongo_client.assert_called_once_with(
            "mongodb://mongodb:27017",
            serverSelectionTimeoutMS=5000
        )

        # Verify admin command was called to check connection
        self.mock_admin.command.assert_called_once_with('ping')

        # Verify database and collection were initialized
        self.assertEqual(self.storage.client, self.mock_client_instance)
        self.assertEqual(self.storage.db, self.mock_db)
        self.assertEqual(self.storage.collection, self.mock_collection)

        # Verify create_indexes was called
        self.mock_collection.list_indexes.assert_called_once()

    @patch('src.storage.time.sleep', return_value=None)
    def test_connect_failure_retry(self, mock_sleep):
        """Test connection failure with retry."""
        # Configure mongo client to fail twice and then succeed
        self.mock_mongo_client.side_effect = [
            PyMongoError("Test DB error 1"),
            PyMongoError("Test DB error 2"),
            self.mock_client_instance
        ]

        # Call the method
        result = self.storage.connect()

        # Check the result
        self.assertTrue(result)

        # Verify MongoDB client was created the expected number of times
        self.assertEqual(self.mock_mongo_client.call_count, 3)

        # Verify sleep was called with exponential backoff
        mock_sleep.assert_has_calls([
            call(1.0),  # First retry: 1000ms
            call(2.0)   # Second retry: 2000ms (doubling)
        ])

    @patch('src.storage.time.sleep', return_value=None)
    def test_connect_failure_max_retries(self, mock_sleep):
        """Test connection failure reaching max retries."""
        # Configure mongo client to always fail
        self.mock_mongo_client.side_effect = PyMongoError("Test DB error")

        # Call the method
        result = self.storage.connect()

        # Check the result
        self.assertFalse(result)

        # Verify MongoDB client was created max_retries times
        self.assertEqual(self.mock_mongo_client.call_count, self.storage.max_retries)

        # Verify sleep was called the expected number of times
        self.assertEqual(mock_sleep.call_count, self.storage.max_retries - 1)

    def test_create_indexes_new(self):
        """Test creating an index that doesn't exist."""
        # Set up mock for list_indexes
        mock_index_list = []
        self.mock_collection.list_indexes.return_value = mock_index_list

        # Initialize storage with connection
        self.storage.client = self.mock_client_instance
        self.storage.db = self.mock_db
        self.storage.collection = self.mock_collection

        # Call the method
        self.storage.create_indexes()

        # Verify create_index was called
        self.mock_collection.create_index.assert_called_once_with(
            [('created_at', pymongo.ASCENDING)],
            background=True
        )

    def test_create_indexes_existing(self):
        """Test handling an index that already exists."""
        # Set up mock for list_indexes
        mock_index = {"name": "created_at_1"}
        self.mock_collection.list_indexes.return_value = [mock_index]

        # Initialize storage with connection
        self.storage.client = self.mock_client_instance
        self.storage.db = self.mock_db
        self.storage.collection = self.mock_collection

        # Call the method
        self.storage.create_indexes()

        # Verify create_index was not called (index already exists)
        self.mock_collection.create_index.assert_not_called()

    def test_insert_batch_empty(self):
        """Test inserting an empty batch."""
        # Initialize storage with connection
        self.storage.client = self.mock_client_instance
        self.storage.db = self.mock_db
        self.storage.collection = self.mock_collection

        # Call the method with empty list
        result = self.storage.insert_batch([])

        # Check the result
        self.assertTrue(result)

        # Verify insert_many was not called
        self.mock_collection.insert_many.assert_not_called()

    def test_insert_batch_success(self):
        """Test successful batch insert."""
        # Set up mock for insert_many
        mock_result = MagicMock()
        mock_result.inserted_ids = ["id1", "id2", "id3"]
        self.mock_collection.insert_many.return_value = mock_result

        # Initialize storage with connection
        self.storage.client = self.mock_client_instance
        self.storage.db = self.mock_db
        self.storage.collection = self.mock_collection

        # Test data
        documents = [
            {"id": "id1", "data": "value1"},
            {"id": "id2", "data": "value2"},
            {"id": "id3", "data": "value3"}
        ]

        # Call the method
        result = self.storage.insert_batch(documents)

        # Check the result
        self.assertTrue(result)

        # Verify insert_many was called correctly
        self.mock_collection.insert_many.assert_called_once()

        # Verify _id was set for each document
        documents_with_id = self.mock_collection.insert_many.call_args[0][0]
        for i, doc in enumerate(documents_with_id):
            self.assertEqual(doc["_id"], f"id{i+1}")

    def test_insert_batch_duplicate_key(self):
        """Test handling duplicate key errors in batch insert."""
        # Set up mock for insert_many to raise BulkWriteError with duplicate key
        error_details = {
            "writeErrors": [
                {"code": 11000, "index": 1, "errmsg": "Duplicate key error"}
            ]
        }
        bulk_write_error = BulkWriteError(error_details)
        self.mock_collection.insert_many.side_effect = bulk_write_error

        # Initialize storage with connection
        self.storage.client = self.mock_client_instance
        self.storage.db = self.mock_db
        self.storage.collection = self.mock_collection

        # Test data
        documents = [
            {"id": "id1", "data": "value1"},
            {"id": "id2", "data": "value2"} # This one causes duplicate key error
        ]

        # Call the method
        result = self.storage.insert_batch(documents)

        # Check the result - should still return True for duplicate key errors
        self.assertTrue(result)

        # Verify insert_many was called
        self.mock_collection.insert_many.assert_called_once()

    @patch('src.storage.time.sleep', return_value=None)
    def test_insert_batch_failure_retry(self, mock_sleep):
        """Test batch insert failure with retry."""
        # Set up mock for insert_many to fail twice then succeed
        mock_result = MagicMock()
        mock_result.inserted_ids = ["id1"]
        self.mock_collection.insert_many.side_effect = [
            PyMongoError("Test error 1"),
            PyMongoError("Test error 2"),
            mock_result
        ]

        # Initialize storage with connection
        self.storage.client = self.mock_client_instance
        self.storage.db = self.mock_db
        self.storage.collection = self.mock_collection

        # Test data
        documents = [{"id": "id1", "data": "value1"}]

        # Call the method
        result = self.storage.insert_batch(documents)

        # Check the result
        self.assertTrue(result)

        # Verify insert_many was called multiple times
        self.assertEqual(self.mock_collection.insert_many.call_count, 3)

        # Verify sleep was called with exponential backoff
        mock_sleep.assert_has_calls([
            call(1.0),  # First retry: 1000ms
            call(2.0)   # Second retry: 2000ms (doubling)
        ])

    def test_close(self):
        """Test closing the MongoDB connection."""
        # Mock the client
        mock_client = MagicMock()
        self.storage.client = mock_client

        # Call the method
        self.storage.close()

        # Verify client.close was called
        mock_client.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()

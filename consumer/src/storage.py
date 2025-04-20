"""
MongoDB storage module for persisting Kafka messages.
"""
import logging
import time
from typing import Dict, Any, List

import pymongo
from pymongo.errors import PyMongoError


class MongoDBHandler:
    """
    Handles MongoDB operations for storing consumed messages.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MongoDB handler with configuration.

        Args:
            config: Configuration dictionary with MongoDB settings
        """
        self.logger = logging.getLogger(__name__)
        self.uri = config.get('mongodb', {}).get('uri', 'mongodb://mongodb:27017')
        self.database_name = config.get('mongodb', {}).get('database', 'pubsub_data')
        self.collection_name = config.get('mongodb', {}).get('collection', 'messages')
        self.max_retries = config.get('consumer', {}).get('max_retries', 3)
        self.retry_backoff_ms = config.get('consumer', {}).get('retry_backoff_ms', 1000)
        self.client = None
        self.db = None
        self.collection = None

    def connect(self) -> bool:
        """
        Establish connection to MongoDB with retry logic.

        Returns:
            bool: True if connection successful, False otherwise
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.logger.info(f"Connecting to MongoDB at {self.uri}")
                self.client = pymongo.MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=5000  # 5 second timeout for server selection
                )
                # Verify connection is alive with a ping
                self.client.admin.command('ping')
                self.db = self.client[self.database_name]
                self.collection = self.db[self.collection_name]

                # Create indexes if they don't exist
                self.create_indexes()

                self.logger.info("Successfully connected to MongoDB")
                return True
            except PyMongoError as e:
                retry_count += 1
                backoff_time = (self.retry_backoff_ms / 1000) * (2 ** (retry_count - 1))
                self.logger.error(f"Failed to connect to MongoDB (attempt {retry_count}/{self.max_retries}): {str(e)}")

                if retry_count < self.max_retries:
                    self.logger.info(f"Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
                else:
                    self.logger.error("Maximum retries reached. Could not connect to MongoDB.")
                    return False

    def create_indexes(self) -> None:
        """
        Create necessary indexes in MongoDB collection if they don't already exist.
        This method is idempotent to handle multiple consumer instances.
        """
        try:
            # Check existing indexes
            existing_indexes = list(self.collection.list_indexes())
            index_names = [idx.get('name') for idx in existing_indexes]

            # Create created_at index if it doesn't exist
            if 'created_at_1' not in index_names:
                self.logger.info("Creating index on 'created_at' field")
                self.collection.create_index([('created_at', pymongo.ASCENDING)], background=True)
                self.logger.info("Index created successfully")
            else:
                self.logger.info("Index on 'created_at' already exists")
        except PyMongoError as e:
            self.logger.error(f"Failed to create indexes: {str(e)}")

    def insert_batch(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Insert a batch of documents with retry logic.

        Args:
            documents: List of documents to insert

        Returns:
            bool: True if insertion was successful, False otherwise
        """
        if not documents:
            return True

        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # Insert documents with _id as the message_id to ensure idempotency
                for doc in documents:
                    if 'id' in doc:
                        doc['_id'] = doc['id']

                start_time = time.time()
                result = self.collection.insert_many(
                    documents,
                    ordered=False  # Continue on error (duplicate key)
                )
                elapsed_time = time.time() - start_time

                inserted_count = len(result.inserted_ids)
                if inserted_count < len(documents):
                    self.logger.warning(
                        f"Partial batch insert: {inserted_count}/{len(documents)} documents inserted"
                    )
                else:
                    self.logger.info(
                        f"Successfully inserted {inserted_count} documents in {elapsed_time:.3f} seconds"
                    )
                return True

            except PyMongoError as e:
                retry_count += 1
                backoff_time = (self.retry_backoff_ms / 1000) * (2 ** (retry_count - 1))

                # Handle duplicate key errors (messages already processed)
                if isinstance(e, pymongo.errors.BulkWriteError) and all(
                    error.get('code') == 11000 for error in e.details.get('writeErrors', [])
                ):
                    self.logger.warning(f"Encountered duplicate keys during insert: {str(e)}")
                    return True

                self.logger.error(f"MongoDB insert error (attempt {retry_count}/{self.max_retries}): {str(e)}")

                if retry_count < self.max_retries:
                    self.logger.info(f"Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
                else:
                    self.logger.error("Maximum retries reached. Could not insert batch.")
                    return False

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed")

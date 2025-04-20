"""
Message processing module for Kafka consumer.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


class DataProcessor:
    """
    Processes Kafka messages for consumption and MongoDB storage.
    """

    def __init__(self):
        """Initialize the data processor."""
        self.logger = logging.getLogger(__name__)

    def process_message(self, message: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Process a single Kafka message.

        Args:
            message: Raw Kafka message object

        Returns:
            Tuple[bool, Optional[Dict]]: (success, processed_message)
        """
        try:
            # Extract message value (JSON string)
            if not message or not message.value():
                self.logger.warning("Received empty message")
                return False, None

            # Parse JSON message
            try:
                payload = json.loads(message.value().decode('utf-8'))
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse message as JSON: {str(e)}")
                return False, None

            # Validate message structure
            if not isinstance(payload, dict):
                self.logger.error(f"Invalid message format: expected dict, got {type(payload)}")
                return False, None

            # Add received_at timestamp
            payload['received_at'] = datetime.utcnow().isoformat() + 'Z'

            # Message is valid, return processed payload
            return True, payload

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return False, None

    def process_batch(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of Kafka messages.

        Args:
            messages: List of raw Kafka message objects

        Returns:
            List[Dict]: List of processed messages ready for MongoDB
        """
        processed_messages = []

        for message in messages:
            success, processed_message = self.process_message(message)
            if success and processed_message:
                processed_messages.append(processed_message)

        self.logger.info(f"Processed {len(processed_messages)}/{len(messages)} messages successfully")
        return processed_messages

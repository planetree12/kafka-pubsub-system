"""Data generator for the Kafka Producer."""

import uuid
import random
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple

class DataGenerator:
    """Generator for simple event data."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data generator.

        Args:
            config: Configuration dictionary.
        """
        self.config = config

    def generate_event(self) -> Tuple[str, Dict[str, Any], Dict[str, str]]:
        """
        Generate a single event with key, value and header.

        Returns:
            A tuple containing (key, value, headers) for Kafka message.
        """
        # 生成簡單的 UUID 作為 key
        key = str(uuid.uuid4())

        # 硬編碼生成固定結構的消息數據
        value = {
            "id": str(uuid.uuid4()),
            "name": f"item_{random.randint(10000000, 99999999)}",  # 8位數字
            "created_at": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "source": random.choice(["system-a", "system-b", "system-c"]),
                "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            }
        }

        # 簡單的 header
        headers = {
            "content-type": "application/json",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        return key, value, headers

    def generate_batch(self, size: int) -> List[Tuple[str, Dict[str, Any], Dict[str, str]]]:
        """
        Generate a batch of events.

        Args:
            size: The number of events to generate.

        Returns:
            A list of (key, value, headers) tuples.
        """
        return [self.generate_event() for _ in range(size)]

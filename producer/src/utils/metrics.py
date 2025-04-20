"""Metrics collection for the Kafka Producer using Prometheus."""

import threading
import time
from typing import Dict, Any
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from .logging import get_logger

logger = get_logger("metrics")

class ProducerMetrics:
    """Metrics collector for the Kafka Producer."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize metrics collector.

        Args:
            config: Metrics configuration.
        """
        self.config = config
        self.enabled = config["metrics"]["enabled"]

        if not self.enabled:
            logger.info("Metrics collection is disabled")
            return

        # Operational status (0 = down, 1 = up)
        self.operational_status = Gauge(
            "producer_operational_status",
            "Producer operational status (0 = down, 1 = up)"
        )

        # Message production rate
        self.messages_sent = Counter(
            "producer_messages_sent_total",
            "Total number of messages sent"
        )

        # Batch size
        self.batch_size = Histogram(
            "producer_batch_size",
            "Batch size distribution",
            buckets=[1, 10, 50, 100, 200, 500, 1000]
        )

        # Error rate
        self.message_send_failures = Counter(
            "producer_message_send_failures_total",
            "Total number of message send failures"
        )

        # Message send latency
        self.message_send_latency = Histogram(
            "producer_message_send_latency_seconds",
            "Message send latency in seconds",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5]
        )

        # Start metrics server
        self._start_metrics_server()

    def _start_metrics_server(self) -> None:
        """Start the Prometheus metrics server in a separate thread."""
        if not self.enabled:
            return

        def _run_server():
            port = self.config["metrics"]["port"]
            logger.info(f"Starting metrics server on port {port}")
            start_http_server(port)

        server_thread = threading.Thread(target=_run_server, daemon=True)
        server_thread.start()

    def record_operational_status(self, is_operational: bool) -> None:
        """
        Record the operational status of the producer.

        Args:
            is_operational: Whether the producer is operational.
        """
        if not self.enabled:
            return

        self.operational_status.set(1 if is_operational else 0)

    def record_message_sent(self) -> None:
        """Record a message sent event."""
        if not self.enabled:
            return

        self.messages_sent.inc()

    def record_batch_sent(self, batch_size: int) -> None:
        """
        Record a batch sent event.

        Args:
            batch_size: The size of the batch.
        """
        if not self.enabled:
            return

        self.batch_size.observe(batch_size)

    def record_send_failure(self, error_type: str = None, count: int = 1) -> None:
        """
        Record a message send failure.

        Args:
            error_type: The type of error that occurred.
            count: Number of errors to record.
        """
        if not self.enabled:
            return

        # Log the error type for debugging
        if error_type:
            logger.debug(f"Recording send failure of type: {error_type}")

        self.message_send_failures.inc(count)

    def time_send_operation(self):
        """
        Time a message send operation.

        Returns:
            A context manager that times the operation.
        """
        if not self.enabled:
            # Return dummy context manager if metrics disabled
            class DummyContextManager:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
            return DummyContextManager()

        return self.message_send_latency.time()

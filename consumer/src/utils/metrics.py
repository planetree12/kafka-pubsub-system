"""
Prometheus metrics collection for the consumer application.
"""
import logging
import threading
import time
from typing import Dict, Any

from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Define metrics
MESSAGES_PROCESSED = Counter(
    'consumer_messages_processed_total',
    'Total number of messages processed'
)

PROCESSING_ERRORS = Counter(
    'consumer_processing_errors_total',
    'Total number of processing errors'
)

BATCH_SIZE = Histogram(
    'consumer_batch_size',
    'Size of processed batches',
    buckets=(1, 5, 10, 20, 50, 100, 200, 500)
)

PROCESSING_TIME = Histogram(
    'consumer_processing_time_seconds',
    'Time spent processing messages',
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

MONGODB_WRITE_TIME = Histogram(
    'consumer_mongodb_write_time_seconds',
    'Time spent writing to MongoDB',
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

OFFSET_COMMIT_TIME = Histogram(
    'consumer_offset_commit_time_seconds',
    'Time spent committing offsets',
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0)
)

CONSUMER_LAG = Gauge(
    'consumer_lag',
    'Lag in number of messages behind latest offset'
)

ACTIVE_CONNECTIONS = Gauge(
    'consumer_active_connections',
    'Number of active connections',
    ['connection_type']
)


class MetricsCollector:
    """
    Collects and exposes Prometheus metrics for the consumer application.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize metrics collector.

        Args:
            config: Configuration dictionary
        """
        self.enabled = config.get('metrics', {}).get('enabled', True)
        self.port = config.get('metrics', {}).get('port', 8001)
        self.server_started = False
        self.logger = logging.getLogger(__name__)

        # Start metrics server in a separate thread if enabled
        if self.enabled:
            self._start_server()

    def _start_server(self):
        """Start the metrics HTTP server in a background thread."""
        def server_thread():
            try:
                start_http_server(self.port)
                self.server_started = True
                self.logger.info(f"Metrics server started on port {self.port}")
            except Exception as e:
                self.logger.error(f"Failed to start metrics server: {str(e)}")

        thread = threading.Thread(target=server_thread, daemon=True)
        thread.start()
        # Give the server a moment to start
        time.sleep(0.1)

    def increment_messages_processed(self, count: int = 1):
        """Increment the messages processed counter."""
        if self.enabled:
            MESSAGES_PROCESSED.inc(count)

    def increment_processing_errors(self, count: int = 1):
        """Increment the processing errors counter."""
        if self.enabled:
            PROCESSING_ERRORS.inc(count)

    def observe_batch_size(self, size: int):
        """Record a batch size observation."""
        if self.enabled:
            BATCH_SIZE.observe(size)

    def observe_processing_time(self, seconds: float):
        """Record a processing time observation."""
        if self.enabled:
            PROCESSING_TIME.observe(seconds)

    def observe_mongodb_write_time(self, seconds: float):
        """Record a MongoDB write time observation."""
        if self.enabled:
            MONGODB_WRITE_TIME.observe(seconds)

    def observe_offset_commit_time(self, seconds: float):
        """Record an offset commit time observation."""
        if self.enabled:
            OFFSET_COMMIT_TIME.observe(seconds)

    def set_consumer_lag(self, lag: int):
        """Set the consumer lag gauge."""
        if self.enabled:
            CONSUMER_LAG.set(lag)

    def set_active_connections(self, connection_type: str, count: int):
        """Set the active connections gauge for a specific connection type."""
        if self.enabled:
            ACTIVE_CONNECTIONS.labels(connection_type=connection_type).set(count)

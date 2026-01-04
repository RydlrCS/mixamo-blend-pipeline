"""
Prometheus metrics for production monitoring.

Provides instrumentation for key pipeline operations with standardized
Prometheus metrics. Tracks success/failure rates, latencies, and resource usage.

Author: Ted Iro
Organization: Rydlr Cloud Services Ltd (github.com/rydlrcs)
Date: January 4, 2026

Metrics Provided:
    - blend_requests_total: Counter for blend operations
    - blend_duration_seconds: Histogram for blend latency
    - upload_bytes_total: Counter for uploaded bytes
    - upload_requests_total: Counter for upload operations
    - download_requests_total: Counter for download operations
    - gcs_api_errors_total: Counter for GCS API errors
    - worker_pool_utilization: Gauge for worker utilization
    - queue_depth: Gauge for pending jobs

Usage:
    # In application code:
    from src.utils.metrics import metrics
    
    # Track operation
    with metrics.blend_duration.time():
        result = blend_animations(...)
    
    if result.success:
        metrics.blend_requests.labels(status="success").inc()
    else:
        metrics.blend_requests.labels(status="failure").inc()
    
    # Start metrics server:
    python -m src.utils.metrics --port 9090
"""

import os
import time
from typing import Optional
from functools import wraps

from src.utils.logging import get_logger

# Module-level logger
logger = get_logger(__name__)

# Try to import prometheus_client (optional dependency)
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Summary,
        Info,
        start_http_server,
        REGISTRY,
        CollectorRegistry,
    )
    PROMETHEUS_AVAILABLE = True
    logger.info("Prometheus client available")
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus_client not installed - metrics collection disabled. "
        "Install with: pip install prometheus-client"
    )


# ============================================================================
# Metric Definitions
# ============================================================================

class PrometheusMetrics:
    """
    Centralized Prometheus metrics for the pipeline.
    
    Provides standardized metrics for all pipeline operations following
    Prometheus best practices and naming conventions.
    
    Example:
        >>> from src.utils.metrics import metrics
        >>> metrics.blend_requests.labels(status="success").inc()
        >>> metrics.upload_bytes.inc(1024000)  # 1MB uploaded
    """
    
    def __init__(self, enabled: bool = True, registry: Optional[any] = None) -> None:
        """
        Initialize metrics collectors.
        
        Args:
            enabled: Whether metrics collection is enabled
            registry: Custom Prometheus registry (uses default if None)
        
        Note:
            If prometheus_client not installed, all metrics become no-ops
        """
        logger.info("Initializing PrometheusMetrics")
        
        self.enabled = enabled and PROMETHEUS_AVAILABLE
        self.registry = registry if registry else (REGISTRY if PROMETHEUS_AVAILABLE else None)
        
        if not self.enabled:
            logger.warning("Metrics collection disabled")
            return
        
        # ====================================================================
        # Blend Operations
        # ====================================================================
        
        # Counter: Total blend requests by status
        self.blend_requests = Counter(
            name="blend_requests_total",
            documentation="Total number of blend requests",
            labelnames=["status"],  # success, failure
            registry=self.registry,
        )
        
        # Histogram: Blend operation duration
        self.blend_duration = Histogram(
            name="blend_duration_seconds",
            documentation="Time spent blending animations",
            labelnames=["method"],  # linear, snn, spade
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
            registry=self.registry,
        )
        
        # Counter: Frames processed
        self.blend_frames_processed = Counter(
            name="blend_frames_processed_total",
            documentation="Total animation frames processed",
            registry=self.registry,
        )
        
        # ====================================================================
        # Upload Operations
        # ====================================================================
        
        # Counter: Total upload requests by status
        self.upload_requests = Counter(
            name="upload_requests_total",
            documentation="Total number of upload requests",
            labelnames=["status", "destination"],  # status: success/failure, destination: folder name
            registry=self.registry,
        )
        
        # Counter: Total bytes uploaded
        self.upload_bytes = Counter(
            name="upload_bytes_total",
            documentation="Total bytes uploaded to GCS",
            registry=self.registry,
        )
        
        # Histogram: Upload operation duration
        self.upload_duration = Histogram(
            name="upload_duration_seconds",
            documentation="Time spent uploading files",
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self.registry,
        )
        
        # ====================================================================
        # Download Operations
        # ====================================================================
        
        # Counter: Total download requests by status
        self.download_requests = Counter(
            name="download_requests_total",
            documentation="Total number of download requests",
            labelnames=["status", "format"],  # status: success/failure, format: fbx/bvh
            registry=self.registry,
        )
        
        # Histogram: Download operation duration
        self.download_duration = Histogram(
            name="download_duration_seconds",
            documentation="Time spent downloading animations",
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry,
        )
        
        # ====================================================================
        # API and External Services
        # ====================================================================
        
        # Counter: GCS API errors
        self.gcs_api_errors = Counter(
            name="gcs_api_errors_total",
            documentation="Total GCS API errors",
            labelnames=["operation", "error_type"],  # operation: upload/download/list
            registry=self.registry,
        )
        
        # Counter: BigQuery API errors
        self.bq_api_errors = Counter(
            name="bq_api_errors_total",
            documentation="Total BigQuery API errors",
            labelnames=["operation", "error_type"],
            registry=self.registry,
        )
        
        # Histogram: GCS API latency
        self.gcs_api_duration = Histogram(
            name="gcs_api_duration_seconds",
            documentation="GCS API call latency",
            labelnames=["operation"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )
        
        # ====================================================================
        # System and Resources
        # ====================================================================
        
        # Gauge: Current worker pool utilization (0.0 to 1.0)
        self.worker_pool_utilization = Gauge(
            name="worker_pool_utilization",
            documentation="Worker pool utilization (0.0 to 1.0)",
            registry=self.registry,
        )
        
        # Gauge: Current queue depth (pending jobs)
        self.queue_depth = Gauge(
            name="queue_depth",
            documentation="Number of jobs waiting in queue",
            registry=self.registry,
        )
        
        # Gauge: Active requests
        self.active_requests = Gauge(
            name="active_requests",
            documentation="Number of requests currently being processed",
            labelnames=["operation"],  # blend, upload, download
            registry=self.registry,
        )
        
        # ====================================================================
        # Application Info
        # ====================================================================
        
        # Info: Application metadata
        self.app_info = Info(
            name="application",
            documentation="Application metadata",
            registry=self.registry,
        )
        
        # Set application info
        self.app_info.info({
            "version": "0.1.0",
            "name": "mixamo-blend-pipeline",
            "author": "Ted Iro",
            "organization": "Rydlr Cloud Services Ltd",
        })
        
        logger.info("PrometheusMetrics initialized with all collectors")
    
    def track_blend(self, method: str = "linear"):
        """
        Context manager for tracking blend operations.
        
        Args:
            method: Blend method (linear, snn, spade)
        
        Example:
            >>> with metrics.track_blend(method="linear"):
            ...     result = blend_animations(...)
        """
        if not self.enabled:
            # No-op context manager if metrics disabled
            from contextlib import nullcontext
            return nullcontext()
        
        return self.blend_duration.labels(method=method).time()
    
    def track_upload(self):
        """
        Context manager for tracking upload operations.
        
        Example:
            >>> with metrics.track_upload():
            ...     upload_file(path, config)
        """
        if not self.enabled:
            from contextlib import nullcontext
            return nullcontext()
        
        return self.upload_duration.time()
    
    def track_download(self):
        """
        Context manager for tracking download operations.
        
        Example:
            >>> with metrics.track_download():
            ...     download_animation(config)
        """
        if not self.enabled:
            from contextlib import nullcontext
            return nullcontext()
        
        return self.download_duration.time()
    
    def record_blend_success(self, frames_processed: int = 0):
        """
        Record successful blend operation.
        
        Args:
            frames_processed: Number of animation frames processed
        """
        if not self.enabled:
            return
        
        self.blend_requests.labels(status="success").inc()
        if frames_processed > 0:
            self.blend_frames_processed.inc(frames_processed)
    
    def record_blend_failure(self):
        """Record failed blend operation."""
        if not self.enabled:
            return
        
        self.blend_requests.labels(status="failure").inc()
    
    def record_upload_success(self, bytes_uploaded: int, destination: str = "unknown"):
        """
        Record successful upload operation.
        
        Args:
            bytes_uploaded: Number of bytes uploaded
            destination: Upload destination folder (seed, blend, output)
        """
        if not self.enabled:
            return
        
        self.upload_requests.labels(status="success", destination=destination).inc()
        self.upload_bytes.inc(bytes_uploaded)
    
    def record_upload_failure(self, destination: str = "unknown"):
        """
        Record failed upload operation.
        
        Args:
            destination: Upload destination folder
        """
        if not self.enabled:
            return
        
        self.upload_requests.labels(status="failure", destination=destination).inc()
    
    def record_download_success(self, file_format: str = "unknown"):
        """
        Record successful download operation.
        
        Args:
            file_format: Downloaded file format (fbx, bvh)
        """
        if not self.enabled:
            return
        
        self.download_requests.labels(status="success", format=file_format).inc()
    
    def record_download_failure(self, file_format: str = "unknown"):
        """
        Record failed download operation.
        
        Args:
            file_format: File format attempted
        """
        if not self.enabled:
            return
        
        self.download_requests.labels(status="failure", format=file_format).inc()
    
    def record_gcs_error(self, operation: str, error_type: str):
        """
        Record GCS API error.
        
        Args:
            operation: GCS operation (upload, download, list, delete)
            error_type: Error type (timeout, permission_denied, not_found)
        """
        if not self.enabled:
            return
        
        self.gcs_api_errors.labels(operation=operation, error_type=error_type).inc()


# ============================================================================
# Global Metrics Instance
# ============================================================================

# Global metrics instance (singleton)
_metrics_instance: Optional[PrometheusMetrics] = None


def get_metrics() -> PrometheusMetrics:
    """
    Get global metrics instance (singleton).
    
    Returns:
        Global PrometheusMetrics instance
    
    Example:
        >>> from src.utils.metrics import get_metrics
        >>> metrics = get_metrics()
        >>> metrics.blend_requests.labels(status="success").inc()
    """
    global _metrics_instance
    
    if _metrics_instance is None:
        logger.debug("Initializing global metrics instance")
        
        # Check if metrics are enabled via environment variable
        enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
        
        _metrics_instance = PrometheusMetrics(enabled=enabled)
    
    return _metrics_instance


# Convenience alias
metrics = get_metrics()


# ============================================================================
# Decorator for Automatic Metric Tracking
# ============================================================================

def track_operation(operation_type: str, labels: Optional[dict] = None):
    """
    Decorator to automatically track operation metrics.
    
    Args:
        operation_type: Type of operation (blend, upload, download)
        labels: Optional labels for the metrics
    
    Example:
        >>> @track_operation("blend", labels={"method": "linear"})
        ... def my_blend_function():
        ...     # ... blend logic ...
        ...     return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics()
            
            if not metrics.enabled:
                # Just call function if metrics disabled
                return func(*args, **kwargs)
            
            # Increment active requests
            metrics.active_requests.labels(operation=operation_type).inc()
            
            # Track duration
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            
            finally:
                # Record duration
                duration = time.time() - start_time
                
                # Decrement active requests
                metrics.active_requests.labels(operation=operation_type).dec()
                
                logger.debug(
                    f"Operation {operation_type} completed in {duration:.2f}s"
                )
        
        return wrapper
    return decorator


# ============================================================================
# Metrics Server
# ============================================================================

def start_metrics_server(port: int = 9090, addr: str = "0.0.0.0") -> None:
    """
    Start Prometheus metrics HTTP server.
    
    Args:
        port: Port to listen on (default: 9090)
        addr: Address to bind to (default: 0.0.0.0 - all interfaces)
    
    Note:
        Blocks forever - run in separate thread or process
    
    Example:
        >>> from src.utils.metrics import start_metrics_server
        >>> start_metrics_server(port=9090)
    """
    if not PROMETHEUS_AVAILABLE:
        logger.error("Cannot start metrics server - prometheus_client not installed")
        return
    
    logger.info(f"Starting Prometheus metrics server on {addr}:{port}")
    
    try:
        start_http_server(port=port, addr=addr)
        logger.info(f"Metrics server running at http://{addr}:{port}/metrics")
        
        # Keep server running
        import signal
        signal.pause()
    
    except KeyboardInterrupt:
        logger.info("Metrics server shutting down")
    except Exception as e:
        logger.error(f"Metrics server error: {e}", exc_info=True)
        raise


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Mixamo Blend Pipeline Metrics Server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9090,
        help="Metrics server port (default: 9090)",
    )
    parser.add_argument(
        "--addr",
        type=str,
        default="0.0.0.0",
        help="Address to bind to (default: 0.0.0.0)",
    )
    
    args = parser.parse_args()
    
    # Start metrics server
    start_metrics_server(port=args.port, addr=args.addr)

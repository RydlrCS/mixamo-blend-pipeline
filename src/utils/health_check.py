"""
Health check module for production monitoring.

Provides HTTP endpoints for Kubernetes liveness, readiness, and startup probes.
Also includes system health checks for dependencies (GCS, BigQuery, filesystem).

Author: Ted Iro
Organization: Rydlr Cloud Services Ltd (github.com/rydlrcs)
Date: January 4, 2026

Purpose:
    - Kubernetes health probe endpoints
    - Dependency health checks (GCS, BigQuery availability)
    - System resource monitoring (disk space, memory)
    - Graceful degradation indicators

Usage:
    # As standalone HTTP server:
    python -m src.utils.health_check --port 8080

    # In application code:
    from src.utils.health_check import HealthChecker
    checker = HealthChecker()
    status = checker.check_health()
    if status.healthy:
        print("System is healthy")
"""

import os
import sys
import time
import psutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

from src.utils.logging import get_logger

# Module-level logger with entry/exit logging
logger = get_logger(__name__)


# ============================================================================
# Health Status Enums and Data Classes
# ============================================================================

class HealthStatus(str, Enum):
    """
    Health status enumeration.
    
    Values align with Kubernetes probe expectations:
    - HEALTHY: All checks passed, ready to serve traffic
    - DEGRADED: Partial functionality, can serve some traffic
    - UNHEALTHY: Critical failure, should not serve traffic
    """
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """
    Health status for a single component.
    
    Attributes:
        name: Component name (e.g., "gcs", "bigquery", "filesystem")
        status: Health status enum value
        message: Human-readable status message
        latency_ms: Response latency in milliseconds (optional)
        details: Additional diagnostic information
    """
    name: str
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """
    Overall system health status.
    
    Attributes:
        status: Aggregate health status
        timestamp: UTC timestamp of health check
        components: Health status of individual components
        version: Application version
        uptime_seconds: Time since application start
    """
    status: HealthStatus
    timestamp: float
    components: List[ComponentHealth] = field(default_factory=list)
    version: str = "0.1.0"
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert health status to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of health status
        """
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": round(c.latency_ms, 2) if c.latency_ms else None,
                    "details": c.details,
                }
                for c in self.components
            ],
        }


# ============================================================================
# Health Checker Implementation
# ============================================================================

class HealthChecker:
    """
    Production-ready health checker for Kubernetes environments.
    
    Performs comprehensive health checks including:
    - Python module imports
    - Filesystem availability and disk space
    - Memory usage
    - GCS connectivity (optional)
    - BigQuery connectivity (optional)
    
    Example:
        >>> checker = HealthChecker()
        >>> health = checker.check_health()
        >>> if health.status == HealthStatus.HEALTHY:
        ...     print("All systems operational")
    """
    
    def __init__(self) -> None:
        """
        Initialize health checker.
        
        Logs entry and captures application start time for uptime calculation.
        """
        logger.info("Initializing HealthChecker")
        self.start_time = time.time()
        self._check_gcs = os.getenv("HEALTH_CHECK_GCS", "false").lower() == "true"
        self._check_bq = os.getenv("HEALTH_CHECK_BQ", "false").lower() == "true"
        logger.debug(f"GCS health checks: {self._check_gcs}, BQ health checks: {self._check_bq}")
    
    def check_health(self) -> SystemHealth:
        """
        Execute all health checks and aggregate results.
        
        Returns:
            SystemHealth object with overall status and component details
        
        Note:
            - Logs entry and exit with timing information
            - Individual component failures are logged but don't stop execution
            - Overall status is determined by worst component status
        """
        logger.info("Starting comprehensive health check")
        start_time = time.time()
        
        components: List[ComponentHealth] = []
        
        # Execute all health checks (order matters - fast checks first)
        components.append(self._check_python_modules())
        components.append(self._check_filesystem())
        components.append(self._check_memory())
        
        # Optional checks (may be slow or require external connectivity)
        if self._check_gcs:
            components.append(self._check_gcs_connectivity())
        
        if self._check_bq:
            components.append(self._check_bigquery_connectivity())
        
        # Aggregate status: worst component status becomes overall status
        overall_status = self._aggregate_status(components)
        
        # Calculate uptime
        uptime = time.time() - self.start_time
        
        # Build system health object
        health = SystemHealth(
            status=overall_status,
            timestamp=time.time(),
            components=components,
            uptime_seconds=uptime,
        )
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Health check completed: {overall_status.value} "
            f"({len(components)} components checked in {duration_ms:.2f}ms)"
        )
        
        return health
    
    def _aggregate_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """
        Aggregate component statuses into overall system status.
        
        Logic:
            - If any component is UNHEALTHY -> system is UNHEALTHY
            - Else if any component is DEGRADED -> system is DEGRADED
            - Else all components are HEALTHY -> system is HEALTHY
        
        Args:
            components: List of component health statuses
        
        Returns:
            Aggregated health status
        """
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            return HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in components):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _check_python_modules(self) -> ComponentHealth:
        """
        Verify critical Python modules can be imported.
        
        Returns:
            ComponentHealth for module import check
        
        Note:
            - Tests imports for all pipeline modules
            - Failure indicates broken deployment or missing dependencies
        """
        logger.debug("Checking Python module imports")
        start_time = time.time()
        
        try:
            # Attempt to import all critical modules
            import src.blender
            import src.downloader
            import src.uploader
            import src.npc_engine
            import src.utils.config
            import src.utils.logging
            
            latency_ms = (time.time() - start_time) * 1000
            logger.debug(f"Module import check passed ({latency_ms:.2f}ms)")
            
            return ComponentHealth(
                name="python_modules",
                status=HealthStatus.HEALTHY,
                message="All modules importable",
                latency_ms=latency_ms,
                details={"modules_checked": 6},
            )
        
        except ImportError as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Module import failed: {e}")
            
            return ComponentHealth(
                name="python_modules",
                status=HealthStatus.UNHEALTHY,
                message=f"Import error: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )
    
    def _check_filesystem(self) -> ComponentHealth:
        """
        Check filesystem availability and disk space.
        
        Returns:
            ComponentHealth for filesystem check
        
        Thresholds:
            - < 10% free space: UNHEALTHY
            - < 20% free space: DEGRADED
            - >= 20% free space: HEALTHY
        """
        logger.debug("Checking filesystem health")
        start_time = time.time()
        
        try:
            # Check data directory
            data_dir = Path("/app/data")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Get disk usage statistics
            usage = psutil.disk_usage(str(data_dir))
            percent_free = (usage.free / usage.total) * 100
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Determine status based on free space
            if percent_free < 10:
                logger.warning(f"Low disk space: {percent_free:.1f}% free")
                status = HealthStatus.UNHEALTHY
                message = f"Critical: Only {percent_free:.1f}% disk space free"
            elif percent_free < 20:
                logger.warning(f"Disk space warning: {percent_free:.1f}% free")
                status = HealthStatus.DEGRADED
                message = f"Warning: {percent_free:.1f}% disk space free"
            else:
                logger.debug(f"Disk space OK: {percent_free:.1f}% free")
                status = HealthStatus.HEALTHY
                message = f"Filesystem healthy ({percent_free:.1f}% free)"
            
            return ComponentHealth(
                name="filesystem",
                status=status,
                message=message,
                latency_ms=latency_ms,
                details={
                    "percent_free": round(percent_free, 2),
                    "bytes_free": usage.free,
                    "bytes_total": usage.total,
                },
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Filesystem check failed: {e}")
            
            return ComponentHealth(
                name="filesystem",
                status=HealthStatus.UNHEALTHY,
                message=f"Filesystem error: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )
    
    def _check_memory(self) -> ComponentHealth:
        """
        Check memory usage.
        
        Returns:
            ComponentHealth for memory check
        
        Thresholds:
            - > 90% used: UNHEALTHY
            - > 80% used: DEGRADED
            - <= 80% used: HEALTHY
        """
        logger.debug("Checking memory usage")
        start_time = time.time()
        
        try:
            # Get memory statistics
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Determine status based on memory usage
            if percent_used > 90:
                logger.warning(f"Critical memory usage: {percent_used:.1f}%")
                status = HealthStatus.UNHEALTHY
                message = f"Critical: {percent_used:.1f}% memory used"
            elif percent_used > 80:
                logger.warning(f"High memory usage: {percent_used:.1f}%")
                status = HealthStatus.DEGRADED
                message = f"Warning: {percent_used:.1f}% memory used"
            else:
                logger.debug(f"Memory usage OK: {percent_used:.1f}%")
                status = HealthStatus.HEALTHY
                message = f"Memory healthy ({percent_used:.1f}% used)"
            
            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                latency_ms=latency_ms,
                details={
                    "percent_used": round(percent_used, 2),
                    "bytes_available": memory.available,
                    "bytes_total": memory.total,
                },
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Memory check failed: {e}")
            
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check error: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )
    
    def _check_gcs_connectivity(self) -> ComponentHealth:
        """
        Check Google Cloud Storage connectivity (optional).
        
        Returns:
            ComponentHealth for GCS connectivity
        
        Note:
            - Only runs if HEALTH_CHECK_GCS=true
            - Tests bucket access without downloading files
            - Failure is DEGRADED, not UNHEALTHY (allows graceful degradation)
        """
        logger.debug("Checking GCS connectivity")
        start_time = time.time()
        
        try:
            from google.cloud import storage
            
            bucket_name = os.getenv("GCS_BUCKET")
            if not bucket_name:
                logger.warning("GCS_BUCKET not configured, skipping check")
                return ComponentHealth(
                    name="gcs",
                    status=HealthStatus.DEGRADED,
                    message="GCS bucket not configured",
                    latency_ms=(time.time() - start_time) * 1000,
                )
            
            # Test bucket access (lightweight operation)
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            _ = bucket.exists()
            
            latency_ms = (time.time() - start_time) * 1000
            logger.debug(f"GCS connectivity OK ({latency_ms:.2f}ms)")
            
            return ComponentHealth(
                name="gcs",
                status=HealthStatus.HEALTHY,
                message="GCS accessible",
                latency_ms=latency_ms,
                details={"bucket": bucket_name},
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"GCS connectivity check failed: {e}")
            
            # GCS failure is DEGRADED, not UNHEALTHY
            # Application can still function without GCS for some operations
            return ComponentHealth(
                name="gcs",
                status=HealthStatus.DEGRADED,
                message=f"GCS unavailable: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )
    
    def _check_bigquery_connectivity(self) -> ComponentHealth:
        """
        Check BigQuery connectivity (optional).
        
        Returns:
            ComponentHealth for BigQuery connectivity
        
        Note:
            - Only runs if HEALTH_CHECK_BQ=true
            - Tests project access without running queries
            - Failure is DEGRADED, not UNHEALTHY
        """
        logger.debug("Checking BigQuery connectivity")
        start_time = time.time()
        
        try:
            from google.cloud import bigquery
            
            project_id = os.getenv("BQ_PROJECT")
            if not project_id:
                logger.warning("BQ_PROJECT not configured, skipping check")
                return ComponentHealth(
                    name="bigquery",
                    status=HealthStatus.DEGRADED,
                    message="BigQuery project not configured",
                    latency_ms=(time.time() - start_time) * 1000,
                )
            
            # Test project access (lightweight operation)
            client = bigquery.Client(project=project_id)
            _ = client.project
            
            latency_ms = (time.time() - start_time) * 1000
            logger.debug(f"BigQuery connectivity OK ({latency_ms:.2f}ms)")
            
            return ComponentHealth(
                name="bigquery",
                status=HealthStatus.HEALTHY,
                message="BigQuery accessible",
                latency_ms=latency_ms,
                details={"project": project_id},
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"BigQuery connectivity check failed: {e}")
            
            return ComponentHealth(
                name="bigquery",
                status=HealthStatus.DEGRADED,
                message=f"BigQuery unavailable: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )


# ============================================================================
# Standalone Server (for HTTP health endpoints)
# ============================================================================

def run_health_server(port: int = 8080) -> None:
    """
    Run standalone HTTP health check server.
    
    Endpoints:
        GET /health - Full health check (all components)
        GET /ready  - Readiness check (critical components only)
        GET /live   - Liveness check (basic functionality)
    
    Args:
        port: HTTP port to listen on
    
    Note:
        Uses simple HTTP server for minimal dependencies
        For production, consider using Flask or FastAPI
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    logger.info(f"Starting health check HTTP server on port {port}")
    
    class HealthHandler(BaseHTTPRequestHandler):
        """HTTP request handler for health endpoints."""
        
        def log_message(self, format: str, *args: Any) -> None:
            """Override to use our logger instead of stderr."""
            logger.info(f"{self.address_string()} - {format % args}")
        
        def do_GET(self) -> None:  # noqa: N802
            """Handle GET requests."""
            checker = HealthChecker()
            
            if self.path == "/health":
                # Full health check
                health = checker.check_health()
                status_code = 200 if health.status == HealthStatus.HEALTHY else 503
                
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(health.to_dict(), indent=2).encode())
            
            elif self.path in ["/ready", "/readiness"]:
                # Readiness check (simplified)
                health = checker.check_health()
                status_code = 200 if health.status != HealthStatus.UNHEALTHY else 503
                
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": health.status.value}).encode())
            
            elif self.path in ["/live", "/liveness"]:
                # Liveness check (minimal - just check imports)
                module_health = checker._check_python_modules()
                status_code = 200 if module_health.status == HealthStatus.HEALTHY else 503
                
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": module_health.status.value}).encode())
            
            else:
                # 404 for unknown paths
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        logger.info(f"Health server listening on http://0.0.0.0:{port}")
        logger.info("Endpoints: /health, /ready, /live")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Health server shutting down")
        server.shutdown()
    except Exception as e:
        logger.error(f"Health server error: {e}", exc_info=True)
        raise


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Mixamo Blend Pipeline Health Checker"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP server port (default: 8080)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run single health check and exit (no HTTP server)",
    )
    
    args = parser.parse_args()
    
    if args.check_only:
        # Single health check, print results, exit
        checker = HealthChecker()
        health = checker.check_health()
        
        import json
        print(json.dumps(health.to_dict(), indent=2))
        
        # Exit with appropriate code
        sys.exit(0 if health.status == HealthStatus.HEALTHY else 1)
    else:
        # Start HTTP server
        run_health_server(port=args.port)

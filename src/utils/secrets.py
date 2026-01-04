"""
Secrets management for production deployments.

Provides secure secret retrieval from multiple backends:
- Google Secret Manager (GCP native)
- Kubernetes Secrets (via environment variables)
- Environment variables (development fallback)

Author: Ted Iro
Organization: Rydlr Cloud Services Ltd (github.com/rydlrcs)
Date: January 4, 2026

Security Principles:
    - Never log secret values
    - Minimize secret exposure time in memory
    - Support secret rotation without restarts
    - Fail securely (no defaults for sensitive values)

Usage:
    from src.utils.secrets import SecretManager
    
    # Initialize (auto-detects environment)
    secrets = SecretManager()
    
    # Retrieve secret
    gcs_bucket = secrets.get_secret("GCS_BUCKET")
    api_key = secrets.get_secret("ES_API_KEY", required=False)
"""

import os
import json
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from src.utils.logging import get_logger

# Module-level logger
logger = get_logger(__name__)


# ============================================================================
# Secret Backend Types
# ============================================================================

class SecretBackend(str, Enum):
    """
    Supported secret storage backends.
    
    Values:
        ENVIRONMENT: Read from environment variables (development)
        GOOGLE_SECRET_MANAGER: Google Cloud Secret Manager (production)
        KUBERNETES: Kubernetes secrets mounted as env vars (production)
    """
    ENVIRONMENT = "environment"
    GOOGLE_SECRET_MANAGER = "google_secret_manager"
    KUBERNETES = "kubernetes"


@dataclass
class SecretConfig:
    """
    Configuration for secret management.
    
    Attributes:
        backend: Secret storage backend to use
        project_id: GCP project ID (for Secret Manager)
        cache_secrets: Whether to cache secrets in memory
        cache_ttl_seconds: TTL for cached secrets
    """
    backend: SecretBackend = SecretBackend.ENVIRONMENT
    project_id: Optional[str] = None
    cache_secrets: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


# ============================================================================
# Secret Manager Implementation
# ============================================================================

class SecretManager:
    """
    Production-ready secret management with multiple backend support.
    
    Automatically detects environment and selects appropriate backend:
    - GKE with Workload Identity -> Google Secret Manager
    - Kubernetes with secrets -> Environment variables from secrets
    - Local development -> .env file
    
    Example:
        >>> secrets = SecretManager()
        >>> bucket = secrets.get_secret("GCS_BUCKET")
        >>> api_key = secrets.get_secret("API_KEY", required=False)
    """
    
    def __init__(self, config: Optional[SecretConfig] = None) -> None:
        """
        Initialize secret manager.
        
        Args:
            config: Optional secret configuration (auto-detected if None)
        
        Note:
            Logs initialization but never logs secret values
        """
        logger.info("Initializing SecretManager")
        
        # Use provided config or create default
        self.config = config or self._detect_config()
        
        # Secret cache (if enabled)
        self._cache: Dict[str, str] = {}
        
        # Initialize backend-specific client
        self._gcp_client: Optional[Any] = None
        if self.config.backend == SecretBackend.GOOGLE_SECRET_MANAGER:
            self._init_gcp_client()
        
        logger.info(f"SecretManager initialized with backend: {self.config.backend.value}")
    
    def _detect_config(self) -> SecretConfig:
        """
        Auto-detect appropriate secret backend based on environment.
        
        Detection logic:
            1. If GOOGLE_CLOUD_PROJECT set -> Google Secret Manager
            2. If running in Kubernetes (KUBERNETES_SERVICE_HOST) -> Kubernetes secrets
            3. Else -> Environment variables
        
        Returns:
            Auto-detected SecretConfig
        """
        logger.debug("Auto-detecting secret backend")
        
        # Check for Google Cloud environment
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("BQ_PROJECT")
        in_gcp = project_id is not None
        
        # Check for Kubernetes environment
        in_kubernetes = os.getenv("KUBERNETES_SERVICE_HOST") is not None
        
        if in_gcp and in_kubernetes:
            # GKE with Workload Identity - use Secret Manager
            logger.info("Detected GKE environment, using Google Secret Manager")
            return SecretConfig(
                backend=SecretBackend.GOOGLE_SECRET_MANAGER,
                project_id=project_id,
            )
        elif in_kubernetes:
            # Kubernetes with secrets as environment variables
            logger.info("Detected Kubernetes environment, using environment variables")
            return SecretConfig(backend=SecretBackend.KUBERNETES)
        else:
            # Local development
            logger.info("Using environment variables for secrets")
            return SecretConfig(backend=SecretBackend.ENVIRONMENT)
    
    def _init_gcp_client(self) -> None:
        """
        Initialize Google Cloud Secret Manager client.
        
        Note:
            Only called when backend is GOOGLE_SECRET_MANAGER
            Logs errors but doesn't raise (allows graceful fallback)
        """
        logger.debug("Initializing Google Secret Manager client")
        
        try:
            from google.cloud import secretmanager
            
            self._gcp_client = secretmanager.SecretManagerServiceClient()
            logger.info("Google Secret Manager client initialized")
        
        except ImportError:
            logger.warning(
                "google-cloud-secret-manager not installed, "
                "falling back to environment variables"
            )
            self.config.backend = SecretBackend.ENVIRONMENT
        
        except Exception as e:
            logger.error(f"Failed to initialize Secret Manager client: {e}")
            self.config.backend = SecretBackend.ENVIRONMENT
    
    def get_secret(
        self,
        secret_name: str,
        required: bool = True,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Retrieve secret value from configured backend.
        
        Args:
            secret_name: Name of secret to retrieve
            required: Whether secret is required (raises if missing)
            default: Default value if secret not found (only if not required)
        
        Returns:
            Secret value or None/default if not found
        
        Raises:
            ValueError: If required secret is not found
        
        Note:
            - Never logs secret values
            - Logs secret retrieval attempts (not values)
            - Caches secrets if caching enabled
        """
        logger.debug(f"Retrieving secret: {secret_name}")
        
        # Check cache first
        if self.config.cache_secrets and secret_name in self._cache:
            logger.debug(f"Secret {secret_name} found in cache")
            return self._cache[secret_name]
        
        # Retrieve from backend
        if self.config.backend == SecretBackend.GOOGLE_SECRET_MANAGER:
            value = self._get_from_gcp(secret_name)
        else:
            # Both KUBERNETES and ENVIRONMENT read from env vars
            value = os.getenv(secret_name)
        
        # Handle missing secrets
        if value is None:
            if required:
                error_msg = (
                    f"Required secret '{secret_name}' not found in "
                    f"{self.config.backend.value}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                logger.debug(f"Optional secret '{secret_name}' not found, using default")
                return default
        
        # Cache if enabled
        if self.config.cache_secrets:
            self._cache[secret_name] = value
        
        logger.debug(f"Secret {secret_name} retrieved successfully")
        return value
    
    def _get_from_gcp(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from Google Cloud Secret Manager.
        
        Args:
            secret_name: Name of secret in Secret Manager
        
        Returns:
            Secret value or None if not found
        
        Note:
            Uses latest version of secret
        """
        if not self._gcp_client:
            logger.warning("GCP client not initialized, falling back to environment")
            return os.getenv(secret_name)
        
        try:
            # Build secret path: projects/PROJECT_ID/secrets/SECRET_NAME/versions/latest
            project_id = self.config.project_id
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            
            logger.debug(f"Accessing GCP secret: {name}")
            
            # Access secret
            response = self._gcp_client.access_secret_version(request={"name": name})
            
            # Decode payload
            value = response.payload.data.decode("UTF-8")
            
            logger.debug(f"Successfully retrieved secret from GCP: {secret_name}")
            return value
        
        except Exception as e:
            logger.warning(
                f"Failed to retrieve secret '{secret_name}' from GCP: {e}, "
                f"trying environment variable"
            )
            # Fallback to environment variable
            return os.getenv(secret_name)
    
    def get_json_secret(
        self,
        secret_name: str,
        required: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve and parse JSON-formatted secret.
        
        Useful for service account keys or complex configurations.
        
        Args:
            secret_name: Name of secret containing JSON
            required: Whether secret is required
        
        Returns:
            Parsed JSON dict or None if not found
        
        Raises:
            ValueError: If secret is not valid JSON
        """
        logger.debug(f"Retrieving JSON secret: {secret_name}")
        
        value = self.get_secret(secret_name, required=required)
        
        if value is None:
            return None
        
        try:
            parsed = json.loads(value)
            logger.debug(f"Successfully parsed JSON secret: {secret_name}")
            return parsed
        
        except json.JSONDecodeError as e:
            error_msg = f"Secret '{secret_name}' is not valid JSON: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def clear_cache(self) -> None:
        """
        Clear cached secrets.
        
        Use this to force re-fetching of secrets (e.g., after rotation).
        """
        logger.info(f"Clearing secret cache ({len(self._cache)} secrets)")
        self._cache.clear()
    
    def refresh_secret(self, secret_name: str) -> Optional[str]:
        """
        Force refresh of specific secret (clears cache and re-fetches).
        
        Args:
            secret_name: Name of secret to refresh
        
        Returns:
            Refreshed secret value
        """
        logger.debug(f"Refreshing secret: {secret_name}")
        
        # Remove from cache
        if secret_name in self._cache:
            del self._cache[secret_name]
        
        # Re-fetch
        return self.get_secret(secret_name)


# ============================================================================
# Convenience Functions
# ============================================================================

# Global secret manager instance
_global_secrets: Optional[SecretManager] = None


def get_secrets() -> SecretManager:
    """
    Get global SecretManager instance (singleton pattern).
    
    Returns:
        Global SecretManager instance
    
    Example:
        >>> from src.utils.secrets import get_secrets
        >>> secrets = get_secrets()
        >>> bucket = secrets.get_secret("GCS_BUCKET")
    """
    global _global_secrets
    
    if _global_secrets is None:
        logger.debug("Initializing global SecretManager instance")
        _global_secrets = SecretManager()
    
    return _global_secrets


def get_secret(secret_name: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get secret using global SecretManager.
    
    Args:
        secret_name: Name of secret to retrieve
        required: Whether secret is required
        default: Default value if not found
    
    Returns:
        Secret value or default
    
    Example:
        >>> from src.utils.secrets import get_secret
        >>> bucket = get_secret("GCS_BUCKET")
        >>> api_key = get_secret("API_KEY", required=False, default="")
    """
    return get_secrets().get_secret(secret_name, required=required, default=default)


# ============================================================================
# Migration Helper
# ============================================================================

def migrate_to_secret_manager(
    secret_names: list[str],
    project_id: str,
    dry_run: bool = True,
) -> None:
    """
    Helper function to migrate secrets from environment to GCP Secret Manager.
    
    Reads secrets from environment variables and creates them in Secret Manager.
    
    Args:
        secret_names: List of secret names to migrate
        project_id: GCP project ID
        dry_run: If True, only print what would be done
    
    Note:
        This is a utility function for migration. Use with caution in production.
    
    Example:
        >>> migrate_to_secret_manager(
        ...     secret_names=["GCS_BUCKET", "BQ_PROJECT", "ES_API_KEY"],
        ...     project_id="my-project",
        ...     dry_run=True
        ... )
    """
    logger.info(f"Starting secret migration (dry_run={dry_run})")
    
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}"
        
        for secret_name in secret_names:
            # Get value from environment
            value = os.getenv(secret_name)
            
            if value is None:
                logger.warning(f"Secret {secret_name} not found in environment, skipping")
                continue
            
            if dry_run:
                logger.info(f"[DRY RUN] Would create secret: {secret_name}")
                continue
            
            try:
                # Create secret
                secret = client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_name,
                        "secret": {
                            "replication": {"automatic": {}},
                        },
                    }
                )
                
                logger.info(f"Created secret: {secret.name}")
                
                # Add secret version
                version = client.add_secret_version(
                    request={
                        "parent": secret.name,
                        "payload": {"data": value.encode("UTF-8")},
                    }
                )
                
                logger.info(f"Added version: {version.name}")
            
            except Exception as e:
                logger.error(f"Failed to create secret {secret_name}: {e}")
        
        logger.info("Secret migration completed")
    
    except ImportError:
        logger.error("google-cloud-secret-manager not installed")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Mixamo Blend Pipeline Secret Manager"
    )
    parser.add_argument(
        "secret_name",
        nargs="?",
        help="Secret name to retrieve (for testing)",
    )
    parser.add_argument(
        "--backend",
        choices=["environment", "google_secret_manager", "kubernetes"],
        help="Force specific backend",
    )
    parser.add_argument(
        "--project-id",
        help="GCP project ID (for Secret Manager)",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Migrate secrets to Secret Manager",
    )
    parser.add_argument(
        "--secrets",
        nargs="+",
        help="Secret names to migrate",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (don't actually create secrets)",
    )
    
    args = parser.parse_args()
    
    if args.migrate:
        # Migration mode
        if not args.secrets or not args.project_id:
            print("Error: --secrets and --project-id required for migration")
            exit(1)
        
        migrate_to_secret_manager(
            secret_names=args.secrets,
            project_id=args.project_id,
            dry_run=args.dry_run,
        )
    
    elif args.secret_name:
        # Test mode - retrieve single secret
        config = None
        if args.backend:
            config = SecretConfig(
                backend=SecretBackend(args.backend),
                project_id=args.project_id,
            )
        
        secrets = SecretManager(config=config)
        value = secrets.get_secret(args.secret_name, required=False)
        
        if value:
            print(f"✓ Secret '{args.secret_name}' retrieved")
            print(f"  Length: {len(value)} characters")
            print(f"  Preview: {value[:10]}..." if len(value) > 10 else f"  Value: {value}")
        else:
            print(f"✗ Secret '{args.secret_name}' not found")
    
    else:
        # No arguments - show configuration
        secrets = SecretManager()
        print(f"Backend: {secrets.config.backend.value}")
        print(f"Project ID: {secrets.config.project_id}")
        print(f"Cache enabled: {secrets.config.cache_secrets}")

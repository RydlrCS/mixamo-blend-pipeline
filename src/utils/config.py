"""
Environment configuration loader for mixamo-blend-pipeline.

Loads configuration from .env file or environment variables for GCS, BigQuery,
and Elasticsearch integration.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Pipeline environment configuration."""

    # Google Cloud Storage
    gcs_bucket: str

    # BigQuery
    bq_project: str
    bq_dataset: str

    # Elasticsearch
    elasticsearch_url: Optional[str] = None
    es_api_key: Optional[str] = None
    es_index: Optional[str] = None

    # Google Cloud Authentication
    google_credentials_path: Optional[str] = None

    # Pipeline settings
    max_upload_size_mb: int = 500
    upload_timeout_seconds: int = 300

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """
        Load configuration from environment variables.

        Attempts to load .env file if present, then reads from os.environ.

        Returns:
            PipelineConfig instance with loaded values

        Raises:
            ValueError: If required environment variables are missing
        """
        # Try to load .env file using python-dotenv if available
        try:
            from dotenv import load_dotenv  # type: ignore

            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        except ImportError:
            pass  # python-dotenv not installed, use system env vars

        # Required variables
        gcs_bucket = os.getenv("GCS_BUCKET")
        bq_project = os.getenv("BQ_PROJECT")
        bq_dataset = os.getenv("BQ_DATASET")

        if not gcs_bucket:
            raise ValueError(
                "GCS_BUCKET environment variable is required. "
                "Set it in .env or export it."
            )
        if not bq_project:
            raise ValueError(
                "BQ_PROJECT environment variable is required. "
                "Set it in .env or export it."
            )
        if not bq_dataset:
            raise ValueError(
                "BQ_DATASET environment variable is required. "
                "Set it in .env or export it."
            )

        # Optional variables
        return cls(
            gcs_bucket=gcs_bucket,
            bq_project=bq_project,
            bq_dataset=bq_dataset,
            elasticsearch_url=os.getenv("ELASTICSEARCH_URL"),
            es_api_key=os.getenv("ES_API_KEY"),
            es_index=os.getenv("ES_INDEX", "mb_blends_v1"),
            google_credentials_path=os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS"
            ),
            max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "500")),
            upload_timeout_seconds=int(
                os.getenv("UPLOAD_TIMEOUT_SECONDS", "300")
            ),
        )


# Global config instance (lazy-loaded)
_config: Optional[PipelineConfig] = None


def get_config() -> PipelineConfig:
    """
    Get or create pipeline configuration singleton.

    Returns:
        PipelineConfig instance loaded from environment

    Example:
        >>> config = get_config()
        >>> print(config.gcs_bucket)
        motionblend-mocap
    """
    global _config
    if _config is None:
        _config = PipelineConfig.from_env()
    return _config

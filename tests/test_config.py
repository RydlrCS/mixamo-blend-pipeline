"""Tests for pipeline configuration module."""

import pytest

from src.utils.config import PipelineConfig, get_config


class TestPipelineConfig:
    """Test PipelineConfig dataclass and loading."""

    def test_config_creation(self):
        """Test direct PipelineConfig instantiation."""
        config = PipelineConfig(
            gcs_bucket="test-bucket",
            bq_project="test-project",
            bq_dataset="TEST_DEV",
        )

        assert config.gcs_bucket == "test-bucket"
        assert config.bq_project == "test-project"
        assert config.bq_dataset == "TEST_DEV"
        assert config.max_upload_size_mb == 500
        assert config.upload_timeout_seconds == 300

    def test_config_with_optional_values(self):
        """Test PipelineConfig with all optional fields."""
        config = PipelineConfig(
            gcs_bucket="test-bucket",
            bq_project="test-project",
            bq_dataset="TEST_DEV",
            elasticsearch_url="https://elastic.example.com",
            es_api_key="test-key",
            es_index="custom_index",
            google_credentials_path="/path/to/creds.json",
            max_upload_size_mb=1000,
            upload_timeout_seconds=600,
        )

        assert config.elasticsearch_url == "https://elastic.example.com"
        assert config.es_api_key == "test-key"
        assert config.es_index == "custom_index"
        assert config.google_credentials_path == "/path/to/creds.json"
        assert config.max_upload_size_mb == 1000
        assert config.upload_timeout_seconds == 600

    def test_from_env_missing_required(self, monkeypatch):
        """Test from_env raises ValueError when required vars missing."""
        # Clear all env vars
        monkeypatch.delenv("GCS_BUCKET", raising=False)
        monkeypatch.delenv("BQ_PROJECT", raising=False)
        monkeypatch.delenv("BQ_DATASET", raising=False)

        with pytest.raises(ValueError, match="GCS_BUCKET.*required"):
            PipelineConfig.from_env()

    def test_from_env_with_required_only(self, monkeypatch):
        """Test from_env with only required environment variables."""
        monkeypatch.setenv("GCS_BUCKET", "env-bucket")
        monkeypatch.setenv("BQ_PROJECT", "env-project")
        monkeypatch.setenv("BQ_DATASET", "ENV_DEV")

        # Clear optional vars
        monkeypatch.delenv("ELASTICSEARCH_URL", raising=False)
        monkeypatch.delenv("ES_API_KEY", raising=False)

        config = PipelineConfig.from_env()

        assert config.gcs_bucket == "env-bucket"
        assert config.bq_project == "env-project"
        assert config.bq_dataset == "ENV_DEV"
        assert config.elasticsearch_url is None
        assert config.es_api_key is None
        assert config.es_index == "mb_blends_v1"  # Default value

    def test_from_env_with_all_vars(self, monkeypatch):
        """Test from_env loads all environment variables correctly."""
        monkeypatch.setenv("GCS_BUCKET", "full-bucket")
        monkeypatch.setenv("BQ_PROJECT", "full-project")
        monkeypatch.setenv("BQ_DATASET", "FULL_DEV")
        monkeypatch.setenv("ELASTICSEARCH_URL", "https://es.test.com")
        monkeypatch.setenv("ES_API_KEY", "test-api-key")
        monkeypatch.setenv("ES_INDEX", "custom_index")
        monkeypatch.setenv(
            "GOOGLE_APPLICATION_CREDENTIALS", "/path/to/sa.json"
        )
        monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "750")
        monkeypatch.setenv("UPLOAD_TIMEOUT_SECONDS", "450")

        config = PipelineConfig.from_env()

        assert config.gcs_bucket == "full-bucket"
        assert config.bq_project == "full-project"
        assert config.bq_dataset == "FULL_DEV"
        assert config.elasticsearch_url == "https://es.test.com"
        assert config.es_api_key == "test-api-key"
        assert config.es_index == "custom_index"
        assert config.google_credentials_path == "/path/to/sa.json"
        assert config.max_upload_size_mb == 750
        assert config.upload_timeout_seconds == 450

    def test_get_config_singleton(self, monkeypatch):
        """Test get_config returns singleton instance."""
        monkeypatch.setenv("GCS_BUCKET", "singleton-bucket")
        monkeypatch.setenv("BQ_PROJECT", "singleton-project")
        monkeypatch.setenv("BQ_DATASET", "SINGLETON_DEV")

        # Reset global config to test fresh load
        import src.utils.config as config_module

        config_module._config = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
        assert config1.gcs_bucket == "singleton-bucket"

from cobalt_wren.config.artifact_store import normalize_artifact_store_settings
from cobalt_wren.config.checkpoint_store import normalize_checkpoint_store_settings
from cobalt_wren.config.models import PostgresCheckpointStoreSettings, S3ArtifactStoreSettings, StoreBackendConfig


def test_s3_artifact_settings() -> None:
    value = normalize_artifact_store_settings(StoreBackendConfig(backend="s3", config={"bucket": "artifacts", "prefix": "prod"}))
    assert isinstance(value, S3ArtifactStoreSettings)


def test_postgres_checkpoint_settings() -> None:
    value = normalize_checkpoint_store_settings(StoreBackendConfig(backend="postgres", config={"dsn": "postgresql://example/db"}))
    assert isinstance(value, PostgresCheckpointStoreSettings)

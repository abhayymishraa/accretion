"""Object storage and daily transfer ceilings."""

from config import BaseConfig


class StorageConfig(BaseConfig):
    STORAGE_PROVIDER: str = "minio"
    STORAGE_BUCKET: str = ""

    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""

    STORAGE_DAILY_UPLOAD_MB: int = 256
    STORAGE_DAILY_DOWNLOAD_MB: int = 1024

    @property
    def required_keys(self) -> tuple[str, ...]:
        """Names that must be set before a run may start, given the provider."""
        minio = ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")
        return ("STORAGE_BUCKET",) + (minio if self.STORAGE_PROVIDER == "minio" else ())

    @property
    def configured(self) -> bool:
        return all(getattr(self, name) for name in self.required_keys)

    def daily_limit_bytes(self, direction: str) -> int:
        megabytes = self.STORAGE_DAILY_UPLOAD_MB if direction == "uploaded" else self.STORAGE_DAILY_DOWNLOAD_MB
        return megabytes * 1024 * 1024


storage_settings = StorageConfig()

"""Типизированная загрузка конфигурации
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_env: Literal["development", "production", "test"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    # Security
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    password_hash_scheme: Literal["argon2", "bcrypt"] = "argon2"
    # Database
    database_url: str = "sqlite:///./data/receipt_ai.db"
    # Uploads
    upload_dir: Path = Path("./data/uploads")
    max_upload_mb: int = 15
    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@receipt-ai.local"
    email_backend: Literal["console", "smtp"] = "console"
    # Rate limiting
    login_max_attempts: int = 5
    login_window_seconds: int = 300
    # Configs
    configs_dir: Path = Path("./configs")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


class DetectorTargets(BaseModel):
    successful_alignment: float = 0.90


class DetectorFallback(BaseModel):
    enabled: bool = True
    min_area_ratio: float = 0.15
    canny_low: int = 50
    canny_high: int = 150


class DetectorConfig(BaseModel):
    method: Literal["yolo", "contour"] = "yolo"
    weights_path: str = "weights/detector/best.pt"
    conf_threshold: float = 0.25
    iou_threshold: float = 0.45
    input_size: int = 640
    fallback: DetectorFallback = Field(default_factory=DetectorFallback)
    targets: DetectorTargets = Field(default_factory=DetectorTargets)


class DonutInference(BaseModel):
    num_beams: int = 1
    device: str = "auto"


class DonutTrain(BaseModel):
    epochs: int = 15
    batch_size: int = 2
    grad_accum_steps: int = 4
    lr: float = 3.0e-5
    weight_decay: float = 0.01
    warmup_steps: int = 300
    fp16: bool = True
    checkpoint_dir: str = ""
    save_every_steps: int = 200
    resume_from_checkpoint: bool = True


class DonutTargets(BaseModel):
    field_accuracy_total: float = 0.85
    field_accuracy_merchant: float = 0.80
    field_accuracy_date: float = 0.80


class DonutFields(BaseModel):
    weights_path: str = "weights/donut_sroie"
    task_prompt: str = "<s_sroie>"
    max_length: int = 512
    field_order: list[str] = Field(
        default_factory=lambda: ["company", "date", "address", "total"]
    )


class DonutItems(BaseModel):
    task_prompt: str = "<s_cord-v2>"
    max_length: int = 768


class DonutConfig(BaseModel):
    base_model: str = "naver-clova-ix/donut-base-finetuned-cord-v2"
    image_size: list[int] = Field(default_factory=lambda: [1280, 960])
    fields: DonutFields = Field(default_factory=DonutFields)
    items: DonutItems = Field(default_factory=DonutItems)
    inference: DonutInference = Field(default_factory=DonutInference)
    train: DonutTrain = Field(default_factory=DonutTrain)
    targets: DonutTargets = Field(default_factory=DonutTargets)


class CategorizerInference(BaseModel):
    device: str = "auto"
    confidence_threshold: float = 0.45


class CategorizerTrain(BaseModel):
    epochs: int = 10
    batch_size: int = 16
    lr: float = 2.0e-5
    weight_decay: float = 0.01
    fp16: bool = True
    checkpoint_dir: str = ""


class CategorizerTargets(BaseModel):
    macro_f1: float = 0.80


class CategorizerConfig(BaseModel):
    base_model: str = "bert-base-multilingual-cased"
    weights_path: str = "weights/categorizer"
    max_length: int = 128
    labels: list[str] = Field(
        default_factory=lambda: [
            "Продукты", "Кафе и рестораны", "Транспорт",
            "Аптека", "Развлечения", "Прочее",
        ]
    )
    inference: CategorizerInference = Field(default_factory=CategorizerInference)
    train: CategorizerTrain = Field(default_factory=CategorizerTrain)
    targets: CategorizerTargets = Field(default_factory=CategorizerTargets)


class AppMeta(BaseModel):
    name: str = "Receipt-AI"
    version: str = "1.0"
    cors_origins: list[str] = Field(default_factory=list)


class UploadsCfg(BaseModel):
    allowed_extensions: list[str] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "heic"]
    )
    max_upload_mb: int = 15


class PipelineCfg(BaseModel):
    target_latency_seconds: int = 10
    default_category: str = "Прочее"


class AppConfig(BaseModel):
    app: AppMeta = Field(default_factory=AppMeta)
    uploads: UploadsCfg = Field(default_factory=UploadsCfg)
    pipeline: PipelineCfg = Field(default_factory=PipelineCfg)


class Configs(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    donut: DonutConfig = Field(default_factory=DonutConfig)
    categorizer: CategorizerConfig = Field(default_factory=CategorizerConfig)


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_configs(configs_dir: str | None = None) -> Configs:
    base = Path(configs_dir or settings.configs_dir)
    app_raw = _read_yaml(base / "app.yaml")
    return Configs(
        app=AppConfig(**app_raw) if app_raw else AppConfig(),
        detector=DetectorConfig(**_read_yaml(base / "detector.yaml").get("detector", {})),
        donut=DonutConfig(**_read_yaml(base / "donut.yaml").get("donut", {})),
        categorizer=CategorizerConfig(
            **_read_yaml(base / "categorizer.yaml").get("categorizer", {})
        ),
    )


configs = get_configs()

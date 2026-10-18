import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
ISSUES = {"port", "workers"}

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# Load .env without overwriting variables supplied by the hosting environment.
load_dotenv(BASE_DIR / ".env", override=False)

app = FastAPI(title="Effective Configuration API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def coerce(key: str, value: object):
    text = str(value).strip()
    normalized_key = key.lower()
    if normalized_key in {"port", "workers"}:
        return int(text)
    if normalized_key == "debug":
        return text.lower() in {"true", "1", "yes", "on"}
    return text


def effective_config(cli_overrides: Optional[list[str]] = None):
    config = dict(DEFAULTS)

    environment = os.getenv("APP_ENV", "development").strip().lower()
    yaml_path = BASE_DIR / f"config.{environment}.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_values = yaml.safe_load(file) or {}
        if isinstance(yaml_values, dict):
            for key, value in yaml_values.items():
                config[key.lower()] = coerce(key, value)

    # .env layer: NUM_WORKERS is an alias for workers.
    env_file_values = {}
    dotenv_path = BASE_DIR / ".env"
    if dotenv_path.exists():
        from dotenv import dotenv_values
        env_file_values = dotenv_values(dotenv_path)
    for key, value in env_file_values.items():
        if value is None:
            continue
        mapped_key = "workers" if key == "NUM_WORKERS" else (
            key[4:].lower() if key.startswith("APP_") else key.lower()
        )
        config[mapped_key] = coerce(mapped_key, value)

    # OS-level APP_* values take precedence over the .env layer.
    for key, value in os.environ.items():
        if key.startswith("APP_") and key != "APP_ENV":
            mapped_key = key[4:].lower()
            config[mapped_key] = coerce(mapped_key, value)

    # Query parameters are the highest-precedence layer.
    for override in cli_overrides or []:
        if "=" not in override:
            continue
        key, value = override.split("=", 1)
        key = key.strip().lower()
        if not key:
            continue
        try:
            config[key] = coerce(key, value)
        except (TypeError, ValueError):
            # Ignore malformed overrides instead of failing the whole request.
            continue

    # Never expose the configured secret.
    config["api_key"] = "****"
    return config


@app.get("/effective-config")
def get_effective_config(set: Optional[list[str]] = Query(default=None)):
    return effective_config(set)


@app.get("/health")
def health():
    return {"ok": True}

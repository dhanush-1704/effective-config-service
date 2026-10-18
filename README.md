# Effective Configuration Service

FastAPI endpoint merges hardcoded defaults, `config.<APP_ENV>.yaml`, `.env`, OS `APP_*` environment variables, then repeated `?set=key=value` query overrides. The `api_key` field is always masked as `****`.

Run with `pip install -r requirements.txt` then `uvicorn app:app --reload`.

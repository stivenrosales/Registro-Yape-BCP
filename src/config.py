from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str
    gemini_model: str = "google/gemini-2.5-flash-lite"

    # Google Sheets
    google_sheet_id: str

    # Gmail
    gmail_credentials_path: str = "credentials.json"
    gmail_token_path: str = "token.json"

    # Configuración — remitentes separados por coma
    email_senders: str = "notificaciones@notificacionesbcp.com.pe,notificaciones@yape.pe"
    emails_after_date: str = "2026/03/01"
    max_emails_per_run: int = 50
    gmail_processed_label: str = "gastos-procesado"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

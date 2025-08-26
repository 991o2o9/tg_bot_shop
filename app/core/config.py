from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

	bot_token: str
	admin_ids: str | None = None

	database_url: str

	# optional
	webhook_url: str | None = None
	webapp_host: str = "0.0.0.0"
	webapp_port: int = 8080

	# messaging
	manager_chat_id: int | None = None

	# branding/welcome
	logo_file_id: str | None = None
	welcome_text: str | None = None


settings = Settings()  # type: ignore[arg-type]



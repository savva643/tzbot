import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    bot_token: str
    openrouter_key: str
    pay_amount: int
    db_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data.db'}"
    default_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    fallback_model: str = "openai/gpt-oss-20b:free"
    gemini_model: str = "google/gemini-flash-1.5-8b:free"
    admin_ids: tuple[int, ...] = ()
    app_name: str = "tzbot"

# берём из .env
def get_settings() -> Settings:
    admin_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = tuple(int(x.strip()) for x in admin_raw.split(",") if x.strip().isdigit())
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        openrouter_key=os.getenv("OPENROUTER_API_KEY", ""),
        pay_amount=int(os.getenv("PAY_AMOUNT_STARS", "10")),
        admin_ids=admin_ids,
    )

from __future__ import annotations

from pathlib import Path

import requests
from dotenv import load_dotenv
import os


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
PHOTO_PATH = ROOT / "test.png"


def load_credentials() -> tuple[str, str]:
    if not ENV_PATH.exists():
        raise RuntimeError(f"Missing .env file at {ENV_PATH}")
    load_dotenv(ENV_PATH)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in .env")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is missing in .env")
    return token, chat_id


def main() -> int:
    try:
        if not PHOTO_PATH.exists() or not PHOTO_PATH.is_file():
            raise RuntimeError(f"Missing photo file: {PHOTO_PATH}")
        token, chat_id = load_credentials()
        with PHOTO_PATH.open("rb") as photo:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": "SheGuard Telegram photo test."},
                files={"photo": photo},
                timeout=30,
            )
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}
        print("Telegram API response:")
        print(body)
        if response.ok and body.get("ok"):
            print("SUCCESS: Telegram photo sent.")
            return 0
        print("FAILURE: Telegram photo was not sent.")
        return 1
    except requests.RequestException as exc:
        print(f"FAILURE: Network or Telegram API request failed: {exc}")
        return 1
    except RuntimeError as exc:
        print(f"FAILURE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

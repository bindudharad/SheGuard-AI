from __future__ import annotations

from pathlib import Path

import requests
from dotenv import load_dotenv
import os


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
MESSAGE = "🚨 SheGuard Test Alert\n\nTelegram integration working successfully."


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
        token, chat_id = load_credentials()
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": MESSAGE},
            timeout=15,
        )
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}
        print("Telegram API response:")
        print(body)
        if response.ok and body.get("ok"):
            print("SUCCESS: Telegram text message sent.")
            return 0
        print("FAILURE: Telegram text message was not sent.")
        return 1
    except requests.RequestException as exc:
        print(f"FAILURE: Network or Telegram API request failed: {exc}")
        return 1
    except RuntimeError as exc:
        print(f"FAILURE: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

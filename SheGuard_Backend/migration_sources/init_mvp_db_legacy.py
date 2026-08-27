from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import init_database  # noqa: E402


if __name__ == "__main__":
    init_database()
    print(f"SheGuard MVP database initialized at {ROOT / 'sheguard.db'}")

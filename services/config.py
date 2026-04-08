import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=DOTENV_PATH, override=False)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "666")
RULES_DIR = os.path.join(BASE_DIR, "rules_storage")
HISTORY_FILE = os.path.join(BASE_DIR, "audit_history.json")
CUSTOM_RULES_FILE = os.path.join(BASE_DIR, "custom_rules.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "system_settings.json")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "50"))
MAX_AUDIT_TARGET_CHARS = int(os.getenv("MAX_AUDIT_TARGET_CHARS", "50000"))
MAX_BATCH_ITEMS = int(os.getenv("MAX_BATCH_ITEMS", "50"))

DEFAULT_SETTINGS = {
    "risk_threshold": {"high": 0.8, "medium": 0.5},
    "speed_mode": "balanced",  # fast|balanced|deep
    "local_mode": True,
    "retain_days": 7,
}

for path in [RULES_DIR]:
    os.makedirs(path, exist_ok=True)

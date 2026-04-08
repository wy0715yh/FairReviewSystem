import json
import os
from datetime import datetime
from typing import Any, Dict, List

from .config import (
    CUSTOM_RULES_FILE,
    DEFAULT_SETTINGS,
    HISTORY_FILE,
    MAX_HISTORY,
    RULES_DIR,
    SETTINGS_FILE,
)


def _load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---- history ----
def load_history() -> List[Dict[str, Any]]:
    return _load_json(HISTORY_FILE, [])


def add_history(title: str, content: str, report_html: str, structured: Dict[str, Any] | None = None):
    items = load_history()
    record = {
        "id": (items[0]["id"] + 1 if items else 1),
        "title": title[:80],
        "content": content,
        "result": report_html,
        "structured": structured or {},
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    items.insert(0, record)
    _save_json(HISTORY_FILE, items[:MAX_HISTORY])
    return record


def remove_history(record_id: int) -> bool:
    items = load_history()
    nxt = [x for x in items if int(x.get("id", 0)) != int(record_id)]
    if len(nxt) == len(items):
        return False
    _save_json(HISTORY_FILE, nxt)
    return True


def clear_history() -> int:
    items = load_history()
    count = len(items)
    _save_json(HISTORY_FILE, [])
    return count


# ---- rules ----
def list_rules() -> List[str]:
    files = [f for f in os.listdir(RULES_DIR) if f.endswith(".txt")]
    return sorted([f[:-4] for f in files])


def read_all_rules() -> List[Dict[str, str]]:
    rows = []
    for name in list_rules():
        path = os.path.join(RULES_DIR, f"{name}.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                rows.append({"name": name, "text": f.read()})
        except Exception:
            continue
    return rows


def save_rule(name: str, text: str):
    path = os.path.join(RULES_DIR, f"{name}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def delete_rule(name: str) -> bool:
    path = os.path.join(RULES_DIR, f"{name}.txt")
    if not os.path.exists(path):
        return False
    os.remove(path)
    return True


# ---- custom rules ----
def load_custom_rules() -> List[Dict[str, Any]]:
    return _load_json(CUSTOM_RULES_FILE, [])


def save_custom_rules(items: List[Dict[str, Any]]):
    _save_json(CUSTOM_RULES_FILE, items)


def upsert_custom_rule(rule: Dict[str, Any]):
    rows = load_custom_rules()
    rid = str(rule.get("id") or "").strip() or str(int(datetime.now().timestamp() * 1000))
    payload = {
        "id": rid,
        "name": str(rule.get("name", "")).strip() or f"规则-{rid[-6:]}",
        "risk_level": str(rule.get("risk_level", "中")).strip() or "中",
        "description": str(rule.get("description", "")).strip(),
        "keywords": [str(x).strip() for x in rule.get("keywords", []) if str(x).strip()],
        "contract_type": str(rule.get("contract_type", "通用")).strip() or "通用",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    replaced = False
    for i, row in enumerate(rows):
        if str(row.get("id")) == rid:
            rows[i] = payload
            replaced = True
            break
    if not replaced:
        rows.insert(0, payload)
    save_custom_rules(rows)
    return payload


def remove_custom_rule(rule_id: str) -> bool:
    rows = load_custom_rules()
    nxt = [x for x in rows if str(x.get("id")) != str(rule_id)]
    if len(nxt) == len(rows):
        return False
    save_custom_rules(nxt)
    return True


# ---- settings ----
def load_settings() -> Dict[str, Any]:
    raw = _load_json(SETTINGS_FILE, {})
    merged = dict(DEFAULT_SETTINGS)
    merged.update(raw if isinstance(raw, dict) else {})
    return merged


def save_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings()
    current.update(data or {})
    _save_json(SETTINGS_FILE, current)
    return current

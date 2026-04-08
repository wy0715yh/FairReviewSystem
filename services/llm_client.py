from __future__ import annotations

import json
import os
import re
import time
from urllib.parse import urlparse
from typing import Any, Dict, List

import requests
from dotenv import dotenv_values

from .config import DOTENV_PATH


def strip_think_blocks(text: str) -> str:
    t = text or ""
    t = re.sub(r"<think>[\s\S]*?</think>", "", t, flags=re.IGNORECASE)
    if "<think>" in t.lower():
        t = re.sub(r"<think>[\s\S]*", "", t, flags=re.IGNORECASE)
    return t.strip()


def _extract_text_from_response(data: Dict[str, Any]) -> str:
    # OpenAI-compatible shape
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        c0 = choices[0] if isinstance(choices[0], dict) else {}
        msg = c0.get("message") if isinstance(c0.get("message"), dict) else {}
        content = msg.get("content")
        if isinstance(content, list):
            text = "".join((x.get("text", "") if isinstance(x, dict) else str(x)) for x in content)
            if text.strip():
                return text
        if isinstance(content, str) and content.strip():
            return content
        c0_text = c0.get("text")
        if isinstance(c0_text, str) and c0_text.strip():
            return c0_text

    # MiniMax v2 shape (commonly uses reply)
    for key in ["reply", "output_text", "text", "answer"]:
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val

    return ""


def _should_retry_by_status(status_code: int) -> bool:
    return status_code in (408, 409, 429) or status_code >= 500


def _build_proxy_from_env(env: Dict[str, Any]) -> Dict[str, str] | None:
    raw = str(env.get("MINIMAX_PROXY_URLS") or os.getenv("MINIMAX_PROXY_URLS") or "").strip()
    if not raw:
        return None
    first = ""
    for item in raw.split(","):
        s = item.strip()
        if s:
            first = s
            break
    if not first:
        return None
    return {"http": first, "https": first}


def _merge_no_proxy_for_minimax():
    targets = ["api.minimax.chat", "api.minimaxi.com"]
    existing = os.getenv("NO_PROXY", "")
    items = [x.strip() for x in existing.split(",") if x.strip()]
    changed = False
    for t in targets:
        if t not in items:
            items.append(t)
            changed = True
    if changed:
        os.environ["NO_PROXY"] = ",".join(items)


def _normalize_url(u: str) -> str:
    s = (u or "").strip()
    if not s:
        return ""
    parsed = urlparse(s)
    if parsed.scheme and parsed.netloc and parsed.path.rstrip("/") == "/v1":
        return s.rstrip("/") + "/chat/completions"
    return s


def call_llm(
    prompt: str,
    max_total_seconds: float = 45,
    connect_timeout: float = 4,
    read_timeout: float = 18,
    retries_per_url: int = 1,
    max_urls: int = 3,
    max_tokens: int = 1200,
    temperature: float = 0.2,
) -> str:
    env = dotenv_values(DOTENV_PATH)
    api_key = env.get("MINIMAX_API_KEY") or os.getenv("MINIMAX_API_KEY")
    model = env.get("MINIMAX_MODEL") or os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
    url_main = _normalize_url(
        env.get("MINIMAX_URL")
        or os.getenv("MINIMAX_URL", "https://api.minimax.chat/v1/text/chatcompletion_v2")
    )
    if not api_key:
        raise RuntimeError("未配置 MINIMAX_API_KEY")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": int(max_tokens),
    }

    _merge_no_proxy_for_minimax()
    proxies = _build_proxy_from_env(env)

    urls = []
    default_fallbacks = [
        "https://api.minimax.chat/v1/text/chatcompletion_v2",
        "https://api.minimax.chat/v1/chat/completions",
    ]
    for u in [url_main] + default_fallbacks:
        nu = _normalize_url(u)
        if nu and nu not in urls:
            urls.append(nu)
    urls = urls[: max(1, max_urls)]

    start = time.time()
    last_err: Exception | None = None
    hard_err: Exception | None = None
    for url in urls:
        for _ in range(max(1, retries_per_url)):
            remain = max_total_seconds - (time.time() - start)
            if remain <= 0:
                break
            try:
                t_conn = min(connect_timeout, max(0.5, remain * 0.35))
                t_read = min(read_timeout, max(1.0, remain - t_conn))
                r = requests.post(url, headers=headers, json=payload, timeout=(t_conn, t_read), proxies=proxies)
                if r.status_code >= 400:
                    body = (r.text or "")[:260]
                    msg = f"LLM接口错误: HTTP {r.status_code} @ {url} | {body}"
                    if _should_retry_by_status(r.status_code):
                        raise RuntimeError(msg)
                    hard_err = RuntimeError(msg)
                    break
                data = r.json()
                text = _extract_text_from_response(data)
                if not text:
                    raise RuntimeError(f"LLM返回内容为空 @ {url}")
                return strip_think_blocks(str(text))
            except Exception as e:
                last_err = e
                time.sleep(0.3)
                continue
        if hard_err is not None:
            break
    if hard_err is not None:
        raise RuntimeError(str(hard_err))
    raise RuntimeError(f"LLM调用失败: {last_err}")


def extract_json_object(text: str) -> Dict[str, Any] | None:
    t = (text or "").strip()
    if not t:
        return None
    blocks: List[str] = []
    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", t, flags=re.IGNORECASE):
        raw = (m.group(1) or "").strip()
        if raw.startswith("{") and raw.endswith("}"):
            blocks.append(raw)

    starts = [i for i, ch in enumerate(t) if ch == "{"]
    for st in starts:
        depth = 0
        in_str = False
        esc = False
        for i in range(st, len(t)):
            ch = t[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(t[st : i + 1])
                    break

    seen = set()
    for raw in blocks:
        if raw in seen:
            continue
        seen.add(raw)
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None

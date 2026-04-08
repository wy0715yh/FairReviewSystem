from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

from .storage import read_all_rules


def split_text_to_chunks(text: str, chunk_size: int = 1000, overlap: int = 120) -> List[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    res: List[str] = []
    step = max(1, chunk_size - overlap)
    i = 0
    while i < len(clean):
        s = clean[i : i + chunk_size].strip()
        if s:
            res.append(s)
        i += step
    return res


def normalize_for_match(text: str, max_len: int = 8000) -> str:
    t = (text or "").lower()
    t = re.sub(r"\s+", "", t)
    return t[:max_len]


def vectorize_text(text: str) -> Counter:
    n = normalize_for_match(text)
    if not n:
        return Counter()
    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", n)
    tokens += [n[i : i + 2] for i in range(max(0, len(n) - 1))]
    return Counter(tokens)


def cosine_sim(v1: Counter, v2: Counter) -> float:
    if not v1 or not v2:
        return 0.0
    keys = set(v1.keys()) & set(v2.keys())
    dot = sum(v1[k] * v2[k] for k in keys)
    n1 = math.sqrt(sum(x * x for x in v1.values()))
    n2 = math.sqrt(sum(x * x for x in v2.values()))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def build_rule_chunks() -> List[Dict]:
    chunks: List[Dict] = []
    for row in read_all_rules():
        for i, chunk in enumerate(split_text_to_chunks(row["text"]), start=1):
            chunks.append({"source": row["name"], "chunk_id": i, "text": chunk})
    return chunks


def retrieve_relevant_knowledge(query: str, top_k: int = 5, max_chunk_chars: int = 360) -> str:
    rows = search_knowledge(query, top_k=top_k, max_chunk_chars=max_chunk_chars)
    if not rows:
        return ""
    lines = []
    for i, row in enumerate(rows, start=1):
        lines.append(
            f"【依据片段{i}｜来源：{row['source']}｜片段：{row['chunk_id']}｜相似度：{row['score']:.3f}】\n{row['text']}"
        )
    return "\n".join(lines)


def search_knowledge(query: str, top_k: int = 10, max_chunk_chars: int = 260) -> List[Dict]:
    chunks = build_rule_chunks()
    if not chunks:
        return []
    qv = vectorize_text(query)
    scored = []
    for row in chunks:
        score = cosine_sim(qv, vectorize_text(row["text"]))
        if score > 0:
            scored.append((score, row))
    if not scored:
        return [
            {
                "source": row["source"],
                "chunk_id": row["chunk_id"],
                "score": 0.0,
                "text": row["text"][:max_chunk_chars],
            }
            for row in chunks[:top_k]
        ]
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, row in scored[:top_k]:
        out.append(
            {
                "source": row["source"],
                "chunk_id": row["chunk_id"],
                "score": score,
                "text": row["text"][:max_chunk_chars],
            }
        )
    return out


def match_custom_rules(text: str, custom_rules: List[Dict]) -> List[Dict]:
    content = text or ""
    out = []
    for r in custom_rules or []:
        keys = [str(x).strip() for x in (r.get("keywords") or []) if str(x).strip()]
        if not keys:
            continue
        hits = [k for k in keys if k in content]
        if not hits:
            continue
        out.append(
            {
                "rule_id": r.get("id"),
                "rule_name": r.get("name"),
                "risk_level": r.get("risk_level", "中"),
                "description": r.get("description", ""),
                "keywords_hit": hits,
            }
        )
    return out

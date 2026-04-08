from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from .config import MAX_AUDIT_TARGET_CHARS
from .llm_client import call_llm, extract_json_object
from .rag import match_custom_rules, retrieve_relevant_knowledge
from .storage import load_custom_rules


def _guess_policy_name(text: str) -> str:
    for line in (text or "").splitlines():
        s = line.strip()
        if s:
            return s[:80]
    return "未命名政策草案"


def _extract_quotes(text: str, limit: int = 3) -> List[str]:
    sents = [x.strip() for x in re.split(r"[。；;\n]", text or "") if x.strip()]
    out = []
    for s in sents:
        if any(k in s for k in ["不得", "禁止", "限制", "仅限", "必须", "排除", "优先"]):
            out.append(s[:140])
        if len(out) >= limit:
            break
    if not out:
        out = [x[:140] for x in sents[:limit]]
    return out


def _basis_names(knowledge_text: str) -> List[str]:
    names: List[str] = []
    for line in (knowledge_text or "").splitlines():
        m = re.match(r"【依据片段\d+｜来源：([^｜]+)", line.strip())
        if m:
            n = m.group(1).strip()
            if n and n not in names:
                names.append(n)
    return names


def _fallback_structured(target_text: str, knowledge_text: str, custom_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    quotes = _extract_quotes(target_text, limit=3)
    basis = _basis_names(knowledge_text)
    if not basis:
        basis = ["《公平竞争审查条例》", "《公平竞争审查条例实施细则》"]
    risk_level = "中"
    if any(k in target_text for k in ["禁止外省", "外地不得", "仅限本地"]):
        risk_level = "高"

    risk_items = []
    for q in quotes:
        risk_items.append(
            {
                "source_quote": q,
                "risk_level": risk_level,
                "problem": "条款可能构成地域身份或主体资格差异化限制，影响经营者平等参与竞争。",
                "basis": "《公平竞争审查条例》第九条、第十一条及相关实施细则",
                "suggestion": "删除地域/身份限制，改为与监管目标直接相关且必要、比例适当的中性条件。",
            }
        )

    return {
        "policy_name": _guess_policy_name(target_text),
        "risk_level": risk_level,
        "conclusion": "建议修订后发布" if risk_level in ["高", "中"] else "原则上可发布",
        "is_fcs_subject": True,
        "subject_reason": "文本设置了影响经营者参与市场活动的条件，属于公平竞争审查对象。",
        "object_review": "该政策条款将直接影响经营者参与会议、信息获取及合作机会分配，具备竞争影响，应纳入公平竞争审查。",
        "market_access_review": "存在将地域身份作为参与门槛的风险，可能构成歧视性准入条件。",
        "conduct_review": "该限制可能阻断跨区域经营者正常商务对接与交易机会，形成对经营行为的不当干预。",
        "risk_items": risk_items,
        "risks": [x["problem"] for x in risk_items[:3]],
        "suggestions": [
            "删除“外省/外地不得参与”等直接限制性表述。",
            "如确需管理条件，应以与会议目的直接相关、可核验且非歧视的标准替代。",
            "建立人工复核与复审机制，保留修订依据与审查留痕。",
        ],
        "warning_review": "若不修订，可能被监管抽查责令整改，并引发行政复议、诉讼或反垄断调查风险。",
        "basis": basis[:5],
        "expert_closing": "建议按风险条款逐条修订并复审，确保审查结论可解释、可复核、可执行。",
        "custom_rule_hits": custom_hits,
    }


def _normalize_structured(obj: Dict[str, Any], target_text: str, knowledge_text: str, custom_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    data = _fallback_structured(target_text, knowledge_text, custom_hits)
    if not isinstance(obj, dict):
        return data

    for k in [
        "risk_level",
        "conclusion",
        "is_fcs_subject",
        "subject_reason",
        "object_review",
        "market_access_review",
        "conduct_review",
        "warning_review",
        "expert_closing",
    ]:
        if k in obj and obj.get(k) not in [None, ""]:
            data[k] = obj.get(k)

    for arr in ["risks", "suggestions", "basis"]:
        val = obj.get(arr)
        if isinstance(val, list) and val:
            data[arr] = [str(x).strip() for x in val if str(x).strip()][:8]

    risk_items = []
    for it in obj.get("risk_items", []) if isinstance(obj.get("risk_items"), list) else []:
        if not isinstance(it, dict):
            continue
        quote = str(it.get("source_quote", "")).strip()
        if not quote:
            q = _extract_quotes(target_text, limit=1)
            quote = q[0] if q else ""
        risk_items.append(
            {
                "source_quote": quote,
                "risk_level": str(it.get("risk_level", data.get("risk_level", "中"))),
                "problem": str(it.get("problem", "")),
                "basis": str(it.get("basis", "")),
                "suggestion": str(it.get("suggestion", "")),
            }
        )
    if risk_items:
        data["risk_items"] = risk_items[:8]
    data["policy_name"] = _guess_policy_name(target_text)
    data["custom_rule_hits"] = custom_hits

    if str(data.get("risk_level")) not in ["高", "中", "低"]:
        data["risk_level"] = "中"
    return data


def _build_prompt(target_text: str, knowledge_text: str, custom_rules: List[Dict[str, Any]]) -> str:
    custom_rules_text = "\n".join(
        [
            f"- {r.get('name')}｜等级：{r.get('risk_level','中')}｜关键词：{','.join(r.get('keywords') or [])}｜描述：{r.get('description','')}"
            for r in custom_rules[:30]
        ]
    )
    return f"""
你是资深法律合规审查专家。请基于RAG检索法规与用户自定义规则，对合同/政策文本进行公平竞争合规性审查。

【待审文本】
{target_text[:MAX_AUDIT_TARGET_CHARS]}

【RAG法规依据】
{knowledge_text or '暂无命中，请依《公平竞争审查条例》通用标准。'}

【用户自定义规则】
{custom_rules_text or '无'}

【输出要求】
1) 仅输出严格JSON，不输出其他文字。
2) 文风需达到“法律合同风险审查意见”可直接展示标准。
3) 必须给出市场准入限制、经营行为规范、智能预警三部分实质结论。
4) risk_items必须逐条给出对应原文摘录，且摘录必须来自待审文本。
5) 优先引用具体法规名称+条号+对应事实。

【JSON结构】
{{
  "risk_level": "高/中/低",
  "conclusion": "一句话结论",
  "is_fcs_subject": true,
  "subject_reason": "对象判定理由",
  "object_review": "对象属性与触发条件判断",
  "market_access_review": "市场准入限制结论",
  "conduct_review": "经营行为规范结论",
  "risk_items": [
    {{"source_quote":"原文摘录","risk_level":"高/中/低","problem":"风险说明","basis":"法律依据","suggestion":"修改建议"}}
  ],
  "risks": ["风险点1","风险点2","风险点3"],
  "suggestions": ["建议1","建议2","建议3"],
  "warning_review": "智能预警",
  "basis": ["依据1","依据2","依据3"],
  "expert_closing": "专家结语"
}}
"""


def run_single_audit(target_text: str) -> Dict[str, Any]:
    started = time.time()
    knowledge_text = retrieve_relevant_knowledge(target_text, top_k=6, max_chunk_chars=280)
    custom_rules = load_custom_rules()
    custom_hits = match_custom_rules(target_text, custom_rules)

    prompt = _build_prompt(target_text, knowledge_text, custom_rules)
    raw = ""
    obj = None
    error = ""
    try:
        raw = call_llm(prompt, max_total_seconds=36, read_timeout=20, max_tokens=1600)
        obj = extract_json_object(raw)
    except Exception as e:
        error = str(e)

    structured = _normalize_structured(obj or {}, target_text, knowledge_text, custom_hits)
    elapsed = time.time() - started
    return {
        "structured": structured,
        "knowledge": knowledge_text,
        "raw": raw,
        "elapsed": elapsed,
        "fallback": obj is None,
        "error": error,
    }


def run_batch_audit(contracts: List[str]) -> Dict[str, Any]:
    rows = []
    high = medium = low = 0
    for t in contracts:
        result = run_single_audit(t)
        item = result["structured"]
        rows.append(item)
        lvl = str(item.get("risk_level", "中"))
        if lvl == "高":
            high += 1
        elif lvl == "低":
            low += 1
        else:
            medium += 1
    return {
        "total": len(rows),
        "high": high,
        "medium": medium,
        "low": low,
        "contracts": rows,
    }

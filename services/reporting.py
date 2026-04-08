from __future__ import annotations

import html
from typing import Dict, List


def _li(items: List[str]) -> str:
    return "".join([f"<li>{html.escape(str(x))}</li>" for x in items if str(x).strip()])


def render_single_report(data: Dict, elapsed_seconds: float | None = None) -> str:
    policy_name = str(data.get("policy_name", "未命名政策草案"))
    basis = data.get("basis") or []
    if not isinstance(basis, list):
        basis = [str(basis)]
    market_access_review = str(data.get("market_access_review", ""))
    conduct_review = str(data.get("conduct_review", ""))
    warning_review = str(data.get("warning_review", ""))
    risk_items = data.get("risk_items") or []
    suggestions = data.get("suggestions") or []
    conclusion = str(data.get("conclusion", "建议修订后发布"))
    risk_level = str(data.get("risk_level", "中"))
    subject_reason = str(data.get("subject_reason", ""))
    object_review = str(data.get("object_review", ""))
    expert_closing = str(data.get("expert_closing", ""))
    custom_hits = data.get("custom_rule_hits") or []

    risk_html = ""
    for item in risk_items:
        if not isinstance(item, dict):
            continue
        risk_html += (
            "<li>"
            f"<p><b>风险等级：</b>{html.escape(str(item.get('risk_level', risk_level)))}</p>"
            f"<p><b>对应原文：</b>{html.escape(str(item.get('source_quote', '')))}</p>"
            f"<p><b>风险说明：</b>{html.escape(str(item.get('problem', '')))}</p>"
            f"<p><b>法律依据：</b>{html.escape(str(item.get('basis', '')))}</p>"
            f"<p><b>优化建议：</b>{html.escape(str(item.get('suggestion', '')))}</p>"
            "</li>"
        )

    custom_html = ""
    for hit in custom_hits:
        custom_html += (
            "<li>"
            f"<b>{html.escape(str(hit.get('rule_name', '自定义规则')))}</b>"
            f"（等级：{html.escape(str(hit.get('risk_level', '中')))}）"
            f" 命中关键词：{html.escape(','.join(hit.get('keywords_hit') or []))}"
            "</li>"
        )

    elapsed_line = f"<p><i>耗时：{elapsed_seconds:.2f}s</i></p>" if elapsed_seconds is not None else ""

    return (
        "<h3>法律合同风险审查意见</h3>"
        f"<p><b>政策草案名称：</b>{html.escape(policy_name)}</p>"
        f"<p><b>审查依据：</b>{html.escape('、'.join([str(x) for x in basis if str(x).strip()]))}</p>"
        f"<p><b>审查结论：</b>{html.escape(conclusion)}（风险等级：{html.escape(risk_level)}）</p>"
        "<h4>1. 市场准入限制：是否存在排斥外地经营者、设置歧视性准入条件的情况？</h4>"
        f"<p>{html.escape(market_access_review)}</p>"
        "<h4>2. 经营行为规范：是否存在强制交易、影响生产经营成本或影响生产经营行为的条款？</h4>"
        f"<p>{html.escape(conduct_review)}</p>"
        "<h4>补充风险点（条款级定位）</h4>"
        f"<ul>{risk_html or '<li>未检出条款级高置信风险，建议人工复核。</li>'}</ul>"
        "<h4>修订建议</h4>"
        f"<ul>{_li([str(x) for x in suggestions])}</ul>"
        "<h4>3. 智能预警：若不修改，可能面临哪些法律风险或行政复议风险？</h4>"
        f"<p>{html.escape(warning_review)}</p>"
        "<h4>对象判定</h4>"
        f"<p>{html.escape(subject_reason)}</p>"
        f"<p>{html.escape(object_review)}</p>"
        "<h4>审查专家结语</h4>"
        f"<p>{html.escape(expert_closing)}</p>"
        + ("<h4>自定义规则命中</h4><ul>" + custom_html + "</ul>" if custom_html else "")
        + elapsed_line
    )


def render_batch_report(summary: Dict) -> str:
    contracts = summary.get("contracts") or []
    lis = []
    for c in contracts:
        lis.append(f"{c.get('policy_name','未命名')}：{c.get('risk_level','中')} - {c.get('conclusion','')} ")
    return (
        "<h3>批量合同审查汇总报告</h3>"
        f"<p><b>合同总数：</b>{summary.get('total', 0)}</p>"
        f"<p><b>高风险：</b>{summary.get('high', 0)} ｜ <b>中风险：</b>{summary.get('medium', 0)} ｜ <b>低风险：</b>{summary.get('low', 0)}</p>"
        "<h4>单份结果摘要</h4>"
        f"<ul>{_li(lis)}</ul>"
    )

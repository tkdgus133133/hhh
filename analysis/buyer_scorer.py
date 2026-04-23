"""바이어 평가 점수 계산 + 랭킹.

점수는 내부 정렬용으로만 사용 — 외부(프론트/PDF)에 노출하지 않음.
criteria=None: 성분 매칭 우선 + enrichment 완성도 순 정렬
criteria 있음: 선택 항목 점수 합산 → 성분 매칭 tie-break
전체 candidate 풀(20개) 대상으로 상위 top_n(10) 선택.
"""

from __future__ import annotations

import re
from typing import Any

SCORE_CRITERIA = [
    {"key": "기업규모",     "label": "기업 규모"},
    {"key": "유통실적",     "label": "유통 실적"},
    {"key": "GMP보유",      "label": "GMP 보유"},
    {"key": "공공채널",     "label": "공공 채널"},
    {"key": "민간채널",     "label": "민간 채널"},
    {"key": "파트너적합성", "label": "파트너 적합성"},
    {"key": "한국거래",     "label": "한국 거래 경험"},
    {"key": "MAH가능",      "label": "MAH 가능"},
]


def _bool_score(val: Any) -> int:
    return 100 if val is True else 0


def _revenue_score(revenue: str) -> int:
    if not revenue or revenue == "-":
        return 0
    r = revenue.upper()
    for marker, score in [
        ("$10B", 100), ("$5B", 100), ("$2B", 95), ("$1B", 90),
        ("$500M", 80), ("$300M", 75), ("$200M", 70),
        ("$100M", 60), ("$50M", 50), ("$20M", 40), ("$10M", 30),
    ]:
        if marker in r:
            return score
    return 20 if len(r) > 1 else 0


def _employee_score(employees: str) -> int:
    if not employees or employees == "-":
        return 0
    nums = [int(x.replace(",", "")) for x in re.findall(r"[\d,]+", employees)]
    if not nums:
        return 20
    n = max(nums)
    if n >= 10000: return 100
    if n >= 5000:  return 90
    if n >= 1000:  return 75
    if n >= 500:   return 60
    if n >= 100:   return 40
    return 20


def _korea_score(val: Any) -> int:
    if not val or val in ("-", "없음", "None"):
        return 0
    s = str(val)
    try:
        n = int(re.search(r"\d+", s).group())
        if n >= 5: return 100
        if n >= 3: return 80
        if n >= 1: return 60
    except Exception:
        pass
    if "있음" in s or "경험" in s:
        return 50
    return 0


def _enrichment_completeness(company: dict[str, Any]) -> int:
    """enrichment 완성도 점수 (정렬 보조용)."""
    e = company.get("enriched", {})
    score = 0
    if e.get("company_overview_kr", "-") not in ("-", ""):
        score += 30
    if e.get("recommendation_reason", "-") not in ("-", ""):
        score += 30
    if company.get("website", "-") != "-":
        score += 20
    if e.get("territories"):
        score += 10
    if e.get("revenue", "-") != "-":
        score += 10
    return score


def _normalize_text(s: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", str(s or "").lower())


def _static_signal_score(company: dict[str, Any], ctx: dict[str, Any]) -> float:
    """3개 정적 소스(NEAK/OGYEI/EMA) 기반 주점수."""
    prof = ctx.get("static_profile") or {}
    raw = prof.get("raw_payload") or {}
    price_rows = max(int(raw.get("price_rows", 0) or 0), 0)       # NEAK
    registry_rows = max(int(raw.get("registry_rows", 0) or 0), 0) # OGYEI
    ema_rows = max(int(raw.get("ema_rows", 0) or 0), 0)           # EMA

    # 3개 소스 기반 기본점 (0~100)
    base = min(100.0, price_rows * 1.4 + registry_rows * 0.22 + ema_rows * 2.2)

    # 정적 제조사와 후보 기업명이 유사하면 강한 가산
    manufacturer = _normalize_text(prof.get("manufacturer", ""))
    company_name = _normalize_text(company.get("company_name", ""))
    m_bonus = 0.0
    if manufacturer and company_name:
        if manufacturer in company_name or company_name in manufacturer:
            m_bonus = 25.0
        else:
            m_tokens = [t for t in re.split(r"\s+", str(prof.get("manufacturer", "")).lower()) if len(t) >= 4]
            c_text = str(company.get("company_name", "")).lower()
            if any(t in c_text for t in m_tokens):
                m_bonus = 15.0

    # 등록번호가 있는 품목은 실시장 품목 신뢰 가산
    reg_bonus = 8.0 if str(prof.get("registration_number", "")).strip() else 0.0
    return min(140.0, base + m_bonus + reg_bonus)


def _criterion_value(scores: dict[str, int], company: dict[str, Any], criterion_key: str) -> float:
    """UI 평가 기준 key를 내부 점수 키와 매핑."""
    if criterion_key in scores:
        return float(scores.get(criterion_key, 0))
    e = company.get("enriched", {})
    alias_map: dict[str, float] = {
        "pharmacy_chain": 100.0 if e.get("has_pharmacy_chain") else 0.0,
        "파이프라인": float(scores.get("유통실적", 0)),
        "매출규모": float(scores.get("기업규모", 0)),
        "제조소 보유": float(scores.get("GMP보유", 0)),
        "수입 경험": float(scores.get("한국거래", 0)),
        "약국체인 운영": 100.0 if e.get("has_pharmacy_chain") else 0.0,
    }
    return alias_map.get(criterion_key, 0.0)


def compute_scores(company: dict[str, Any]) -> dict[str, int]:
    """기업 1개 → 항목별 점수 dict (내부 정렬용)."""
    e = company.get("enriched", {})

    rev_s = _revenue_score(str(e.get("revenue", "-")))
    emp_s = _employee_score(str(e.get("employees", "-")))
    size_score = (rev_s + emp_s) // 2 if (rev_s or emp_s) else 0

    imp_s = _bool_score(e.get("import_history"))
    pro_s = _bool_score(e.get("procurement_history"))
    dist_score = (imp_s + pro_s) // 2

    partner_s = max(
        _bool_score(e.get("mah_capable")),
        _korea_score(e.get("korea_experience")),
    )

    return {
        "기업규모":     size_score,
        "유통실적":     dist_score,
        "GMP보유":      _bool_score(e.get("has_gmp")),
        "공공채널":     _bool_score(e.get("public_channel")),
        "민간채널":     _bool_score(e.get("private_channel")),
        "파트너적합성": partner_s,
        "한국거래":     _korea_score(e.get("korea_experience")),
        "MAH가능":      _bool_score(e.get("mah_capable")),
        "타깃국가진출": _bool_score(e.get("has_target_country_presence")),
    }


def rank_companies(
    all_candidates: list[dict[str, Any]],
    active_criteria: list[str] | None = None,
    top_n: int = 10,
    analysis_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    전체 후보 풀(all_candidates)에서 criteria 기준으로 상위 top_n 선택.
    composite_score는 내부 정렬용 — 반환 딕셔너리에서 제거.
    """
    scored: list[dict[str, Any]] = []
    ctx = analysis_context or {}
    target_market = str(ctx.get("target_market", "")).strip().lower()
    price_level = str(ctx.get("price_level", "")).strip().lower()
    market_fit_weight = 0
    if target_market == "public":
        market_fit_weight = 25
    elif target_market == "private":
        market_fit_weight = 18
    price_bonus = 0
    if price_level in ("aggressive", "low"):
        price_bonus = 8
    elif price_level in ("premium", "high"):
        price_bonus = 6
    for c in all_candidates:
        scores = compute_scores(c)
        ingredient_match = c.get("ingredient_match", False)
        completeness    = _enrichment_completeness(c)
        static_score = _static_signal_score(c, ctx)

        target_presence = scores.get("타깃국가진출", 0)
        market_fit = 0
        if target_market == "public":
            market_fit = scores.get("공공채널", 0)
        elif target_market == "private":
            market_fit = scores.get("민간채널", 0)

        context_bonus = 0
        if market_fit > 0 and market_fit_weight:
            context_bonus += market_fit_weight
        if target_presence > 0:
            context_bonus += 12
        if c.get("ingredient_match", False):
            context_bonus += price_bonus

        if active_criteria:
            # criteria 선택 시: 선택 항목 점수 합산
            criteria_avg = sum(_criterion_value(scores, c, k) for k in active_criteria) / len(active_criteria)
            # 대표님 요구: 3개 정적데이터 주점수 + 평가표 보조점수
            primary_score = static_score * 0.7 + criteria_avg * 0.3
            # tie-break: 시장조사/가격 컨텍스트 보너스 → 타깃국가 진출 → 성분 매칭 → 완성도
            sort_key = (primary_score, static_score, context_bonus, target_presence, 10 if ingredient_match else 0, completeness)
        else:
            # criteria 없음: 3개 정적데이터 주점수 우선 → 컨텍스트 보너스 → 타깃국가 진출 순
            sort_key = (static_score, context_bonus, target_presence, 100 if ingredient_match else 0, completeness, 0)

        scored.append({
            **c,
            "scores": scores,
            "_sort_key": sort_key,
        })

    scored.sort(key=lambda x: x["_sort_key"], reverse=True)

    result = []
    for item in scored[:top_n]:
        item.pop("_sort_key", None)
        # composite_score 제거 (외부 노출 금지)
        item.pop("composite_score", None)
        result.append(item)

    return result

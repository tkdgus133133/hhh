"""KUP 역산 공식 (수출 과업·P2 AI·수동 계산 공통).

KUP = (((DIPC ÷ 1.05) ÷ (1+약국마진) ÷ (1+도매마진)) × (1−페이백율)) ÷ (1+파트너마진) − 물류비

마진·페이백은 소수(decimal)로 전달합니다. 예: 약국 15% → 0.15
"""

from __future__ import annotations

from typing import Any


def pct_to_rate(v: Any) -> float:
    """퍼센트 숫자(15) 또는 소수(0.15) 입력을 소수 비율로 통일."""
    if v is None:
        return 0.0
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    if x == 0.0:
        return 0.0
    # '25' 또는 25 → 0.25 / 이미 '0.25' → 0.25
    return x / 100.0 if abs(x) > 1.0 else x


def compute_kup_usd(
    dipc: float,
    *,
    pharmacy_rate: float = 0.0,
    wholesale_rate: float = 0.0,
    payback_rate: float = 0.0,
    partner_rate: float = 0.0,
    logistics_usd: float = 0.0,
    tax_divisor: float = 1.05,
) -> float:
    """DIPC(현지 소비자측 참고가)에서 역산한 KUP(USD)."""
    try:
        d = float(dipc)
    except (TypeError, ValueError):
        return 0.0
    if d <= 0 or tax_divisor <= 0:
        return 0.0

    ph = float(pharmacy_rate)
    wh = float(wholesale_rate)
    pb = float(payback_rate)
    pt = float(partner_rate)
    log = float(logistics_usd)

    x = d / tax_divisor
    den_ph = 1.0 + ph
    den_wh = 1.0 + wh
    den_pt = 1.0 + pt
    if den_ph <= 0 or den_wh <= 0 or den_pt <= 0:
        return 0.0
    x = x / den_ph / den_wh
    x *= max(0.0, 1.0 - pb)
    x /= den_pt
    x -= max(0.0, log)
    return max(x, 0.0)


def format_kup_formula_ko(
    dipc: float,
    *,
    pharmacy_rate: float,
    wholesale_rate: float,
    payback_rate: float,
    partner_rate: float,
    logistics_usd: float | None = None,
    logistics_sgd: float | None = None,
    tax_divisor: float = 1.05,
    kup: float | None = None,
) -> str:
    """디버그·프롬프트용 한 줄 요약."""
    # USD 전환 이후에도 기존 호출(logistics_sgd)을 안전하게 허용
    logistics_val = (
        float(logistics_usd)
        if logistics_usd is not None
        else float(logistics_sgd or 0.0)
    )
    parts = [
        f"DIPC {dipc:.2f}",
        f"÷ {tax_divisor:.2f}",
        f"÷ (1+약국 {pharmacy_rate*100:.2f}%)",
        f"÷ (1+도매 {wholesale_rate*100:.2f}%)",
        f"× (1−페이백 {payback_rate*100:.2f}%)",
        f"÷ (1+파트너 {partner_rate*100:.2f}%)",
        f"− 물류 {logistics_val:.2f}",
    ]
    tail = f" = KUP {kup:.2f} USD" if kup is not None else ""
    return " ".join(parts) + tail


def compute_kup_sgd(
    dipc: float,
    *,
    pharmacy_rate: float = 0.0,
    wholesale_rate: float = 0.0,
    payback_rate: float = 0.0,
    partner_rate: float = 0.0,
    logistics_sgd: float = 0.0,
    tax_divisor: float = 1.05,
) -> float:
    """하위호환용 별칭. 내부 계산은 USD 기준 엔진과 동일."""
    return compute_kup_usd(
        dipc,
        pharmacy_rate=pharmacy_rate,
        wholesale_rate=wholesale_rate,
        payback_rate=payback_rate,
        partner_rate=partner_rate,
        logistics_usd=logistics_sgd,
        tax_divisor=tax_divisor,
    )

"""Perplexity API로 품목별 관련 논문·레퍼런스 검색.

PERPLEXITY_API_KEY 설정 시 자동 실행.
미설정 시 빈 리스트 반환 (UI에서 "API 키 미설정" 표시).

쿼리 방향:
  - 임상 중심 품목: 임상 근거 + 헝가리 시장/급여(NEAK) 데이터
  - 진입전략 중심 품목: OGYÉI/EMA 규제 진입 경로 + 복합제 승인 사례

출력 (품목별):
  [
    {"title": "...", "url": "https://...", "reason": "한 줄 근거", "source": "PubMed 등"},
    ...
  ]
"""

from __future__ import annotations

import os
from typing import Any

# 임상 중심 품목: 임상 근거 + 헝가리 현지 시장 쿼리
# 진입전략 품목: 규제 진입 경로 + 복합제 승인 사례 쿼리
_QUERIES: dict[str, str] = {
    "SG_hydrine_hydroxyurea_500": (
        "hydroxyurea Hungary OGYEI NEAK reimbursement hospital procurement "
        "sickle cell chronic myeloid leukemia guideline EU"
    ),
    "SG_gadvoa_gadobutrol_604": (
        "gadobutrol Hungary OGYEI EMA registration macrocyclic GBCA "
        "safety efficacy radiology hospital formulary EU"
    ),
    "SG_sereterol_activair": (
        "fluticasone salmeterol fixed dose combination Hungary OGYEI NEAK registration "
        "asthma COPD inhaler GINA GOLD guideline EU market"
    ),
    "SG_omethyl_omega3_2g": (
        "omega-3 ethyl esters 2g Hungary OGYEI EMA new drug application "
        "hypertriglyceridemia registration pathway REDUCE-IT cardiovascular"
    ),
    "SG_rosumeg_combigel": (
        "rosuvastatin omega-3 fixed dose combination Hungary OGYEI EMA approval pathway "
        "registration dyslipidemia combination product regulatory EU"
    ),
    "SG_atmeg_combigel": (
        "atorvastatin omega-3 fixed dose combination approval pathway Hungary "
        "OGYEI EMA registration dyslipidemia EU"
    ),
    "SG_ciloduo_cilosta_rosuva": (
        "cilostazol Hungary OGYEI EMA registration approval pathway "
        "peripheral artery disease rosuvastatin combination regulatory evidence EU"
    ),
    "SG_gastiin_cr_mosapride": (
        "mosapride Hungary OGYEI EMA regulatory approval market entry "
        "prokinetic gastric motility registration sustained release clinical EU"
    ),
}

# 각 품목의 쿼리 초점 유형 (프롬프트 커스터마이징용)
_QUERY_FOCUS: dict[str, str] = {
    "SG_hydrine_hydroxyurea_500": "clinical_evidence",
    "SG_gadvoa_gadobutrol_604": "clinical_evidence",
    "SG_sereterol_activair": "clinical_evidence",
    "SG_omethyl_omega3_2g": "regulatory_pathway",
    "SG_rosumeg_combigel": "regulatory_pathway",
    "SG_atmeg_combigel": "regulatory_pathway",
    "SG_ciloduo_cilosta_rosuva": "regulatory_pathway",
    "SG_gastiin_cr_mosapride": "regulatory_pathway",
}


async def fetch_references(
    product_id: str,
    max_refs: int = 4,
) -> list[dict[str, str]]:
    """논문·규제 사례 검색. Perplexity 미사용 — 빈 리스트 반환."""
    return []


async def fetch_references_for_custom(
    trade_name: str,
    inn: str,
    max_refs: int = 4,
) -> list[dict[str, str]]:
    """신약(커스텀 입력) 논문·규제 사례 검색. Perplexity 미사용 — 빈 리스트 반환."""
    return []


async def fetch_all_references(
    product_ids: list[str] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """8품목 전체 논문·규제 사례 검색. Perplexity 미사용 — 빈 dict 반환."""
    targets = product_ids or list(_QUERIES.keys())
    return {pid: [] for pid in targets}

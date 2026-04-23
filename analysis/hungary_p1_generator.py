"""헝가리 P1 시장조사 보고서 생성기.

데이터 소스:
  - datas/static/market_source.json (OGYEI/NEAK/EMA 카운트, 등록번호)
  - frontend/static/hungary-export-data.js (판정, neak_range 등 상세 데이터)

출력: reports/sg01.pdf
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# ── product_id → JS PRODUCT_DATA 키 매핑 ────────────────────────────────────
_PID_TO_JS_KEY: dict[str, str] = {
    "SG_omethyl_omega3_2g":       "Omega-3 (Omethyl)",
    "SG_gadvoa_gadobutrol_604":   "Gadobutrol (Gadvoa)",
    "SG_sereterol_activair":      "Fluticasone+Salmeterol (Sereterol)",
    "SG_hydrine_hydroxyurea_500": "Hydroxyurea (Hydrine)",
    "SG_rosumeg_combigel":        "Rosuvastatin (Rosumeg)",
    "SG_atmeg_combigel":          "Atorvastatin (Atmeg)",
    "SG_ciloduo_cilosta_rosuva":  "Cilostazol (Ciloduo)",
    "SG_gastiin_cr_mosapride":    "Mosapride (Gastiin)",
}

# 판정 변환
_VT_TO_KO: dict[str, str] = {
    "ok":   "적합",
    "warn": "조건부",
    "no":   "부적합",
}


def _load_js_product_data(js_path: Path) -> dict[str, dict]:
    """hungary-export-data.js 에서 PRODUCT_DATA 섹션을 파싱해 반환."""
    try:
        content = js_path.read_text(encoding="utf-8")
        idx = content.find("PRODUCT_DATA:")
        if idx < 0:
            return {}
        brace_start = content.index("{", idx)
        depth = 0
        for i in range(brace_start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(content[brace_start : i + 1])
    except Exception:
        pass
    return {}


def _load_market_source(json_path: Path) -> dict[str, dict]:
    """market_source.json 에서 product_id → row 딕셔너리 반환."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return {r["product_id"]: r for r in data.get("rows", [])}
    except Exception:
        return {}


def build_hungary_products() -> list[dict[str, Any]]:
    """헝가리 P1 분석 데이터를 조합해 품목 리스트 반환."""
    js_data   = _load_js_product_data(ROOT / "frontend" / "static" / "hungary-export-data.js")
    ms_by_pid = _load_market_source(ROOT / "datas" / "static" / "market_source.json")

    products: list[dict[str, Any]] = []
    for pid, js_key in _PID_TO_JS_KEY.items():
        ms   = ms_by_pid.get(pid, {})
        jd   = js_data.get(js_key, {})
        raw  = ms.get("raw_payload", {})

        trade_name  = ms.get("trade_name") or jd.get("drug_name", pid)
        inn         = ms.get("inn_name")   or jd.get("inn", "")
        reg_num     = ms.get("registration_number", "") or ""
        manufacturer = ms.get("manufacturer", "") or ""
        atc          = (ms.get("country_specific", {}) or {}).get("atc", "") or ""

        ogyei       = int(jd.get("ogyei", raw.get("registry_rows", 0)))
        neak_count  = int(jd.get("neak_count", raw.get("price_rows", 0)))
        neak_range  = str(jd.get("neak_range", "-") or "-")
        ema_count   = int(raw.get("ema_rows", 0))
        vt          = str(jd.get("verdict_type", "no") or "no")
        verdict     = _VT_TO_KO.get(vt, "부적합")

        # ── 섹션 텍스트 자동 생성 ─────────────────────────────────────────────
        market_text = (
            f"{inn} 성분의 {trade_name}은(는) 헝가리 의약품 시장에서 "
            f"OGYEI(국가의약청) 등록 데이터베이스에 {ogyei}건 매칭됩니다. "
            f"NEAK(국민건강보험공단) 급여 의약품으로 {neak_count}건이 확인되며, "
            + (f"EMA(유럽의약청) 등재 관련 의약품이 {ema_count}건 조회됩니다. " if ema_count else "EMA 등재 직접 매칭 미확인. ")
            + f"헝가리는 EU 회원국으로 EMA 중앙화 허가 의약품이 자동 효력을 가지며, "
            f"병원·약국·공공조달 채널 수요가 지속적으로 확인됩니다."
        )

        if reg_num:
            reg_text = (
                f"OGYEI 등록 번호 {reg_num} 기준 동일 성분 계열 품목이 헝가리 시장에 등재되어 있습니다. "
                f"제조사: {manufacturer.title()[:40] if manufacturer else '미확인'}. "
                f"동등성(abridged) 신청 또는 MRP(상호인정절차) 경로를 통해 진입 시 기존 허가 선례를 활용할 수 있습니다."
            )
        else:
            reg_text = (
                f"현재 확인된 데이터 범위에서 헝가리 OGYEI 등록 번호가 미확인입니다. "
                f"EMA 중앙화 허가(CAP) 취득 후 EU 회원국 자동 효력 적용 또는 "
                f"분산형 절차(DCP/MRP)를 통한 헝가리 직접 허가 신청을 검토해야 합니다."
            )

        trade_text = (
            f"HS 코드 3004.90 분류 해당 품목으로 EU 역내 수입 시 기본 관세율 0% 적용(부가세 27% 별도). "
            f"한국-EU FTA 협정에 따라 관세 혜택 및 원산지 증명(EUR.1) 절차가 적용됩니다. "
            f"헝가리 시장은 병원·약국·공공조달(OEP 텐더) 채널로 구성됩니다."
        )

        pathway_text = (
            f"헝가리 진출 경로: OGYEI를 통한 MRP(상호인정)/DCP(분산절차) 또는 신규 NDA 신청. "
            f"EU GMP 인증 제조 시설 필수. "
            f"현지 MAH(Marketing Authorization Holder) 지정 또는 직접 신청 가능. "
            + (f"기존 OGYEI 등록 선례({reg_num}) 참조 가능." if reg_num else "기존 EMA CAP 기반 상호인정 경로 우선 검토 권장.")
        )

        if neak_range and neak_range != "-":
            price_text = (
                f"NEAK 급여 참고 가격 범위: {neak_range} EUR/단위(국제 가격 비교 리스트 {neak_count}건 기준). "
                f"동 가격 범위 내에서 경쟁 포지셔닝 전략 수립 권장. "
                f"헝가리 NEAK 약가 등재 시 기준 가격의 70~85% 수준으로 초기 진입 권장."
            )
        else:
            price_text = (
                f"현재 확인된 범위에서 NEAK 급여 가격 데이터가 미확보 상태입니다. "
                f"EMA 유사 성분 의약품의 국제 가격 비교 자료를 기반으로 추가 시장조사가 필요합니다."
            )

        risk_text = (
            f"주요 리스크: EU GMP 인증 취득 필요({atc or '해당 ATC'} 분류). "
            f"NEAK 약가 협상 과정에서 추가 임상·경제성 자료 제출 요건 발생 가능. "
            f"매칭 건수는 성분 표기 차이에 따른 자동 집계 결과이므로 반드시 원본 데이터 추가 검증 필요."
        )

        links = [
            ("OGYEI — 헝가리 국가의약청 의약품 등록 데이터베이스", "https://www.ogyei.gov.hu/"),
            ("NEAK — 헝가리 국민건강보험공단 급여 의약품 목록", "https://www.neak.gov.hu/"),
            ("EMA — 유럽의약청 의약품 데이터베이스", "https://www.ema.europa.eu/en/medicines"),
            ("Patikaradar — 헝가리 약국 가격 비교 데이터", "https://www.patikaradar.hu/"),
        ]

        products.append({
            "product_id":   pid,
            "trade_name":   trade_name,
            "inn":          inn,
            "verdict":      verdict,
            "reg_num":      reg_num,
            "manufacturer": manufacturer,
            "atc":          atc,
            "ogyei":        ogyei,
            "neak_count":   neak_count,
            "neak_range":   neak_range,
            "ema_count":    ema_count,
            "market_text":  market_text,
            "reg_text":     reg_text,
            "trade_text":   trade_text,
            "pathway_text": pathway_text,
            "price_text":   price_text,
            "risk_text":    risk_text,
            "links":        links,
        })

    return products


def build_hu_static_prompt_for_analysis(product_id: str) -> str:
    """헝가리 정적 번들 기반 분석 프롬프트용 텍스트를 생성."""
    pid = str(product_id or "").strip()
    if not pid:
        return ""

    products = build_hungary_products()
    row = next((p for p in products if str(p.get("product_id", "")).strip() == pid), None)
    if not row:
        return ""

    trade_name = str(row.get("trade_name", "") or "")
    inn = str(row.get("inn", "") or "")
    reg_num = str(row.get("reg_num", "") or "")
    manufacturer = str(row.get("manufacturer", "") or "")
    atc = str(row.get("atc", "") or "")
    ogyei = int(row.get("ogyei", 0) or 0)
    neak_count = int(row.get("neak_count", 0) or 0)
    neak_range = str(row.get("neak_range", "-") or "-")
    ema_count = int(row.get("ema_count", 0) or 0)
    verdict = str(row.get("verdict", "") or "")

    links = row.get("links", []) or []
    source_lines = []
    for title, url in links:
        source_lines.append(f"- {title}: {url}")
    sources = "\n".join(source_lines) if source_lines else "- 출처 정보 없음"

    return (
        "### 헝가리 정적 데이터 요약\n"
        f"- product_id: {pid}\n"
        f"- 제품명: {trade_name}\n"
        f"- 성분(INN): {inn}\n"
        f"- OGYEI 매칭 건수: {ogyei}건\n"
        f"- NEAK 급여 매칭 건수: {neak_count}건\n"
        f"- NEAK 가격 범위: {neak_range}\n"
        f"- EMA 매칭 건수: {ema_count}건\n"
        f"- 판정: {verdict}\n"
        f"- 등록번호: {reg_num or '미확인'}\n"
        f"- 제조사: {manufacturer or '미확인'}\n"
        f"- ATC: {atc or '미확인'}\n\n"
        "### 시장/규제 본문\n"
        f"{str(row.get('market_text', '') or '').strip()}\n\n"
        f"{str(row.get('reg_text', '') or '').strip()}\n\n"
        f"{str(row.get('pathway_text', '') or '').strip()}\n\n"
        f"{str(row.get('trade_text', '') or '').strip()}\n\n"
        f"{str(row.get('price_text', '') or '').strip()}\n\n"
        f"{str(row.get('risk_text', '') or '').strip()}\n\n"
        "### 참고 출처\n"
        f"{sources}"
    )


def _norm_text(value: str) -> str:
    """문자열 비교용 정규화."""
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def product_id_from_hu_p1_filename_only(filename: str) -> str | None:
    """P1 PDF 파일명만으로 product_id를 추정."""
    base = Path(str(filename or "")).name.lower()
    if not base:
        return None

    # 1) product_id 전체 문자열이 파일명에 포함된 경우
    for pid in _PID_TO_JS_KEY.keys():
        if pid.lower() in base:
            return pid

    # 2) SG_ 접두어 제거 별칭이 파일명에 포함된 경우 (예: sereterol_activair)
    for pid in _PID_TO_JS_KEY.keys():
        alias = pid.replace("SG_", "", 1).lower()
        if alias and alias in base:
            return pid

    return None


def resolve_hu_product_id_for_p2(pdf_filename: str, extracted: dict[str, Any] | None = None) -> str | None:
    """P2 파이프라인용 product_id를 파일명/추출결과로 보정."""
    pid = product_id_from_hu_p1_filename_only(pdf_filename)
    if pid:
        return pid

    data = extracted or {}
    product_name = _norm_text(str(data.get("product_name", "") or ""))
    inn_name = _norm_text(str(data.get("inn_name", "") or ""))
    haystack = f"{product_name} {inn_name}".strip()
    if not haystack:
        return None

    for pid, js_key in _PID_TO_JS_KEY.items():
        pid_alias = _norm_text(pid.replace("SG_", "", 1))
        js_alias = _norm_text(js_key)
        if pid_alias and pid_alias in haystack:
            return pid
        if js_alias and js_alias in haystack:
            return pid

    for p in build_hungary_products():
        pid_cand = str(p.get("product_id", "") or "")
        trade = _norm_text(str(p.get("trade_name", "") or ""))
        inn = _norm_text(str(p.get("inn", "") or ""))
        if trade and trade in haystack:
            return pid_cand or None
        if inn and inn in haystack:
            return pid_cand or None

    return None


def render_hungary_p1_pdf(products: list[dict], out_path: Path) -> None:
    """헝가리 P1 시장조사 보고서 PDF 생성 — sg04 템플릿 스타일 (싱가포르 포맷 동일)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    W, H = A4
    MARGIN = 20 * mm
    CONTENT_W = W - 2 * MARGIN

    # ── 폰트 ─────────────────────────────────────────────────────────────────
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    _font_candidates = [
        ("NanumGothic", str(ROOT / "fonts" / "NanumGothic.ttf")),
        ("MalgunGothic", "C:/Windows/Fonts/malgun.ttf"),
        ("AppleGothic",  "/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    ]
    base_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    for name, path in _font_candidates:
        if Path(path).is_file():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                bold_path = str(ROOT / "fonts" / "NanumGothicBold.ttf")
                if name == "NanumGothic" and Path(bold_path).is_file():
                    pdfmetrics.registerFont(TTFont(f"{name}-Bold", bold_path))
                    bold_font = f"{name}-Bold"
                else:
                    bold_font = name
                base_font = name
                break
            except Exception:
                continue

    # ── 색상 (sg04 동일) ──────────────────────────────────────────────────────
    C_RED    = colors.HexColor("#C0392B")
    C_NAVY   = colors.HexColor("#1B2A4A")
    C_BODY   = colors.HexColor("#1A1A1A")
    C_BORDER = colors.HexColor("#D0D7E3")
    C_ALT    = colors.HexColor("#F4F6F9")
    C_GRAY   = colors.HexColor("#6B7280")
    C_HDR_FG = colors.HexColor("#9CA3AF")

    COL1 = CONTENT_W * 0.26
    COL2 = CONTENT_W * 0.74

    def ps(name: str, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, **kw)

    # ── running header/footer ─────────────────────────────────────────────────
    _HDR_TEXT = "한국유나이티드제약  |  헝가리 시장보고서"

    def _on_page(canvas, doc):
        canvas.saveState()
        pg = doc.page
        canvas.setFont(base_font, 8)
        canvas.setFillColor(C_HDR_FG)
        canvas.drawString(MARGIN, H - 13 * mm, _HDR_TEXT)
        canvas.drawRightString(W - MARGIN, H - 13 * mm, f"기밀 — 내부용  {pg}")
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, H - 15 * mm, W - MARGIN, H - 15 * mm)
        canvas.restoreState()

    s_title   = ps("HuTitle",  fontName=bold_font, fontSize=20, leading=26,
                   textColor=C_RED, spaceAfter=2)
    s_section = ps("HuSec",    fontName=bold_font, fontSize=11, textColor=C_NAVY,
                   leading=15, spaceBefore=10, spaceAfter=2)
    s_cell_h  = ps("HuCellH",  fontName=bold_font, fontSize=9, textColor=C_NAVY,
                   leading=13, wordWrap="CJK")
    s_cell    = ps("HuCell",   fontName=base_font, fontSize=9, textColor=C_BODY,
                   leading=14, wordWrap="CJK")
    s_bar     = ps("HuBar",    fontName=bold_font, fontSize=9, textColor=colors.white,
                   leading=13, wordWrap="CJK")
    s_hdr     = ps("HuHdrW",   fontName=bold_font, fontSize=9, textColor=colors.white,
                   leading=13, wordWrap="CJK")
    s_sub_hdr = ps("HuSubHdr", fontName=bold_font, fontSize=9, textColor=colors.white,
                   leading=13, wordWrap="CJK")
    s_body    = ps("HuBody",   fontName=base_font, fontSize=9, textColor=C_BODY,
                   leading=14, wordWrap="CJK", spaceAfter=2)

    def _rx(t: str) -> str:
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _base_style(extra: list | None = None) -> list:
        cmds = [
            ("GRID",          (0, 0), (-1, -1), 0.5, C_BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]
        if extra:
            cmds.extend(extra)
        return cmds

    def _simple_table(rows: list[tuple[str, str]], shade_alt: bool = True) -> Table:
        pdata = [
            [Paragraph(_rx(r[0]), s_cell_h), Paragraph(_rx(r[1]), s_cell)]
            for r in rows
        ]
        t = Table(pdata, colWidths=[COL1, COL2])
        extras: list = []
        if shade_alt:
            for i in range(len(rows)):
                if i % 2 == 1:
                    extras.append(("BACKGROUND", (0, i), (-1, i), C_ALT))
        t.setStyle(TableStyle(_base_style(extras)))
        return t

    def _sub_bar(label: str) -> Table:
        t = Table([[Paragraph(_rx(label), s_sub_hdr)]], colWidths=[CONTENT_W])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # ── 헝가리 HS 코드 ────────────────────────────────────────────────────────
    _HU_HS: dict[str, str] = {
        "SG_omethyl_omega3_2g":       "3004.90",
        "SG_sereterol_activair":      "3004.90",
        "SG_hydrine_hydroxyurea_500": "3004.90",
        "SG_gadvoa_gadobutrol_604":   "3006.30",
        "SG_rosumeg_combigel":        "3004.90",
        "SG_atmeg_combigel":          "3004.90",
        "SG_ciloduo_cilosta_rosuva":  "3004.90",
        "SG_gastiin_cr_mosapride":    "3004.90",
    }

    # ── 헝가리 거시 통계 (정적) ───────────────────────────────────────────────
    _HU_MACRO: list[tuple[str, str]] = [
        ("인구",            "약 960만 명 (2024)"),
        ("1인당 GDP",       "USD 22,000 (IMF 2024)"),
        ("의료비 지출",      "GDP의 약 6.5% (WHO 2023)"),
        ("의약품 시장 규모", "EUR 2.2B (IQVIA 2024)"),
        ("NEAK 등재 의약품", "약 3,400 품목"),
        ("주요 조달 채널",   "병원 입찰 · 약국 · NEAK 공공조달(OEP)"),
    ]

    # ── DB/기관 설명 ──────────────────────────────────────────────────────────
    _DB_SOURCES = [
        ("OGYEI", "헝가리 국가의약청 — 의약품 등록 DB, 등록번호·승인일·성분명 조회"),
        ("NEAK",  "헝가리 국민건강보험공단 — 급여 의약품 목록·가격 범위 조회"),
        ("EMA",   "유럽의약청 — 중앙화 허가(CAP) 의약품 목록 및 EU 자동 효력 확인"),
        ("Patikaradar", "헝가리 약국 가격 비교 플랫폼 — 소매 가격 참고"),
    ]

    generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title="헝가리 시장조사 보고서 (P1)",
    )

    story: list = []

    for idx, p in enumerate(products):
        trade    = str(p.get("trade_name", "") or "—")
        inn      = str(p.get("inn",        "") or "—")
        pid      = str(p.get("product_id", ""))
        hs_code  = _HU_HS.get(pid, "3004.90")
        verdict  = str(p.get("verdict",    "") or "—")
        ogyei    = p.get("ogyei",      0)
        neak_cnt = p.get("neak_count", 0)
        ema_cnt  = p.get("ema_count",  0)
        neak_rng = str(p.get("neak_range", "-") or "-")
        atc      = str(p.get("atc", "") or "")

        # ── 제목 + 정보 바 ─────────────────────────────────────────────────────
        story.append(Paragraph(_rx(f"헝가리 시장보고서 — {trade}"), s_title))
        story.append(Spacer(1, 4))
        bar_txt = f"{inn}  |  HS CODE: {hs_code}  |  Hungary  |  {generated_date}"
        bar_tbl = Table([[Paragraph(_rx(bar_txt), s_bar)]], colWidths=[CONTENT_W])
        bar_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#4B5563")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(bar_tbl)
        story.append(Spacer(1, 10))

        # ── 1. 의료 거시환경 파악 ─────────────────────────────────────────────
        story.append(Paragraph(_rx("1. 의료 거시환경 파악"), s_section))
        macro_rows: list[tuple[str, str]] = list(_HU_MACRO)
        if atc:
            macro_rows.insert(0, ("ATC 코드", atc))
        macro_rows += [
            ("OGYEI 데이터베이스 매칭", f"{ogyei}건"),
            ("NEAK 급여 의약품 매칭",   f"{neak_cnt}건"),
            ("EMA 등재 의약품 매칭",    f"{ema_cnt}건"),
        ]
        story.append(_simple_table(macro_rows))
        story.append(Spacer(1, 4))
        story.append(Paragraph(_rx(p["market_text"]), s_body))
        story.append(Spacer(1, 6))

        # ── 2. 무역/규제 환경 ─────────────────────────────────────────────────
        story.append(Paragraph(_rx("2. 무역/규제 환경"), s_section))
        for sub_lbl, field in [
            ("▸ OGYEI 등록 현황", "reg_text"),
            ("▸ 진입 채널 권고",  "pathway_text"),
            ("▸ 관세 및 무역",    "trade_text"),
        ]:
            val = str(p.get(field, "") or "").strip()
            if val:
                story.append(_sub_bar(sub_lbl))
                story.append(Paragraph(_rx(val), s_body))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 2))

        # ── 3. 참고 가격 ──────────────────────────────────────────────────────
        story.append(Paragraph(_rx("3. 참고 가격"), s_section))
        neak_label = (
            f"NEAK 급여 가격 범위: {neak_rng} EUR/단위  ({neak_cnt}건 기준, 방법론적 추산)"
            if neak_rng != "-"
            else "NEAK 급여 가격 데이터 미확보 — 추가 시장조사 필요"
        )
        price_tbl = Table(
            [[Paragraph(_rx("참고 가격 (NEAK 기준)"), s_cell_h),
              Paragraph(_rx(neak_label), s_cell)]],
            colWidths=[COL1, COL2],
        )
        price_tbl.setStyle(TableStyle(_base_style()))
        story.append(price_tbl)
        price_body = str(p.get("price_text", "") or "").strip()
        if price_body:
            story.append(Spacer(1, 4))
            story.append(Paragraph(_rx(price_body), s_body))
        story.append(Spacer(1, 6))

        # ── 4. 리스크 / 조건 ──────────────────────────────────────────────────
        story.append(Paragraph(_rx("4. 리스크 / 조건"), s_section))
        story.append(Paragraph(_rx(str(p.get("risk_text", "") or "—")), s_body))

        story.append(PageBreak())

        # ── 5. 근거 및 출처 ────────────────────────────────────────────────────
        story.append(Paragraph(_rx("5. 근거 및 출처"), s_section))

        # ▸ 5-1. 참고 링크
        story.append(_sub_bar("▸ 5-1. 참고 링크"))
        links = p.get("links", []) or []
        if links:
            w_no    = CONTENT_W * 0.05
            w_title = CONTENT_W * 0.52
            w_url   = CONTENT_W * 0.43
            link_rows: list[list] = [[
                Paragraph("No.", s_hdr),
                Paragraph("기관 / 출처", s_hdr),
                Paragraph("URL", s_hdr),
            ]]
            extras_l: list[tuple] = [("BACKGROUND", (0, 0), (-1, 0), C_NAVY)]
            for i, (title_l, url_l) in enumerate(links, 1):
                link_rows.append([
                    Paragraph(str(i), s_cell),
                    Paragraph(_rx(title_l), s_cell),
                    Paragraph(_rx(url_l[:65] + ("…" if len(url_l) > 65 else "")), s_cell),
                ])
                if i % 2 == 0:
                    extras_l.append(("BACKGROUND", (0, i), (-1, i), C_ALT))
            lt = Table(link_rows, colWidths=[w_no, w_title, w_url])
            lt.setStyle(TableStyle(_base_style(extras_l)))
            story.append(lt)
        else:
            story.append(Paragraph(_rx("• 참고 링크 없음"), s_body))

        story.append(Spacer(1, 8))

        # ▸ 5-2. 사용된 DB/기관
        story.append(_sub_bar("▸ 5-2. 사용된 DB/기관"))
        for db_name, db_desc in _DB_SOURCES:
            story.append(Paragraph(_rx(f"•  {db_name} — {db_desc}"), s_body))

        if idx < len(products) - 1:
            story.append(PageBreak())

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)


def generate_sg01(out_dir: Path | None = None) -> Path:
    """헝가리 P1 보고서를 reports/sg01.pdf 로 저장 후 경로 반환."""
    out_dir = out_dir or (ROOT / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sg01.pdf"

    products = build_hungary_products()
    if not products:
        raise RuntimeError("헝가리 데이터 로드 실패 — market_source.json / hungary-export-data.js 확인 필요")

    render_hungary_p1_pdf(products, out_path)
    print(f"[hungary-p1] PDF → {out_path}  ({len(products)}품목)")
    return out_path


if __name__ == "__main__":
    generate_sg01()

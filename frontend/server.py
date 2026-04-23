"""?? ??????????: SSE ??????? + ??/????API."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os as _os

# PDF/JSON ?? (Vercel ? ????: ???? REPORTS_DIR=/tmp/upharma_reports ??)
_rde = (_os.environ.get("REPORTS_DIR") or _os.environ.get("UPHARMA_REPORTS_DIR") or "").strip()
REPORTS_DIR: Path = Path(_rde).expanduser().resolve() if _rde else (ROOT / "reports")
REPORTS_BUCKET = (_os.environ.get("REPORTS_BUCKET") or "reports").strip() or "reports"

from frontend.dashboard_sites import DASHBOARD_SITES

STATIC = Path(__file__).resolve().parent / "static"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

_state: dict[str, Any] = {
    "events": [],
    "lock": None,
}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _state["lock"] = asyncio.Lock()
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    yield


app = FastAPI(title="HU Export Analysis Dashboard", version="2.0.0", lifespan=_lifespan)

_cors_origins = _os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _disable_api_cache(request: Request, call_next):
    """Vercel/CDN 캐시로 인한 상태 불일치를 방지한다."""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


async def _emit(event: dict[str, Any]) -> None:
    payload = {**event, "ts": time.time()}
    lock = _state["lock"]
    if lock is None:
        return
    async with lock:
        _state["events"].append(payload)
        if len(_state["events"]) > 500:
            _state["events"] = _state["events"][-400:]


_COMBINED_COVER_TEMPLATE = ROOT / "reports" / "hu_cover_template.pdf"
_IS_VERCEL = bool(_os.environ.get("VERCEL", "").strip())


def _strip_double_question_marks(text: str) -> str:
    """깨진 자리표시자(??)만 제거하고 일반 텍스트는 유지."""
    import re
    s = str(text or "")
    s = re.sub(r"\?{2,}", "", s)
    s = re.sub(r" {2,}", " ", s)
    return s.strip()


def _strip_encoding_artifacts(text: str) -> str:
    """깨진 대체문자(U+FFFD)를 제거."""
    s = str(text or "")
    return s.replace("\ufffd", "")


def _sanitize_p2_payload(value: Any) -> Any:
    """P2 PDF 직전 payload에서 ?? 토큰만 재귀적으로 정리."""
    if isinstance(value, str):
        return _strip_encoding_artifacts(_strip_double_question_marks(value))
    if isinstance(value, list):
        return [_sanitize_p2_payload(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_p2_payload(v) for k, v in value.items()}
    return value


def _sanitize_p1_payload(value: Any) -> Any:
    """P1 PDF 직전 payload에서 깨진 인코딩 문자만 재귀적으로 정리."""
    if isinstance(value, str):
        return _strip_encoding_artifacts(value)
    if isinstance(value, list):
        return [_sanitize_p1_payload(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_p1_payload(v) for k, v in value.items()}
    return value


def _upload_report_to_storage(local_path: Path) -> None:
    """로컬 보고서 파일을 Supabase Storage에 업로드 (Vercel 영속성 보완)."""
    if not local_path.is_file():
        return
    try:
        from utils.db import get_client
        sb = get_client()
        with open(local_path, "rb") as fin:
            sb.storage.from_(REPORTS_BUCKET).upload(
                path=local_path.name,
                file=fin,
                file_options={"upsert": "true", "content-type": "application/pdf"},
            )
    except Exception:
        # 업로드 실패는 로컬 응답 자체를 막지 않는다.
        pass


def _download_report_from_storage(name: str) -> bytes | None:
    """Supabase Storage에서 보고서 파일 바이트를 조회."""
    safe = Path(str(name or "")).name
    if not safe:
        return None
    try:
        from utils.db import get_client
        sb = get_client()
        blob = sb.storage.from_(REPORTS_BUCKET).download(safe)
        if isinstance(blob, (bytes, bytearray)) and blob:
            return bytes(blob)
    except Exception:
        return None
    return None


def _materialize_report_from_storage(name: str) -> Path | None:
    """Storage의 PDF를 로컬 REPORTS_DIR에 복원."""
    safe = Path(str(name or "")).name
    if not safe:
        return None
    blob = _download_report_from_storage(safe)
    if not blob:
        return None
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    local_path = REPORTS_DIR / safe
    local_path.write_bytes(blob)
    return local_path if local_path.is_file() else None


# ?????API ??????????? ?????????????????????????????????????????????????????????????????????????????????????????????????????????????????

class ApiKeysBody(BaseModel):
    perplexity_api_key: str = ""
    anthropic_api_key:  str = ""


@app.post("/api/settings/keys")
async def set_api_keys(body: ApiKeysBody) -> JSONResponse:
    """???????????API ???? ??????? ??? (?????? ????????)."""
    import os
    updated: list[str] = []
    if body.perplexity_api_key.strip():
        os.environ["PERPLEXITY_API_KEY"] = body.perplexity_api_key.strip()
        updated.append("PERPLEXITY_API_KEY")
    if body.anthropic_api_key.strip():
        os.environ["ANTHROPIC_API_KEY"] = body.anthropic_api_key.strip()
        updated.append("ANTHROPIC_API_KEY")
    return JSONResponse({"ok": True, "updated": updated})


@app.get("/api/settings/keys/status")
async def get_keys_status() -> JSONResponse:
    """??? API ????? ???? ??? (??? ??????? ???)."""
    import os
    return JSONResponse({
        "perplexity": bool(os.environ.get("PERPLEXITY_API_KEY", "").strip()),
        "anthropic":  bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()),
    })


# ??????? ?????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

_analysis_cache: dict[str, Any] = {"result": None, "running": False}


class AnalyzeBody(BaseModel):
    use_perplexity: bool = True
    force_refresh: bool = False


@app.post("/api/analyze")
async def trigger_analyze(body: AnalyzeBody | None = None) -> JSONResponse:
    """8??? ??? ??????? ??? (Claude API + Perplexity ??)."""
    req = body if body is not None else AnalyzeBody()
    if _analysis_cache["running"]:
        raise HTTPException(status_code=409, detail="???????? ??? ?????.")
    if _analysis_cache["result"] and not req.force_refresh:
        return JSONResponse({"ok": True, "message": "?????? ?? ???. force_refresh=true???????"})

    async def _run() -> None:
        _analysis_cache["running"] = True
        try:
            from analysis.sg_export_analyzer import analyze_all
            from analysis.perplexity_references import fetch_all_references

            results = await analyze_all(use_perplexity=req.use_perplexity)
            pids = [r["product_id"] for r in results]
            refs = await fetch_all_references(pids)
            for r in results:
                r["references"] = refs.get(r["product_id"], [])
            _analysis_cache["result"] = results
        finally:
            _analysis_cache["running"] = False

    asyncio.create_task(_run())
    return JSONResponse({"ok": True, "message": "???????????????????????."})


@app.get("/api/analyze/result")
async def analyze_result() -> JSONResponse:
    if _analysis_cache["running"]:
        return JSONResponse({"status": "running"}, status_code=202)
    if not _analysis_cache["result"]:
        raise HTTPException(status_code=404, detail="?? ?? ???. POST /api/analyze ??? ???")
    return JSONResponse({
        "status": "done",
        "count": len(_analysis_cache["result"]),
        "results": _analysis_cache["result"],
    })


@app.get("/api/analyze/status")
async def analyze_status() -> dict[str, Any]:
    return {
        "running": _analysis_cache["running"],
        "has_result": _analysis_cache["result"] is not None,
        "product_count": len(_analysis_cache["result"]) if _analysis_cache["result"] else 0,
    }


# ???????? ??? ? ??? (Naver 1??? ??Perplexity ???) ???????????????????????????????????????????????????

_news_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_NEWS_TTL = 600  # 10????


async def _scrape_naver_news(count: int = 7) -> list[dict[str, str]]:
    """Naver ??????? ???'??????????? ????????"""
    import re as _re

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(
            "https://m.search.naver.com/search.naver",
            params={"where": "m_news", "query": "??? ???", "sort": "1"},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Referer": "https://m.naver.com/",
            },
        )
    resp.raise_for_status()
    html = resp.text
    items: list[dict[str, str]] = []

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        seen: set[str] = set()

        for a in soup.find_all("a", href=_re.compile(r"n\.news\.naver\.com")):
            if len(items) >= count:
                break
            href = str(a.get("href", ""))
            if href in seen:
                continue
            seen.add(href)

            # ???: title ??? > ?????> ??? heading
            title = (a.get("title") or a.get_text(" ", strip=True)).strip()
            if not title or len(title) < 8:
                for parent in a.parents:
                    h = parent.find(["strong", "h2", "h3", "h4"])
                    if h:
                        t = h.get_text(strip=True)
                        if len(t) >= 8:
                            title = t
                            break
                    if parent.name in ("body", "html"):
                        break
            if not title or len(title) < 8:
                continue

            # ?????? ???: 5??? ??? ???????? ???
            container = a
            for _ in range(5):
                container = container.parent
                if not container:
                    break
            press = date = ""
            if container:
                pe = container.select_one(".press, .source, .media_nm, .info.press")
                de = container.select_one(".time, .date, .info_time")
                press = pe.get_text(strip=True) if pe else ""
                date  = de.get_text(strip=True) if de else ""

            items.append({"title": title, "link": href, "source": press, "date": date})

        if items:
            return items
    except ImportError:
        pass

    # regex ???
    for m in _re.finditer(
        r'href="(https://n\.news\.naver\.com/[^"]+)"[^>]*title="([^"]{8,})"', html
    ):
        if len(items) >= count:
            break
        items.append({"title": m.group(2).strip(), "link": m.group(1), "source": "", "date": ""})

    return items


def _parse_perplexity_news_items(raw_text: str) -> list[dict[str, str]]:
    """Perplexity ??????????? ??? ??(JSON) ???."""
    import re

    text = (raw_text or "").strip()
    if not text:
        return []

    candidates: list[str] = [text]
    m = re.search(r"\[\s*\{.*\}\s*\]", text, flags=re.S)
    if m:
        candidates.append(m.group(0))

    for cand in candidates:
        try:
            parsed = json.loads(cand)
        except Exception:
            continue
        if not isinstance(parsed, list):
            continue
        items: list[dict[str, str]] = []
        for row in parsed[:7]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title", "") or "").strip()
            if not title:
                continue
            items.append({
                "title":  title,
                "source": str(row.get("source", "") or "").strip(),
                "date":   str(row.get("date",   "") or "").strip(),
                "link":   str(row.get("link",   "") or "").strip(),
            })
        if items:
            return items
    return []


@app.get("/api/news")
async def api_news() -> JSONResponse:
    """?????????????? ??Naver ???????????, Perplexity ??? (10????)."""
    import time as _time
    import os

    if _news_cache["data"] and _time.time() - _news_cache["ts"] < _NEWS_TTL:
        return JSONResponse(_news_cache["data"])

    # 1) Naver ?? ??
    try:
        items = await _scrape_naver_news(7)
        if items:
            data = {"ok": True, "source": "naver", "items": items}
            _news_cache["data"] = data
            _news_cache["ts"]   = _time.time()
            return JSONResponse(data)
    except Exception:
        pass  # Naver ??? ??Perplexity ???

    # ??Perplexity ???
    px_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if not px_key:
        return JSONResponse({
            "ok": False,
            "error": "?? ?? ??: Naver ?? ?? PERPLEXITY_API_KEY ???",
            "items": [],
        })

    try:
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Hungary pharmaceutical market analyst. "
                        "Return ONLY a JSON array with up to 7 recent news items. "
                        "All 'title' values MUST be written in Korean (?????."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Find the latest Hungary pharmaceutical market and regulatory news. "
                        "Return a strict JSON array. Each item: title (Korean), source, date, link."
                    ),
                },
            ],
            "max_tokens": 900,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {px_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            raw = resp.json()

        content = str(
            raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        items = _parse_perplexity_news_items(content)
        if not items:
            return JSONResponse({"ok": False, "error": "Perplexity ??? ??? ???", "items": []})

        data = {"ok": True, "source": "perplexity", "items": items}
        _news_cache["data"] = data
        _news_cache["ts"]   = _time.time()
        return JSONResponse(data)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:120], "items": []})


# ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

@app.get("/api/macro")
async def api_macro() -> JSONResponse:
    stats = await preview_stats()
    data = json.loads(stats.body.decode("utf-8"))
    return JSONResponse(
        {
            "gdp_per_capita": data.get("gdp", {}).get("value", ""),
            "gdp_source": data.get("gdp", {}).get("source", "World Bank"),
            "population": data.get("population", {}).get("value", ""),
            "pop_source": data.get("population", {}).get("source", "World Bank"),
            "pharma_market": data.get("pharma_market", {}).get("value", ""),
            "pharma_source": data.get("pharma_market", {}).get("source", "World Bank"),
            "real_growth": data.get("import_dep", {}).get("value", ""),
            "growth_source": data.get("import_dep", {}).get("source", "World Bank"),
        }
    )


# ????????????? ??? (GDP ? ??? ? ???????? ? ??? ????? ???????????????????????????????????

_PREVIEW_STATS_STATIC = {
    "gdp":           {"value": "US$ 212.0B",   "source": "World Bank"},
    "population":    {"value": "9,600,000",    "source": "World Bank"},
    "pharma_market": {"value": "$14.0B",       "source": "World Bank"},
    "import_dep":    {"value": "57.0%",        "source": "World Bank"},
}


@app.get("/api/preview/stats")
async def preview_stats() -> JSONResponse:
    """????????? ??? 4????World Bank API ???, ??? ????? ???."""
    result: dict[str, Any] = {k: dict(v) for k, v in _PREVIEW_STATS_STATIC.items()}

    async def _wb_latest(indicator: str) -> float | None:
        url = f"https://api.worldbank.org/v2/country/HUN/indicator/{indicator}"
        params = {"format": "json", "per_page": 80}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            return None
        for row in payload[1]:
            val = row.get("value")
            if isinstance(val, (int, float)):
                return float(val)
        return None

    try:
        gdp = await _wb_latest("NY.GDP.MKTP.CD")
        pop = await _wb_latest("SP.POP.TOTL")
        chex = await _wb_latest("SH.XPD.CHEX.CD")
        imports = await _wb_latest("NE.IMP.GNFS.ZS")

        if gdp:
            result["gdp"] = {"value": f"US$ {gdp/1_000_000_000:.1f}B", "source": "World Bank"}
        if pop:
            result["population"] = {"value": f"{int(pop):,}", "source": "World Bank"}
        if chex:
            # ???????????????? ???????? ?????(????? ????? ???
            result["pharma_market"] = {"value": f"US$ {chex/1_000_000_000:.1f}B", "source": "World Bank (Health Expenditure)"}
        if imports:
            result["import_dep"] = {"value": f"{imports:.1f}%", "source": "World Bank (Imports % of GDP)"}
        return JSONResponse(result)
    except Exception:
        return JSONResponse(result)


# ???????? (yfinance USD/HUF + KRW) ???????????????????????????????????????????????????????????????????????????????????????????

_exchange_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_EXCHANGE_TTL_SEC = 0.0


@app.get("/api/exchange")
async def api_exchange() -> JSONResponse:
    """????????? ???(1 USD ??? HUF/KRW + USD ?????) ???."""
    import time as _time

    if _exchange_cache["data"] and _time.time() - _exchange_cache["ts"] < _EXCHANGE_TTL_SEC:
        return JSONResponse(_exchange_cache["data"])

    def _fetch() -> dict[str, Any]:
        import yfinance as yf  # type: ignore[import]
        usd_huf = float(yf.Ticker("USDHUF=X").fast_info.last_price)
        usd_krw = float(yf.Ticker("USDKRW=X").fast_info.last_price)
        usd_eur = float(yf.Ticker("USDEUR=X").fast_info.last_price)
        usd_jpy = float(yf.Ticker("USDJPY=X").fast_info.last_price)
        usd_cny = float(yf.Ticker("USDCNY=X").fast_info.last_price)
        return {
            "usd_huf": round(usd_huf, 2),
            "usd_krw": round(usd_krw, 2),
            "usd_eur": round(usd_eur, 4),
            "usd_jpy": round(usd_jpy, 2),
            "usd_cny": round(usd_cny, 4),
            "source": "Yahoo Finance",
            "fetched_at": _time.time(),
            "ok": True,
        }

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch)
        _exchange_cache["data"] = data
        _exchange_cache["ts"]   = _time.time()
        return JSONResponse(data)
    except Exception as exc:
        fallback: dict[str, Any] = {
            "usd_huf": 360.0,
            "usd_krw": 1393.0,
            "usd_eur": 0.92,
            "usd_jpy": 150.0,
            "usd_cny": 7.2,
            "source": "fallback (Yahoo Finance ??? ???)",
            "fetched_at": _time.time(),
            "ok": False,
            "error": str(exc),
        }
        return JSONResponse(fallback)


# ???????? ??? ????????(?? + ??? + PDF) ?????????????????????????????????????????????????????????????????????

_pipeline_tasks: dict[str, dict[str, Any]] = {}


def _apply_hu_p1_meta(report_obj: dict[str, Any], generated_at: str) -> None:
    """P1: meta.country=HU, ReportLab ??? ????? ??(?? sg04 ????)? ?? ??."""
    _ok = "\uc801\ud569"
    _cond = "\uc870\uac74\ubd80"
    _ng = "\ubd80\uc801\ud569"
    _na = "\ubbf8\ubd84\uc11d"
    meta = report_obj.setdefault("meta", {})
    meta["country"] = "HU"
    meta["currency"] = "HUF"
    if generated_at:
        meta["generated_at"] = generated_at
    items = report_obj.get("products") or []
    if items:
        meta["total_products"] = len(items)
    meta["verdict_summary"] = {
        _ok: sum(1 for it in items if it.get("verdict") == _ok),
        _cond: sum(1 for it in items if it.get("verdict") == _cond),
        _ng: sum(1 for it in items if it.get("verdict") == _ng),
        _na: sum(1 for it in items if it.get("verdict") is None),
    }
    meta["data_sources"] = [
        "OGY\u00c9I / NEAK (\ubc0f \uacf5\uac1c DB)",
        "EMA EU \uc758\uc57d\ud488 \uc815\ubcf4",
        "WHO EML",
        "GLOBOCAN",
        "PBS Australia (\uad6d\uc81c DPMQ \ubca4\uce58\ub9c8, \ubc29\ubc95\ub860\uc801 \ucd94\uc0b0)",
    ]
    meta["reference_pricing"] = {
        "primary_label": "(PBS DPMQ, \uad6d\uc81c \ubca4\uce58\ub9c8 \u2014 \ud5dd\uac00\ub9ac TTB/NEAK \uc9c1\uc811\uac00 \uc544\ub2d8)",
        "aud_field": "pbs_dpmq_aud (DPMQ)",
        "eur_note": "pbs_dpmq_eur_hint\ub294 AUD\u2192EUR \ucc38\uace0 \ud658\uc0b0; HUF/NEAK \uc2e4\uccb4\uac00\uc640 \ub2e4\ub97c \uc218 \uc788\uc74c",
    }
    meta["note"] = (
        "\ud5dd\uac00\ub9ac NEAK\xb7OGY\u00c9I \uacf5\uac1c \uc57d\uac00\ub294 \uc218\uc2dc \uac31\uc2e0\ub429\ub2c8\ub2e4. "
        "\ubcf8 \ud30c\uc774\ud504\ub77c\uc778\uc5d0\uc11c\ub294 PBS \uacf5\uac1c DPMQ\ub97c \uad6d\uc81c \ubca4\uce58\ub9c8\ub85c"
        " \uc81c\uc2dc\ud558\uba70, \uc2b9\uc778\xb7\uae09\uc5ec \ud655\uc815\uac00\ub294 OGY\u00c9I/NEAK \ucd5c\uc2e0"
        " \uc790\ub8cc\ub85c \uad50\ucc28\ud655\uc778\ud574\uc57c \ud569\ub2c8\ub2e4."
    )


async def _run_pipeline_for_product(product_key: str) -> None:
    task = _pipeline_tasks[product_key]
    try:
        # 0) DB ??
        task.update({"step": "db_load", "step_label": "Supabase ??? ?? ?..."})
        await _emit({"phase": "pipeline", "message": f"{product_key} DB ?? ??", "level": "info"})

        from utils.db import fetch_kup_products
        kup_rows = await asyncio.to_thread(fetch_kup_products, "HU")
        db_row = next((r for r in kup_rows if r.get("product_id") == product_key), None)
        if db_row is None:
            await _emit({"phase": "pipeline", "message": f"DB ?? ??: {product_key}", "level": "warn"})

        # 1) ??
        task.update({"step": "analyze", "step_label": "Claude ?? ?..."})
        await _emit({"phase": "pipeline", "message": f"{product_key} ?? ??", "level": "info"})
        from analysis.sg_export_analyzer import analyze_product
        result = await analyze_product(product_key, db_row)
        task["result"] = result
        verdict = result.get("verdict") or "??"
        await _emit({"phase": "pipeline", "message": f"?? ??: {verdict}", "level": "success"})

        # 2) ?? ??
        task.update({"step": "refs", "step_label": "?? ?? ?? ?..."})
        from analysis.perplexity_references import fetch_references
        refs = await fetch_references(product_key)
        task["refs"] = refs
        await _emit({"phase": "pipeline", "message": f"?? ?? {len(refs)}?", "level": "success"})

        # 3) P1 PDF ??
        task.update({"step": "report", "step_label": "P1 PDF ?? ?..."})
        await _emit({"phase": "pipeline", "message": "P1 PDF ?? ??", "level": "info"})

        from datetime import datetime, timezone as _tz
        from report_generator import build_report, render_pdf

        ts = datetime.now(_tz.utc).strftime("%Y%m%d_%H%M%S")
        gen_at = datetime.now(_tz.utc).isoformat()
        reports_dir = REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)

        refs_map = {product_key: refs}
        report_obj = await asyncio.to_thread(
            lambda: build_report(
                kup_rows,
                gen_at,
                [result],
                references=refs_map,
            )
        )
        report_obj = _sanitize_p1_payload(report_obj)
        _apply_hu_p1_meta(report_obj, gen_at)
        pdf_name = f"hu_report_{product_key}_{ts}.pdf"
        pdf_path = reports_dir / pdf_name
        json_path = reports_dir / f"hu_report_{product_key}_{ts}.json"
        await asyncio.to_thread(
            lambda: json_path.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        )
        await asyncio.to_thread(render_pdf, report_obj, pdf_path)

        task["pdf"] = pdf_name
        task.update({"status": "done", "step": "done", "step_label": "??"})
        await _emit({"phase": "pipeline", "message": "????? ??", "level": "success"})
    except Exception as exc:
        task.update({"status": "error", "step": "error", "step_label": str(exc)})
        await _emit({"phase": "pipeline", "message": f"??: {exc}", "level": "error"})


# ????????(????? ?????????????????????????????????????????????????????????????????????????????????????????????????????????????????
# ??: ??????("/api/pipeline/custom/...")??????{product_key} ??????????? ???

_custom_task: dict[str, Any] = {}


class CustomDrugBody(BaseModel):
    trade_name: str
    inn: str
    dosage_form: str = ""


async def _run_custom_pipeline(trade_name: str, inn: str, dosage_form: str) -> None:
    global _custom_task
    try:
        # Step 1: Claude ??
        _custom_task.update({"step": "analyze", "step_label": "Claude ?? ?..."})
        from analysis.sg_export_analyzer import analyze_custom_product
        result = await analyze_custom_product(trade_name, inn, dosage_form)
        _custom_task["result"] = result

        # Step 2: Perplexity ?? ??
        _custom_task.update({"step": "refs", "step_label": "?? ?? ?? ?..."})
        from analysis.perplexity_references import fetch_references_for_custom
        refs = await fetch_references_for_custom(trade_name, inn)
        _custom_task["refs"] = refs

        # Step 3: PDF ??(in-process)
        _custom_task.update({"step": "report", "step_label": "PDF ?? ?..."})
        from datetime import datetime, timezone as _tz2
        from report_generator import build_report, render_pdf
        from utils.db import fetch_kup_products

        _ts2 = datetime.now(_tz2.utc).strftime("%Y%m%d_%H%M%S")
        _gen_at2 = datetime.now(_tz2.utc).isoformat()
        _reports_dir2 = REPORTS_DIR
        _reports_dir2.mkdir(parents=True, exist_ok=True)

        _products_db2 = await asyncio.to_thread(fetch_kup_products, "HU")
        _refs_map2 = {result.get("product_id") or "custom": refs}
        _report2 = await asyncio.to_thread(
            lambda: build_report(
                _products_db2,
                _gen_at2,
                [result],
                references=_refs_map2,
            )
        )
        _report2 = _sanitize_p1_payload(_report2)
        _apply_hu_p1_meta(_report2, _gen_at2)
        _pdf_name2 = f"hu_report_custom_{_ts2}.pdf"
        _pdf_path2 = _reports_dir2 / _pdf_name2
        _json_name2 = f"hu_report_custom_{_ts2}.json"
        _json_path2 = _reports_dir2 / _json_name2
        await asyncio.to_thread(
            lambda: _json_path2.write_text(json.dumps(_report2, ensure_ascii=False, indent=2), encoding="utf-8")
        )
        await asyncio.to_thread(render_pdf, _report2, _pdf_path2)

        _custom_task["pdf"] = _pdf_name2
        _custom_task.update({"status": "done", "step": "done", "step_label": "??"})

    except Exception as exc:
        _custom_task.update({"status": "error", "step": "error", "step_label": str(exc)})


@app.post("/api/pipeline/custom")
async def trigger_custom_pipeline(body: CustomDrugBody) -> JSONResponse:
    global _custom_task
    if _custom_task.get("status") == "running":
        raise HTTPException(status_code=409, detail="??? ?????? ?? ?? ????.")
    _custom_task = {
        "status": "running", "step": "analyze", "step_label": "?? ?...",
        "result": None, "refs": [], "pdf": None,
    }
    if _IS_VERCEL:
        # Vercel 서버리스에서는 백그라운드 task 메모리가 보장되지 않아 인라인 실행한다.
        await _run_custom_pipeline(body.trade_name, body.inn, body.dosage_form)
    else:
        asyncio.create_task(_run_custom_pipeline(body.trade_name, body.inn, body.dosage_form))
    return JSONResponse({"ok": True})


@app.get("/api/pipeline/custom/status")
async def custom_pipeline_status() -> JSONResponse:
    if not _custom_task:
        return JSONResponse({"status": "idle"})
    return JSONResponse({
        "status":     _custom_task.get("status", "idle"),
        "step":       _custom_task.get("step", ""),
        "step_label": _custom_task.get("step_label", ""),
        "has_result": _custom_task.get("result") is not None,
        "has_pdf":    bool(_custom_task.get("pdf")),
    })


@app.get("/api/pipeline/custom/result")
async def custom_pipeline_result() -> JSONResponse:
    if not _custom_task:
        raise HTTPException(404, "??? ????? ???")
    return JSONResponse({
        "status": _custom_task.get("status"),
        "result": _custom_task.get("result"),
        "refs":   _custom_task.get("refs", []),
        "pdf":    _custom_task.get("pdf"),
    })


# ??????? ??? ?????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

@app.post("/api/pipeline/{product_key}")
async def trigger_pipeline(product_key: str) -> JSONResponse:
    if _pipeline_tasks.get(product_key, {}).get("status") == "running":
        raise HTTPException(status_code=409, detail="?????? ?? ?? ????.")
    _pipeline_tasks[product_key] = {
        "status": "running", "step": "init", "step_label": "?? ?...",
        "result": None, "refs": [], "pdf": None,
    }
    if _IS_VERCEL:
        # Vercel 서버리스에서는 백그라운드 task 메모리가 보장되지 않아 인라인 실행한다.
        await _run_pipeline_for_product(product_key)
    else:
        asyncio.create_task(_run_pipeline_for_product(product_key))
    return JSONResponse({"ok": True, "message": "?????? ??????."})


@app.get("/api/pipeline/{product_key}/status")
async def pipeline_status(product_key: str) -> JSONResponse:
    task = _pipeline_tasks.get(product_key)
    if not task:
        return JSONResponse({"status": "idle"})
    return JSONResponse({
        "status":     task["status"],
        "step":       task["step"],
        "step_label": task["step_label"],
        "has_result": task["result"] is not None,
        "has_pdf":    bool(task["pdf"]),
        "ref_count":  len(task.get("refs", [])),
    })


@app.get("/api/pipeline/{product_key}/result")
async def pipeline_result(product_key: str) -> JSONResponse:
    task = _pipeline_tasks.get(product_key)
    if not task:
        raise HTTPException(404, "????? ???")
    return JSONResponse({
        "status": task["status"],
        "step":   task["step"],
        "result": task.get("result"),
        "refs":   task.get("refs", []),
        "pdf":    task.get("pdf"),
    })


# ??????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

_report_cache: dict[str, Any] = {"path": None, "running": False}


def _p1_market_research_pdf_paths(reports_dir: Path) -> list[Path]:
    """P1 ReportLab PDF (hu_report_*.pdf)."""
    if not reports_dir.is_dir():
        return []
    return [p for p in reports_dir.glob("hu_report_*.pdf") if p.is_file()]


def _latest_p1_market_research_pdf(reports_dir: Path) -> Path | None:
    pdfs = _p1_market_research_pdf_paths(reports_dir)
    if not pdfs:
        return None
    return max(pdfs, key=lambda p: p.stat().st_mtime)


def _latest_report_pdf() -> Path | None:
    return _latest_p1_market_research_pdf(REPORTS_DIR)


def _latest_p2_pdf(reports_dir: Path) -> Path | None:
    """가격산출(P2) PDF 중 최신 파일을 반환."""
    candidates: list[Path] = []
    fixed = reports_dir / "hu02.pdf"
    if fixed.is_file():
        candidates.append(fixed)
    candidates.extend([p for p in reports_dir.glob("hu_p2_*.pdf") if p.is_file()])
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


class ReportBody(BaseModel):
    run_analysis: bool = False
    use_perplexity: bool = False


@app.post("/api/report")
async def trigger_report(body: ReportBody | None = None) -> JSONResponse:
    req = body if body is not None else ReportBody()
    if _report_cache["running"]:
        raise HTTPException(status_code=409, detail="????????????? ??? ?????.")

    async def _run_report() -> None:
        _report_cache["running"] = True
        try:
            import subprocess
            cmd = [
                sys.executable, str(ROOT / "report_generator.py"),
                "--out", str(REPORTS_DIR),
            ]
            if req.run_analysis:
                cmd.append("--run-analysis")
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: subprocess.run(cmd, capture_output=True, text=True)
            )
            reports_dir = REPORTS_DIR
            pdfs = sorted(_p1_market_research_pdf_paths(reports_dir), key=lambda p: p.stat().st_mtime, reverse=True)
            _report_cache["path"] = str(pdfs[0]) if pdfs else None
        finally:
            _report_cache["running"] = False

    asyncio.create_task(_run_report())
    return JSONResponse({"ok": True, "message": "????????????????????????????."})


@app.get("/api/report/status")
async def report_status() -> dict[str, Any]:
    reports_dir = REPORTS_DIR
    pdfs = _p1_market_research_pdf_paths(reports_dir) if reports_dir.exists() else []
    latest = _latest_report_pdf()
    return {
        "running": _report_cache["running"],
        "latest_pdf": str(latest) if latest else _report_cache["path"],
        "pdf_count": len(pdfs),
    }


@app.get("/api/report/download")
async def download_report(name: str | None = None, inline: bool = False) -> Any:
    """PDF ??. inline=true????????/iframe ??????Content-Disposition: inline)."""
    reports_dir = REPORTS_DIR
    disp = "inline" if inline else "attachment"
    if name:
        req_name = Path(name).name
        target = reports_dir / req_name
        is_p2_request = (req_name == "hu02.pdf" or req_name.startswith("hu_p2_"))
        if target.is_file():
            return FileResponse(
                str(target),
                media_type="application/pdf",
                filename=target.name,
                content_disposition_type=disp,
            )
        # Vercel 환경에서는 로컬 파일이 사라질 수 있어 Storage에서 복원 시도
        blob = _download_report_from_storage(req_name)
        if blob:
            import io
            return StreamingResponse(
                io.BytesIO(blob),
                media_type="application/pdf",
                headers={"Content-Disposition": f"{disp}; filename={req_name}"},
            )
        # 구버전 SG 파일명 자동 보정
        if "_SG_" in req_name:
            alt_name = req_name.replace("_SG_", "_HU_")
            alt_local = reports_dir / alt_name
            if alt_local.is_file():
                return FileResponse(
                    str(alt_local),
                    media_type="application/pdf",
                    filename=alt_local.name,
                    content_disposition_type=disp,
                )
            alt_blob = _download_report_from_storage(alt_name)
            if alt_blob:
                import io
                return StreamingResponse(
                    io.BytesIO(alt_blob),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"{disp}; filename={alt_name}"},
                )
        # 품목 토큰 기반 최신 P1 PDF fallback
        import re as _re_p1_dl
        m = _re_p1_dl.search(r"hu_report_(?:SG|HU)_(.+?)_\d{8}_\d{6}\.pdf$", req_name, _re_p1_dl.I)
        if m:
            token = m.group(1).lower()
            candidates = sorted(
                [p for p in _p1_market_research_pdf_paths(reports_dir) if token in p.name.lower()],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                latest_by_token = candidates[0]
                return FileResponse(
                    str(latest_by_token),
                    media_type="application/pdf",
                    filename=latest_by_token.name,
                    content_disposition_type=disp,
                )
        if is_p2_request:
            latest_p2 = _latest_p2_pdf(reports_dir)
            if latest_p2:
                return FileResponse(
                    str(latest_p2),
                    media_type="application/pdf",
                    filename=latest_p2.name,
                    content_disposition_type=disp,
                )
            raise HTTPException(
                status_code=404,
                detail="가격산출 PDF가 없습니다. 먼저 AI 가격 산출(/api/p2/pipeline 또는 /api/p2/report)을 실행하세요.",
            )

    latest = _latest_report_pdf()
    if not latest:
        raise HTTPException(status_code=404, detail="????????????. POST /api/report ??? ???")
    return FileResponse(
        str(latest),
        media_type="application/pdf",
        filename=latest.name,
        content_disposition_type=disp,
    )


# ?????2?? ?????? PDF ???????????????????????????????????????????????????????????????????????????????????????????????????????????????

class P2ReportBody(BaseModel):
    product_name:  str   = ""
    inn_name:      str   = ""
    verdict:       str   = ""
    seg_label:     str   = ""
    base_price:    float | None = None
    formula_str:   str   = ""
    mode_label:    str   = ""
    macro_text:    str   = ""
    scenarios:     list  = []
    ai_rationale:  list  = []
    sections:      list  = []  # [{seg_label, base_price, scenarios}] ??+?? ?? ?
    country:       str   = "HU"  # SG | HU
    usd_huf:       float | None = None  # ??, HUF ???


@app.post("/api/p2/report")
async def generate_p2_report(body: P2ReportBody) -> JSONResponse:
    """2?? ??? ?????? PDF ??? (report_generator.render_p2_pdf ??sg02.pdf?????? ??????)."""
    import re
    from datetime import datetime, timezone as _tz_p2

    from report_generator import render_p2_pdf

    _ts = datetime.now(_tz_p2.utc).strftime("%Y%m%d_%H%M%S")
    _reports_dir = REPORTS_DIR
    _reports_dir.mkdir(parents=True, exist_ok=True)

    _cc = (body.country or "HU").strip().upper()
    pdf_name = "hu02.pdf"
    pdf_path = _reports_dir / pdf_name

    _macro = (body.macro_text or "").strip()
    if not _macro:
        _macro = (
            "?????? EU ?????? NEAK(???????) ??????? ?????????? ??????? ??????????? "
            "KUP?????? USD?????? ?? ??????, ???ERP?????? HUF?EUR?????????????????"
        )

    p2_data: dict[str, Any] = {
        "product_name":  body.product_name,
        "inn_name":      body.inn_name,
        "verdict":       body.verdict,
        "seg_label":     body.seg_label,
        "base_price":    body.base_price,
        "formula_str":   body.formula_str,
        "mode_label":    body.mode_label,
        "macro_text":    _macro,
        "scenarios":     body.scenarios,
        "ai_rationale":  body.ai_rationale,
        "country":       _cc,
    }
    if body.sections:
        p2_data["sections"] = body.sections
    if body.usd_huf is not None:
        p2_data["usd_huf"] = body.usd_huf

    p2_data = _sanitize_p2_payload(p2_data)
    await asyncio.to_thread(render_p2_pdf, p2_data, pdf_path)
    await asyncio.to_thread(_upload_report_to_storage, pdf_path)

    return JSONResponse({"ok": True, "pdf": pdf_name})


# ?????2?? AI ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
# ???????(POST /api/p2/pipeline) ????? ?????**????** ??????.
#   1) pypdf ??1?? PDF ???????
#   2) Claude ?????DIPC??? ??JSON ??
#   3) yfinance ??SGD/HUF ?????
#   4) utils.kup_formula ??compute_kup_usd + format_kup_formula_ko (???? KUP)
#   5) Claude ??KUP ??????????????? ??/?? ????? JSON
#   6) _apply_kup_to_analysis ??????? ???formula?????? KUP???? ?????#   7) report_generator.render_p2_pdf ??hu02.pdf / sg02.pdf (UI ???????? ?????????? ??)

_p2_ai_task: dict[str, Any] = {}


async def _run_p2_ai_pipeline(
    report_path: str,
    market: str,
    target_country: str = "HU",
) -> None:
    global _p2_ai_task
    try:
        import json
        import os
        import re
        from datetime import datetime, timezone as _tz_p2ai

        import anthropic

        _tcd = "HU"
        _is_hu = True
        api_key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")).strip()
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY? ???? ?????.")

        from analysis.hungary_p1_generator import (
            build_hu_static_prompt_for_analysis,
            product_id_from_hu_p1_filename_only,
            resolve_hu_product_id_for_p2,
        )

        _p2_ai_task.update({"step": "extract", "step_label": "PDF ??"})
        await _emit({"phase": "p2_pipeline", "message": "PDF ?? ??", "level": "info"})
        pdf_text = ""
        _pdf_basename = Path(report_path).name
        try:
            from pypdf import PdfReader  # type: ignore[import]
            reader = PdfReader(report_path)
            for page in reader.pages:
                pdf_text += (page.extract_text() or "") + "\n"
        except Exception as exc_pdf:
            await _emit({"phase": "p2_pipeline", "message": f"PDF ?? ??: {exc_pdf}", "level": "warn"})
        if not pdf_text.strip():
            raise ValueError("PDF?? ???? ?? ? ????.")

        # ??: P1 PDF ????? ?? ??(??? ??)
        _pid_pre: str | None = product_id_from_hu_p1_filename_only(_pdf_basename) if _is_hu else None
        _hu_for_extract = (
            (build_hu_static_prompt_for_analysis(_pid_pre) or "").strip() if _pid_pre and _is_hu else ""
        )
        if _is_hu and not _hu_for_extract:
            _hu_for_extract = (
                "[??] P1 PDF ????? ?? ID? ?? ?? ?????. "
                "?? PDF ????? ????, ???(NEAK?OGY?I?EU) ???? ?????."
            )
        _p2_ai_task.update({"step": "ai_extract", "step_label": "AI ?? ??"})
        client = anthropic.Anthropic(api_key=api_key)
        extract_prompt = f"""P1 ???? PDF?? ??/?? ??? JSON??? ?????.

[??/?? ??]
{_hu_for_extract}

[PDF ?? (? 7000?)]
{pdf_text[:7000]}

??: ???? ?? JSON ?? ??.
??:
- product_name, inn_name: ???
- ref_price_usd, dipc_usd: USD ?? ?? null (HUF/EUR/AUD ??? USD? ??)
- ref_price_text: ?? ?? ?? ?? 1?
- pharmacy_margin_pct, wholesale_margin_pct, payback_pct, partner_margin_pct: ??? ?? ?? null
- logistics_usd: USD ?? ?? null
- competitor_prices: [{{"name": "...", "price_usd": number}}]
- market_context: NEAK?OGY?I???/??/?? (??? 2~4??, EU ??)
- hs_code: ???
- verdict: "적합" | "조건부" | "부적합" | "검토필"
"""
        extract_resp = await asyncio.to_thread(
            lambda: client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": extract_prompt}],
            )
        )
        extracted: dict[str, Any] = {}
        try:
            raw_extract = extract_resp.content[0].text
            m_json = re.search(r"\{.*\}", raw_extract, re.S)
            if m_json:
                extracted = json.loads(m_json.group(0))
        except Exception:
            pass
        if not extracted:
            extracted = {
                "product_name": "미상",
                "ref_price_usd": None,
                "market_context": "",
                "verdict": "검토필",
            }
        _p2_ai_task["extracted"] = extracted

        _p2_ai_task.update({"step": "exchange", "step_label": "?? ??"})
        exchange_rates: dict[str, Any] = {
            "usd_huf": 360.0,
            "usd_krw": 1393.0,
            "usd_eur": 0.92,
            "px_per_usd": 1.0,
            "source": "fallback",
        }
        try:
            import yfinance as yf  # type: ignore[import]
            exchange_rates = {
                "usd_huf": round(float(yf.Ticker("USDHUF=X").fast_info.last_price), 2),
                "usd_krw": round(float(yf.Ticker("USDKRW=X").fast_info.last_price), 2),
                "usd_eur": round(float(yf.Ticker("USDEUR=X").fast_info.last_price), 4),
                "px_per_usd": 1.0,
                "source": "Yahoo Finance",
            }
        except Exception:
            pass
        _p2_ai_task["exchange_rates"] = exchange_rates

        # DIPC/??? ?? ? PDF?? HUF?EUR?AUD? USD ??
        def _num_or_none(v: Any) -> float | None:
            try:
                if v in (None, ""):
                    return None
                return float(v)
            except (TypeError, ValueError):
                return None

        if _num_or_none(extracted.get("dipc_usd")) is None and _num_or_none(extracted.get("ref_price_usd")) is None:
            huf_match = re.search(r"HUF\s*([0-9]+(?:\.[0-9]+)?)", pdf_text, re.I)
            usd_huf = float(exchange_rates.get("usd_huf") or 360.0)
            fallback_usd: float | None = None
            if _is_hu and huf_match and usd_huf > 0:
                huf_val = float(huf_match.group(1))
                fallback_usd = round(huf_val / usd_huf, 2)
            eur_match = re.search(r"EUR\s*([0-9]+(?:\.[0-9]+)?)", pdf_text, re.I)
            aud_match = re.search(r"AUD\s*([0-9]+(?:\.[0-9]+)?)", pdf_text, re.I)
            usd_eur = float(exchange_rates.get("usd_eur") or 0.92)
            if fallback_usd is None and eur_match and usd_eur > 0:
                eur_val = float(eur_match.group(1))
                fallback_usd = round(eur_val / usd_eur, 2)
            elif fallback_usd is None and aud_match:
                fallback_usd = float(aud_match.group(1))
            if fallback_usd and fallback_usd > 0:
                extracted["ref_price_usd"] = fallback_usd
                extracted["dipc_usd"] = fallback_usd
                src = "HUF" if (huf_match and _is_hu) else ("EUR" if eur_match else "AUD")
                extracted["ref_price_text"] = f"PDF ??? ?? {src} -> USD {fallback_usd:.2f}"

        _hu_product_id: str | None = resolve_hu_product_id_for_p2(_pdf_basename, extracted) if _is_hu else None
        _hu_static_analysis = (
            (build_hu_static_prompt_for_analysis(_hu_product_id) or "").strip() if _hu_product_id and _is_hu else ""
        )
        if _is_hu and not _hu_static_analysis:
            _hu_static_analysis = (
                "[??] P1/PDF ?? ??. ??? NEAK?OGY?I?EU ?? ???? ????, "
                "?EU ??? KUP? ?? ???? ???."
            )
        _p2_analysis_ctx = _hu_static_analysis

        _p2_ai_task.update({"step": "ai_analysis", "step_label": "AI ?? ????"})

        from utils.kup_formula import compute_kup_usd, format_kup_formula_ko, pct_to_rate
        dipc_raw = extracted.get("dipc_usd")
        if dipc_raw in (None, ""):
            dipc_raw = extracted.get("ref_price_usd")
        dipc_val: float | None = None
        try:
            if dipc_raw not in (None, ""):
                _dipc_num = float(dipc_raw)
                if _dipc_num > 0:
                    dipc_val = _dipc_num
        except (TypeError, ValueError):
            dipc_val = None
        has_price_input = dipc_val is not None

        def _mr(k: str, d: float) -> float:
            v = extracted.get(k)
            return pct_to_rate(d if v in (None, "") else v)

        kup_base: float | None = None
        kup_formula_line = "가격 데이터 없음(미등재/유통 미확인)"
        if has_price_input and dipc_val is not None:
            kup_base = compute_kup_usd(
                dipc_val,
                pharmacy_rate=_mr("pharmacy_margin_pct", 15.0),
                wholesale_rate=_mr("wholesale_margin_pct", 15.0),
                payback_rate=_mr("payback_pct", 0.0),
                partner_rate=_mr("partner_margin_pct", 20.0),
                logistics_usd=float(extracted.get("logistics_usd") or 0),
            )
            kup_formula_line = format_kup_formula_ko(
                dipc_val,
                pharmacy_rate=_mr("pharmacy_margin_pct", 15.0),
                wholesale_rate=_mr("wholesale_margin_pct", 15.0),
                payback_rate=_mr("payback_pct", 0.0),
                partner_rate=_mr("partner_margin_pct", 20.0),
                logistics_usd=float(extracted.get("logistics_usd") or 0),
                kup=kup_base,
            )

        analysis: dict[str, Any] = {}
        try:
            _excerpt = json.dumps(extracted, ensure_ascii=False)[:3500]
            _ex_rate = json.dumps(exchange_rates, ensure_ascii=False)
            analysis_prompt = f"""P1 PDF ???? KUP(USD)? ???? ?? ????? JSON?? ?????.

[??/??]
{_p2_analysis_ctx}

[?? ???]
{_excerpt}

[??]
{_ex_rate}

[KUP]
- KUP(USD) = {f"{kup_base:.2f}" if kup_base is not None else "null"}
- ??: {kup_formula_line}

??(JSON, ???? ??):
{{
  "rationale": "??? 4~6??: NEAK?OGY?I?EU ??, KUP, ??? ??",
  "public_market": {{
    "final_price_usd": 0.0,
    "scenarios": [
      {{"name": "string", "price_usd": 0.0, "reason": "???", "formula": "string"}},
      {{"name": "string", "price_usd": 0.0, "reason": "???", "formula": "string"}},
      {{"name": "string", "price_usd": 0.0, "reason": "???", "formula": "string"}}
    ]
  }},
  "private_market": {{
    "final_price_usd": 0.0,
    "scenarios": [
      {{"name": "string", "price_usd": 0.0, "reason": "???", "formula": "string"}},
      {{"name": "string", "price_usd": 0.0, "reason": "???", "formula": "string"}},
      {{"name": "string", "price_usd": 0.0, "reason": "???", "formula": "string"}}
    ]
  }}
}}

- public: NEAK/????, private: ????????. ????? KUP(USD)? ??.
"""
            analysis_resp = await asyncio.to_thread(
                lambda: client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": analysis_prompt}],
                )
            )
            raw_analysis = analysis_resp.content[0].text
            m_json2 = re.search(r"\{.*\}", raw_analysis, re.S)
            if m_json2:
                analysis = json.loads(m_json2.group(0))
        except Exception:
            pass

        if not analysis:
            def _fb(base: float) -> list[dict[str, Any]]:
                return [
                    {
                        "name": "기준 시나리오",
                        "price_usd": round(base * 0.88, 2),
                        "reason": "??/?? ??? ??? ?? ??",
                        "formula": f"{base:.2f} x 0.88",
                    },
                    {
                        "name": "기준 시나리오",
                        "price_usd": round(base, 2),
                        "reason": "KUP 기준",
                        "formula": f"{base:.2f}",
                    },
                    {
                        "name": "기준 시나리오",
                        "price_usd": round(base * 1.12, 2),
                        "reason": "???? ??? ??? ?? ??",
                        "formula": f"{base:.2f} x 1.12",
                    },
                ]
            if kup_base is not None and kup_base > 0:
                analysis = {
                    "rationale": "PDF ???? ???? KUP ?? ?? ????? ??????. ?? ??? ?????.",
                    "public_market": {"final_price_usd": round(kup_base * 0.85, 2), "scenarios": _fb(round(kup_base * 0.85, 2))},
                    "private_market": {"final_price_usd": round(kup_base, 2), "scenarios": _fb(round(kup_base, 2))},
                }
            else:
                analysis = {
                    "rationale": "?? ??? ??(???/?? ???)?? KUP ? ???? ??? ??????.",
                    "public_market": {"final_price_usd": None, "scenarios": []},
                    "private_market": {"final_price_usd": None, "scenarios": []},
                }

        def _norm_positive(v: Any) -> float | None:
            try:
                n = float(v)
                return n if n > 0 else None
            except (TypeError, ValueError):
                return None

        def _clean_market_prices(a: dict[str, Any]) -> None:
            for mk in ("public_market", "private_market"):
                mkt = a.get(mk)
                if not isinstance(mkt, dict):
                    continue
                # 0/??? '??? ??'?? ??
                mkt["final_price_usd"] = _norm_positive(mkt.get("final_price_usd"))
                sc_raw = mkt.get("scenarios")
                if not isinstance(sc_raw, list):
                    mkt["scenarios"] = []
                    a[mk] = mkt
                    continue
                fixed_sc: list[dict[str, Any]] = []
                for s in sc_raw:
                    if not isinstance(s, dict):
                        continue
                    s2 = dict(s)
                    # Claude 응답 편차 대응: price_usd가 없으면 price를 USD로 간주
                    s2["price_usd"] = _norm_positive(s2.get("price_usd"))
                    if s2["price_usd"] is None:
                        s2["price_usd"] = _norm_positive(s2.get("price"))
                    fixed_sc.append(s2)
                mkt["scenarios"] = fixed_sc
                a[mk] = mkt

        def _apply_neak_fallback_if_needed(a: dict[str, Any]) -> None:
            # ?? ???? ?? ??? 0? ???? NEAK(EUR) ?? ?? ???? ??
            if has_price_input:
                return
            pub = a.get("public_market") if isinstance(a.get("public_market"), dict) else {}
            pri = a.get("private_market") if isinstance(a.get("private_market"), dict) else {}
            has_pub_price = _norm_positive(pub.get("final_price_usd")) is not None
            has_pri_price = _norm_positive(pri.get("final_price_usd")) is not None
            if has_pub_price or has_pri_price:
                return

            pa = a.get("pricing_assumptions") if isinstance(a.get("pricing_assumptions"), dict) else {}
            neak_range = pa.get("neak_range_eur")
            if not isinstance(neak_range, list) or len(neak_range) < 2:
                return
            low_eur = _norm_positive(neak_range[0])
            high_eur = _norm_positive(neak_range[1])
            usd_eur = _norm_positive(exchange_rates.get("usd_eur"))
            if low_eur is None or high_eur is None or usd_eur is None:
                return

            mid_eur = (low_eur + high_eur) / 2.0
            # EUR -> USD ??
            pub_base = round(mid_eur / usd_eur * 0.85, 2)
            pri_base = round(mid_eur / usd_eur, 2)

            a["public_market"] = {
                "final_price_usd": pub_base,
                "scenarios": [
                    {"name": "Conservative", "price_usd": round(pub_base * 0.92, 2), "reason": "NEAK EUR ??/?? ?? ?? ??", "formula": f"{pub_base:.2f} x 0.92"},
                    {"name": "Base", "price_usd": pub_base, "reason": "NEAK EUR ??? ??", "formula": f"{pub_base:.2f}"},
                    {"name": "Premium", "price_usd": round(pub_base * 1.08, 2), "reason": "NEAK EUR ?? ??", "formula": f"{pub_base:.2f} x 1.08"},
                ],
            }
            a["private_market"] = {
                "final_price_usd": pri_base,
                "scenarios": [
                    {"name": "Conservative", "price_usd": round(pri_base * 0.92, 2), "reason": "?? ?? ?? ?? ??", "formula": f"{pri_base:.2f} x 0.92"},
                    {"name": "Base", "price_usd": pri_base, "reason": "NEAK EUR ??? ??", "formula": f"{pri_base:.2f}"},
                    {"name": "Premium", "price_usd": round(pri_base * 1.08, 2), "reason": "?? ?? ???? ??", "formula": f"{pri_base:.2f} x 1.08"},
                ],
            }
            _rt = str(a.get("rationale") or "").strip()
            add_msg = "?? ??? ??(???/?? ???)?? NEAK EUR ?? ?? ?? ????? ??????."
            a["rationale"] = f"{_rt} {add_msg}".strip()


        def _apply_kup_to_analysis(a: dict[str, Any], kup: float) -> None:
            pm = a.get("private_market") or {}
            pub = a.get("public_market") or {}
            pm_sc = pm.get("scenarios") or []
            pub_sc = pub.get("scenarios") or []
            for i, m in enumerate([0.88, 1.00, 1.12]):
                if i < len(pm_sc):
                    pm_sc[i]["price_usd"] = round(kup * m, 2)
                    pm_sc[i]["formula"] = f"?? KUP {kup:.2f} USD x {m:.2f}"
            for i, m in enumerate([0.78, 0.85, 0.92]):
                if i < len(pub_sc):
                    pub_sc[i]["price_usd"] = round(kup * m, 2)
                    pub_sc[i]["formula"] = f"?? KUP {kup:.2f} USD x {m:.2f}"
            pm["final_price_usd"] = round(kup, 2)
            pub["final_price_usd"] = round(kup * 0.85, 2)
            a["private_market"] = pm
            a["public_market"] = pub

        if kup_base is not None and kup_base > 0:
            _apply_kup_to_analysis(analysis, kup_base)
        _clean_market_prices(analysis)
        _apply_neak_fallback_if_needed(analysis)
        _p2_ai_task["analysis"] = analysis
        _p2_ai_task["kup_base_usd"] = kup_base
        _p2_ai_task["kup_dipc_usd"] = dipc_val

        _p2_ai_task.update({"step": "report", "step_label": "PDF ??"})
        reports_dir = REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(extracted.get("product_name", "product"))).strip("._-")
        if not safe:
            safe = "product"
        safe = safe[:30]
        pdf_name = "hu02.pdf"
        pdf_path = reports_dir / pdf_name
        _p2_ts = datetime.now(_tz_p2ai.utc).strftime("%Y%m%d_%H%M%S")
        _p2_prefix = "hu_p2"
        json_path = reports_dir / f"{_p2_prefix}_{safe}_{_p2_ts}.json"

        def _norm_sc(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return [{"label": s.get("name", s.get("label", "")), "price": s.get("price_usd", s.get("price")), "reason": s.get("reason", ""), "formula": s.get("formula", "")} for s in (raw or [])]

        pub_data = (analysis.get("public_market") or {})
        priv_data = (analysis.get("private_market") or {})
        sections = [
            {
                "seg_label": "Public Market (NEAK/Hospital/Tender)",
                "base_price": pub_data.get("final_price_usd"),
                "scenarios": _norm_sc(pub_data.get("scenarios", [])),
            },
            {
                "seg_label": "Private Market (Pharmacy/Wholesale)",
                "base_price": priv_data.get("final_price_usd"),
                "scenarios": _norm_sc(priv_data.get("scenarios", [])),
            },
        ]
        p2_data = {
            "product_name": extracted.get("product_name", "Unknown Product"),
            "inn_name": extracted.get("inn_name", ""),
            "verdict": extracted.get("verdict", "Conditional"),
            "seg_label": "Public/Private Pricing Strategy",
            "base_price": pub_data.get("final_price_usd"),
            "formula_str": kup_formula_line,
            "mode_label": "AI Analysis (Claude Haiku)",
            "macro_text": analysis.get("rationale", ""),
            "scenarios": _norm_sc(pub_data.get("scenarios", [])),
            "ai_rationale": [analysis.get("rationale", "")],
            "sections": sections,
            "country": _tcd,
            "usd_huf": float(exchange_rates.get("usd_huf", 0) or 0) or None,
        }
        if _is_hu and _hu_product_id:
            p2_data["hu_product_id"] = _hu_product_id
        p2_data = _sanitize_p2_payload(p2_data)
        pipeline_meta = {
            "kup_engine": {
                "module": "utils.kup_formula",
                "dipc_usd": dipc_val,
                "kup_base_usd": kup_base,
                "kup_formula_line_ko": kup_formula_line,
                "price_data_available": has_price_input,
                "apply_kup_to_analysis_applied": bool(kup_base is not None and kup_base > 0),
            },
            "hu_product_id": _hu_product_id,
            "hu_static_analysis_chars": len(_hu_static_analysis) if _is_hu else 0,
            "steps": ["pypdf_extract", "claude_extract_prices", "yfinance_exchange", "compute_kup_usd", "claude_price_strategy_json", "apply_kup_to_analysis", "render_p2_pdf"],
        }
        await asyncio.to_thread(
            lambda: json_path.write_text(
                json.dumps({"extracted": extracted, "exchange_rates": exchange_rates, "analysis": analysis, "p2_data": p2_data, "pipeline_meta": pipeline_meta}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        )
        from report_generator import render_p2_pdf
        await asyncio.to_thread(render_p2_pdf, p2_data, pdf_path)
        await asyncio.to_thread(_upload_report_to_storage, pdf_path)

        _p2_ai_task["pdf"] = pdf_name
        _p2_ai_task.update({"status": "done", "step": "done", "step_label": "??"})
        await _emit({"phase": "p2_pipeline", "message": "P2 ???? ?? ??", "level": "success"})
    except Exception as exc:
        _p2_ai_task.update({"status": "error", "step": "error", "step_label": str(exc)[:300]})
        await _emit({"phase": "p2_pipeline", "message": f"P2 ??: {exc}", "level": "error"})


class UploadBody(BaseModel):
    filename: str
    content_b64: str  # base64 ?????? PDF ?????


@app.post("/api/p2/upload")
async def upload_p2_pdf(body: UploadBody) -> JSONResponse:
    """P2 ????????? PDF ?????(base64 JSON ??python-multipart ????."""
    import base64
    import re as _re_up

    fname = body.filename or "upload.pdf"
    if not fname.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF ???(.pdf)??????????????.")

    try:
        content = base64.b64decode(body.content_b64)
    except Exception:
        raise HTTPException(400, "base64 ???????? ???????PDF ??????? ????????")

    safe_fname = _re_up.sub(r"[^A-Za-z0-9_.-]+", "_", fname).strip("._-")
    if not safe_fname:
        safe_fname = "upload.pdf"
    safe_fname = safe_fname[:80]
    _reports_dir = REPORTS_DIR
    _reports_dir.mkdir(parents=True, exist_ok=True)
    dest = _reports_dir / f"upload_{safe_fname}"
    dest.write_bytes(content)

    return JSONResponse({"ok": True, "filename": dest.name})


class P2PipelineBody(BaseModel):
    report_filename: str = ""  # reports/ ???????(?? ??????? 1?? PDF ???)
    market: str = "public"     # "public" | "private" (??? AI ?????????? ????? ??? ???)
    target_country: str = "HU"  # SG | HU ??P2 PDF(?1 ????NEAK ??? ALPS ???)


@app.post("/api/p2/pipeline")
async def trigger_p2_pipeline(body: P2PipelineBody) -> JSONResponse:
    """2?? AI ???????????."""
    global _p2_ai_task
    if _p2_ai_task.get("status") == "running":
        raise HTTPException(409, "P2 ????????? ???? ??? ?????.")

    if body.report_filename:
        requested_name = Path(body.report_filename).name
        report_path = REPORTS_DIR / requested_name
        if not report_path.is_file():
            restored = _materialize_report_from_storage(requested_name)
            if restored is not None:
                report_path = restored
        # 로컬스토리지의 구버전 SG 파일명 선택값을 HU 파일명으로 자동 보정
        if not report_path.is_file() and "_SG_" in requested_name:
            alt_name = requested_name.replace("_SG_", "_HU_")
            alt_path = REPORTS_DIR / alt_name
            if alt_path.is_file():
                report_path = alt_path
            else:
                restored_alt = _materialize_report_from_storage(alt_name)
                if restored_alt is not None:
                    report_path = restored_alt
        # 이름 불일치 시 같은 품목 토큰의 최신 P1을 선택
        if not report_path.is_file():
            import re as _re_p2
            m = _re_p2.search(r"hu_report_(?:SG|HU)_(.+?)_\d{8}_\d{6}\.pdf$", requested_name, _re_p2.I)
            if m:
                token = m.group(1).lower()
                candidates = sorted(
                    [p for p in _p1_market_research_pdf_paths(REPORTS_DIR) if token in p.name.lower()],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if candidates:
                    report_path = candidates[0]
    else:
        report_path = _latest_report_pdf()

    # P1 PDF ??? ? ?? ????(sg_report_ / hu_report_) ??
    if not report_path or not Path(report_path).is_file():
        report_path = _latest_p1_market_research_pdf(REPORTS_DIR)
    if not report_path or not Path(report_path).is_file():
        raise HTTPException(404, f"???? P1 PDF? ?? ? ????: {body.report_filename or '(?? PDF ??)'}")

    _p2_ai_task = {
        "status":   "running",
        "step":     "extract",
        "step_label": "?? ?...",
        "extracted": None,
        "exchange_rates": None,
        "analysis": None,
        "pdf":      None,
    }
    asyncio.create_task(
        _run_p2_ai_pipeline(str(report_path), body.market, body.target_country)
    )
    return JSONResponse({"ok": True})


@app.get("/api/p2/pipeline/status")
async def p2_pipeline_status_ai() -> JSONResponse:
    if not _p2_ai_task:
        return JSONResponse({"status": "idle"})
    return JSONResponse({
        "status":     _p2_ai_task.get("status", "idle"),
        "step":       _p2_ai_task.get("step", ""),
        "step_label": _p2_ai_task.get("step_label", ""),
        "has_result": _p2_ai_task.get("analysis") is not None,
        "has_pdf":    bool(_p2_ai_task.get("pdf")),
    })


@app.get("/api/p2/pipeline/result")
async def p2_pipeline_result_ai() -> JSONResponse:
    if not _p2_ai_task:
        raise HTTPException(404, "P2 ????? ???")
    return JSONResponse({
        "status":         _p2_ai_task.get("status"),
        "extracted":      _p2_ai_task.get("extracted"),
        "exchange_rates": _p2_ai_task.get("exchange_rates"),
        "analysis":       _p2_ai_task.get("analysis"),
        "pdf":            _p2_ai_task.get("pdf"),
    })


# ?????products ?? ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

@app.get("/api/products")
async def products() -> list[dict[str, Any]]:
    from utils.db import fetch_kup_products
    return fetch_kup_products("HU")


# ?????API ????? (U1) ?????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

@app.get("/api/keys/status")
async def keys_status() -> dict[str, Any]:
    """Claude?Perplexity API ????? ???? ?? (??? ????? ??????? ???)."""
    import os
    claude_key     = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "")
    return {
        "claude":     bool(claude_key.strip()),
        "perplexity": bool(perplexity_key.strip()),
    }


# ????????????? ??? (U5?B1) ?????????????????????????????????????????????????????????????????????????????????????????????????????

@app.get("/api/datasource/status")
async def datasource_status() -> JSONResponse:
    """Supabase ??? ???, KUP ??? ?? ??? ????? ?? ??."""
    try:
        from utils.db import fetch_kup_products
        kup_rows = fetch_kup_products("HU")
        kup_count = len(kup_rows)
        context_source = f"KUP/?? {kup_count}?"
        ctx_count = 0

        return JSONResponse({
            "supabase":       "ok",
            "kup_count":      kup_count,
            "context_ok":     ctx_count > 0,
            "context_source": context_source,
            "message":        f"KUP {kup_count}? ??",
        })
    except Exception as exc:
        return JSONResponse({
            "supabase":       "error",
            "kup_count":      0,
            "context_ok":     False,
            "context_source": "??? ???",
            "message":        str(exc)[:120],
        })


# ???????? / SSE ????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

@app.get("/api/status")
async def status() -> dict[str, Any]:
    lock = _state["lock"]
    assert lock is not None
    async with lock:
        n = len(_state["events"])
    return {"event_count": n}


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Render ????????? ????????"""
    return {"ok": True, "service": "hu-export-analysis-dashboard"}


@app.get("/api/stream")
async def stream() -> StreamingResponse:
    last = 0

    async def gen() -> Any:
        nonlocal last
        while True:
            await asyncio.sleep(0.12)
            chunk: list[dict[str, Any]] = []
            lock = _state["lock"]
            assert lock is not None
            async with lock:
                while last < len(_state["events"]):
                    chunk.append(_state["events"][last])
                    last += 1
            for ev in chunk:
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ?????3??: ?????? ???????????????????????????????????????????????????????????????????????????????????????????????????

_buyer_task: dict[str, Any] = {}

_PROD_LABELS: dict[str, str] = {
    "SG_sereterol_activair":      "Sereterol Activair (Fluticasone+Salmeterol)",
    "SG_omethyl_omega3_2g":       "Omethyl Cutielet (Omega-3-EE90 2g)",
    "SG_hydrine_hydroxyurea_500": "Hydrine (Hydroxyurea 500mg)",
    "SG_gadvoa_gadobutrol_604":   "Gadvoa Inj. (Gadobutrol)",
    "SG_rosumeg_combigel":        "Rosumeg Combigel (Rosuvastatin+Omega-3)",
    "SG_atmeg_combigel":          "Atmeg Combigel (Atorvastatin+Omega-3)",
    "SG_ciloduo_cilosta_rosuva":  "Ciloduo (Cilostazol+Rosuvastatin)",
    "SG_gastiin_cr_mosapride":    "Gastiin CR (Mosapride citrate 15mg)",
}


def _load_static_profile(product_key: str) -> dict[str, Any]:
    """3????? ??? ?? ??? ?????? ??."""
    try:
        from utils.market_data_source import load_market_rows
        rows = load_market_rows()
    except Exception:
        return {}
    row = next((r for r in rows if str(r.get("product_id", "")).strip() == product_key), None)
    if not row:
        return {}
    return {
        "product_id": row.get("product_id", ""),
        "trade_name": row.get("trade_name", ""),
        "manufacturer": row.get("manufacturer", ""),
        "registration_number": row.get("registration_number", ""),
        "market_segment": row.get("market_segment", ""),
        "raw_payload": row.get("raw_payload", {}) or {},
    }


class BuyerRunBody(BaseModel):
    product_key:     str = "SG_sereterol_activair"
    active_criteria: list[str] | None = None
    target_country:  str = "Hungary"
    target_region:   str = "Europe"
    analysis_context: dict[str, Any] | None = None


async def _run_buyer_pipeline(
    product_key: str,
    active_criteria: list[str] | None = None,
    target_country: str = "Hungary",
    target_region: str = "Europe",
    analysis_context: dict[str, Any] | None = None,
) -> None:
    global _buyer_task

    async def _log(msg: str, level: str = "info") -> None:
        await _emit({"phase": "buyer", "message": msg, "level": level})

    try:
        product_label = _PROD_LABELS.get(product_key, product_key)
        merged_context = dict(analysis_context or {})
        static_profile = _load_static_profile(product_key)
        if static_profile:
            merged_context["static_profile"] = static_profile
        _buyer_task["analysis_context"] = merged_context

        hu_enrich = ""
        try:
            from analysis.hungary_p1_generator import build_hu_static_prompt_for_analysis
            hu_enrich = (build_hu_static_prompt_for_analysis(product_key) or "").strip()
        except Exception:
            hu_enrich = ""
        if hu_enrich:
            merged_context["hu_market_static"] = hu_enrich

        _buyer_task.update({"step": "crawl", "step_label": "CPHI ??"})
        await _log(f"??? ?? ??: {product_label} / {target_country} ({target_region})")
        from utils.cphi_crawler import crawl as cphi_crawl, PRODUCT_SEARCH_MAP
        candidate_pool = int(_os.environ.get("BUYER_CANDIDATE_POOL", "8" if _IS_VERCEL else "20"))
        companies = await cphi_crawl(product_key=product_key, candidate_pool=max(5, candidate_pool), emit=_log)
        _buyer_task["crawl_count"] = len(companies)

        if not companies:
            await _log("CPHI ?? ?? - Perplexity fallback ??")
            mapping = PRODUCT_SEARCH_MAP.get(product_key, {})
            ingredient = ", ".join(mapping.get("ingredients", [])[:2]) or product_label
            therapeutic = ", ".join(mapping.get("therapeutic", [])[:2]) or "pharmaceutical"
            from utils.buyer_enricher import discover_companies_via_perplexity
            companies = await discover_companies_via_perplexity(
                ingredient, therapeutic, target_country, target_region, emit=_log
            )
            _buyer_task["crawl_count"] = len(companies)

        _buyer_task.update({"step": "enrich", "step_label": "?? ?? ??"})
        from utils.buyer_enricher import enrich_all
        enriched = await enrich_all(
            companies,
            product_label=product_label,
            target_country=target_country,
            target_region=target_region,
            emit=_log,
            hu_market_static=hu_enrich,
            max_concurrency=4 if _IS_VERCEL else 2,
            use_perplexity=not _IS_VERCEL,
        )
        _buyer_task["all_candidates"] = enriched

        _buyer_task.update({"step": "rank", "step_label": "Top 10 ??"})
        from analysis.buyer_scorer import rank_companies
        ranked = rank_companies(
            enriched,
            active_criteria=active_criteria,
            top_n=10,
            analysis_context=merged_context,
        )
        _buyer_task["buyers"] = ranked

        _buyer_task.update({"step": "report", "step_label": "PDF ??"})
        from datetime import datetime, timezone as _tz_b
        from analysis.buyer_report_generator import build_buyer_pdf
        import re as _re_b

        ts = datetime.now(_tz_b.utc).strftime("%Y%m%d_%H%M%S")
        reports_dir = REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe = _re_b.sub(r"[^\w?-?]", "_", product_key)[:30] or "product"
        # ?? ??? hu ? ?? ??? ReportLab? ??? PDF ??(?? ?? ??)
        base_name = f"hu_buyers_{safe}_{ts}"
        pdf_name = f"{base_name}.pdf"
        pdf_path = reports_dir / pdf_name
        json_path = reports_dir / f"{base_name}.json"

        def _write_json() -> None:
            json_path.write_text(
                json.dumps(
                    {
                        "product_key": product_key,
                        "product_label": product_label,
                        "target_country": target_country,
                        "target_region": target_region,
                        "buyers": ranked,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        await asyncio.to_thread(_write_json)
        await asyncio.to_thread(
            build_buyer_pdf,
            ranked,
            product_label,
            pdf_path,
            target_country=target_country,
            target_region=target_region,
        )
        await asyncio.to_thread(_upload_report_to_storage, pdf_path)
        _buyer_task["pdf"] = pdf_name
        _buyer_task.update({"status": "done", "step": "done", "step_label": "??"})
        await _log("??? ??? ?? ??", "success")
    except Exception as exc:
        _buyer_task.update({"status": "error", "step": "error", "step_label": str(exc)})
        await _emit({"phase": "buyer", "message": f"??: {exc}", "level": "error"})


@app.post("/api/buyers/run")
async def trigger_buyers(body: BuyerRunBody | None = None) -> JSONResponse:
    global _buyer_task
    import uuid
    req = body if body is not None else BuyerRunBody()
    if _buyer_task.get("status") == "running":
        raise HTTPException(409, "??? ?????? ?? ?? ????.")
    task_id = str(uuid.uuid4())
    _buyer_task = {
        "status": "running", "step": "crawl", "step_label": "??",
        "crawl_count": 0, "all_candidates": [], "buyers": [], "pdf": None,
        "task_id": task_id,
    }
    if _IS_VERCEL:
        await _run_buyer_pipeline(
            req.product_key,
            req.active_criteria,
            req.target_country,
            req.target_region,
            req.analysis_context,
        )
    else:
        asyncio.create_task(_run_buyer_pipeline(
            req.product_key,
            req.active_criteria,
            req.target_country,
            req.target_region,
            req.analysis_context,
        ))
    return JSONResponse({"ok": True, "task_id": task_id})


@app.get("/api/buyers/status")
async def buyer_status() -> JSONResponse:
    if not _buyer_task:
        return JSONResponse({"status": "idle"})
    return JSONResponse({
        "status":          _buyer_task.get("status", "idle"),
        "step":            _buyer_task.get("step", ""),
        "step_label":      _buyer_task.get("step_label", ""),
        "crawl_count":     _buyer_task.get("crawl_count", 0),
        "buyer_count":     len(_buyer_task.get("buyers", [])),
        "candidate_count": len(_buyer_task.get("all_candidates", [])),
        "has_pdf":         bool(_buyer_task.get("pdf")),
        "task_id":         _buyer_task.get("task_id", ""),
    })


@app.get("/api/buyers/result")
async def buyer_result() -> JSONResponse:
    if not _buyer_task:
        raise HTTPException(404, "??? ??? ????.")
    return JSONResponse({
        "status":  _buyer_task.get("status"),
        "buyers":  _buyer_task.get("buyers", []),
        "pdf":     _buyer_task.get("pdf"),
    })


@app.post("/api/buyers/rerank")
async def buyer_rerank(body: dict = None) -> JSONResponse:
    """?? ???? Top 10? ??????."""
    all_candidates = _buyer_task.get("all_candidates", [])
    if not all_candidates:
        raise HTTPException(404, "???? ??? ????. ?? ??? ??? ??? ???.")
    criteria = (body or {}).get("criteria")
    analysis_context = _buyer_task.get("analysis_context", {})
    from analysis.buyer_scorer import rank_companies
    ranked = rank_companies(
        all_candidates,
        active_criteria=criteria,
        top_n=10,
        analysis_context=analysis_context,
    )
    _buyer_task["buyers"] = ranked
    return JSONResponse({"buyers": ranked})


@app.get("/api/report/combined")
async def download_combined_report() -> Any:
    """P1/P2/P3 ?? PDF 3?? ??? ???????."""
    import io
    from datetime import datetime, timezone as _tz_c

    reports_dir = REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    def _latest(pattern: str):
        pdfs = sorted(reports_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        return pdfs[0] if pdfs else None

    p2_pdf = _latest("hu02.pdf") or _latest("hu_p2_*.pdf")
    p3_pdf = _latest("hu_buyers_*.pdf")
    p1_pdf = _latest("hu_report_*.pdf")
    if not (p1_pdf and p2_pdf and p3_pdf):
        missing: list[str] = []
        if not p1_pdf:
            missing.append("P1(????)")
        if not p2_pdf:
            missing.append("P2(????)")
        if not p3_pdf:
            missing.append("P3(???)")
        miss = ", ".join(missing)
        raise HTTPException(
            404,
            f"?? ???? P1/P2/P3 PDF 3?? ?? ?????. ??: {miss}",
        )

    # ?????????(?????????????????
    ts = datetime.now(_tz_c.utc).strftime("%Y%m%d_%H%M%S")
    pdf_name = f"hu_combined_{ts}.pdf"
    pdf_path = reports_dir / pdf_name

    def _build_cover_pdf(out_path: Path) -> bool:
        """템플릿 표지 PDF를 복사하고 회사명 아래 날짜를 실시간으로 오버레이한다."""
        if not _COMBINED_COVER_TEMPLATE.is_file():
            return False
        try:
            from io import BytesIO
            from pypdf import PdfReader, PdfWriter  # type: ignore[import]
            from reportlab.lib.colors import Color
            from reportlab.pdfgen import canvas

            reader = PdfReader(str(_COMBINED_COVER_TEMPLATE))
            if not reader.pages:
                return False

            first_page = reader.pages[0]
            w = float(first_page.mediabox.width)
            h = float(first_page.mediabox.height)

            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=(w, h))
            c.setFillColor(Color(0.45, 0.45, 0.45))
            c.setFont("Helvetica", 14)
            # '한국유나이티드제약' 아래 위치에 실시간 날짜를 중앙 정렬로 표시
            c.drawCentredString(w * 0.5, h * 0.205, datetime.now(_tz_c.utc).strftime("%Y-%m-%d"))
            c.save()
            packet.seek(0)

            overlay = PdfReader(packet)
            first_page.merge_page(overlay.pages[0])

            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(out_path, "wb") as fout:
                writer.write(fout)
            writer.close()
            return True
        except Exception:
            return False

    def _merge_pdfs() -> None:
        from pypdf import PdfWriter  # type: ignore[import]

        writer = PdfWriter()
        cover_pdf = reports_dir / f"hu_cover_{ts}.pdf"
        has_cover = _build_cover_pdf(cover_pdf)

        # 병합 순서: 표지(옵션) -> P2(가격산출) -> P3(바이어) -> P1(시장보고서)
        if has_cover and cover_pdf.is_file():
            writer.append(str(cover_pdf))
        writer.append(str(p2_pdf))
        writer.append(str(p3_pdf))
        writer.append(str(p1_pdf))
        with open(pdf_path, "wb") as fout:
            writer.write(fout)
        writer.close()

    try:
        await asyncio.to_thread(_merge_pdfs)
    except Exception as exc:
        raise HTTPException(500, f"?? PDF ?? ??: {exc}")

    with open(pdf_path, "rb") as fin:
        buf = io.BytesIO(fin.read())
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={pdf_name}",
            "X-PDF-Name": pdf_name,
            "Access-Control-Expose-Headers": "X-PDF-Name",
        },
    )


@app.get("/api/buyers/report/download")
async def buyer_report_download(name: str | None = None) -> Any:
    reports_dir = REPORTS_DIR
    if name:
        target = reports_dir / Path(name).name
        if target.is_file():
            return FileResponse(
                str(target), media_type="application/pdf",
                filename=target.name, content_disposition_type="attachment",
            )
        blob = _download_report_from_storage(Path(name).name)
        if blob:
            import io
            return StreamingResponse(
                io.BytesIO(blob),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={Path(name).name}"},
            )
    # ?? hu ??? ReportLab PDF(??? sg_* ??)
    pdfs = sorted(
        reports_dir.glob("hu_buyers_*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not pdfs:
        raise HTTPException(404, "??? PDF? ????. ??? ??? ?? ?????.")
    return FileResponse(
        str(pdfs[0]), media_type="application/pdf",
        filename=pdfs[0].name, content_disposition_type="attachment",
    )


@app.get("/")
async def index() -> FileResponse:
    index_path = STATIC / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="index.html ???")
    return FileResponse(index_path)


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="HU export dashboard (FastAPI)")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    if args.open:
        def _open_later() -> None:
            time.sleep(1.0)
            webbrowser.open(f"http://127.0.0.1:{args.port}/")
        threading.Thread(target=_open_later, daemon=True).start()

    print(f"\nDashboard: http://127.0.0.1:{args.port}/\n")
    uvicorn.run(app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()


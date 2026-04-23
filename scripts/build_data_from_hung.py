from pathlib import Path
import json
import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P1 = Path(r'c:\Users\user\Desktop\hung\DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx')
P2 = Path(r'c:\Users\user\Desktop\hung\medicines-output-medicines-report_en (1).xlsx')
P3 = Path(r'c:\Users\user\Desktop\hung\tk_lista.csv')

price_df = pd.read_excel(P1, sheet_name='IPC_DRUG_LIST_20250714').fillna('')
ema_raw = pd.read_excel(P2, header=None)
header_idx = ema_raw.index[ema_raw.iloc[:,0].astype(str).str.strip().eq('Category')][0]
ema_df = pd.read_excel(P2, header=header_idx).fillna('')
tk_df = pd.read_csv(P3, sep=';', encoding='latin1', dtype=str, low_memory=False).fillna('')

price_df['_blob'] = price_df.apply(lambda r: ' '.join([str(r.get('Product name','')), str(r.get('INN & Strength','')), str(r.get('ATC','')), str(r.get('Company',''))]).lower(), axis=1)
ema_df['_blob'] = ema_df.apply(lambda r: ' '.join([str(r.get('Name of medicine','')), str(r.get('International non-proprietary name (INN) / common name','')), str(r.get('Active substance','')), str(r.get('ATC code (human)',''))]).lower(), axis=1)

cols = list(tk_df.columns)
name_col = cols[1] if len(cols) > 1 else cols[0]
inn_col = cols[4] if len(cols) > 4 else cols[-1]
atc_col = cols[5] if len(cols) > 5 else cols[-1]
company_col = cols[6] if len(cols) > 6 else cols[-1]
short_col = cols[-1]
tk_df['_blob'] = tk_df.apply(lambda r: ' '.join([str(r.get(name_col,'')), str(r.get(inn_col,'')), str(r.get(atc_col,'')), str(r.get(company_col,''))]).lower(), axis=1)

TARGETS = [
    ('SG_omethyl_omega3_2g', 'Omega-3 (Omethyl)', 'Omethyl Cutielet', 'Omega-3-EE90 2g', ['omega-3', 'ethyl']),
    ('SG_gadvoa_gadobutrol_604', 'Gadobutrol (Gadvoa)', 'Gadvoa Inj.', 'Gadobutrol 604.72mg', ['gadobutrol']),
    ('SG_sereterol_activair', 'Fluticasone+Salmeterol (Sereterol)', 'Sereterol Activair', 'Fluticasone+Salmeterol', ['fluticasone', 'salmeterol']),
    ('SG_hydrine_hydroxyurea_500', 'Hydroxyurea (Hydrine)', 'Hydrine', 'Hydroxyurea 500mg', ['hydroxyurea']),
    ('SG_rosumeg_combigel', 'Rosuvastatin (Rosumeg)', 'Rosumeg Combigel', 'Rosuvastatin+Omega-3-EE90', ['rosuvastatin']),
    ('SG_atmeg_combigel', 'Atorvastatin (Atmeg)', 'Atmeg Combigel', 'Atorvastatin+Omega-3-EE90', ['atorvastatin']),
    ('SG_ciloduo_cilosta_rosuva', 'Cilostazol (Ciloduo)', 'Ciloduo', 'Cilostazol+Rosuvastatin', ['cilostazol']),
    ('SG_gastiin_cr_mosapride', 'Mosapride (Gastiin)', 'Gastiin CR', 'Mosapride Citrate 15mg', ['mosapride']),
]


def subset(df, kws):
    mask = False
    for kw in kws:
        mask = mask | df['_blob'].str.contains(re.escape(kw), na=False)
    return df[mask]

products = []
product_data = {}
competitor_data = {}
static_data = {}

market_rows = []

for product_id, key, name, inn, kws in TARGETS:
    pm = subset(price_df, kws)
    em = subset(ema_df, kws)
    tk = subset(tk_df, kws)

    gross = pd.to_numeric(pm.get('Gross retail price', pd.Series(dtype=float)), errors='coerce').dropna()
    pmin = float(gross.min()) if len(gross) else None
    pmax = float(gross.max()) if len(gross) else None

    shortage = int(tk[short_col].astype(str).str.lower().str.contains('igen|yes|true').sum()) if len(tk) else 0

    vt = 'ok' if len(pm) and len(em) else ('warn' if (len(pm) or len(em) or len(tk)) else 'no')
    verdict = {'ok': '적합', 'warn': '검토 필요', 'no': '데이터 부족'}[vt]

    products.append({'key': key, 'name': name, 'inn': inn, 'verdict': verdict, 'vt': vt})

    competitors = []
    if len(pm):
        tmp = pm.copy()
        tmp['_gross'] = pd.to_numeric(tmp['Gross retail price'], errors='coerce')
        grouped = tmp.groupby(tmp['Company'].astype(str).str.strip())['_gross'].agg(['min','max','count']).sort_values(['count','min'], ascending=[False,True]).head(7)
        rank = 1
        for cname, row in grouped.iterrows():
            if not str(cname).strip():
                continue
            sample_rows = pm[pm['Company'].astype(str).str.strip() == cname]
            sample_name = str(sample_rows.iloc[0]['Product name']) if len(sample_rows) else '-'
            competitors.append({
                'rank': rank,
                'company': str(cname),
                'min': float(row['min']) if pd.notna(row['min']) else 0.0,
                'max': float(row['max']) if pd.notna(row['max']) else 0.0,
                'products': int(row['count']) if pd.notna(row['count']) else 0,
                'sample': sample_name,
                'status': '참고'
            })
            rank += 1

    product_data[key] = {
        'drug_name': name,
        'inn': inn,
        'strength': str(pm.iloc[0].get('INN & Strength', '-')) if len(pm) else '-',
        'hs_code': '-',
        'channel': '병원/약국/조달 (원본 파일 기준)',
        'confidence': round(min(0.99, 0.45 + (0.2 if len(pm) else 0) + (0.2 if len(em) else 0) + (0.15 if len(tk) else 0)), 2),
        'verdict': verdict,
        'verdict_type': vt,
        'ogyei': int(len(tk)),
        'ogyei_shortage': shortage,
        'neak_count': int(len(pm)),
        'neak_range': (f'{pmin:.2f} ~ {pmax:.2f}' if pmin is not None else '-'),
        'ema': f'EMA medicines 매칭 {len(em)}건',
        'patikaradar': f'국제 가격 비교 리스트 매칭 {len(pm)}건',
        'pubmed': '제공 3개 파일에는 PubMed 원문 메타 없음',
        'strategy': '세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립',
        'risk': '원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요',
    }

    competitor_data[key] = {
        'total_products': int(len(pm)),
        'total_companies': int(pm['Company'].astype(str).str.strip().replace('', pd.NA).dropna().nunique()) if len(pm) else 0,
        'price_min': pmin,
        'price_max': pmax,
        'note': 'DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계',
        'recommended_price': '하위 25%~중앙값 구간에서 포지셔닝 권장' if pmin is not None else '가격 데이터 부족',
        'competitors': competitors,
    }

    patika = []
    if len(pm):
        for _, r in pm[['Product name', 'Gross retail price']].head(10).iterrows():
            patika.append({'pharmacy': str(r['Product name'])[:80], 'price': str(r['Gross retail price'])})

    ema_rows = []
    if len(em):
        cols_need = ['Name of medicine', 'ATC code (human)', 'Medicine URL']
        for _, r in em[cols_need].head(6).iterrows():
            ema_rows.append({'pmid': 'EMA', 'title': str(r['Name of medicine']), 'journal': str(r['ATC code (human)']), 'finding': str(r['Medicine URL'])})

    static_data[key] = {
        'ema': {'count': int(len(em)), 'note': 'medicines-output-medicines-report_en (1).xlsx'},
        'ogyei': {'count': int(len(tk)), 'shortage': shortage},
        'neak': {'count': int(len(pm)), 'range': (f'{pmin:.2f} ~ {pmax:.2f}' if pmin is not None else '-')},
        'patikaradar': patika,
        'pubmed': ema_rows,
        'condition': [
            '데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx',
            '데이터 소스: medicines-output-medicines-report_en (1).xlsx',
            '데이터 소스: tk_lista.csv',
        ],
        'reject': [],
    }

    atc = str(pm.iloc[0].get('ATC', '')) if len(pm) else str(tk.iloc[0].get(atc_col, '')) if len(tk) else ""
    market_rows.append(
        {
            "product_id": product_id,
            "trade_name": name,
            "active_ingredient": inn,
            "inn_name": inn,
            "strength": str(pm.iloc[0].get('INN & Strength', '-')) if len(pm) else '-',
            "dosage_form": str(pm.iloc[0].get('Dosage Form', '')) if len(pm) else "",
            "market_segment": "병원/약국/조달",
            "registration_number": str(tk.iloc[0].get(cols[0], "")) if len(tk) else "",
            "manufacturer": str(pm.iloc[0].get('Company', '')) if len(pm) else str(tk.iloc[0].get(company_col, "")) if len(tk) else "",
            "country_specific": {
                "atc": atc,
                "therapeutic_area": "",
                "hsa_reg": f"매칭 {len(tk)}건",
                "key_risk": "매칭 건수 기반 자동 집계",
                "product_type": "일반제",
            },
            "raw_payload": {
                "price_rows": int(len(pm)),
                "ema_rows": int(len(em)),
                "registry_rows": int(len(tk)),
            },
            "country": "SG",
            "source_name": "SG:kup_pipeline",
            "source_url": f"local://{P1.name}+{P2.name}+{P3.name}/{product_id}",
            "deleted_at": None,
        }
    )

header = '''// ════════════════════════════════════════════════════════════════
// UPharma Export AI — 공유 데이터 (단일 진실 공급원)
// 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx
//      medicines-output-medicines-report_en (1).xlsx
//      tk_lista.csv
// ════════════════════════════════════════════════════════════════

// ── 타입 ────────────────────────────────────────────────────────

export interface ProductEntry {
  drug_name: string;
  inn: string;
  strength: string;
  hs_code: string;
  channel: string;
  confidence: number;
  verdict: string;
  verdict_type: "ok" | "warn" | "no";
  ogyei: number;
  ogyei_shortage: number;
  neak_count: number;
  neak_range: string;
  ema: string;
  patikaradar: string;
  pubmed: string;
  strategy: string;
  risk: string;
}

export interface Competitor {
  rank: number;
  company: string;
  min: number;
  max: number;
  products: number;
  sample: string;
  status: string;
}

export interface CompetitorEntry {
  total_products: number;
  total_companies: number;
  price_min: number | null;
  price_max: number | null;
  note: string;
  recommended_price: string;
  competitors: Competitor[];
}

export interface PatikaPrice { pharmacy: string; price: string; }
export interface PubmedEntry { pmid: string; title: string; journal: string; finding: string; }
export interface StaticEntry {
  ema: { count: number; note: string };
  ogyei: { count: number; shortage: number };
  neak: { count: number; range: string };
  patikaradar: PatikaPrice[];
  pubmed: PubmedEntry[];
  condition: string[];
  reject: string[];
}

'''

out = [header]
out.append('// ── 제품 리스트 (UI 탭·드롭다운용) ────────────────────────────\n\n')
out.append('export const PRODUCTS = ' + json.dumps(products, ensure_ascii=False, indent=2) + ' as const;\n\n')
out.append('// ── 제품 데이터 (원본 3개 파일 집계) ─────────────────────────\n\n')
out.append('export const PRODUCT_DATA: Record<string, ProductEntry> = ' + json.dumps(product_data, ensure_ascii=False, indent=2) + ';\n\n')
out.append('// ── 경쟁사/가격 데이터 ───────────────────────────────────────\n\n')
out.append('export const COMPETITOR_DATA: Record<string, CompetitorEntry> = ' + json.dumps(competitor_data, ensure_ascii=False, indent=2) + ';\n\n')
out.append('// ── 정적 표시 데이터 ────────────────────────────────────────\n\n')
out.append('export const STATIC_DATA: Record<string, StaticEntry> = ' + json.dumps(static_data, ensure_ascii=False, indent=2) + ';\n\n')
out.append('export const VT: Record<string, string> = {\n  ok: "bg-emerald-100 text-emerald-700 border border-emerald-200",\n  warn: "bg-amber-100 text-amber-700 border border-amber-200",\n  no: "bg-slate-100 text-slate-700 border border-slate-200",\n};\n\n')
out.append('export const VERDICT_KO: Record<string, string> = {\n  ok: "적합",\n  warn: "검토 필요",\n  no: "데이터 부족",\n};\n')

(ROOT / 'datas' / 'lib').mkdir(parents=True, exist_ok=True)
(ROOT / 'datas' / 'lib' / 'data.ts').write_text(''.join(out), encoding='utf-8')

(ROOT / 'datas' / 'static').mkdir(parents=True, exist_ok=True)
(ROOT / 'datas' / 'static' / 'market_source.json').write_text(
    json.dumps(
        {
            "meta": {
                "sources": [str(P1), str(P2), str(P3)],
                "generated_at": pd.Timestamp.utcnow().isoformat(),
            },
            "rows": market_rows,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print('wrote data.ts and market_source.json')

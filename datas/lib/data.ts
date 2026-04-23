// ════════════════════════════════════════════════════════════════
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

// ── 제품 리스트 (UI 탭·드롭다운용) ────────────────────────────

export const PRODUCTS = [
  {
    "key": "Omega-3 (Omethyl)",
    "name": "Omethyl Cutielet",
    "inn": "Omega-3-EE90 2g",
    "verdict": "적합",
    "vt": "ok"
  },
  {
    "key": "Gadobutrol (Gadvoa)",
    "name": "Gadvoa Inj.",
    "inn": "Gadobutrol 604.72mg",
    "verdict": "검토 필요",
    "vt": "warn"
  },
  {
    "key": "Fluticasone+Salmeterol (Sereterol)",
    "name": "Sereterol Activair",
    "inn": "Fluticasone+Salmeterol",
    "verdict": "적합",
    "vt": "ok"
  },
  {
    "key": "Hydroxyurea (Hydrine)",
    "name": "Hydrine",
    "inn": "Hydroxyurea 500mg",
    "verdict": "데이터 부족",
    "vt": "no"
  },
  {
    "key": "Rosuvastatin (Rosumeg)",
    "name": "Rosumeg Combigel",
    "inn": "Rosuvastatin+Omega-3-EE90",
    "verdict": "검토 필요",
    "vt": "warn"
  },
  {
    "key": "Atorvastatin (Atmeg)",
    "name": "Atmeg Combigel",
    "inn": "Atorvastatin+Omega-3-EE90",
    "verdict": "검토 필요",
    "vt": "warn"
  },
  {
    "key": "Cilostazol (Ciloduo)",
    "name": "Ciloduo",
    "inn": "Cilostazol+Rosuvastatin",
    "verdict": "검토 필요",
    "vt": "warn"
  },
  {
    "key": "Mosapride (Gastiin)",
    "name": "Gastiin CR",
    "inn": "Mosapride Citrate 15mg",
    "verdict": "데이터 부족",
    "vt": "no"
  }
] as const;

// ── 제품 데이터 (원본 3개 파일 집계) ─────────────────────────

export const PRODUCT_DATA: Record<string, ProductEntry> = {
  "Omega-3 (Omethyl)": {
    "drug_name": "Omethyl Cutielet",
    "inn": "Omega-3-EE90 2g",
    "strength": "disulfiram 500 mg",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.99,
    "verdict": "적합",
    "verdict_type": "ok",
    "ogyei": 327,
    "ogyei_shortage": 0,
    "neak_count": 33,
    "neak_range": "1.77 ~ 1000.21",
    "ema": "EMA medicines 매칭 21건",
    "patikaradar": "국제 가격 비교 리스트 매칭 33건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  },
  "Gadobutrol (Gadvoa)": {
    "drug_name": "Gadvoa Inj.",
    "inn": "Gadobutrol 604.72mg",
    "strength": "gadobutrol 9070,8 mg",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.8,
    "verdict": "검토 필요",
    "verdict_type": "warn",
    "ogyei": 5,
    "ogyei_shortage": 0,
    "neak_count": 3,
    "neak_range": "40.94 ~ 149.26",
    "ema": "EMA medicines 매칭 0건",
    "patikaradar": "국제 가격 비교 리스트 매칭 3건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  },
  "Fluticasone+Salmeterol (Sereterol)": {
    "drug_name": "Sereterol Activair",
    "inn": "Fluticasone+Salmeterol",
    "strength": "fluticasone 0,05 mg",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.99,
    "verdict": "적합",
    "verdict_type": "ok",
    "ogyei": 115,
    "ogyei_shortage": 0,
    "neak_count": 40,
    "neak_range": "2.79 ~ 55.66",
    "ema": "EMA medicines 매칭 12건",
    "patikaradar": "국제 가격 비교 리스트 매칭 40건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  },
  "Hydroxyurea (Hydrine)": {
    "drug_name": "Hydrine",
    "inn": "Hydroxyurea 500mg",
    "strength": "-",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.45,
    "verdict": "데이터 부족",
    "verdict_type": "no",
    "ogyei": 0,
    "ogyei_shortage": 0,
    "neak_count": 0,
    "neak_range": "-",
    "ema": "EMA medicines 매칭 0건",
    "patikaradar": "국제 가격 비교 리스트 매칭 0건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  },
  "Rosuvastatin (Rosumeg)": {
    "drug_name": "Rosumeg Combigel",
    "inn": "Rosuvastatin+Omega-3-EE90",
    "strength": "rosuvastatin 10 mg",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.8,
    "verdict": "검토 필요",
    "verdict_type": "warn",
    "ogyei": 559,
    "ogyei_shortage": 0,
    "neak_count": 93,
    "neak_range": "1.20 ~ 27.86",
    "ema": "EMA medicines 매칭 0건",
    "patikaradar": "국제 가격 비교 리스트 매칭 93건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  },
  "Atorvastatin (Atmeg)": {
    "drug_name": "Atmeg Combigel",
    "inn": "Atorvastatin+Omega-3-EE90",
    "strength": "atorvastatin 40 mg",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.8,
    "verdict": "검토 필요",
    "verdict_type": "warn",
    "ogyei": 232,
    "ogyei_shortage": 0,
    "neak_count": 51,
    "neak_range": "1.05 ~ 17.15",
    "ema": "EMA medicines 매칭 0건",
    "patikaradar": "국제 가격 비교 리스트 매칭 51건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  },
  "Cilostazol (Ciloduo)": {
    "drug_name": "Ciloduo",
    "inn": "Cilostazol+Rosuvastatin",
    "strength": "cilostazol 100 mg",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.8,
    "verdict": "검토 필요",
    "verdict_type": "warn",
    "ogyei": 19,
    "ogyei_shortage": 0,
    "neak_count": 5,
    "neak_range": "6.66 ~ 11.83",
    "ema": "EMA medicines 매칭 0건",
    "patikaradar": "국제 가격 비교 리스트 매칭 5건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  },
  "Mosapride (Gastiin)": {
    "drug_name": "Gastiin CR",
    "inn": "Mosapride Citrate 15mg",
    "strength": "-",
    "hs_code": "-",
    "channel": "병원/약국/조달 (원본 파일 기준)",
    "confidence": 0.45,
    "verdict": "데이터 부족",
    "verdict_type": "no",
    "ogyei": 0,
    "ogyei_shortage": 0,
    "neak_count": 0,
    "neak_range": "-",
    "ema": "EMA medicines 매칭 0건",
    "patikaradar": "국제 가격 비교 리스트 매칭 0건",
    "pubmed": "제공 3개 파일에는 PubMed 원문 메타 없음",
    "strategy": "세 파일 기준으로 허가·가격·등록 데이터가 확인된 범위에서 단계별 진입 전략 수립",
    "risk": "원본 파일 매칭 건수/성분 표기 차이에 따라 추가 검증 필요"
  }
};

// ── 경쟁사/가격 데이터 ───────────────────────────────────────

export const COMPETITOR_DATA: Record<string, CompetitorEntry> = {
  "Omega-3 (Omethyl)": {
    "total_products": 33,
    "total_companies": 13,
    "price_min": 1.7689036889271026,
    "price_max": 1000.2081536901541,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "하위 25%~중앙값 구간에서 포지셔닝 권장",
    "competitors": [
      {
        "rank": 1,
        "company": "roche registration gmbh",
        "min": 87.83862683701004,
        "max": 343.0230244143926,
        "products": 6,
        "sample": "mircera 50 mikrogramm/0,3 ml oldatos injekció előretöltött fecskendőben",
        "status": "참고"
      },
      {
        "rank": 2,
        "company": "pfizer gyógyszerkereskedelmi korlátolt felelősségű társaság",
        "min": 6.062904033497879,
        "max": 24.684489846387574,
        "products": 5,
        "sample": "medrol 4 mg tabletta",
        "status": "참고"
      },
      {
        "rank": 3,
        "company": "sandoz pharmaceuticals gmbh",
        "min": 1.7689036889271026,
        "max": 3.201127823768382,
        "products": 4,
        "sample": "ospen 1 000 000 ne filmtabletta",
        "status": "참고"
      },
      {
        "rank": 4,
        "company": "teva gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 12.727021556434728,
        "max": 355.79547099002934,
        "products": 3,
        "sample": "metilprednizolon-teva 40 mg por oldatos injekcióhoz",
        "status": "참고"
      },
      {
        "rank": 5,
        "company": "stada arzneimittel aktiengesellschaft",
        "min": 91.01837818115392,
        "max": 355.7927989300763,
        "products": 2,
        "sample": "dimetil-fumarát stada 120 mg gyomornedv-ellenálló kemény kapszula",
        "status": "참고"
      },
      {
        "rank": 6,
        "company": "richter gedeon vegyészeti gyár nyilvánosan működő részvénytársaság",
        "min": 123.16593147644392,
        "max": 484.3562915117056,
        "products": 2,
        "sample": "dimethyl fumarate gedeon richter 240 mg gyomornedv-ellenálló kemény kapszula",
        "status": "참고"
      },
      {
        "rank": 7,
        "company": "egis gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 130.270938891636,
        "max": 509.70612428640567,
        "products": 2,
        "sample": "arbicen 240 mg gyomornedv-ellenálló kemény kapszula",
        "status": "참고"
      }
    ]
  },
  "Gadobutrol (Gadvoa)": {
    "total_products": 3,
    "total_companies": 1,
    "price_min": 40.94397466077039,
    "price_max": 149.26126897804826,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "하위 25%~중앙값 구간에서 포지셔닝 권장",
    "competitors": [
      {
        "rank": 1,
        "company": "bayer aktiengesellschaft",
        "min": 40.94397466077039,
        "max": 149.26126897804826,
        "products": 3,
        "sample": "gadovist 1,0 mmol/ml oldatos injekció",
        "status": "참고"
      }
    ]
  },
  "Fluticasone+Salmeterol (Sereterol)": {
    "total_products": 40,
    "total_companies": 10,
    "price_min": 2.7896305909968206,
    "price_max": 55.659008822283305,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "하위 25%~중앙값 구간에서 포지셔닝 권장",
    "competitors": [
      {
        "rank": 1,
        "company": "glaxosmithkline trading services limited",
        "min": 2.7896305909968206,
        "max": 55.659008822283305,
        "products": 21,
        "sample": "flixonase szuszpenziós orrspray",
        "status": "참고"
      },
      {
        "rank": 2,
        "company": "sager pharma szolgáltató korlátolt felelősségű társaság",
        "min": 7.652779705569822,
        "max": 22.955667056756404,
        "products": 4,
        "sample": "reviflut axahaler 250 mikrogramm inhalációs por kemény kapszulában",
        "status": "참고"
      },
      {
        "rank": 3,
        "company": "mediner gyógyszerkereskedelmi, marketing és szolgáltató korlátolt felelősségű társaság",
        "min": 17.558105951570983,
        "max": 24.75663546512025,
        "products": 3,
        "sample": "fluzalto airmaster 50 mikrogramm/100 mikrogramm/adag adagolt inhalációs por",
        "status": "참고"
      },
      {
        "rank": 4,
        "company": "viatris healthcare limited",
        "min": 10.290102879242104,
        "max": 16.454545190956342,
        "products": 2,
        "sample": "dymista szuszpenziós orrspray",
        "status": "참고"
      },
      {
        "rank": 5,
        "company": "zentiva k.s.",
        "min": 19.009034506083697,
        "max": 23.658418824411733,
        "products": 2,
        "sample": "sirmin 50 mikrogramm/250 mikrogramm/adag adagolt inhalációs por",
        "status": "참고"
      },
      {
        "rank": 6,
        "company": "orion corporation",
        "min": 20.76457789524549,
        "max": 25.9163094847492,
        "products": 2,
        "sample": "safumix easyhaler 50 mikrogramm/500 mikrogramm/adag, inhalációs por",
        "status": "참고"
      },
      {
        "rank": 7,
        "company": "sandoz hungária kereskedelmi korlátolt felelősségű társaság",
        "min": 21.357775204825273,
        "max": 26.525539154047355,
        "products": 2,
        "sample": "airflusol forspiro 50 mikrogramm/500 mikrogramm/adag adagolt inhalációs por",
        "status": "참고"
      }
    ]
  },
  "Hydroxyurea (Hydrine)": {
    "total_products": 0,
    "total_companies": 0,
    "price_min": null,
    "price_max": null,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "가격 데이터 부족",
    "competitors": []
  },
  "Rosuvastatin (Rosumeg)": {
    "total_products": 93,
    "total_companies": 8,
    "price_min": 1.1970828589718157,
    "price_max": 27.8615691305784,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "하위 25%~중앙값 구간에서 포지셔닝 권장",
    "competitors": [
      {
        "rank": 1,
        "company": "krka tovarna zdravil, d.d.",
        "min": 1.6459889310862466,
        "max": 19.19073458289192,
        "products": 29,
        "sample": "roxera 10 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 2,
        "company": "sandoz hungária kereskedelmi korlátolt felelősségű társaság",
        "min": 1.3680946959677893,
        "max": 27.8615691305784,
        "products": 18,
        "sample": "rosuvastatin sandoz 40 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 3,
        "company": "richter gedeon vegyészeti gyár nyilvánosan működő részvénytársaság",
        "min": 4.098939967997244,
        "max": 16.62021290804619,
        "products": 16,
        "sample": "xeter 10 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 4,
        "company": "teva gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 1.1970828589718157,
        "max": 27.412663058463966,
        "products": 13,
        "sample": "rozuva-teva 5 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 5,
        "company": "egis gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 4.232542965650349,
        "max": 26.26634933860033,
        "products": 9,
        "sample": "delipid 20 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 6,
        "company": "vivanta generics s.r.o.",
        "min": 2.348740698741576,
        "max": 9.13310091956622,
        "products": 3,
        "sample": "rosuvastatin msn 10 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 7,
        "company": "kéri pharma hungary piac- és közvélemény kutató korlátolt felelősségű társaság",
        "min": 2.6720599530620888,
        "max": 9.916014485813411,
        "products": 3,
        "sample": "rosutec 10 mg filmtabletta",
        "status": "참고"
      }
    ]
  },
  "Atorvastatin (Atmeg)": {
    "total_products": 51,
    "total_companies": 10,
    "price_min": 1.050119561553401,
    "price_max": 17.154624898658607,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "하위 25%~중앙값 구간에서 포지셔닝 권장",
    "competitors": [
      {
        "rank": 1,
        "company": "krka tovarna zdravil, d.d.",
        "min": 1.6486609910393086,
        "max": 17.151952838705547,
        "products": 10,
        "sample": "atoris 10 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 2,
        "company": "richter gedeon vegyészeti gyár nyilvánosan működő részvénytársaság",
        "min": 1.7689036889271026,
        "max": 9.325489236186689,
        "products": 8,
        "sample": "amlator 20 mg/10 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 3,
        "company": "egis gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 5.405577285044605,
        "max": 14.947503377429324,
        "products": 5,
        "sample": "valongix 10 mg/5 mg/5 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 4,
        "company": "teva gmbh",
        "min": 1.050119561553401,
        "max": 7.40695018988811,
        "products": 4,
        "sample": "atorvastatin teva gmbh 10 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 5,
        "company": "teva gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 1.1089048805207669,
        "max": 7.781038583316802,
        "products": 4,
        "sample": "atorvastatin-teva 80 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 6,
        "company": "holsten pharma gmbh",
        "min": 1.1249372402391393,
        "max": 10.370264677833966,
        "products": 4,
        "sample": "atorvastatin rivopharm 10 mg filmtabletta",
        "status": "참고"
      },
      {
        "rank": 7,
        "company": "zentiva k.s.",
        "min": 1.5818594922127565,
        "max": 6.541202765095993,
        "products": 4,
        "sample": "torvalipin 10 mg filmtabletta",
        "status": "참고"
      }
    ]
  },
  "Cilostazol (Ciloduo)": {
    "total_products": 5,
    "total_companies": 4,
    "price_min": 6.664117522936849,
    "price_max": 11.831881472158928,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "하위 25%~중앙값 구간에서 포지셔닝 권장",
    "competitors": [
      {
        "rank": 1,
        "company": "egis gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 7.249298652657447,
        "max": 11.831881472158928,
        "products": 2,
        "sample": "noclaud 50 mg tabletta",
        "status": "참고"
      },
      {
        "rank": 2,
        "company": "teva gyógyszergyár zártkörűen működő részvénytársaság",
        "min": 6.664117522936849,
        "max": 6.664117522936849,
        "products": 1,
        "sample": "cilostazol-teva 100 mg tabletta",
        "status": "참고"
      },
      {
        "rank": 3,
        "company": "adamed pharma spolka akcyjna",
        "min": 7.12638389481659,
        "max": 7.12638389481659,
        "products": 1,
        "sample": "cilozek 100 mg tabletta",
        "status": "참고"
      },
      {
        "rank": 4,
        "company": "richter gedeon vegyészeti gyár nyilvánosan működő részvénytársaság",
        "min": 7.783710643269864,
        "max": 7.783710643269864,
        "products": 1,
        "sample": "antaclast 100 mg tabletta",
        "status": "참고"
      }
    ]
  },
  "Mosapride (Gastiin)": {
    "total_products": 0,
    "total_companies": 0,
    "price_min": null,
    "price_max": null,
    "note": "DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx 기준 집계",
    "recommended_price": "가격 데이터 부족",
    "competitors": []
  }
};

// ── 정적 표시 데이터 ────────────────────────────────────────

export const STATIC_DATA: Record<string, StaticEntry> = {
  "Omega-3 (Omethyl)": {
    "ema": {
      "count": 21,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 327,
      "shortage": 0
    },
    "neak": {
      "count": 33,
      "range": "1.77 ~ 1000.21"
    },
    "patikaradar": [
      {
        "pharmacy": "antaethyl 500 mg tabletta",
        "price": "4.005417869640071"
      },
      {
        "pharmacy": "medrol 4 mg tabletta",
        "price": "6.062904033497879"
      },
      {
        "pharmacy": "medrol 16 mg tabletta",
        "price": "7.989459259655645"
      },
      {
        "pharmacy": "medrol 32 mg tabletta",
        "price": "8.018851919139328"
      },
      {
        "pharmacy": "medrol 100 mg tabletta",
        "price": "24.684489846387574"
      },
      {
        "pharmacy": "ospen 1 000 000 ne filmtabletta",
        "price": "2.3727892383191347"
      },
      {
        "pharmacy": "ospen 1 500 000 ne filmtabletta",
        "price": "3.201127823768382"
      },
      {
        "pharmacy": "ospen 400 000 ne/5 ml belsőleges szuszpenzió",
        "price": "2.322020099210955"
      },
      {
        "pharmacy": "ospen 500 000 ne filmtabletta",
        "price": "1.7689036889271026"
      },
      {
        "pharmacy": "tabletta antidolorica fono viii. parma",
        "price": "3.5458235577133914"
      }
    ],
    "pubmed": [
      {
        "pmid": "EMA",
        "title": "Vazkepa",
        "journal": "C10AX",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/vazkepa"
      },
      {
        "pmid": "EMA",
        "title": "Relistor",
        "journal": "A06AH01",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/relistor"
      },
      {
        "pmid": "EMA",
        "title": "Tuzulby",
        "journal": "N06BA04",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/tuzulby"
      },
      {
        "pmid": "EMA",
        "title": "Methylthioninium chloride Proveblue",
        "journal": "V03AB17",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/methylthioninium-chloride-proveblue"
      },
      {
        "pmid": "EMA",
        "title": "Xermelo",
        "journal": "A16A",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/xermelo"
      },
      {
        "pmid": "EMA",
        "title": "Spexotras",
        "journal": "L01EE01",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/spexotras"
      }
    ],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  },
  "Gadobutrol (Gadvoa)": {
    "ema": {
      "count": 0,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 5,
      "shortage": 0
    },
    "neak": {
      "count": 3,
      "range": "40.94 ~ 149.26"
    },
    "patikaradar": [
      {
        "pharmacy": "gadovist 1,0 mmol/ml oldatos injekció",
        "price": "77.54852395776794"
      },
      {
        "pharmacy": "gadovist 1,0 mmol/ml oldatos injekció",
        "price": "40.94397466077039"
      },
      {
        "pharmacy": "gadovist 1,0 mmol/ml oldatos injekció",
        "price": "149.26126897804826"
      }
    ],
    "pubmed": [],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  },
  "Fluticasone+Salmeterol (Sereterol)": {
    "ema": {
      "count": 12,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 115,
      "shortage": 0
    },
    "neak": {
      "count": 40,
      "range": "2.79 ~ 55.66"
    },
    "patikaradar": [
      {
        "pharmacy": "flixonase szuszpenziós orrspray",
        "price": "6.725574901857277"
      },
      {
        "pharmacy": "cutivate 0,05 mg/g kenőcs",
        "price": "2.7896305909968206"
      },
      {
        "pharmacy": "cutivate 0,5 mg/g krém",
        "price": "2.7896305909968206"
      },
      {
        "pharmacy": "serevent diskus 50 mikrogramm/adag adagolt inhalációs por",
        "price": "17.256163176874967"
      },
      {
        "pharmacy": "flixotide diskus 100 mikrogramm/adag adagolt inhalációs por",
        "price": "5.905252496267216"
      },
      {
        "pharmacy": "flixotide diskus 250 mikrogramm/adag adagolt inhalációs por",
        "price": "12.569370019204065"
      },
      {
        "pharmacy": "flixotide diskus 500 mikrogramm/adag adagolt inhalációs por",
        "price": "25.40594603371434"
      },
      {
        "pharmacy": "seretide diskus 50/250 mikrogramm/adag adagolt inhalációs por",
        "price": "25.005137040755024"
      },
      {
        "pharmacy": "seretide diskus 50/500 mikrogramm/adag adagolt inhalációs por",
        "price": "28.387964941331628"
      },
      {
        "pharmacy": "seretide diskus 50/100 mikrogramm/adag adagolt inhalációs por",
        "price": "21.817369516751953"
      }
    ],
    "pubmed": [
      {
        "pmid": "EMA",
        "title": "Seffalair Spiromax",
        "journal": "R03AK06",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/seffalair-spiromax"
      },
      {
        "pmid": "EMA",
        "title": "BroPair Spiromax",
        "journal": "R03AK06",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/bropair-spiromax"
      },
      {
        "pmid": "EMA",
        "title": "Avamys",
        "journal": "R01AD12",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/avamys"
      },
      {
        "pmid": "EMA",
        "title": "Elebrato Ellipta",
        "journal": "R03AL08",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/elebrato-ellipta"
      },
      {
        "pmid": "EMA",
        "title": "Trelegy Ellipta",
        "journal": "R03AL08",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/trelegy-ellipta"
      },
      {
        "pmid": "EMA",
        "title": "Relvar Ellipta",
        "journal": "R03AK10",
        "finding": "https://www.ema.europa.eu/en/medicines/human/EPAR/relvar-ellipta"
      }
    ],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  },
  "Hydroxyurea (Hydrine)": {
    "ema": {
      "count": 0,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 0,
      "shortage": 0
    },
    "neak": {
      "count": 0,
      "range": "-"
    },
    "patikaradar": [],
    "pubmed": [],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  },
  "Rosuvastatin (Rosumeg)": {
    "ema": {
      "count": 0,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 559,
      "shortage": 0
    },
    "neak": {
      "count": 93,
      "range": "1.20 ~ 27.86"
    },
    "patikaradar": [
      {
        "pharmacy": "xeter 10 mg filmtabletta",
        "price": "4.141692927246237"
      },
      {
        "pharmacy": "xeter 40 mg filmtabletta",
        "price": "10.530588275017692"
      },
      {
        "pharmacy": "xeter 20 mg filmtabletta",
        "price": "6.608004263922545"
      },
      {
        "pharmacy": "rosuvastatin sandoz 40 mg filmtabletta",
        "price": "19.500693537447123"
      },
      {
        "pharmacy": "rosuvastatin sandoz 40 mg filmtabletta",
        "price": "9.560630512056154"
      },
      {
        "pharmacy": "rosuvastatin sandoz 20 mg filmtabletta",
        "price": "12.28345960422642"
      },
      {
        "pharmacy": "rosuvastatin sandoz 20 mg filmtabletta",
        "price": "5.85982747706516"
      },
      {
        "pharmacy": "rosuvastatin sandoz 10 mg filmtabletta",
        "price": "6.02549519415501"
      },
      {
        "pharmacy": "rosuvastatin sandoz 10 mg filmtabletta",
        "price": "2.883152689353994"
      },
      {
        "pharmacy": "rosuvastatin sandoz 5 mg filmtabletta",
        "price": "1.3680946959677893"
      }
    ],
    "pubmed": [],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  },
  "Atorvastatin (Atmeg)": {
    "ema": {
      "count": 0,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 232,
      "shortage": 0
    },
    "neak": {
      "count": 51,
      "range": "1.05 ~ 17.15"
    },
    "patikaradar": [
      {
        "pharmacy": "sortis 40 mg filmtabletta",
        "price": "12.799167175167405"
      },
      {
        "pharmacy": "atoris 10 mg filmtabletta",
        "price": "3.524447078088895"
      },
      {
        "pharmacy": "atorvastatin rivopharm 10 mg filmtabletta",
        "price": "3.334730821421487"
      },
      {
        "pharmacy": "atorvastatin rivopharm 20 mg filmtabletta",
        "price": "1.1249372402391393"
      },
      {
        "pharmacy": "atorvastatin rivopharm 40 mg filmtabletta",
        "price": "6.501121865800061"
      },
      {
        "pharmacy": "atorvastatin rivopharm 80 mg filmtabletta",
        "price": "10.370264677833966"
      },
      {
        "pharmacy": "atoris 40 mg filmtabletta",
        "price": "6.746951381481773"
      },
      {
        "pharmacy": "atorvastatin hexal 40 mg filmtabletta",
        "price": "6.51181010561231"
      },
      {
        "pharmacy": "atorvastatin hexal 10 mg filmtabletta",
        "price": "1.6807257104760538"
      },
      {
        "pharmacy": "atorvastatin hexal 20 mg filmtabletta",
        "price": "1.6566771708984949"
      }
    ],
    "pubmed": [],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  },
  "Cilostazol (Ciloduo)": {
    "ema": {
      "count": 0,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 19,
      "shortage": 0
    },
    "neak": {
      "count": 5,
      "range": "6.66 ~ 11.83"
    },
    "patikaradar": [
      {
        "pharmacy": "cilostazol-teva 100 mg tabletta",
        "price": "6.664117522936849"
      },
      {
        "pharmacy": "noclaud 50 mg tabletta",
        "price": "11.831881472158928"
      },
      {
        "pharmacy": "noclaud 100 mg tabletta",
        "price": "7.249298652657447"
      },
      {
        "pharmacy": "cilozek 100 mg tabletta",
        "price": "7.12638389481659"
      },
      {
        "pharmacy": "antaclast 100 mg tabletta",
        "price": "7.783710643269864"
      }
    ],
    "pubmed": [],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  },
  "Mosapride (Gastiin)": {
    "ema": {
      "count": 0,
      "note": "medicines-output-medicines-report_en (1).xlsx"
    },
    "ogyei": {
      "count": 0,
      "shortage": 0
    },
    "neak": {
      "count": 0,
      "range": "-"
    },
    "patikaradar": [],
    "pubmed": [],
    "condition": [
      "데이터 소스: DRUG_LIST_FOR_INTERNATIONAL_PRICE_COMPARISON_20250714.xlsx",
      "데이터 소스: medicines-output-medicines-report_en (1).xlsx",
      "데이터 소스: tk_lista.csv"
    ],
    "reject": []
  }
};

export const VT: Record<string, string> = {
  ok: "bg-emerald-100 text-emerald-700 border border-emerald-200",
  warn: "bg-amber-100 text-amber-700 border border-amber-200",
  no: "bg-slate-100 text-slate-700 border border-slate-200",
};

export const VERDICT_KO: Record<string, string> = {
  ok: "적합",
  warn: "검토 필요",
  no: "데이터 부족",
};

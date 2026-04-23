/**
 * datas/lib/data.ts 번들(HUNGARY_EXPORT) — 헝가리 페이지(hu-*) · index 시장조사 탭(sm-*) 공용
 */
'use strict';

function _escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** @param {'hu'|'sm'} scope */
function _dom(scope) {
  const p = scope === 'sm' ? 'sm' : 'hu';
  return {
    verdictName: p + '-verdict-name',
    verdictInn: p + '-verdict-inn',
    summary: p + '-product-summary',
    badge: p + '-verdict-badge',
    tlRed: p + '-tl-red',
    tlYel: p + '-tl-yellow',
    tlGrn: p + '-tl-green',
    cardProduct: p + '-card-product-body',
    cardCompetitor: p + '-card-competitor-body',
    cardStatic: p + '-card-static-body',
    select: p + '-product-select',
    tabs: p + '-product-tabs',
  };
}

function _huVerdictBadgeClass(vt) {
  if (vt === 'ok') return 'verdict-badge v-ok';
  if (vt === 'warn') return 'verdict-badge v-warn';
  if (vt === 'no') return 'verdict-badge v-err';
  return 'verdict-badge v-none';
}

function _huTrafficLights(vt, scope) {
  const d = _dom(scope);
  const red = document.getElementById(d.tlRed);
  const yel = document.getElementById(d.tlYel);
  const grn = document.getElementById(d.tlGrn);
  if (!red || !yel || !grn) return;
  red.classList.remove('on');
  yel.classList.remove('on');
  grn.classList.remove('on');
  if (vt === 'no') red.classList.add('on');
  else if (vt === 'warn') yel.classList.add('on');
  else if (vt === 'ok') grn.classList.add('on');
}

function _huProductRows(pe) {
  const rows = [
    ['품목명', pe.drug_name],
    ['성분', pe.inn],
    ['함량·제형', pe.strength],
    ['HS 코드', pe.hs_code],
    ['채널', pe.channel],
    ['신뢰도', String(pe.confidence)],
    ['상태 요약', pe.verdict],
    ['허가·등재 건수 (참고)', String(pe.ogyei)],
    ['공급·조달 이슈 건수 (참고)', String(pe.ogyei_shortage)],
    ['조달·포털 레퍼런스 건수 (참고)', String(pe.neak_count)],
    ['조달 가격 레인지 (참고)', pe.neak_range],
    ['EMA / 중앙허가 참고', pe.ema],
    ['현지 유통·소매 참고가', pe.patikaradar],
    ['근거 문헌', pe.pubmed],
    ['전략', pe.strategy],
    ['리스크', pe.risk],
  ];
  return rows
    .map(
      ([k, v]) =>
        `<div class="irow"><div class="tit">${_escapeHtml(k)}</div><div class="sub">${_escapeHtml(v)}</div></div>`
    )
    .join('');
}

function _huCompetitorHtml(ce) {
  const priceRange =
    ce.price_min != null && ce.price_max != null
      ? `${ce.price_min} ~ ${ce.price_max} EUR`
      : '—';
  let html = `
    <div class="irow"><div class="tit">요약</div><div class="sub">${_escapeHtml(ce.note)}</div></div>
    <div class="irow-row" style="margin-bottom:10px;">
      <div><span class="basis-label">총 품목</span><div class="basis-value">${ce.total_products}</div></div>
      <div><span class="basis-label">회사 수</span><div class="basis-value">${ce.total_companies}</div></div>
      <div><span class="basis-label">가격대</span><div class="basis-value">${_escapeHtml(priceRange)}</div></div>
    </div>
    <div class="irow"><div class="tit">추천 포지션</div><div class="sub">${_escapeHtml(ce.recommended_price)}</div></div>`;

  if (ce.competitors && ce.competitors.length) {
    html +=
      `<div class="p2-dist-title" style="margin-top:12px;">경쟁사 (NEAK DIPC)</div>` +
      `<table class="p2-prod-table"><thead><tr>` +
      `<th>순위</th><th>회사</th><th>Min</th><th>Max</th><th>품목수</th><th>샘플</th><th>비고</th>` +
      `</tr></thead><tbody>` +
      ce.competitors
        .map(
          (c) =>
            `<tr><td>${c.rank}</td><td>${_escapeHtml(c.company)}</td>` +
            `<td>${c.min}</td><td>${c.max}</td><td>${c.products}</td>` +
            `<td>${_escapeHtml(c.sample)}</td><td>${_escapeHtml(c.status)}</td></tr>`
        )
        .join('') +
      `</tbody></table>`;
  } else {
    html += `<div class="p3-empty-cell" style="padding:16px 0;">등록된 경쟁사 행이 없습니다.</div>`;
  }
  return html;
}

function _huStaticHtml(se) {
  let html = `
    <div class="macro-grid" style="margin-bottom:10px;">
      <div class="macro-card">
        <div class="macro-label">EMA</div>
        <div class="macro-value" style="font-size:18px;">${se.ema.count}</div>
        <div class="macro-source">${_escapeHtml(se.ema.note)}</div>
      </div>
      <div class="macro-card">
        <div class="macro-label">OGYEI</div>
        <div class="macro-value" style="font-size:18px;">${se.ogyei.count}</div>
        <div class="macro-source">부족 ${se.ogyei.shortage}</div>
      </div>
      <div class="macro-card">
        <div class="macro-label">NEAK</div>
        <div class="macro-value" style="font-size:18px;">${se.neak.count}</div>
        <div class="macro-source">${_escapeHtml(se.neak.range)}</div>
      </div>
    </div>`;

  if (se.patikaradar && se.patikaradar.length) {
    html += `<div class="basis-label" style="margin-bottom:8px;">PatikaRadar (약국가)</div>`;
    html += `<table class="p2-prod-table"><thead><tr><th>약국</th><th>가격 (HUF)</th></tr></thead><tbody>`;
    html += se.patikaradar
      .map((p) => `<tr><td>${_escapeHtml(p.pharmacy)}</td><td>${_escapeHtml(p.price)}</td></tr>`)
      .join('');
    html += `</tbody></table>`;
  }

  if (se.pubmed && se.pubmed.length) {
    html += `<div class="basis-label" style="margin:14px 0 8px;">PubMed</div><div class="basis-grid">`;
    html += se.pubmed
      .map(
        (p) =>
          `<div class="basis-item"><div class="basis-label">PMID ${_escapeHtml(p.pmid)}</div>` +
          `<div class="basis-value"><strong>${_escapeHtml(p.title)}</strong> · ${_escapeHtml(p.journal)}` +
          `<br/>${_escapeHtml(p.finding)}</div></div>`
      )
      .join('');
    html += `</div>`;
  }

  if (se.condition && se.condition.length) {
    html += `<div class="basis-label" style="margin:14px 0 6px;">조건·주의</div>`;
    html += se.condition.map((t) => `<div class="irow"><div class="sub">${_escapeHtml(t)}</div></div>`).join('');
  }
  if (se.reject && se.reject.length) {
    html += `<div class="basis-label" style="margin:14px 0 6px;">불가·거절 근거</div>`;
    html += se.reject.map((t) => `<div class="irow"><div class="sub">${_escapeHtml(t)}</div></div>`).join('');
  }

  return html;
}

function huRenderCards(productKey, scope) {
  const X = window.HUNGARY_EXPORT;
  if (!X) return;
  const d = _dom(scope);

  const pe = X.PRODUCT_DATA[productKey];
  const ce = X.COMPETITOR_DATA[productKey];
  const se = X.STATIC_DATA[productKey];
  const meta = X.PRODUCTS.find((p) => p.key === productKey);

  const nameEl = document.getElementById(d.verdictName);
  const innEl = document.getElementById(d.verdictInn);
  const sumEl = document.getElementById(d.summary);
  const badgeEl = document.getElementById(d.badge);

  if (!pe || !ce || !se) {
    if (nameEl) nameEl.textContent = '—';
    if (innEl) innEl.textContent = '';
    if (sumEl) sumEl.textContent = '';
    if (badgeEl) {
      badgeEl.textContent = '데이터 없음';
      badgeEl.className = 'verdict-badge v-none';
    }
    _huTrafficLights('', scope);
    const cp = document.getElementById(d.cardProduct);
    const cc = document.getElementById(d.cardCompetitor);
    const cs = document.getElementById(d.cardStatic);
    if (cp) cp.innerHTML = '';
    if (cc) cc.innerHTML = '';
    if (cs) cs.innerHTML = '';
    return;
  }

  if (nameEl) nameEl.textContent = pe.drug_name || '—';
  if (innEl) innEl.textContent = meta ? `${meta.inn}` : pe.inn || '';
  if (sumEl) sumEl.textContent = `HS ${pe.hs_code} · ${pe.channel}`;

  const vt = pe.verdict_type;
  const vk = (X.VERDICT_KO && X.VERDICT_KO[vt]) || pe.verdict;

  if (badgeEl) {
    badgeEl.className = _huVerdictBadgeClass(vt);
    badgeEl.textContent = vk;
  }
  _huTrafficLights(vt, scope);

  const cp = document.getElementById(d.cardProduct);
  const cc = document.getElementById(d.cardCompetitor);
  const cs = document.getElementById(d.cardStatic);
  if (cp) cp.innerHTML = _huProductRows(pe);
  if (cc) cc.innerHTML = _huCompetitorHtml(ce);
  if (cs) cs.innerHTML = _huStaticHtml(se);

  document.querySelectorAll(`#${d.tabs} .p2-tab-btn`).forEach((btn) => {
    btn.classList.toggle('on', btn.getAttribute('data-key') === productKey);
  });

  const sel = document.getElementById(d.select);
  if (sel && sel.value !== productKey) sel.value = productKey;
}

function huSelectProduct(key, scope) {
  huRenderCards(key, scope);
}

/** @param {'hu'|'sm'} scope */
function huInitStaticMarket(scope) {
  const X = window.HUNGARY_EXPORT;
  const d = _dom(scope);
  const tabs = document.getElementById(d.tabs);
  const sel = document.getElementById(d.select);
  if (!X || !X.PRODUCTS || !tabs || !sel) return;

  tabs.innerHTML = '';
  sel.innerHTML = '';

  X.PRODUCTS.forEach((p) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'p2-tab-btn';
    b.setAttribute('data-key', p.key);
    b.textContent = p.name;
    b.onclick = () => huSelectProduct(p.key, scope);
    tabs.appendChild(b);

    const opt = document.createElement('option');
    opt.value = p.key;
    opt.textContent = `${p.name} · ${p.inn}`;
    sel.appendChild(opt);
  });

  sel.onchange = () => huSelectProduct(sel.value, scope);

  huSelectProduct(X.PRODUCTS[0].key, scope);
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('hu-product-select')) huInitStaticMarket('hu');
  if (document.getElementById('sm-product-select')) huInitStaticMarket('sm');
});

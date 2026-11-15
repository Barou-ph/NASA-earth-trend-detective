// CYCLE drawer: how the seasonal swing (amplitude) of temperature, AOD and NO2 changes, monthly or yearly, plus the correlations worth looking at.
// Amplitude data: /api/cycle (computed live). Correlations: /api/correlations (computed by the preprocessing module scripts/prepare_hcm_data.py, only served here).
(function () {
  Object.assign(T.vi, {
    nCycle: "So sánh chu kỳ", cyEyebrow: "Biên độ theo chu kỳ", cyTitle: "Chu kỳ và tương quan",
    cyLead: "Biên độ là chênh lệch giữa tháng cao nhất và thấp nhất trong năm. So sánh biên độ giữa hai nửa giai đoạn, hoặc theo từng năm, cho thấy mức dao động theo mùa đang tăng hay giảm.",
    cyMonth: "Chu kỳ tháng", cyYear: "Chu kỳ năm", cyLoad: "Đang tính chu kỳ từ dữ liệu NASA…",
    cyNorm: "Chu kỳ tháng đã chuẩn hoá (giai đoạn sau, 0 = thấp nhất, 1 = cao nhất của chính chỉ số đó)", cyNormHint: "Đỉnh các đường lệch nhau bao nhiêu tháng cho biết chỉ số nào đến trước, gợi ý cặp có thể liên quan.",
    cyEarly: "Giai đoạn đầu", cyLate: "Giai đoạn sau", cyAmp: "Biên độ", cyChange: "Thay đổi", cyTrend: "Xu hướng biên độ theo năm",
    cyPeak: "Tháng cao nhất", cyMonthShort: m => "T" + m, cyNoAmp: (n) => `Chỉ có ${n}/12 tháng đủ dữ liệu ở một giai đoạn (thường thiếu mùa mưa), nên không tính biên độ.`,
    cyTrendTxt: (s, u, p, sig) => `Biên độ từng năm ${s >= 0 ? "tăng" : "giảm"} ${Math.abs(s).toPrecision(2)}${u ? " " + u : ""}/năm (Mann-Kendall p = ${p.toFixed(2)}): ${sig ? "có ý nghĩa" : "chưa đủ chắc"}.`,
    cyChangeTxt: (a, b, c, u) => `Biên độ ${a.toPrecision(3)} → ${b.toPrecision(3)}${u ? " " + u : ""} (${c >= 0 ? "+" : ""}${c.toFixed(0)}%)`,
    cyOnlyHcm: "AOD và NO₂ hiện chỉ có cho TP.HCM; thành phố này chỉ có nhiệt độ.", cyCorrTitle: "Tương quan giữa các biến", cyCorrNone: "Chưa cặp nào vượt ngưỡng (q < 0,05 và |r| ≥ 0,3) sau hiệu chỉnh nhiều phép thử.",
    cyCand: "Ứng viên tương quan", cyWeak: "Gợi ý yếu (chưa vượt hiệu chỉnh)", cyNone: "Không thấy tương quan", cyLag: "độ trễ", cyMonths: "tháng", cyAgree: "khớp chiều dự kiến", cyDisagree: "ngược chiều dự kiến",
    cyBy: d => `Do module tiền xử lý tính (scripts/prepare_hcm_data.py), cập nhật ${d}.`, cyErr: "Không tải được: ", cyCorrOnly: "Tương quan chỉ tính cho TP.HCM (nơi có đủ AOD và NO₂).", cyYears: "năm",
    cyInd: "Chỉ số"
  });
  Object.assign(T.en, {
    nCycle: "Compare cycles", cyEyebrow: "Amplitude by cycle", cyTitle: "Cycles and correlation",
    cyLead: "Amplitude is the gap between the highest and lowest month of the year. Comparing it between two halves of the period, or year by year, shows whether the seasonal swing is growing or shrinking.",
    cyMonth: "Monthly cycle", cyYear: "Yearly cycle", cyLoad: "Computing cycles from NASA data…",
    cyNorm: "Monthly cycle, normalised (later period; 0 = lowest, 1 = highest month of that indicator)", cyNormHint: "How many months the peaks are apart shows which indicator comes first, hinting at pairs that may be related.",
    cyEarly: "Earlier period", cyLate: "Later period", cyAmp: "Amplitude", cyChange: "Change", cyTrend: "Yearly amplitude trend",
    cyPeak: "Peak month", cyMonthShort: m => ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1], cyNoAmp: (n) => `Only ${n}/12 months have enough data in one period (usually the rainy season is missing), so no amplitude is given.`,
    cyTrendTxt: (s, u, p, sig) => `Yearly amplitude ${s >= 0 ? "rises" : "falls"} by ${Math.abs(s).toPrecision(2)}${u ? " " + u : ""}/year (Mann-Kendall p = ${p.toFixed(2)}): ${sig ? "significant" : "not certain"}.`,
    cyChangeTxt: (a, b, c, u) => `Amplitude ${a.toPrecision(3)} → ${b.toPrecision(3)}${u ? " " + u : ""} (${c >= 0 ? "+" : ""}${c.toFixed(0)}%)`,
    cyOnlyHcm: "AOD and NO₂ exist only for HCMC for now; this city has temperature only.", cyCorrTitle: "Correlation between variables", cyCorrNone: "No pair passes the threshold (q < 0.05 and |r| ≥ 0.3) after correcting for many tests.",
    cyCand: "Correlation candidates", cyWeak: "Weak hints (not passing correction)", cyNone: "No correlation seen", cyLag: "lag", cyMonths: "mo", cyAgree: "matches the expected sign", cyDisagree: "opposite to the expected sign",
    cyBy: d => `Computed by the preprocessing module (scripts/prepare_hcm_data.py), updated ${d}.`, cyErr: "Could not load: ", cyCorrOnly: "Correlations are computed for HCMC only (where AOD and NO₂ exist).", cyYears: "yr",
    cyInd: "Indicator"
  });
  const COL = {T2M: "#e9863d", hcm_aod: "#e9b44c", hcm_no2: "#5aa9ff", PRECTOTCORR: "#4fc3b5", WS2M: "#b79cff", RH2M: "#7fd4e8"};
  const color = v => COL[v] || "#8fa1c2";
  let mode = "month", data = null, corr = null, key = "", seq = 0, open = false;
  const PL = {displayModeBar: false, responsive: true};
  const lay = (extra = {}) => Object.assign({paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: {color: "#8fa1c2", size: 11, family: "Inter,system-ui,sans-serif"}, margin: {l: 46, r: 12, t: 8, b: 34},
    xaxis: {gridcolor: "#1c2a47", zeroline: false}, yaxis: {gridcolor: "#1c2a47", zeroline: false}, legend: {orientation: "h", y: 1.18, x: 0}, showlegend: true, height: 220}, extra);
  const place = () => { const c = CITIES.find(x => x.id === pos.city); return c ? cityName(c) : `${pos.lat}, ${pos.lon}`; };
  const vname = (it) => it.name[lang] || it.name.vi;
  const num = (x, d = 3) => x === null || x === undefined ? "–" : (+x).toPrecision(d);

  async function load() {
    const my = ++seq, k = (pos.city || pos.lat + "," + pos.lon) + "|" + lang; const x = t();
    const body = $("cyBody"); body.innerHTML = `<div class="skel"></div>`; $("cyStatus").textContent = x.cyLoad;
    try {
      const q = pos.city ? `city=${pos.city}` : `lat=${pos.lat}&lon=${pos.lon}`;
      const vars = pos.city === "hcm" ? "T2M,hcm_aod,hcm_no2" : "T2M";
      const [d, c] = await Promise.all([api(`/api/cycle?${q}&vars=${vars}&start=2004&end=2025`), pos.city === "hcm" ? api("/api/correlations").catch(() => null) : Promise.resolve(null)]);
      if (my !== seq) return; data = d; corr = c; key = k; $("cyStatus").textContent = ""; render();
    } catch (e) { if (my === seq) { $("cyStatus").textContent = ""; body.innerHTML = `<div class="empty">${esc(x.cyErr + e.message)}</div>`; } }
  }
  const sumRow = it => {
    const x = t(), e = it.early, l = it.late, tr = it.amp_trend;
    return `<tr><td><i class="dot" style="background:${color(it.var)}"></i>${esc(vname(it))}</td><td class="num">${num(e.amp)}</td><td class="num">${num(l.amp)}</td>
      <td class="num">${it.amp_change_pct === null ? "–" : (it.amp_change_pct >= 0 ? "+" : "") + it.amp_change_pct.toFixed(0) + "%"}</td>
      <td class="num">${tr ? (tr.sig ? "●" : "○") + " p " + tr.p.toFixed(2) : "–"}</td></tr>`;
  };
  function monthChart(div, it) {
    const x = t(), mm = Array.from({length: 12}, (_, i) => i + 1), c = color(it.var);
    const tr = (p, name, dash, op) => ({x: mm.map(x.cyMonthShort), y: p.months.map(r => r.mean), name: `${name} ${p.label}`, mode: "lines+markers", connectgaps: false, line: {color: c, width: dash ? 1.6 : 2.6, dash: dash ? "dot" : "solid"}, marker: {size: dash ? 4 : 6}, opacity: op});
    Plotly.newPlot(div, [tr(it.early, x.cyEarly, true, .75), tr(it.late, x.cyLate, false, 1)], lay({yaxis: {gridcolor: "#1c2a47", zeroline: false, title: {text: it.unit || "", font: {size: 10}}}}), PL);
  }
  function yearChart(div, it) {
    const x = t(), c = color(it.var), ya = it.yearly.filter(r => r.amp !== null), tr = it.amp_trend, tt = [];
    tt.push({x: ya.map(r => r.y), y: ya.map(r => r.amp), type: "bar", name: x.cyAmp, marker: {color: c, opacity: .75}});
    if (tr && ya.length > 2) { const ys = ya.map(r => r.y), a = ya.map(r => r.amp).sort((p, q) => p - q), med = a[Math.floor(a.length / 2)], ym = ys.reduce((p, q) => p + q, 0) / ys.length;
      tt.push({x: [ys[0], ys[ys.length - 1]], y: [med + tr.slope * (ys[0] - ym), med + tr.slope * (ys[ys.length - 1] - ym)], mode: "lines", name: x.cyTrend, line: {color: "#e8eefb", width: 2, dash: "dash"}}); }
    Plotly.newPlot(div, tt, lay({xaxis: {gridcolor: "#1c2a47", dtick: 2}, yaxis: {gridcolor: "#1c2a47", zeroline: false, title: {text: (x.cyAmp + (it.unit ? ", " + it.unit : "")), font: {size: 10}}}}), PL);
  }
  function normChart(div) {
    const x = t(), mm = Array.from({length: 12}, (_, i) => i + 1);
    const tr = data.items.filter(it => it.late.valid_months >= 6).map(it => {
      const v = it.late.months.map(r => r.mean), ok = v.filter(z => z !== null), lo = Math.min(...ok), hi = Math.max(...ok);
      return {x: mm.map(x.cyMonthShort), y: v.map(z => z === null ? null : (z - lo) / ((hi - lo) || 1)), name: vname(it), mode: "lines+markers", connectgaps: false, line: {color: color(it.var), width: 2.4}, marker: {size: 5}};
    });
    Plotly.newPlot(div, tr, lay({yaxis: {gridcolor: "#1c2a47", zeroline: false, range: [-.05, 1.05]}}), PL);
  }
  function card(it, i) {
    const x = t(), e = it.early, l = it.late, tr = it.amp_trend; let txt;
    if (mode === "month") txt = it.amp_change_pct !== null ? `${x.cyChangeTxt(e.amp, l.amp, it.amp_change_pct, it.unit)}${e.peak && l.peak ? ` · ${x.cyPeak}: ${x.cyMonthShort(e.peak)} → ${x.cyMonthShort(l.peak)}` : ""}` : x.cyNoAmp(Math.min(e.valid_months, l.valid_months));
    else txt = tr ? x.cyTrendTxt(tr.slope, it.unit, tr.p, tr.sig) : x.cyNoAmp(Math.min(e.valid_months, l.valid_months));
    return `<div class="cy-card"><div class="cy-h"><i class="dot" style="background:${color(it.var)}"></i><b>${esc(vname(it))}</b>${it.unit ? `<span class="n">${esc(it.unit)}</span>` : ""}</div><div id="cyc${i}" class="cy-chart"></div><p class="cy-t n">${esc(txt)}</p></div>`;
  }
  function pairName(k) {
    const it = data.items.find(i => i.var === k); if (it) return vname(it);
    const v = VARS.find(z => z.id === k); if (v) return v.name[lang]; const n = corr && corr.names && corr.names[k]; return n ? (n[lang] || n.vi) : k;
  }
  function lagBars(x) {
    const mx = Math.max(.3, ...x.r.map(Math.abs)), W = 92, H = 30, bw = 16;
    return `<svg viewBox="0 0 ${W} ${H}" class="lagbars" aria-hidden="true"><line x1="0" x2="${W}" y1="${H / 2}" y2="${H / 2}" stroke="#2a3d66"/>${x.r.map((r, i) => { const h = Math.abs(r) / mx * (H / 2 - 2); return `<rect x="${4 + i * 22}" y="${r >= 0 ? H / 2 - h : H / 2}" width="${bw}" height="${Math.max(1, h)}" rx="2" fill="${i === x.lags.indexOf(x.best_lag) ? "#5aa9ff" : "#3a4f7d"}"/>`; }).join("")}</svg>`;
  }
  function corrRow(x) {
    const t_ = t(), ag = x.agrees === null ? "" : x.agrees ? `<span class="pill ok">${esc(t_.cyAgree)}</span>` : `<span class="pill">${esc(t_.cyDisagree)}</span>`;
    return `<div class="cy-pair"><div class="cy-pn"><b>${esc(pairName(x.a))} ↔ ${esc(pairName(x.b))}</b><div class="note">${esc(x.why[lang] || x.why.vi)}</div></div>
      ${lagBars(x)}<div class="n cy-pv">r = ${x.r_best >= 0 ? "+" : "−"}${Math.abs(x.r_best).toFixed(2)}<br>${esc(t_.cyLag)} ${x.best_lag} ${esc(t_.cyMonths)} · q ${x.q_best < .001 ? "<0.001" : x.q_best.toFixed(2)}<br>n = ${x.n_best}</div>${ag}</div>`;
  }
  function corrHtml() {
    const x = t(); if (!corr) return pos.city === "hcm" ? "" : `<p class="note">${esc(x.cyCorrOnly)}</p>`;
    const g = s => corr.pairs.filter(p => p.status === s), grp = (s, title) => g(s).length ? `<h4>${esc(title)}</h4>${g(s).map(corrRow).join("")}` : "";
    return `<h3>${esc(x.cyCorrTitle)}</h3>${g("candidate").length ? "" : `<div class="callout warn">${esc(x.cyCorrNone)}</div>`}${grp("candidate", x.cyCand)}${grp("weak", x.cyWeak)}${grp("none", x.cyNone)}
      <p class="note">${esc(corr.method[lang] || corr.method.vi)}</p><p class="note">${esc(corr.caveat[lang] || corr.caveat.vi)}</p><p class="note">${esc(x.cyBy(corr.generated))}</p>`;
  }
  function render() {
    const x = t(); if (!data) return;
    $("cyTitle").textContent = x.cyTitle; $("cyEyebrow").textContent = x.cyEyebrow; $("cyLead").textContent = x.cyLead;
    $("cyMode").innerHTML = ["month", "year"].map(m => `<button role="tab" class="${m === mode ? "on" : ""}" data-m="${m}">${esc(x[m === "month" ? "cyMonth" : "cyYear"])}</button>`).join("");
    $("cyMode").querySelectorAll("button").forEach(b => b.onclick = () => { mode = b.dataset.m; render(); });
    const its = data.items, note = pos.city !== "hcm" ? `<p class="note">${esc(x.cyOnlyHcm)}</p>` : "";
    $("cyBody").innerHTML = `<p class="note"><b>${esc(place())}</b> · ${data.start}–${data.end}</p>${note}
      <div class="tw"><table class="cy-sum"><thead><tr><th>${esc(x.cyInd)}</th><th>${esc(x.cyAmp)} ${esc(its[0].early.label)}</th><th>${esc(x.cyAmp)} ${esc(its[0].late.label)}</th><th>${esc(x.cyChange)}</th><th>${esc(x.cyTrend)}</th></tr></thead><tbody>${its.map(sumRow).join("")}</tbody></table></div>
      ${mode === "month" && its.length > 1 ? `<h3>${esc(x.cyNorm)}</h3><p class="note">${esc(x.cyNormHint)}</p><div id="cyNorm" class="cy-chart tall"></div>` : ""}
      <div class="cy-grid">${its.map(card).join("")}</div>${corrHtml()}`;
    its.forEach((it, i) => (mode === "month" ? monthChart : yearChart)($("cyc" + i), it));
    if ($("cyNorm")) normChart($("cyNorm"));
  }
  function show() { open = true; if (!data || key !== (pos.city || pos.lat + "," + pos.lon) + "|" + lang) load(); else render(); }
  new MutationObserver(() => { if ($("cycleD").classList.contains("open")) { if (!open) show(); } else open = false; }).observe($("cycleD"), {attributes: true, attributeFilter: ["class"]});
  if ($("cycleD").classList.contains("open")) show();                  // opened before this script ran (?open=cycleD)
  document.addEventListener("citychange", () => { if (open && $("cycleD").classList.contains("open")) load(); });
  EXTRA.push(() => { $("nCycle").textContent = t().nCycle; if (data && open && $("cycleD").classList.contains("open")) render(); });
  $("nCycle").textContent = t().nCycle;
  EXTRA.push(() => { for (const id of ["cyTitle", "cyEyebrow", "cyLead"]) $(id).textContent = t()[id]; });
  for (const id of ["cyTitle", "cyEyebrow", "cyLead"]) $(id).textContent = t()[id];
})();

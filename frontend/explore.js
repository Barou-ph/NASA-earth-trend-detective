// DETAIL page: full-screen 2D satellite map (Leaflet, Esri imagery). One dot per city (size = size of change, colour = direction),
// hovering a city shows the WEEKLY picture (last 52 weeks vs the same weeks of earlier years), a year-by-year time-lapse, and the telemetry panel.
// Also owns the view switch between HOME and DETAIL (hash routing: #/ and #/detail). Loaded after app.js, brief.js and hud.js.
(function () {
  const UP = 0xFF8A3D, DN = 0x38BDF8, NEU = 0x6B8FA5;
  const CHIPS = ["CLOUD_AMT", "T2M", "T2M_MIN", "PRECTOTCORR", "WS2M"];
  const PRESETS_IDS = ["hcm", "hanoi", "danang", "delhi", "london", "cairo", "losangeles"];
  const css = n => "#" + n.toString(16).padStart(6, "0");
  Object.assign(T.vi, {
    dVarLbl: "Chỉ số", wkLoad: "Đang tải xu hướng theo tuần từ NASA…", wkErr: "Chưa có xu hướng tuần: ", wkTitle: "52 tuần gần nhất", wkWeek: "Tuần kết thúc", wkNormal: "thường lệ", wkDiff: "lệch",
    wkStale: d => `Dữ liệu NASA mới nhất đến ${d}, chưa tới hôm nay.`, wk7: "7 ngày đến", wk30: "30 ngày gần nhất (tô đậm: 7 ngày cuối)", wkNormalDays: "thường lệ của thời điểm này", wkSig: "có ý nghĩa", wkNoSig: "chưa rõ", wkPerWeek: "/tuần", wkThis: "năm nay", wkClim: "cùng tuần các năm trước",
    tAll: "Toàn cầu",
    tQc: "q (so với các chỉ số của thành phố)", tQw: "q (so với 22 thành phố)", tLocal: "Chỉ số này chỉ có dữ liệu ở TP.HCM, nên bản đồ chỉ hiện một điểm.", tWait: "đang tính…"
  });
  Object.assign(T.en, {
    dVarLbl: "Indicator", wkLoad: "Loading weekly trend from NASA…", wkErr: "No weekly trend: ", wkTitle: "Last 52 weeks", wkWeek: "Week ending", wkNormal: "normal", wkDiff: "deviation",
    wkStale: d => `Latest NASA data is from ${d}, not today.`, wk7: "7 days to", wk30: "last 30 days (shaded: final 7 days)", wkNormalDays: "normal for this time of year", wkSig: "significant", wkNoSig: "unclear", wkPerWeek: "/week", wkThis: "this year", wkClim: "same weeks, earlier years",
    tAll: "World",
    tQc: "q (vs this city's indicators)", tQw: "q (vs 22 cities)", tLocal: "This indicator only has data for Ho Chi Minh City, so the map shows one dot.", tWait: "computing…"
  });
  let view = "home", seq = 0, data = null, local = null, gvar = "CLOUD_AMT", idx = -1, timer = null, loading = 0, m2 = null, loadedOnce = false;
  const mk2 = new Map(), scanCache = new Map(), wkCache = new Map();

  // ------------------------------------------------------------------------------------------------ data helpers
  const sdOf = c => { const v = c.anom.filter(a => a !== null); if (!v.length) return 1; const m = v.reduce((s, a) => s + a, 0) / v.length;
    return Math.sqrt(v.reduce((s, a) => s + (a - m) ** 2, 0) / v.length) || 1; };
  const maxEff = () => Math.max(.5, ...data.cities.map(c => Math.abs(c.effect_sd)));
  const value = c => idx < 0 ? c.effect_sd : (c.anom[idx] === null || c.anom[idx] === undefined ? 0 : c.anom[idx] / c._sd);
  const norm = c => Math.min(1, Math.abs(value(c)) / (idx < 0 ? maxEff() : 2.5));
  const hexOf = c => { const v = value(c); return v > 0.02 ? UP : v < -0.02 ? DN : NEU; };
  const cityOf = id => data && data.cities.find(c => c.city === id);
  const isPreset = v => PRESETS.some(p => p.id === v && p.kind === "csv");

  // ----------------------------------------------------------------------------------------------- weekly hover card
  function weeklyHtml(w) {
    const x = t(), r = w.recent, u = w.unit ? " " + w.unit : "", W = 260, H = 86, P = 5;
    const d = r ? r.days : {v: w.v, clim: w.clim}, n = d.v.length, all = [...d.v.filter(v => v !== null), ...d.clim.filter(v => v !== null)], lo = Math.min(...all), hi = Math.max(...all);
    const X = i => P + i * (W - 2 * P) / (n - 1), Y = v => H - P - (v - lo) / ((hi - lo) || 1) * (H - 2 * P);
    const path = a => a.map((v, i) => v === null ? "" : (i === 0 || a[i - 1] === null ? "M" : "L") + X(i).toFixed(1) + " " + Y(v).toFixed(1)).join(" ");
    const an = r ? r.anom : w.last.anom, col = css(an !== null && an > 0 ? UP : DN), li = d.v.map((v, i) => v === null ? -1 : i).reduce((m, i) => Math.max(m, i), -1);
    const band = r ? `<rect x="${X(n - 7).toFixed(1)}" y="0" width="${(X(n - 1) - X(n - 7)).toFixed(1)}" height="${H}" fill="${col}" opacity=".14" rx="3"/>` : "";
    return `<svg viewBox="0 0 ${W} ${H}" class="wksvg" role="img" aria-label="${esc(x.wkTitle)}">${band}<path d="${path(d.clim)}" fill="none" stroke="#64748B" stroke-width="1.4" stroke-dasharray="4 3"/>
      <path d="${path(d.v)}" fill="none" stroke="${col}" stroke-width="2.2" stroke-linejoin="round"/>${li >= 0 ? `<circle cx="${X(li).toFixed(1)}" cy="${Y(d.v[li]).toFixed(1)}" r="3.6" fill="${col}" stroke="#fff" stroke-width="1.2"/>` : ""}</svg>
      <div class="wkleg"><span><i style="background:${col}"></i>${esc(r ? x.wk30 : x.wkThis)}</span><span><i class="d"></i>${esc(r ? x.wkNormalDays : x.wkClim)}</span></div>` +
      (r ? `<div class="wkrow"><b>${esc(x.wk7)} ${esc(r.end)}</b>: ${f3(r.mean)}${esc(u)} · ${esc(x.wkNormal)} ${f3(r.clim)} → <b style="color:${col}">${esc(x.wkDiff)} ${an > 0 ? "+" : ""}${f3(an)}</b> (${r.effect_sd > 0 ? "+" : ""}${r.effect_sd.toFixed(1)} σ)</div>` :
        `<div class="wkrow"><b>${esc(x.wkWeek)} ${esc(w.last.week)}</b>: ${f3(w.last.v)}${esc(u)}${w.last.clim !== null ? ` · ${esc(x.wkNormal)} ${f3(w.last.clim)}` : ""}${an !== null ? ` → <b style="color:${col}">${esc(x.wkDiff)} ${an > 0 ? "+" : ""}${f3(an)}</b>` : ""}</div>`) +
      (r && r.stale_days >= 7 ? `<div class="wknote">${esc(x.wkStale(r.end))}</div>` : "");
  }
  async function loadWeekly(c, box) {
    const key = gvar + "|" + c.city;
    try {
      let w = wkCache.get(key); if (!w) { w = await api(`/api/weekly?var=${encodeURIComponent(gvar)}&city=${encodeURIComponent(c.city)}`); wkCache.set(key, w); }
      if (box.isConnected) box.innerHTML = weeklyHtml(w);
    } catch (e) { if (box.isConnected) box.textContent = t().wkErr + (e.message || ""); }
  }
  const popHead = c => `<b>${esc(c.name[lang])}</b><small>${esc(data.name[lang])}${data.unit ? " (" + esc(data.unit) + ")" : ""}</small>`;

  // -------------------------------------------------------------------------------------------------- 2D map
  function init2d() {
    if (m2) return;
    m2 = L.map("map2d", {zoomControl: false, attributionControl: false, worldCopyJump: true, minZoom: 2}).setView([pos.lat, pos.lon], 6);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {maxZoom: 18}).addTo(m2);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {maxZoom: 18}).addTo(m2);
    L.control.zoom({position: "topright"}).addTo(m2); mapUpdate();
  }
  function mapUpdate() {
    if (!m2 || !data) return;
    const live = new Set();
    for (const c of data.cities) {
      live.add(c.city);
      const col = css(hexOf(c)), d = Math.round(16 + norm(c) * 30), beat = idx < 0 ? c.sig_fdr : Math.abs(value(c)) > 1.4;
      const icon = L.divIcon({className: "", iconSize: [d, d], iconAnchor: [d / 2, d / 2],
        html: `<div class="pulse ${beat ? "beat" : ""}" style="width:${d}px;height:${d}px"><i style="background:${col}"></i><u style="background:${col}"></u></div>`});
      let m = mk2.get(c.city);
      if (!m) {
        m = L.marker([c.lat, c.lon], {icon}).addTo(m2); mk2.set(c.city, m);
        m.bindPopup("", {closeButton: false, offset: [0, -6], autoPan: true, autoPanPaddingTopLeft: [30, 190], autoPanPaddingBottomRight: [30, 130], className: "wkpop", maxWidth: 300, minWidth: 270});
        let tm = null;
        m.on("click", () => setCity(m.c.city));
        m.on("mouseover", () => { clearTimeout(tm); m.setPopupContent(`<div class="pop">${popHead(m.c)}<div class="wk"><span class="wkload">${esc(t().wkLoad)}</span></div></div>`); m.openPopup();
          tm = setTimeout(() => { const el = m.getPopup() && m.getPopup().getElement(); const box = el && el.querySelector(".wk"); if (box && m.isPopupOpen()) loadWeekly(m.c, box); }, 220); });
        m.on("mouseout", () => { clearTimeout(tm); tm = setTimeout(() => m.closePopup(), 120); });
      } else m.setIcon(icon);
      m.c = c;
    }
    for (const [id, m] of mk2) if (!live.has(id)) { m2.removeLayer(m); mk2.delete(id); }
  }
  // --------------------------------------------------------------------------------------------- panels / texts
  function scanRows(city) {
    if (!city) return null; if (scanCache.has(city)) return scanCache.get(city);
    scanCache.set(city, null);
    try { api(`/api/scan?city=${encodeURIComponent(city)}&${range()}`).then(r => { scanCache.set(city, r); tele(); }).catch(() => scanCache.set(city, [])); } catch (e) { scanCache.set(city, []); }
    return null;
  }
  function refresh() { if (!data) return; hud(); legend(); tele(); mapUpdate(); }
  function hud() {
    const x = t(); if (!data) return; const ys = data.years, has = ys.length > 0;
    $("gyear").textContent = !has ? "—" : idx < 0 ? x.gFinal(ys[0], ys[ys.length - 1]) : ys[idx]; $("gsub").textContent = idx < 0 ? x.gSubFinal : x.gSubYear;
    $("gslider").max = Math.max(0, ys.length - 1); $("gslider").value = idx < 0 ? 0 : idx; $("gslider").disabled = $("gplay").disabled = !has;
    $("gplay").textContent = timer ? "❚❚" : "▶"; $("gplay").setAttribute("aria-label", timer ? x.gPause : x.gPlay); $("gplay").title = x.gPlay; $("gall").textContent = x.gAll;
  }
  function legend() {
    const x = t(); if (!data) { $("glegend").innerHTML = ""; return; }
    $("glegend").innerHTML = `<b>${esc(data.name[lang])}${data.unit ? " (" + esc(data.unit) + ")" : ""}</b>
      <span><i style="background:${css(UP)};color:${css(UP)}"></i>${x.gUp}</span><span><i style="background:${css(DN)};color:${css(DN)}"></i>${x.gDn}</span><div class="cap" style="margin-top:4px">${esc(local ? x.tLocal : idx < 0 ? x.gHint : x.gYearMode)}</div>`;
  }
  function tele() {
    const x = t(), cm = CITIES.find(q => q.id === pos.city), c = cityOf(pos.city), set = (id, v) => { $(id).textContent = v; };
    set("hudName", cm ? cityName(cm) : x.custom2);
    set("hudCoord", `${Math.abs(pos.lat).toFixed(2)}°${pos.lat >= 0 ? "N" : "S"} | ${Math.abs(pos.lon).toFixed(2)}°${pos.lon >= 0 ? "E" : "W"}${cm && cm.region ? " · " + (cm.region === "vn" ? "Việt Nam" : "World") : ""}`);
    const al = $("hudAlert"), prof = $("hudProf");
    if (!c || !data) { for (const i of ["m1v", "m2v"]) set(i, "–"); set("m1u", ""); set("m1b", ""); set("m2b", ""); al.textContent = x.tAlertPt; al.className = "alert"; prof.innerHTML = ""; return; }
    const rows = scanRows(pos.city), sr = rows && rows.find(r => r.var === gvar);          // same numbers as the brief: this city's indicators
    const slope = sr ? sr.slope : c.slope, eff = idx < 0 ? (sr ? sr.effect_sd : c.effect_sd) : value(c), col = css(slope > 0 ? UP : DN);
    const trusted = sr ? sr.sig_fdr : null, lv = sr ? sr.evidence.level : null;
    set("m1v", (slope > 0 ? "+" : "") + f3(slope)); $("m1v").style.color = col; set("m1u", (data.unit || "") + x.perYear);
    set("m2v", (eff > 0 ? "+" : "") + eff.toFixed(2)); $("m2v").style.color = css(hexOf(c)); set("m2l", idx >= 0 ? data.years[idx] + " · " + x.gAnom : x.m2l); set("m1l", data.name[lang]);
    set("m1b", trusted === null ? x.tWait : trusted ? "✔ " + x.tOk + " · " + EVTXT[lv][lang] : x.tNo); $("m1b").style.color = trusted ? "#34D399" : "#94A3B8";
    set("m2b", slope > 0 ? "▲ " + x.gUp : "▼ " + x.gDn); $("m2b").style.color = col;
    al.textContent = trusted === null ? "" : trusted ? x.tAlertOk : x.tAlertNo; al.className = "alert" + (trusted ? " ok" : "");
    const rank = [...data.cities].sort((a, b) => Math.abs(b.effect_sd) - Math.abs(a.effect_sd)).findIndex(q => q.city === c.city) + 1;
    prof.innerHTML = [sr ? [x.tQc, fp(sr.q)] : null, [x.tQw, fp(c.q)], [x.tP, fp(sr ? sr.p : c.p)], [x.tMk, fp(sr ? sr.p_mk : c.p_mk)], [x.tRank, `#${rank} / ${data.cities.length}`],
      [x.tPer, data.years.length ? `${data.years[0]}–${data.years[data.years.length - 1]}` : `${$("y0").value}–${$("y1").value}`]].filter(Boolean)
      .map(([a, b]) => `<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`).join("");
  }
  function presets() {
    const x = t(), list = PRESETS_IDS.map(id => CITIES.find(c => c.id === id)).filter(Boolean);
    $("presets").innerHTML = `<button data-all="1">🌐 ${esc(x.tAll)}</button><span class="pl">${esc(x.tPresets)}</span>` + list.map(c => `<button data-c="${c.id}" class="${c.id === pos.city ? "on" : ""}">${esc(cityName(c))}</button>`).join("");
    $("presets").querySelectorAll("button[data-c]").forEach(b => b.onclick = () => setCity(b.dataset.c));
    $("presets").querySelector("[data-all]").onclick = () => { if (m2) m2.flyToBounds(L.latLngBounds(data ? data.cities.map(c => [c.lat, c.lon]) : [[-40, -120], [60, 150]]).pad(.15), {duration: 1.4}); };
  }
  const busy = on => { loading += on ? 1 : -1; $("gstat").classList.toggle("on", loading > 0); $("gstat").textContent = loading > 0 ? t().gLoad : ""; };
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function togglePlay() {
    if (!data || !data.years.length) return; if (timer) { stop(); hud(); return; }
    idx = 0; refresh(); timer = setInterval(() => { idx++; if (idx >= data.years.length) { stop(); idx = -1; } refresh(); }, 800); hud();
  }
  async function load(v) {
    gvar = v; local = null; stop(); idx = -1; busy(true); chips(); const my = ++seq;
    try { const d = await api(`/api/globe?var=${encodeURIComponent(v)}&${range()}`); if (my !== seq) return;      // a newer choice replaced this one
      d.cities.forEach(c => { c._sd = sdOf(c); }); data = d; loadedOnce = true; refresh(); }
    catch (e) { showErr(e.message); } finally { busy(false); }
  }
  function useLocal(it) {                                              // a CSV preset indicator (e.g. NO2 over Ho Chi Minh City): one dot, numbers from the highlight itself
    gvar = it.var; local = it; stop(); idx = -1; seq++;
    data = {var: it.var, unit: it.unit, name: it.name, years: [], cities: [{city: it.city, name: it.place, region: it.region, lat: it.lat, lon: it.lon, slope: it.slope, p: it.q, p_mk: it.q,
      sig: true, sig_fdr: true, q: it.q, effect_sd: it.effect_sd, anom: [], _sd: 1}]};
    loadedOnce = true; chips(); refresh();
  }
  function chips() {                                               // compact indicator picker in the telemetry card (the current indicator, or the one opened from a home card)
    const s = $("dVar"); if (!s || !VARS.length) return; $("dVarL").textContent = t().dVarLbl;
    s.innerHTML = (local ? `<option value="${esc(local.var)}">${esc(local.name[lang])}</option>` : "") + VARS.map(v => `<option value="${v.id}">${esc(v.name[lang])}</option>`).join("");
    s.value = gvar;
  }

  // ---------------------------------------------------------------------------------------------- views + routing
  const HASH = {home: "#/", detail: "#/detail"};
  const viewFromHash = () => location.hash.startsWith("#/detail") ? "detail" : "home";
  function setView(v, push = true, skipLoad = false) {
    if (view === v) return; view = v;
    for (const k of ["home", "detail"]) document.body.classList.toggle("view-" + k, k === v);
    $("nHome").classList.toggle("on", v === "home"); $("nDetail").classList.toggle("on", v === "detail");
    if (push && location.hash !== HASH[v]) location.hash = HASH[v];
    if (v === "detail") {
      init2d(); if (!skipLoad && !local && (!data || data.var !== gvar)) load(gvar);
      setTimeout(() => { m2.invalidateSize(); m2.setView([pos.lat, pos.lon], Math.max(m2.getZoom(), 6)); }, 80);
    } else window.scrollTo(0, 0);
    fitHudLater();
  }
  const fitHudLater = () => { if (typeof fitHud === "function") setTimeout(fitHud, 50); };
  async function openDetail(o = {}) {
    setView("detail", true, !!o.var); const first = !data;
    if (o.var && (o.var !== gvar || local || first)) { if (isPreset(o.var) && o.item) useLocal(o.item); else await load(o.var); }
    if (o.city) setCity(o.city);
  }
  window.ETD = {openDetail, setView, get gvar() { return gvar; }};

  // --------------------------------------------------------------------------------------------------- wiring
  $("nHome").onclick = () => setView("home"); $("nDetail").onclick = () => setView("detail");
  $("brandLink").onclick = e => { e.preventDefault(); setView("home"); };
  addEventListener("hashchange", () => setView(viewFromHash(), false));
  $("dVar").onchange = e => { if (!isPreset(e.target.value)) load(e.target.value); };
  $("gplay").onclick = togglePlay; $("gslider").oninput = e => { stop(); idx = +e.target.value; refresh(); }; $("gall").onclick = () => { stop(); idx = -1; refresh(); };
  $("demo2").addEventListener("click", () => load("CLOUD_AMT"));
  document.addEventListener("citychange", () => {
    if (m2 && view === "detail") m2.flyTo([pos.lat, pos.lon], Math.max(m2.getZoom(), 7), {duration: 1.3});
    presets(); scanRows(pos.city); refresh(); tele(); });
  EXTRA.push(() => { chips(); hud(); legend(); presets(); tele(); if (m2 && data) mapUpdate(); $("gstat").textContent = loading > 0 ? t().gLoad : ""; });
  function init() { chips(); presets(); setView(viewFromHash(), false); }
  if (window.APP_READY) init(); else document.addEventListener("app-ready", init);
})();

// HOME page: what changed most in the LAST 7 DAYS across the world (vs the normal for this time of year, 22 cities x 14 indicators).
// Each card opens the DETAIL page (2D satellite map) on that city and indicator.
// Data: /api/highlights (computed in the background by the server; polled until finished, cards appear as cities complete). Loaded last.
(function () {
  Object.assign(T.vi, {
    hlTitle: "Biến động nổi bật 7 ngày qua", hlSub: "Chỉ số lệch nhiều nhất so với mức thường lệ của đúng thời điểm này trong năm, tính trên 7 ngày gần nhất có dữ liệu, tại 22 thành phố. Chỉ là một tuần, không phải xu hướng khí hậu. Bấm một thẻ để xem trên bản đồ vệ tinh.",
    hlAll: "Tất cả", hlUp: "▲ Tăng", hlDn: "▼ Giảm", hlVn: "Việt Nam", hlWorld: "Thế giới", hlProg: (d, n) => `Đang phân tích ${d}/${n} thành phố từ dữ liệu NASA theo ngày…`,
    hlNone: "Chưa có biến động nổi bật trong nhóm này.", hlOpen: "Xem chi tiết", openDetail: "Mở bản đồ chi tiết",
    hlDone: (n, c, d) => `${n} biến động nổi bật, chọn từ ${c} phép thử (22 thành phố × các chỉ số có dữ liệu mới)${d ? `, dữ liệu đến ${d}` : ""}. Xếp theo: vượt hiệu chỉnh FDR trước, rồi mức lệch.`,
    hlWeek: "7 ngày đến", hlNormal: "thường lệ", hlDev: "lệch", hlFdr: "vượt hiệu chỉnh FDR", hlHint: "gợi ý, chưa vượt FDR", hlSd: "độ lệch chuẩn", hlLast7: "7 ngày qua", hmHeat: "Heatmap", hmNoLayer: "NASA chưa có bản đồ toàn cầu cho chỉ số này.", hmHeatLoad: "Đang tải bản đồ NASA…", hmHeatNote: (n, m) => `Heatmap: ${n}, trung bình tháng ${m} (NASA GIBS). Đây là bản đồ nền theo tháng, không phải 7 ngày.`, hmHeatErr: "Không tải được bản đồ NASA GIBS.", hmScale: v => `${v}: độ lệch so với thường lệ (σ)`, hlSum: (n, c) => `${n} biến động nổi bật · mạnh nhất: ${c}`, hlSumNone: "Chưa có biến động nổi bật", hlWin: d => `cửa sổ 7 ngày kết thúc ${d}`,
    hlLabel: "Thành phố nổi bật", hmTitle: "Bản đồ biến động 7 ngày qua", hmSub: "Kéo để xoay quả địa cầu. Mỗi chấm là chỉ số lệch mạnh nhất của một thành phố; chấm to = lệch nhiều.",
    hmPick: "Chọn một thẻ hoặc một chấm để xem", hmGo: "Xem chi tiết thành phố →", hmLo: "lệch ít", hmHi: "lệch nhiều", hlRise: "tăng", hlFall: "giảm",
    hlNote: "Mỗi thẻ gồm độ lệch so với thường lệ và đường diễn biến 30 ngày (vùng tô là 7 ngày cuối; nét đứt là mức thường lệ). Khi q (FDR) chưa dưới ngưỡng, đây là gợi ý cần theo dõi, chưa phải kết luận. Bấm một thẻ để mở bản đồ chi tiết.",
    ftSrc: "Nguồn: dữ liệu vệ tinh và tái phân tích NASA POWER · kiểm định có hiệu chỉnh FDR", ftMeth: "Độ lệch σ so với mức thường lệ của đúng thời điểm trong năm; p theo phân phối thực nghiệm", st4l: "kết thúc cửa sổ 7 ngày", hlKm: "TB 7 ngày", hlNorm: "thường lệ"
  });
  Object.assign(T.en, {
    hlTitle: "Notable changes in the last 7 days", hlSub: "The indicators that deviate most from the normal for this time of year, over the latest 7 days with data, in 22 cities. Just one week, not a climate trend. Click a card to see it on the satellite map.",
    hlAll: "All", hlUp: "▲ Rising", hlDn: "▼ Falling", hlVn: "Vietnam", hlWorld: "World", hlProg: (d, n) => `Analysing ${d} of ${n} cities from NASA daily data…`,
    hlNone: "No notable change in this group yet.", hlOpen: "See detail", openDetail: "Open the detail map",
    hlDone: (n, c, d) => `${n} notable changes, picked from ${c} tests (22 cities × indicators with fresh data)${d ? `, data up to ${d}` : ""}. Order: passing FDR correction first, then size of deviation.`,
    hlWeek: "7 days to", hlNormal: "normal", hlDev: "deviation", hlFdr: "passes FDR", hlHint: "suggestive, not FDR", hlSd: "std. deviations", hlLast7: "last 7 days", hmHeat: "Heatmap", hmNoLayer: "NASA has no global map for this indicator.", hmHeatLoad: "Loading the NASA map…", hmHeatNote: (n, m) => `Heatmap: ${n}, monthly mean ${m} (NASA GIBS). A monthly background map, not the 7-day window.`, hmHeatErr: "Could not load the NASA GIBS map.", hmScale: v => `${v}: deviation from normal (σ)`, hlSum: (n, c) => `${n} notable changes · strongest: ${c}`, hlSumNone: "No notable change yet", hlWin: d => `7-day window ending ${d}`,
    hlLabel: "Notable cities", hmTitle: "Map of the last 7 days", hmSub: "Drag to rotate the globe. Each dot is the strongest deviation of one city; a bigger dot means a larger deviation.",
    hmPick: "Pick a card or a dot to see it", hmGo: "Open city detail →", hmLo: "small", hmHi: "large", hlRise: "rising", hlFall: "falling",
    hlNote: "Each card shows the deviation from normal and the last 30 days (shaded = last 7 days; dashed = normal). When q (FDR) is not under the threshold it is a hint to watch, not a conclusion. Click a card to open the detail map.",
    ftSrc: "Source: NASA satellite and POWER reanalysis data · tests corrected for FDR", ftMeth: "σ = deviation from the normal for this time of year; p from the empirical distribution", st4l: "end of the 7-day window", hlKm: "7-day mean", hlNorm: "normal"
  });
  let items = [], tests = 0, done = 0, total = 22, finished = false, tab = "all", timer = null, last = "", sel = -1;
  
  const col = d => d === "up" ? "#4fc3b5" : "#d9a441";               // text colours (readable on navy), same hue family as the globe scale
  const DIV = ["#8c510a", "#bf812d", "#dfc27d", "#f2efe6", "#80cdc1", "#35978f", "#01665e"];   // colour-blind-safe diverging scale: brown = falling, teal = rising
  const hx = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16));
  function ramp(tt) { tt = Math.max(0, Math.min(1, tt)); const x = tt * (DIV.length - 1), i = Math.min(DIV.length - 2, Math.floor(x)), f = x - i, a = hx(DIV[i]), b = hx(DIV[i + 1]); return a.map((c, k) => Math.round(c + (b[k] - c) * f)); }
  const rgba = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  let HI = 6, cur = "all";                                             // HI = |sigma| at the ends of the scale

  function spark(sp, dir) {                                           // last 30 days vs normal; the final 7 days are shaded
    if (!sp || !sp.v || sp.v.length < 8) return "";
    const W = 170, H = 46, P = 3, all = [...sp.v.filter(v => v !== null), ...sp.clim.filter(v => v !== null)], lo = Math.min(...all), hi = Math.max(...all), n = sp.v.length;
    const X = i => P + i * (W - 2 * P) / (n - 1), Y = v => H - P - (v - lo) / ((hi - lo) || 1) * (H - 2 * P);
    const path = a => a.map((v, i) => v === null ? "" : (i === 0 || a[i - 1] === null ? "M" : "L") + X(i).toFixed(1) + " " + Y(v).toFixed(1)).join(" ");
    const c = col(dir), li = sp.v.map((v, i) => v === null ? -1 : i).reduce((m, i) => Math.max(m, i), -1);
    return `<svg viewBox="0 0 ${W} ${H}" class="spark" aria-hidden="true"><rect x="${X(n - 7).toFixed(1)}" y="0" width="${(X(n - 1) - X(n - 7)).toFixed(1)}" height="${H}" fill="${c}" opacity=".13" rx="3"/>
      <path d="${path(sp.clim)}" fill="none" stroke="#64748B" stroke-width="1.3" stroke-dasharray="4 3"/>
      <path d="${path(sp.v)}" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>${li >= 0 ? `<circle cx="${X(li).toFixed(1)}" cy="${Y(sp.v[li]).toFixed(1)}" r="3" fill="${c}"/>` : ""}</svg>`;
  }
  function card(r, i) {
    const x = t(), u = r.unit ? " " + esc(r.unit) : "", c = rgba(ramp(.5 + r.effect_sd / (2 * HI))), tc = col(r.direction);
    return `<button class="hl-card ${i === sel ? "on" : ""}" data-i="${i}">
      <div class="hl-top"><span class="nm">${i + 1}. ${esc(r.place[lang])}</span><span class="z n" style="color:${tc}">${r.direction === "up" ? "▲" : "▼"} ${sgn(r.effect_sd)} σ</span></div>
      <div class="meta"><span>${esc(r.name[lang])} · ${esc(r.region === "vn" ? x.hlVn : x.hlWorld)}</span><span class="pill ${r.sig_fdr ? "ok" : ""}">${esc(r.sig_fdr ? x.hlFdr : x.hlHint)}</span></div>
      ${spark(r.spark, r.direction)}
      <div class="kv n"><span>${esc(x.hlKm)} <b>${f3(r.mean)}${u}</b></span><span>${esc(x.hlNorm)} <b>${f3(r.clim)}</b></span></div>
      <div class="kv n"><span>${esc(x.hlDev)} <b>${r.anom > 0 ? "+" : ""}${f3(r.anom)}</b></span><span>p <b>${fp(r.p)}</b> · q <b>${fp(r.q)}</b></span></div></button>`;
  }
  // left panel: 3D globe (pure canvas). One glowing dot per city = its strongest deviation; colour = signed deviation on the diverging scale.
  let TEX = null, HEAT = null, heatOn = true, heatMap = null, heatMsg = "", heatReq = 0, dirty = true, off = null, offCtx = null, offImg = null, offU32 = null, N = 0, PX = null, PY = null, PZ = null, cnt = 0;
  const HEATC = new Map();
  let cv, ctx, W = 0, H = 0, R = 0, cx = 0, cy = 0, zoom = 1, rot = {lat: 15, lon: 100}, tgt = null, drag = null, idle = true, hit = [], started = false;
  const shownList = () => items.filter(r => cur === "all" || r.var === cur);
  function size() {
    const r = cv.parentNode.getBoundingClientRect(), d = devicePixelRatio || 1; if (r.width < 10 || r.height < 10) return;
    W = r.width; H = r.height; cv.width = W * d; cv.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0); cx = W / 2; cy = H / 2 - 6; R = Math.min(W * .46, H * .43) * zoom;
  }
  function P(lat, lon) {
    const f = lat * Math.PI / 180, l = (lon - rot.lon) * Math.PI / 180, tt = rot.lat * Math.PI / 180, x = Math.cos(f) * Math.sin(l), y = Math.sin(f), z = Math.cos(f) * Math.cos(l);
    return {x: cx + x * R, y: cy - (y * Math.cos(tt) - z * Math.sin(tt)) * R, z: y * Math.sin(tt) + z * Math.cos(tt)};
  }
  const bestPerCity = shown => { const m = new Map(); shown.forEach((r, i) => { const o = m.get(r.city); if (o === undefined || Math.abs(r.effect_sd) > Math.abs(shown[o].effect_sd)) m.set(r.city, i); }); return m; };
  function frame() {
    if (document.body.classList.contains("view-home")) {
      const rr = cv.parentNode.getBoundingClientRect(); if (Math.abs(rr.width - W) > 1 || Math.abs(rr.height - H) > 1) size();
      if (W) draw();
    }
    requestAnimationFrame(frame);
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    if (tgt) { rot.lat += (tgt.lat - rot.lat) * .08; const d = ((tgt.lon - rot.lon + 540) % 360) - 180; rot.lon += d * .08; dirty = true; if (Math.abs(d) < .1 && Math.abs(tgt.lat - rot.lat) < .1) tgt = null; }
    else if (idle && !drag) { rot.lon += .08; dirty = true; }
    const halo = ctx.createRadialGradient(cx, cy, R * .98, cx, cy, R * 1.12); halo.addColorStop(0, "rgba(90,169,255,.35)"); halo.addColorStop(1, "rgba(90,169,255,0)");
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(cx, cy, R * 1.12, 0, 7); ctx.fill();
    const g = ctx.createRadialGradient(cx - R * .35, cy - R * .35, R * .1, cx, cy, R * 1.05); g.addColorStop(0, "#17335f"); g.addColorStop(1, "#08142b");
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.fill();
    if (TEX) drawTex(); else {                                            // fallback while the imagery loads: plain sphere with a graticule
      ctx.strokeStyle = "rgba(130,170,235,.2)"; ctx.lineWidth = 1;
      const line = a => { ctx.beginPath(); let on = false; a.forEach(p => { if (p.z > 0) { on ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y); on = true; } else on = false; }); ctx.stroke(); };
      for (let la = -60; la <= 60; la += 30) { const a = []; for (let lo = -180; lo <= 180; lo += 5) a.push(P(la, lo)); line(a); }
      for (let lo = -180; lo < 180; lo += 30) { const a = []; for (let la = -90; la <= 90; la += 5) a.push(P(la, lo)); line(a); }
    }
    const shown = shownList(), best = bestPerCity(shown), L = [];
    best.forEach((i, city) => { const r = shown[i], p = P(r.lat, r.lon); if (p.z > .05) L.push({r, i, p}); });
    if (!HEAT) L.forEach(({r, p}) => { const c = ramp(.5 + r.effect_sd / (2 * HI)), rad = R * (.07 + .13 * Math.min(1, Math.abs(r.effect_sd) / HI)) * (.55 + .45 * p.z), gr = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, rad);
      gr.addColorStop(0, rgba(c, .95)); gr.addColorStop(.55, rgba(c, .55)); gr.addColorStop(1, rgba(c, 0)); ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(p.x, p.y, rad, 0, 7); ctx.fill(); });
    ctx.font = "12px Helvetica,Arial,sans-serif"; hit = [];
    L.forEach(({r, i, p}) => {
      const on = i === sel; ctx.beginPath(); ctx.arc(p.x, p.y, on ? 4.5 : 3, 0, 7); ctx.fillStyle = "#fff"; ctx.fill(); ctx.strokeStyle = "rgba(0,0,0,.5)"; ctx.stroke();
      if (on) { ctx.strokeStyle = "#5aa9ff"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(p.x, p.y, 10, 0, 7); ctx.stroke(); ctx.lineWidth = 1; }
      ctx.fillStyle = "#e8eefb"; ctx.fillText(r.place[lang], p.x + 10, p.y - 8); hit.push({i, x: p.x, y: p.y});
    });
  }
  function initGlobe() {
    cv = $("cv"); if (!cv || started) return; started = true; ctx = cv.getContext("2d"); size(); loadBase(); $("heatOn").onchange = e => { heatOn = e.target.checked; syncHeat(); };
    cv.onpointerdown = e => { drag = {x: e.clientX, y: e.clientY, m: 0}; cv.setPointerCapture(e.pointerId); cv.style.cursor = "grabbing"; };
    cv.onpointermove = e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.m += Math.abs(dx) + Math.abs(dy); rot.lon -= dx * .4 / zoom; rot.lat = Math.max(-80, Math.min(80, rot.lat + dy * .3)); dirty = true; drag.x = e.clientX; drag.y = e.clientY; tgt = null; idle = false; };
    cv.onpointerup = e => {
      cv.style.cursor = "grab";
      if (drag && drag.m < 5) { const r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, h = hit.map(o => ({...o, d: Math.hypot(o.x - x, o.y - y)})).sort((a, b) => a.d - b.d)[0]; if (h && h.d < 16) select(h.i, true); }
      drag = null;
    };
    cv.addEventListener("wheel", e => { e.preventDefault(); zoom = Math.max(.6, Math.min(2.2, zoom * (e.deltaY < 0 ? 1.08 : .93))); size(); dirty = true; }, {passive: false});
    addEventListener("resize", size); frame();
  }
  // --- real imagery: NASA Blue Marble + coastlines from GIBS (equirectangular), sampled per pixel onto the sphere
  const WMS = (map, layer, w, h, fmt, time) => `${map.wms}?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&STYLES=&SRS=EPSG:4326&BBOX=-180,-90,180,90&LAYERS=${layer}&FORMAT=${fmt}&TRANSPARENT=${fmt === "image/png" ? "TRUE" : "FALSE"}&WIDTH=${w}&HEIGHT=${h}${time ? "&TIME=" + time : ""}`;
  const loadImg = u => new Promise((ok, no) => { const i = new Image(); i.crossOrigin = "anonymous"; i.onload = () => ok(i); i.onerror = () => no(new Error("img")); i.src = u; });
  function toU32(imgs, w, h, blur) { const c = document.createElement("canvas"); c.width = w; c.height = h; const k = c.getContext("2d", {willReadFrequently: true}); if (blur) k.filter = `blur(${blur}px)`; imgs.forEach(i => { if (blur) { k.drawImage(i, -w, 0, w, h); k.drawImage(i, w, 0, w, h); } k.drawImage(i, 0, 0, w, h); }); const d = k.getImageData(0, 0, w, h); return {w, h, d: new Uint32Array(d.data.buffer)}; }
  async function ensureMap() { if (heatMap) return heatMap; heatMap = await api("/api/heatlayers"); return heatMap; }
  async function loadBase() {
    try { const m = await ensureMap(); const [a, b] = await Promise.all([loadImg(WMS(m, m.base, 4096, 2048, "image/jpeg")), loadImg(WMS(m, "Coastlines_15m", 4096, 2048, "image/png")).catch(() => null)]);
      TEX = toU32(b ? [a, b] : [a], 4096, 2048); dirty = true; } catch (e) { TEX = null; }
  }
  const heatVar = () => cur === "all" ? (shownList()[0] || {}).var : cur;
  async function syncHeat() {
    const my = ++heatReq, sw = $("heatOn"), x = t();
    $("heatOn").closest(".stage").classList.toggle("heat", heatOn);
    $("heatLbl").textContent = x.hmHeat;
    let m = null; try { m = await ensureMap(); } catch (e) { heatMsg = x.hmHeatErr; HEAT = null; dirty = true; legend(); return; }
    const L = m.layers[heatVar()]; sw.disabled = !L; sw.checked = !!L && heatOn;
    if (!heatOn || !L) { HEAT = null; heatMsg = heatOn && !L ? x.hmNoLayer : ""; dirty = true; legend(); return; }
    heatMsg = x.hmHeatLoad; legend();
    try {
      if (!HEATC.has(L.layer + L.time)) HEATC.set(L.layer + L.time, toU32([await loadImg(WMS(m, L.layer, 2048, 1024, "image/png", L.time))], 2048, 1024, 5));
      if (my !== heatReq) return; HEAT = HEATC.get(L.layer + L.time); heatMsg = ""; heatInfo = L;
    } catch (e) { if (my !== heatReq) return; HEAT = null; heatMsg = x.hmHeatErr; }
    dirty = true; legend();
  }
  let heatInfo = null;
  function drawTex() {
    const n = Math.max(120, Math.min(560, Math.round(2 * R))); if (n !== N) {
      N = n; off = document.createElement("canvas"); off.width = off.height = N; offCtx = off.getContext("2d"); offImg = offCtx.createImageData(N, N); offU32 = new Uint32Array(offImg.data.buffer);
      PX = new Float32Array(N * N); PY = new Float32Array(N * N); PZ = new Float32Array(N * N); cnt = 0;
      for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { const u = (i + .5) / N * 2 - 1, v = (j + .5) / N * 2 - 1, q = 1 - u * u - v * v; if (q <= 0) continue; PX[cnt] = u; PY[cnt] = -v; PZ[cnt] = Math.sqrt(q); cnt++; }
      PXI = new Uint32Array(cnt); let k = 0; for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { const u = (i + .5) / N * 2 - 1, v = (j + .5) / N * 2 - 1; if (1 - u * u - v * v > 0) PXI[k++] = j * N + i; }
      dirty = true;
    }
    if (dirty) {
      dirty = false; const rt = rot.lat * Math.PI / 180, st = Math.sin(rt), ct = Math.cos(rt), TW = TEX.w, TH = TEX.h, T = TEX.d, o0 = (rot.lon + 180) / 360, hv = HEAT, HW = hv ? hv.w : 0, HH = hv ? hv.h : 0, HD = hv ? hv.d : null, dim = hv ? .78 : 1;
      offU32.fill(0);
      for (let k = 0; k < cnt; k++) {
        const X = PX[k], Yv = PY[k], Zv = PZ[k], y = Yv * ct + Zv * st, z = -Yv * st + Zv * ct, lat = Math.asin(y), lam = Math.atan2(X, z);
        let u = lam / 6.283185307 + o0; u -= Math.floor(u); let ty = ((.5 - lat / Math.PI) * TH) | 0; if (ty >= TH) ty = TH - 1; else if (ty < 0) ty = 0;
        const px = T[ty * TW + ((u * TW) | 0)], sh = (.38 + .62 * Math.pow(Zv, .42)) * dim;
        let r = (px & 255) * sh, g = ((px >> 8) & 255) * sh, b = ((px >> 16) & 255) * sh;
        if (hv) {
          const fy = Math.min(HH - 1.001, Math.max(0, (.5 - lat / Math.PI) * HH - .5)), fx = u * HW - .5, y0 = fy | 0, wy = fy - y0, xf = Math.floor(fx), wx = fx - xf, x0 = (xf + HW) % HW, x1 = (x0 + 1) % HW;
          const h00 = HD[y0 * HW + x0], h10 = HD[y0 * HW + x1], h01 = HD[(y0 + 1) * HW + x0], h11 = HD[(y0 + 1) * HW + x1];
          const w00 = (1 - wx) * (1 - wy) * (h00 >>> 24), w10 = wx * (1 - wy) * (h10 >>> 24), w01 = (1 - wx) * wy * (h01 >>> 24), w11 = wx * wy * (h11 >>> 24), wa = w00 + w10 + w01 + w11;
          if (wa > 0) {
            const hr = (w00 * (h00 & 255) + w10 * (h10 & 255) + w01 * (h01 & 255) + w11 * (h11 & 255)) / wa, hg = (w00 * ((h00 >> 8) & 255) + w10 * ((h10 >> 8) & 255) + w01 * ((h01 >> 8) & 255) + w11 * ((h11 >> 8) & 255)) / wa, hb = (w00 * ((h00 >> 16) & 255) + w10 * ((h10 >> 16) & 255) + w01 * ((h01 >> 16) & 255) + w11 * ((h11 >> 16) & 255)) / wa;
            const a = wa / 255 * .72, s2 = .55 + .45 * Zv; r += (hr * s2 - r) * a; g += (hg * s2 - g) * a; b += (hb * s2 - b) * a;
          }
        }
        offU32[PXI[k]] = 0xFF000000 | (b << 16) | (g << 8) | r;
      }
      offCtx.putImageData(offImg, 0, 0);
    }
    ctx.imageSmoothingEnabled = true; ctx.drawImage(off, cx - R, cy - R, 2 * R, 2 * R);
    const rim = ctx.createRadialGradient(cx, cy, R * .94, cx, cy, R * 1.04); rim.addColorStop(0, "rgba(90,169,255,0)"); rim.addColorStop(.6, "rgba(120,190,255,.55)"); rim.addColorStop(1, "rgba(90,169,255,0)");
    ctx.fillStyle = rim; ctx.beginPath(); ctx.arc(cx, cy, R * 1.04, 0, 7); ctx.fill();
  }
  let PXI = null;
  function pickBox(shown) {
    const x = t(), r = shown[sel];
    $("hmPick").innerHTML = r ? `<b>${esc(r.place[lang])}</b><div class="n">${sgn(r.effect_sd)} σ · ${esc(r.name[lang])}</div><a href="#/detail" id="hmGo">${esc(x.hmGo)}</a>` : `<div class="n">${esc(x.hmPick)}</div>`;
    const gg = $("hmGo"); if (gg) gg.onclick = e => { e.preventDefault(); ETD.openDetail({city: r.city, var: r.var}); };
  }
  function legend() {
    const x = t(), v = cur === "all" ? x.hlAll : (items.find(r => r.var === cur) || {name: {vi: "", en: ""}}).name[lang], h = HI.toFixed(1).replace(".", lang === "vi" ? "," : ".");
    if (heatOn) { $("hmLeg").innerHTML = heatMsg ? `<div>${esc(heatMsg)}</div>` : heatInfo && HEAT ? `<div>${esc(x.hmHeatNote(heatInfo.title, heatInfo.time.slice(0, 7)))}</div><img class="legimg" alt="" src="${esc(heatInfo.legend)}">` : ""; return; }
    $("hmLeg").innerHTML = `<div>${esc(x.hmScale(v))}</div><div class="bar" style="background:linear-gradient(90deg,${[0, .17, .33, .5, .67, .83, 1].map(k => rgba(ramp(k))).join(",")})"></div><div class="tk n"><span>−${h} σ ${esc(x.hlFall)}</span><span>0 · ${esc(x.hlNormal)}</span><span>+${h} σ ${esc(x.hlRise)}</span></div>`;
  }
  function select(i, scroll) {
    sel = i; const shown = shownList(), r = shown[i]; document.querySelectorAll(".hl-card").forEach(b => b.classList.toggle("on", +b.dataset.i === i));
    pickBox(shown); if (r) { tgt = {lat: r.lat, lon: r.lon}; idle = false; }
    if (scroll) { const el = document.querySelector(`.hl-card[data-i="${i}"]`); if (el) el.scrollIntoView({block: "nearest", behavior: "smooth"}); }
  }
  function tabs() {
    const x = t(), vars = []; items.forEach(r => { if (!vars.some(v => v.id === r.var)) vars.push({id: r.var, name: r.name[lang]}); });
    if (cur !== "all" && !vars.some(v => v.id === cur)) cur = "all";
    $("hlTabs").innerHTML = [{id: "all", name: x.hlAll}, ...vars].map(v => `<button role="tab" class="${v.id === cur ? "on" : ""}" data-t="${esc(v.id)}">${esc(v.name)}</button>`).join("");
    $("hlTabs").querySelectorAll("button").forEach(b => b.onclick = () => { cur = b.dataset.t; sel = -1; render(); });
  }
  function render() {
    const x = t(); $("hlProg").hidden = finished; $("hlBar").style.width = Math.round(100 * done / total) + "%";
    HI = Math.max(3, Math.ceil(Math.max(0, ...items.map(r => Math.abs(r.effect_sd)))));
    tabs(); const shown = shownList(); if (sel >= shown.length) sel = -1;
    const end = items.length ? items.map(r => r.end).sort().pop() : "", vn = cur === "all" ? x.hlAll : (items.find(r => r.var === cur) || {name: {vi: "", en: ""}}).name[lang];
    $("hlGrid").innerHTML = shown.map(card).join("") || (finished ? `<div class="empty">${esc(x.hlNone)}</div>` : "");
    $("hlTitle").textContent = shown.length ? x.hlSum(shown.length, shown[0].place[lang]) : x.hlSumNone;
    $("hlSub").textContent = vn + (end ? " · " + x.hlWin(end) : ""); $("hmTitle").textContent = cur === "all" ? x.hmTitle : vn; $("hmSub").textContent = x.hmSub;
    $("hlStatus").textContent = !finished ? x.hlProg(done, total) : "";
    $("st4").textContent = end || "–";
    initGlobe(); pickBox(shown); legend(); syncHeat();
    $("hlGrid").querySelectorAll(".hl-card").forEach(b => {
      b.onclick = () => { const r = shown[+b.dataset.i]; ETD.openDetail({city: r.city, var: r.var}); };
      b.onmouseenter = () => { if (+b.dataset.i !== sel) select(+b.dataset.i, false); };
    });
  }
  function texts() {
    const x = t(); for (const k of ["hlLabel", "hlNote", "ftSrc", "ftMeth", "st4l"]) $(k).textContent = x[k]; $("openDetail").textContent = x.openDetail;
    const cs = CITIES.map(c => `<option value="${c.id}">${esc(cityName(c))}</option>`).join(""); $("homeCity").innerHTML = cs; $("homeCity").value = pos.city || "hcm";
  }
  async function poll() {
    clearTimeout(timer);
    try {
      const r = await api(`/api/highlights?limit=60`), sig = JSON.stringify([r.items.map(i => i.city + i.var), r.done, r.finished]);
      done = r.done; total = r.total; finished = r.finished; items = r.items; tests = r.tests;
      if (sig !== last) { last = sig; render(); } else $("hlBar").style.width = Math.round(100 * done / total) + "%";
    } catch (e) { $("hlStatus").textContent = t().err + e.message; }
    if (!finished) timer = setTimeout(poll, 3500);
  }
  $("openDetail").onclick = () => ETD.openDetail({city: $("homeCity").value});
  $("homeCity").onchange = () => { if ($("homeCity").value) setCity($("homeCity").value); };
  document.addEventListener("citychange", () => { if (pos.city) $("homeCity").value = pos.city; });
  EXTRA.push(() => { texts(); render(); });
  function init() { texts(); render(); poll(); }
  if (window.APP_READY) init(); else document.addEventListener("app-ready", init);
})();

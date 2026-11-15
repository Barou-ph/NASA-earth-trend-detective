// Planner brief, evidence light, hero text, count-up numbers and scroll reveal. Loaded after app.js (shares its globals).
Object.assign(T.vi, {
 nHome:"Trang chủ", nBrief:"Bản tóm tắt", nLab:"Phòng phân tích", nGloss:"Chú giải",
 hEyebrow:"Cho nhà hoạch định đô thị và đơn vị tư vấn môi trường", hTitle:"Biến dữ liệu vệ tinh thành kết luận bạn dám tin.",
 hSub:"Chọn một thành phố, nhận bản tóm tắt một trang: chỉ số nào đang xấu đi, chắc đến đâu và nên xem xét hướng nào. Dữ liệu NASA, kiểm định chặt chẽ, nói thẳng điều chưa chắc.",
 hVar:"Chọn chỉ số, rồi di chuột vào một thành phố để xem xu hướng theo tuần", briefBtn:n => `Tạo bản tóm tắt cho ${n}`, custom2:"Điểm tự chọn",
 st1l:"thành phố", st2l:"chỉ số theo dõi", st3l:"năm dữ liệu",
 bEyebrow:"Bản tóm tắt cho nhà hoạch định", bTitle:"Một trang, mọi con số đều có độ tin cậy",
 bLead:"Tự quét mọi chỉ số của thành phố, hiệu chỉnh việc kiểm định nhiều chỉ số cùng lúc, chấm điểm tin cậy bằng 5 phép kiểm tra rồi gợi ý hướng nên xem xét theo bảng quy tắc công khai.",
 bRun:"Tạo bản tóm tắt", bPrint:"In / Lưu PDF", bCopy:"Sao chép văn bản", bCopied:"Đã sao chép ✓", bPlace:n => `Nơi đang chọn: ${n}`,
 bEmpty:"Chưa có bản tóm tắt. Chọn một thành phố trên bản đồ rồi bấm “Tạo bản tóm tắt”. Lần đầu có thể mất vài chục giây vì phải lấy dữ liệu từ NASA.",
 bPeriod:"Giai đoạn", bDate:"Ngày lập", bChanging:"Điều đang thay đổi, và mức tin cậy", bWatch:"Đáng theo dõi (chưa đủ chắc)", bActions:"Hướng nên xem xét",
 bActNote:"Theo bảng quy tắc công khai, không phải khuyến nghị chính sách. Chỉ đưa ra khi bằng chứng từ mức vừa trở lên.", bCav:"Điều chưa chắc",
 bSrc:"Nguồn: NASA POWER, OMI (NO₂), MODIS (AOD). Kiểm định: t-test hiệu chỉnh tự tương quan, Mann-Kendall, hiệu chỉnh FDR; điểm tin cậy từ 5 phép kiểm tra. Mọi con số do ứng dụng tự tính từ dữ liệu.",
 bCapped:"Hạ từ “mạnh” xuống “vừa” vì q ≥ 0,01 sau khi hiệu chỉnh nhiều chỉ số.", bNone:"Chưa chỉ số nào có xu hướng đáng tin sau hiệu chỉnh.", bNoAct:"Chưa có hướng nào đủ chắc để gợi ý.", bOver:y => `trong ${y} năm`, bSd:"độ lệch chuẩn", bTrusted:(n, m) => `${n}/${m} chỉ số đáng tin`,
 evT:"Điểm tin cậy của bằng chứng", evSum:(s, o, l) => `${s}/${o} phép kiểm tra đạt: bằng chứng ${l}`, evHint:"Điểm này đo độ vững của xu hướng, không phải mức độ nghiêm trọng.", colEv:"Điểm tin cậy",
 labEyebrow:"Phòng phân tích", labTitle:"Đi sâu vào số liệu", labLead:"Các công cụ phía sau bản tóm tắt: xu hướng, độ trễ, tháng bất thường, quét biến, xếp hạng và tải CSV của riêng bạn.",
 gVar:"Chỉ số trên quả địa cầu", gUp:"tăng", gDn:"giảm", gHint:"Chấm to = thay đổi lớn · nhấp nháy = vẫn có ý nghĩa khi so 22 thành phố", gYearMode:"Từng năm: màu và độ cao theo độ lệch so với mức thường của chính thành phố đó",
 gFinal:(a, b) => `${a}–${b}`, gSubFinal:"xu hướng cả kỳ", gSubYear:"so với mức thường", gAll:"Xu hướng cả kỳ", gPlay:"Xem từng năm", gPause:"Tạm dừng", gLoad:"Đang tải dữ liệu NASA…",
 gTipTrend:"Xu hướng", gTipQ:"q (đã hiệu chỉnh)", gTipTrust:"đáng tin", gTipNot:"chưa đủ chắc", gTipClick:"Bấm để chọn thành phố", gAnom:"độ lệch",
 gNoGl:"Không tải được quả địa cầu 3D. Các chức năng khác vẫn dùng bình thường."
});
Object.assign(T.en, {
 nHome:"Home", nBrief:"Brief", nLab:"Analysis lab", nGloss:"Glossary",
 hEyebrow:"For urban planners and environmental consultants", hTitle:"Turn satellite data into conclusions you dare to rely on.",
 hSub:"Pick a city and get a one-page brief: which indicators are getting worse, how sure we are, and which directions to consider. NASA data, rigorous tests, honest about what is uncertain.",
 hVar:"Pick an indicator, then hover a city to see its weekly trend", briefBtn:n => `Create brief for ${n}`, custom2:"Custom point",
 st1l:"cities", st2l:"indicators tracked", st3l:"years of data",
 bEyebrow:"Brief for decision makers", bTitle:"One page, every number with a trust level",
 bLead:"Scans every indicator for the city, corrects for testing many at once, scores trust with 5 checks, then suggests directions to consider from a public rule table.",
 bRun:"Create brief", bPrint:"Print / Save PDF", bCopy:"Copy text", bCopied:"Copied ✓", bPlace:n => `Selected place: ${n}`,
 bEmpty:"No brief yet. Pick a city on the map and press “Create brief”. The first run can take a few dozen seconds while NASA data is fetched.",
 bPeriod:"Period", bDate:"Prepared", bChanging:"What is changing, and how far to trust it", bWatch:"Worth watching (not yet certain)", bActions:"Directions to consider",
 bActNote:"From a public rule table, not policy recommendations. Shown only when evidence is moderate or better.", bCav:"What is uncertain",
 bSrc:"Sources: NASA POWER, OMI (NO₂), MODIS (AOD). Tests: autocorrelation-adjusted t-test, Mann-Kendall, FDR correction; trust score from 5 checks. Every number is computed by the app from the data.",
 bCapped:"Lowered from “strong” to “moderate” because q ≥ 0.01 after correcting for many indicators.", bNone:"No indicator shows a trustworthy trend after correction.", bNoAct:"No direction is certain enough to suggest.", bOver:y => `over ${y} years`, bSd:"std. deviations", bTrusted:(n, m) => `${n} of ${m} indicators trustworthy`,
 evT:"Evidence trust score", evSum:(s, o, l) => `${s} of ${o} checks passed: ${l} evidence`, evHint:"This score measures how robust the trend is, not how serious it is.", colEv:"Trust score",
 labEyebrow:"Analysis lab", labTitle:"Dig into the numbers", labLead:"The tools behind the brief: trends, lags, unusual months, variable scan, ranking and your own CSV.",
 gVar:"Indicator on the globe", gUp:"rising", gDn:"falling", gHint:"Big dot = big change · pulsing = still significant when comparing 22 cities", gYearMode:"Per year: colour and height show each city's deviation from its own normal",
 gFinal:(a, b) => `${a}–${b}`, gSubFinal:"whole-period trend", gSubYear:"vs normal", gAll:"Whole-period trend", gPlay:"Play by year", gPause:"Pause", gLoad:"Loading NASA data…",
 gTipTrend:"Trend", gTipQ:"q (adjusted)", gTipTrust:"trustworthy", gTipNot:"not certain", gTipClick:"Click to select this city", gAnom:"deviation",
 gNoGl:"The 3D globe could not load. Everything else still works."
});
G.evidence = {vi:["Điểm tin cậy của bằng chứng", "Năm phép kiểm tra: (1) cả hai kiểm định có ý nghĩa, (2) vẫn đúng khi bỏ ngoại lai, (3) cùng chiều ở hai nửa giai đoạn, (4) vẫn có ý nghĩa với trung bình năm, (5) đủ dữ liệu. Đạt 4–5 phép là mạnh, 3 là vừa, ít hơn là yếu."],
  en:["Evidence trust score", "Five checks: (1) both tests significant, (2) holds without outliers, (3) same direction in both halves, (4) still significant on yearly means, (5) enough data. 4–5 passed is strong, 3 moderate, fewer weak."]};

const TOPIC_LBL = {heat:{vi:"Nhiệt", en:"Heat"}, air:{vi:"Không khí", en:"Air"}, water:{vi:"Nước", en:"Water"}, energy:{vi:"Năng lượng", en:"Energy"}, wind:{vi:"Gió", en:"Wind"}, other:{vi:"Khác", en:"Other"}};
const sgn = v => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(2).replace(".", lang === "vi" ? "," : ".");
const dots = ev => `<span class="dots" aria-hidden="true"><span class="on">${"●".repeat(ev.score)}</span><span class="off">${"●".repeat(ev.of - ev.score)}</span></span>`;
const light = ev => `<span class="tl ${ev.level}" aria-hidden="true"><b class="r"></b><b class="a"></b><b class="g"></b></span>`;
const placeName = () => { const c = CITIES.find(c => c.id === pos.city); return c ? cityName(c) : t().custom2; };

// ------------------------------------------------------------ count-up and reveal
function countUp(el, to, ms = 1100, dec = 0) {
  if (!el) return;
  if (document.hidden || matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = to.toFixed(dec); return; }   // hidden tabs pause requestAnimationFrame
  const t0 = performance.now(); const step = now => { const k = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - k, 3);
    el.textContent = (to * e).toFixed(dec); if (k < 1) requestAnimationFrame(step); }; requestAnimationFrame(step);
}
const io = "IntersectionObserver" in window ? new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), {threshold:0, rootMargin:"0px 0px -6% 0px"}) : null;   // tall sections must reveal on any overlap
document.querySelectorAll(".reveal").forEach(el => io ? io.observe(el) : el.classList.add("in"));

// -------------------------------------------------------------------- hero + labels
function renderHero() {
  const x = t();
  for (const [id, k] of Object.entries({nHome:"nHome", nBrief:"nBrief", nLab:"nLab", nGloss:"nGloss", hEyebrow:"hEyebrow", hTitle:"hTitle", sub:"hSub", hVarLbl:"hVar",
      st1l:"st1l", st2l:"st2l", st3l:"st3l", bEyebrow:"bEyebrow", bTitle:"bTitle", bLead:"bLead", bRun:"bRun", bPrint:"bPrint", bCopy:"bCopy", briefEmpty:"bEmpty",
      labEyebrow:"labEyebrow", labTitle:"labTitle", labLead:"labLead"})) $(id).textContent = x[k];
  $("briefBtn").textContent = x.briefBtn(placeName()); $("bPlace").textContent = x.bPlace(placeName());
  const cs = CITIES.map(c => `<option value="${c.id}">${esc(cityName(c))}</option>`).join("");
  $("hCity").innerHTML = (pos.city ? "" : `<option value="">${esc(x.custom2)}</option>`) + cs; $("hCity").value = pos.city || "";
  renderBrief(); renderEvidence();
}
EXTRA.push(renderHero);
document.addEventListener("citychange", () => { $("briefBtn").textContent = t().briefBtn(placeName()); $("bPlace").textContent = t().bPlace(placeName());
  $("hCity").innerHTML = (pos.city ? "" : `<option value="">${esc(t().custom2)}</option>`) + CITIES.map(c => `<option value="${c.id}">${esc(cityName(c))}</option>`).join(""); $("hCity").value = pos.city || ""; });
$("hCity").onchange = () => { if ($("hCity").value) setCity($("hCity").value); };
document.addEventListener("app-ready", () => { countUp($("st1"), CITIES.length); countUp($("st2"), allVars().length); countUp($("st3"), +$("y1").value - +$("y0").value + 1); });
if (window.APP_READY) document.dispatchEvent(new Event("app-ready"));

// ----------------------------------------------------------------------- evidence box
function renderEvidence() {
  const a = S.a, ev = a && a.evidence, box = $("evBox"); box.hidden = !ev; if (!ev) return; const x = t();
  box.innerHTML = `<h3 title="${esc(tip("evidence"))}">${esc(x.evT)} ${light(ev)} ${evChip(ev)} ${dots(ev)}</h3><p class="note">${esc(x.evSum(ev.score, ev.of, EVTXT[ev.level][lang]))}. ${esc(x.evHint)}</p>
   <ul>${ev.checks.map(c => `<li class="${c.passed ? "yes" : "no"}"><i>${c.passed ? "✔" : "✘"}</i><span>${esc(c[lang])}</span></li>`).join("")}</ul>`;
}

// ---------------------------------------------------------------------------- brief
function renderBrief() {
  const b = S.brief, doc = $("briefDoc"); $("briefEmpty").hidden = !!b; doc.hidden = !b; $("bPrint").disabled = $("bCopy").disabled = !b; if (!b) return;
  const x = t(), nm = o => o.name[lang];
  const fcard = (f, i) => `<div class="fcard ${f.direction === "up" ? "up" : "dn"}" style="animation-delay:${i * 0.09}s">
    <div class="top"><span class="fname">${esc(nm(f))}</span><span class="fdir" aria-hidden="true">${f.direction === "up" ? "▲" : "▼"}</span></div>
    <div class="fbig">${sgn(f.effect_sd)} <small class="fsub">${esc(x.bSd)}</small></div>
    <div class="fsub">${f.total > 0 ? "+" : ""}${f3(f.total)} ${esc(f.unit)} ${esc(x.bOver(Math.round(f.span)))} · q ${fp(f.q)}</div>
    <div class="fev">${light(f.evidence)}${evChip(f.evidence)}${dots(f.evidence)}</div>${f.evidence.capped ? `<div class="fsub" style="margin-top:6px">${esc(x.bCapped)}</div>` : ""}</div>`;
  const act = (a, i) => `<div class="act" style="animation-delay:${i * 0.08}s"><span class="atag ${esc(a.topic)}">${esc(TOPIC_LBL[a.topic][lang])}</span>
    <div><div>${esc(a[lang])}</div><div class="fsub">${esc(nameOf(a.var) || a.var)} · ${evChip({level:a.level, score:0, of:5}).replace(/ · 0\/5/, "")}</div></div></div>`;
  doc.innerHTML = `<div class="bhead"><div><p class="plab" style="margin:0;color:var(--green);font-weight:700;font-size:.8rem;letter-spacing:.09em">${esc(x.bEyebrow.toUpperCase())}</p>
     <div class="bplace">${esc(b.place[lang])}</div></div>
     <div class="bmeta">${esc(x.bPeriod)}: ${b.period[0]}–${b.period[1]}<br>${esc(x.bDate)}: ${esc(b.generated)}<br><b>${esc(x.bTrusted(b.n_trusted, b.n_vars))}</b></div></div>
   <p class="bhl">${esc(b.headline[lang])}</p>
   <div class="bsec"><h3>${esc(x.bChanging)}</h3><div class="fgrid">${b.findings.length ? b.findings.map(fcard).join("") : `<p class="note">${esc(x.bNone)}</p>`}</div></div>
   ${b.watch.length ? `<div class="bsec"><h3>${esc(x.bWatch)}</h3><ul class="cav">${b.watch.map(w => `<li>${esc(nm(w))}: ${w.direction === "up" ? "▲" : "▼"} ${sgn(w.effect_sd)} ${esc(x.bSd)}, q ${fp(w.q)}</li>`).join("")}</ul></div>` : ""}
   <div class="bsec"><h3>${esc(x.bActions)}</h3><p class="note" style="margin:0 0 10px">${esc(x.bActNote)}</p>
     <div class="alist">${b.actions.length ? b.actions.map(act).join("") : `<p class="note">${esc(x.bNoAct)}</p>`}</div></div>
   <div class="bsec"><h3>${esc(x.bCav)}</h3><ul class="cav">${b.caveats.map(c => `<li>${esc(c[lang])}</li>`).join("")}</ul></div>
   <p class="bfoot">${esc(x.bSrc)}</p>`;
}
async function runBrief() {
  $("briefEmpty").hidden = false; $("briefEmpty").innerHTML = `<div class="skel"></div>`; $("briefDoc").hidden = true;
  try { S.brief = await api(`/api/brief?${place()}&${range()}`); }
  catch (e) { $("briefEmpty").textContent = t().bEmpty; throw e; }
  renderHero(); $("brief").scrollIntoView({behavior:"smooth", block:"start"});
}
function briefText() {
  const b = S.brief; if (!b) return ""; const x = t(), nm = o => o.name[lang];
  return [b.place[lang] + " (" + b.period.join("–") + ")", b.headline[lang], "",
    x.bChanging + ":", ...b.findings.map(f => `- ${nm(f)}: ${f.direction === "up" ? "▲" : "▼"} ${sgn(f.effect_sd)} ${x.bSd}; ${EVTXT[f.evidence.level][lang]} (${f.evidence.score}/${f.evidence.of})`), "",
    x.bActions + ":", ...b.actions.map(a => `- [${TOPIC_LBL[a.topic][lang]}] ${a[lang]}`), "", x.bCav + ":", ...b.caveats.map(c => "- " + c[lang])].join("\n");
}
$("briefBtn").onclick = e => task(e.currentTarget, runBrief);
$("bRun").onclick = e => task(e.currentTarget, runBrief);
$("bPrint").onclick = () => window.print();
$("bCopy").onclick = async () => { const text = briefText();
  try { await navigator.clipboard.writeText(text); } catch (e) { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
  $("bCopy").textContent = t().bCopied; setTimeout(() => { $("bCopy").textContent = t().bCopy; }, 1500); };
S.brief = null;
renderHero();

// HUD shell: labels, slide-over drawers (brief, lab, glossary). Loaded after app.js and brief.js, before globe.js.
Object.assign(T.vi, {
  brandSub: "Xu hướng khí hậu và không khí từ dữ liệu NASA", nDetail: "Chi tiết · bản đồ vệ tinh",
  fLabel: "Chỉ số", fSensor: "NASA POWER · OMI · MODIS", tLock: "VÙNG KHÓA VỆ TINH", m1l: "Xu hướng", m2l: "Thay đổi cả kỳ", tOk: "đáng tin", tNo: "chưa đủ chắc",
  tAlertOk: "Xu hướng vẫn có ý nghĩa sau hiệu chỉnh FDR. Mở bản tóm tắt để xem điểm tin cậy và hướng nên xem xét.",
  tAlertNo: "Chưa đủ chắc sau khi hiệu chỉnh cho nhiều thành phố. Đừng kết luận chỉ từ một chỉ số này.",
  tAlertPt: "Điểm tự chọn trên bản đồ: chưa có số liệu trên quả địa cầu. Dùng Phòng phân tích để phân tích điểm này.",
  tQ: "q (đã hiệu chỉnh)", tP: "p (t-test)", tMk: "p (Mann-Kendall)", tRank: "Xếp hạng độ thay đổi", tPer: "Giai đoạn", tPresets: "Điểm nóng", tClose: "Đóng"
});
Object.assign(T.en, {
  brandSub: "Climate and air trends from NASA data", nDetail: "Detail · satellite map",
  fLabel: "Indicator", fSensor: "NASA POWER · OMI · MODIS", tLock: "SATELLITE LOCK", m1l: "Trend", m2l: "Change over period", tOk: "trusted", tNo: "not certain",
  tAlertOk: "The trend still holds after FDR correction. Open the brief for the trust score and directions to consider.",
  tAlertNo: "Not certain after correcting for many cities. Do not conclude from this single indicator.",
  tAlertPt: "Custom point: no globe data for it. Use the Analysis lab to analyse this point.",
  tQ: "q (adjusted)", tP: "p (t-test)", tMk: "p (Mann-Kendall)", tRank: "Change rank", tPer: "Period", tPresets: "Hotspots", tClose: "Close"
});

const DRAWERS = ["brief", "cycleD", "lab", "glossD"];
const BTN = {brief: "nBrief", cycleD: "nCycle", lab: "nLab", glossD: "nGloss"};
function closeDrawers() {
  DRAWERS.forEach(d => { $(d).classList.remove("open"); $(BTN[d]).classList.remove("on"); }); $("backdrop").classList.remove("on");
}
function openDrawer(id) {
  DRAWERS.forEach(d => { const on = d === id; $(d).classList.toggle("open", on); $(BTN[d]).classList.toggle("on", on); });
  $("backdrop").classList.add("on");
  if (id === "lab") setTimeout(() => map.invalidateSize(), 560);          // the Leaflet map in the lab was laid out while the drawer was off-screen
}
DRAWERS.forEach(d => { $(BTN[d]).onclick = () => $(d).classList.contains("open") ? closeDrawers() : openDrawer(d); });
document.querySelectorAll("[data-close]").forEach(b => b.onclick = closeDrawers);
$("backdrop").onclick = closeDrawers;
$("nHome").addEventListener("click", closeDrawers);
$("nDetail").addEventListener("click", closeDrawers);
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDrawers(); });
// results are rendered inside drawers: opening the right drawer first makes scrollIntoView() work as before
const _scroll = Element.prototype.scrollIntoView;
Element.prototype.scrollIntoView = function (o) { const d = this.closest && this.closest(".drawer"); if (d && !d.classList.contains("open")) openDrawer(d.id); return _scroll.call(this, o); };

function renderHud() {
  const x = t();
  for (const k of ["brandSub", "nDetail", "fLabel", "fSensor", "tLock", "m2l"]) { const e = $(k); if (e) e.textContent = x[k]; }
  document.querySelectorAll("[data-close]").forEach(b => b.setAttribute("aria-label", x.tClose));
}
EXTRA.push(renderHud);
renderHud();
const _open = new URLSearchParams(location.search).get("open");
if (_open && DRAWERS.includes(_open)) openDrawer(_open);

// keep the left panel between the top bar and the bottom bar whatever their wrapped height
function fitHud() {
  const r = document.documentElement.style, top = $("topbar").getBoundingClientRect().bottom, bot = innerHeight - $("botbar").getBoundingClientRect().top;
  if (top > 0) r.setProperty("--topH", Math.round(top + 10) + "px"); if (bot > 0 && bot < innerHeight) r.setProperty("--botH", Math.round(bot + 10) + "px");
}
if ("ResizeObserver" in window) { const ro = new ResizeObserver(fitHud); ro.observe($("topbar")); ro.observe($("botbar")); }
addEventListener("resize", fitHud); EXTRA.push(() => requestAnimationFrame(fitHud)); fitHud();

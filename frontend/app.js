// Set true to serve frontend/mock/*.json instead of the API (or open the page with ?mock=1).
const USE_MOCK = false;
const MOCK = USE_MOCK || /[?&]mock=1/.test(location.search);
const MOCK_FILE = {"/api/analyze":"analyze","/api/lag":"lag","/api/anomaly":"anomaly","/api/ranking":"ranking","/api/upload":"upload","/api/summary":"summary","/api/scan":"scan","/api/weekly":"weekly","/api/heatlayers":"heatlayers","/api/cycle":"cycle","/api/correlations":"correlations","/api/highlights":"highlights",
  "/api/brief":"brief","/api/globe":"globe","/api/presets":"presets","/api/grid":"grid","/api/variables":"variables","/api/cities":"cities"};

const $ = id => document.getElementById(id);
const EXTRA = [];          // render hooks added by brief.js / globe.js; called after every language change
const T = {
vi:{sub:"Chọn một biến và một nơi, rồi kiểm tra xu hướng, độ trễ giữa hai biến và các tháng bất thường. Dữ liệu: NASA POWER và file Giovanni.",
 l1:"1. Chọn biến",l2:"2. Chọn nơi (danh sách hoặc bấm lên bản đồ)",des:"Bỏ chu kỳ mùa",ann:"Trung bình năm",run:"Phân tích",grid:"Bản đồ xu hướng 3×3",demo:"Chạy ca TP.HCM",
 pt:"Điểm",custom:"— Điểm tự chọn trên bản đồ —",wait:"Đang lấy dữ liệu từ NASA…",err:"Lỗi: ",neterr:"Không kết nối được máy chủ. Hãy kiểm tra mạng rồi thử lại.",
 badyears:"Năm bắt đầu phải nhỏ hơn năm kết thúc.",nofile:"Hãy chọn một file CSV trước.",
 res:"Xu hướng",src:"Nguồn",slope:"Độ dốc",ci:"Khoảng tin cậy 95%",pt_:"p (t-test)",mk:"Mann-Kendall τ / p",sen:"Độ dốc Sen",r1:"Tự tương quan r₁",neff:"Số mẫu hiệu dụng",total:"Tổng thay đổi",n:"Số điểm",
 sig:"có ý nghĩa",nosig:"chưa có ý nghĩa",data:"dữ liệu",trend:"xu hướng",band:"khoảng tin cậy của xu hướng",year:"năm",perYear:"/năm",
 lagT:"Độ trễ giữa hai biến",lagA:"Biến A:",lagB:"Biến B (đi sau A)",lagRun:"Tính độ trễ",month:"tháng",lagBest:"Độ trễ tốt nhất",lagCorr:"tương quan",lagSig:"có ý nghĩa thống kê",lagNo:"chưa có ý nghĩa thống kê",lagAxis:"Độ trễ của B so với A (tháng)",
 anoT:"Tháng bất thường",anoRun:"Tìm tháng bất thường",anoBand:"Dải 5–95% cùng tháng",anoHigh:"Cao bất thường",anoLow:"Thấp bất thường",anoFlag:n=>`${n} tháng bị gắn cờ (ngoài dải 5–95% của cùng tháng).`,
 rankT:"Xếp hạng thành phố",rankRun:"Xếp hạng",cmp:"So sánh đã chọn",rankNote:"Dùng biến đang chọn, trung bình năm đã bỏ mùa. Tích chọn 2–5 thành phố để so sánh.",
 cmpNeed:"Hãy chọn từ 2 đến 5 thành phố.",cmpTitle:"So sánh (trung bình năm, đã bỏ mùa)",colCity:"Thành phố",colSlope:"Độ dốc",colP:"p",colSig:"Ý nghĩa",
 upT:"Tải CSV của bạn",upHelp:"CSV kiểu Giovanni: bỏ dòng bắt đầu bằng #, cột đầu là thời gian, cột cuối là giá trị. Tối đa 5 MB.",upRun:"Phân tích file",upName:"Tên chuỗi (tùy chọn)",upUnit:"Đơn vị",upDrop:"Thả file CSV vào đây hoặc bấm để chọn",
 sumT:"Tóm tắt tự động",sumRun:"Tạo tóm tắt",sumCopy:"Sao chép",sumCopied:"Đã sao chép ✓",sumNote:"Viết tự động từ chính các số liệu của biểu đồ (theo quy tắc, không dùng AI).",
 sumSrc:(a,b)=>`Nguồn số liệu: NASA POWER, ${a}–${b}. Các câu trên được sinh từ kết quả thống kê, hãy đọc cùng biểu đồ.`,sumYear:"Trung bình năm",sumFirst:n=>`TB ${n} năm đầu`,sumLast:n=>`TB ${n} năm gần nhất`,sumMax:"Cao nhất",sumMin:"Thấp nhất",
 cSlope:"Xu hướng",cDiff:"Gần đây so với ban đầu",cAno:"Tháng cao bất thường (5 năm gần nhất)",cRank:"Xếp hạng thành phố",cLag:"Tương quan với biến B",
 demo2:"Ca xu hướng ngược chiều",rgAll:"Cả thế giới (22 thành phố)",rgVn:"Việt Nam (12)",rgWorld:"Thế giới (10)",notPower:"Xếp hạng thành phố chỉ có cho biến NASA POWER, không dùng cho chuỗi Giovanni.",
 qT:"Chất lượng dữ liệu",qCov:"Độ phủ",qMiss:"Tháng thiếu",qGap:"Khoảng trống dài nhất",qOutN:"Tháng ngoại lai",qMonth:"Số tháng thiếu theo tháng lịch",qOutList:"Ngoại lai lớn nhất: ",months:"tháng",
 scanT:"Quét biến: biến nào đang có xu hướng?",scanHelp:"Chạy tất cả biến cho nơi đang chọn và xếp theo mức bằng chứng. Các biến có đơn vị khác nhau nên so bằng mức thay đổi tính theo độ lệch chuẩn.",scanRun:"Quét tất cả biến",
 scanNote:(n,m)=>`${n}/${m} biến có xu hướng đáng tin sau hiệu chỉnh nhiều phép thử (FDR).`,colVar:"Biến",colTrend:"Xu hướng",colEff:"Thay đổi (độ lệch chuẩn)",colQ:"q (đã hiệu chỉnh)",colRes:"Kết luận",
 rFdr:"đáng tin (sau hiệu chỉnh)",rSig:"có ý nghĩa, nhưng có thể do ngẫu nhiên",rNo:"chưa có ý nghĩa",src_p:"NASA POWER",src_g:"Giovanni (vệ tinh)",
 oppBoth:(u,d)=>`Cùng một biến nhưng đi ngược chiều: TĂNG ở ${u}; GIẢM ở ${d} (có ý nghĩa sau hiệu chỉnh FDR).`,oppOne:(w,l)=>`Chỉ thấy xu hướng ${w} có ý nghĩa sau hiệu chỉnh FDR ở: ${l}. Chưa có thành phố đi ngược chiều.`,oppNone:"Chưa thành phố nào có xu hướng đáng tin sau hiệu chỉnh FDR.",
 oppUp:"tăng",oppDown:"giảm",rankFdr:"✔ đáng tin sau hiệu chỉnh FDR; (✔) có ý nghĩa nhưng có thể do ngẫu nhiên khi so nhiều thành phố; – chưa có ý nghĩa.",
 glossT:"Chú giải thuật ngữ (bấm để mở)",
 foot:"Chỉ xu hướng tuyến tính. p-value đã hiệu chỉnh tự tương quan bậc 1. Tương quan không chứng minh nhân quả."},
en:{sub:"Pick a variable and a place, then test the trend, the lag between two variables and unusual months. Data: NASA POWER and Giovanni files.",
 l1:"1. Choose a variable",l2:"2. Choose a place (list or click the map)",des:"Remove seasonal cycle",ann:"Yearly averages",run:"Analyze",grid:"3×3 trend map",demo:"Run the HCMC case",
 pt:"Point",custom:"— Custom point on the map —",wait:"Fetching data from NASA…",err:"Error: ",neterr:"Cannot reach the server. Check your connection and try again.",
 badyears:"Start year must be before end year.",nofile:"Choose a CSV file first.",
 res:"Trend",src:"Source",slope:"Slope",ci:"95% confidence interval",pt_:"p (t-test)",mk:"Mann-Kendall τ / p",sen:"Sen slope",r1:"Lag-1 autocorrelation r₁",neff:"Effective sample size",total:"Total change",n:"Points",
 sig:"significant",nosig:"not significant",data:"data",trend:"trend",band:"trend confidence band",year:"year",perYear:"/yr",
 lagT:"Lag between two variables",lagA:"Variable A:",lagB:"Variable B (follows A)",lagRun:"Compute lag",month:"months",lagBest:"Best lag",lagCorr:"correlation",lagSig:"statistically significant",lagNo:"not statistically significant",lagAxis:"Lag of B behind A (months)",
 anoT:"Unusual months",anoRun:"Find unusual months",anoBand:"5–95% band of the same month",anoHigh:"Unusually high",anoLow:"Unusually low",anoFlag:n=>`${n} months flagged (outside the 5–95% band of the same calendar month).`,
 rankT:"City ranking",rankRun:"Rank cities",cmp:"Compare selected",rankNote:"Uses the selected variable, de-seasoned yearly means. Tick 2–5 cities to compare.",
 cmpNeed:"Select between 2 and 5 cities.",cmpTitle:"Comparison (yearly means, de-seasoned)",colCity:"City",colSlope:"Slope",colP:"p",colSig:"Significant",
 upT:"Upload your CSV",upHelp:"Giovanni-style CSV: lines starting with # are skipped, first column = time, last column = value. Max 5 MB.",upRun:"Analyze file",upName:"Series name (optional)",upUnit:"Unit",upDrop:"Drop a CSV here or click to choose",
 sumT:"Automatic summary",sumRun:"Generate summary",sumCopy:"Copy",sumCopied:"Copied ✓",sumNote:"Written automatically from the numbers behind the charts (rule-based, no AI).",
 sumSrc:(a,b)=>`Data source: NASA POWER, ${a}–${b}. These sentences are generated from the statistics; read them together with the charts.`,sumYear:"Yearly mean",sumFirst:n=>`Mean of first ${n} years`,sumLast:n=>`Mean of latest ${n} years`,sumMax:"Highest",sumMin:"Lowest",
 cSlope:"Trend",cDiff:"Recent vs early years",cAno:"Unusually high months (last 5 years)",cRank:"City rank",cLag:"Correlation with variable B",
 demo2:"Opposite-trend case",rgAll:"Worldwide (22 cities)",rgVn:"Vietnam (12)",rgWorld:"World (10)",notPower:"City ranking is only available for NASA POWER variables, not Giovanni series.",
 qT:"Data quality",qCov:"Coverage",qMiss:"Missing months",qGap:"Longest gap",qOutN:"Outlier months",qMonth:"Missing months by calendar month",qOutList:"Largest outliers: ",months:"months",
 scanT:"Variable scan: which variables are trending?",scanHelp:"Runs every variable for the selected place and ranks them by strength of evidence. Units differ, so they are compared by total change in standard deviations.",scanRun:"Scan all variables",
 scanNote:(n,m)=>`${n} of ${m} variables show a trustworthy trend after correcting for multiple tests (FDR).`,colVar:"Variable",colTrend:"Trend",colEff:"Change (std. deviations)",colQ:"q (adjusted)",colRes:"Verdict",
 rFdr:"trustworthy (after correction)",rSig:"significant, but may be chance",rNo:"not significant",src_p:"NASA POWER",src_g:"Giovanni (satellite)",
 oppBoth:(u,d)=>`Same variable, opposite directions: RISING in ${u}; FALLING in ${d} (significant after FDR correction).`,oppOne:(w,l)=>`Only ${w} trends are significant after FDR correction, in: ${l}. No city goes the other way.`,oppNone:"No city shows a trustworthy trend after FDR correction.",
 oppUp:"rising",oppDown:"falling",rankFdr:"✔ trustworthy after FDR correction; (✔) significant but may be chance when comparing many cities; – not significant.",
 glossT:"Glossary of terms (click to open)",
 foot:"Linear trends only. p-values are adjusted for lag-1 autocorrelation. Correlation does not prove causation."}};

// Plain-language definitions: used for the glossary and as tooltips on the number tiles.
const G = {
 slope:{vi:["Độ dốc","Trung bình mỗi năm giá trị tăng (+) hay giảm (−) bao nhiêu, theo đơn vị của biến. Tính bằng hồi quy tuyến tính."],en:["Slope","How much the value rises (+) or falls (−) per year on average, in the variable's unit. Computed by linear regression."]},
 total:{vi:["Tổng thay đổi","Độ dốc nhân với số năm của chuỗi: mức thay đổi ước tính trong cả giai đoạn."],en:["Total change","Slope times the length of the record: the estimated change over the whole period."]},
 ci:{vi:["Khoảng tin cậy 95%","Khoảng mà độ dốc thật nhiều khả năng nằm trong. Nếu khoảng chứa số 0 thì chưa loại trừ được khả năng 'không đổi'."],en:["95% confidence interval","The range where the true slope most likely lies. If it contains 0, 'no change' cannot be ruled out."]},
 p:{vi:["p-value (t-test)","Xác suất thấy độ dốc lớn như vậy nếu thực tế không có xu hướng. p nhỏ hơn 0,05 thường coi là có ý nghĩa. Đã hiệu chỉnh tự tương quan."],en:["p-value (t-test)","The chance of seeing a slope this large if there were really no trend. p below 0.05 is usually called significant. Adjusted for autocorrelation."]},
 mk:{vi:["Mann-Kendall","Kiểm định không tham số: so từng cặp điểm xem phía sau cao hơn hay thấp hơn. τ gần +1 là tăng nhất quán, gần −1 là giảm nhất quán, gần 0 là không rõ."],en:["Mann-Kendall","A rank-based test comparing every pair of points. τ near +1 means consistently rising, near −1 consistently falling, near 0 unclear."]},
 sen:{vi:["Độ dốc Sen","Trung vị độ dốc của mọi cặp điểm; ít bị ngoại lai kéo lệch hơn độ dốc hồi quy."],en:["Sen slope","The median slope over all pairs of points; less affected by outliers than the regression slope."]},
 r1:{vi:["Tự tương quan r₁","Mức các tháng liền nhau giống nhau. Càng cao thì các điểm càng không độc lập."],en:["Autocorrelation r₁","How alike neighbouring months are. The higher it is, the less independent the points."]},
 neff:{vi:["Số mẫu hiệu dụng","Số điểm 'độc lập' tương đương sau khi trừ tự tương quan. Càng nhỏ so với tổng số điểm thì càng phải thận trọng."],en:["Effective sample size","The number of 'independent' points after discounting autocorrelation. The smaller it is versus the total, the more caution is needed."]},
 deseason:{vi:["Bỏ chu kỳ mùa","Trừ trung bình của đúng tháng đó qua các năm, để mùa nóng–lạnh hay mùa mưa–khô không che mất xu hướng."],en:["Removing the seasonal cycle","Subtracting the average of the same calendar month across years so hot–cold or wet–dry seasons do not hide the trend."]},
 fdr:{vi:["Hiệu chỉnh FDR (q)","Khi kiểm định nhiều thành phố hoặc nhiều biến cùng lúc, vài kết quả 'có ý nghĩa' có thể chỉ do ngẫu nhiên. q là p-value đã hiệu chỉnh theo Benjamini–Hochberg; q < 0,05 đáng tin hơn."],en:["FDR correction (q)","When many cities or variables are tested at once, a few 'significant' results can be pure chance. q is the p-value adjusted by Benjamini–Hochberg; q < 0.05 is more trustworthy."]},
 effect:{vi:["Thay đổi theo độ lệch chuẩn","Tổng thay đổi chia cho độ dao động thông thường của biến, để so sánh các biến có đơn vị khác nhau."],en:["Change in standard deviations","Total change divided by the variable's usual fluctuation, so variables with different units can be compared."]},
 lag:{vi:["Độ trễ và tương quan r","r từ −1 đến +1 cho biết hai biến cùng chiều hay ngược chiều sau khi bỏ mùa và xu hướng chung. Tương quan không chứng minh nhân quả."],en:["Lag and correlation r","r from −1 to +1 shows whether two variables move together or oppositely after removing seasons and shared trends. Correlation does not prove causation."]},
 anomaly:{vi:["Tháng bất thường","Tháng nằm ngoài dải 5–95% của cùng tháng qua các năm. Theo cách tính, khoảng 10% tháng bị gắn cờ, nên hãy chú ý chỗ chúng dồn lại."],en:["Unusual months","Months outside the 5–95% band of the same calendar month across years. About 10% are flagged by construction, so look for where they cluster."]},
 missing:{vi:["Tháng thiếu và ngoại lai","Tháng thiếu không được nội suy (không bịa số). Ngoại lai được giữ lại và đánh dấu vì có thể là sự kiện thật như khói cháy rừng."],en:["Missing months and outliers","Missing months are not interpolated (no invented numbers). Outliers are kept and flagged because they may be real events such as smoke haze."]},
 aod:{vi:["AOD (độ dày quang học sol khí)","Mức bụi mịn và khói làm mờ bầu khí quyển. Số càng lớn càng nhiều hạt lơ lửng. Đo bởi vệ tinh MODIS."],en:["AOD (aerosol optical depth)","How much dust and smoke dims the atmosphere. Larger means more suspended particles. Measured by the MODIS satellite."]},
 no2:{vi:["NO₂ tầng đối lưu","Lượng khí nitơ đioxit trong cột không khí gần mặt đất, chủ yếu từ giao thông và công nghiệp. Đo bởi vệ tinh OMI."],en:["Tropospheric NO₂","Nitrogen dioxide in the air column near the ground, mostly from traffic and industry. Measured by the OMI satellite."]},
};
const tip = k => G[k] ? G[k][lang][1] : "";
const TOPICS = {heat:{vi:"Nhiệt độ",en:"Heat"},water:{vi:"Nước & mưa",en:"Water & rain"},air:{vi:"Không khí",en:"Air"},land:{vi:"Mặt trời, mây & cháy",en:"Sun, clouds & fire"}};
const COLORS = ["#34D399","#FF8A3D","#38BDF8","#C084FC","#A3E635"];

let lang = new URLSearchParams(location.search).get("lang") === "en" ? "en" : "vi", VARS = [], CITIES = [], PRESETS = [];
let pos = {lat:10.78, lon:106.7, city:"hcm"};
const S = {scan:null, sum:null, a:null, lag:null, ano:null, rank:null, cmp:null};     // last results, re-rendered on language change
let aMeta = null;                                                 // {unit, label} of the last analysis

// ------------------------------------------------------------------ helpers
const t = () => T[lang];
const f3 = x => (x === null || x === undefined || !isFinite(x)) ? "–" : +x.toPrecision(3);
const fp = p => p < 0.001 ? "<0.001" : String(+p.toPrecision(p < 0.1 ? 3 : 2));      // 0.0497 must not read as 0.05
const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const allVars = () => VARS.concat(PRESETS.filter(p => p.kind === "csv" && p.available).map(p => ({id:p.id, topic:p.topic || "air", unit:p.unit || "", name:p.name, desc:p.desc})));
const varOf = id => allVars().find(v => v.id === id);
const cur = () => varOf($("var").value) || {unit:"", name:{vi:"", en:""}};
const nameOf = id => (varOf(id) || {name:{vi:id, en:id}}).name[lang];
const cityName = c => c.name[lang];
const EVTXT = {strong:{vi:"mạnh", en:"strong"}, moderate:{vi:"vừa", en:"moderate"}, weak:{vi:"yếu", en:"weak"}, none:{vi:"chưa có", en:"none"}};
const evChip = ev => ev ? `<span class="ev ${ev.level}" title="${esc(tip("evidence"))}"><i></i>${EVTXT[ev.level][lang]} · ${ev.score}/${ev.of}</span>` : "";

async function api(path, init) {
  let url = path;
  if (MOCK) { await sleep(300); url = "mock/" + MOCK_FILE[path.split("?")[0]] + ".json"; init = undefined; }
  let r;
  try { r = await fetch(url, init); } catch (e) { throw new Error(t().neterr); }
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    const d = e.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map(x => x.msg).join("; ") : "HTTP " + r.status);
  }
  return r.json();
}
function showErr(msg) { const e = $("err"); e.textContent = t().err + msg; e.style.display = "block"; }
function clearErr() { $("err").style.display = "none"; $("err").textContent = ""; }
// Runs fn with a spinner on btn, a status line and an inline error banner (no alert()).
async function task(btn, fn) {
  clearErr(); btn.disabled = true; btn.classList.add("load"); $("status").textContent = t().wait;
  try { await fn(); } catch (e) { showErr(e.message); }
  finally { btn.disabled = false; btn.classList.remove("load"); $("status").textContent = ""; }
}
function place() { return pos.city ? `city=${encodeURIComponent(pos.city)}` : `lat=${pos.lat}&lon=${pos.lon}`; }
function range() {
  const y0 = +$("y0").value, y1 = +$("y1").value;
  if (!(y0 < y1)) throw new Error(t().badyears);
  return `start=${y0}&end=${y1}`;
}
const deepMerge = (a, b) => { const o = Object.assign({}, a);
  for (const k in b) o[k] = (b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a && a[k] && typeof a[k] === "object") ? deepMerge(a[k], b[k]) : b[k];
  return o; };
const AX = {gridcolor:"rgba(120,220,170,.12)", zerolinecolor:"rgba(120,220,170,.35)", linecolor:"rgba(120,220,170,.25)"};
const plot = (id, data, layout) => { $(id).hidden = false;
  const base = {margin:{t:10,r:12,b:44,l:56}, legend:{orientation:"h", y:-0.22}, hovermode:"closest", paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font:{family:"Be Vietnam Pro, Segoe UI, system-ui, sans-serif", size:13, color:"#CFE6D9"}, xaxis:AX, yaxis:AX,
    hoverlabel:{bgcolor:"#08180F", bordercolor:"#34D399", font:{color:"#E6F5EC"}}};
  return Plotly.react(id, data, deepMerge(base, layout), {responsive:true, displayModeBar:false}); };

// --------------------------------------------------------------------- map
const announce = () => document.dispatchEvent(new CustomEvent("citychange", {detail:pos}));
const map = L.map("map").setView([pos.lat, pos.lon], 6);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {attribution:"© OpenStreetMap"}).addTo(map);
const marker = L.marker([pos.lat, pos.lon]).addTo(map), layer = L.layerGroup().addTo(map), cityLayer = L.layerGroup().addTo(map);
map.on("click", e => { pos = {lat:+e.latlng.lat.toFixed(2), lon:+e.latlng.lng.toFixed(2), city:null}; marker.setLatLng(e.latlng); $("city").value = ""; label(); announce(); });
function setCity(id) {
  const c = CITIES.find(x => x.id === id);
  if (!c) { pos.city = null; return; }
  pos = {lat:c.lat, lon:c.lon, city:c.id}; marker.setLatLng([c.lat, c.lon]); $("city").value = c.id; label(); announce();
}
function drawCities() {
  cityLayer.clearLayers();
  CITIES.forEach(c => L.circleMarker([c.lat, c.lon], {radius:5, color:"#34D399", weight:1, fillOpacity:.5}).bindTooltip(cityName(c))
    .on("click", ev => { L.DomEvent.stopPropagation(ev); setCity(c.id); }).addTo(cityLayer));
}
function label() { $("pt").textContent = `${t().pt}: ${pos.lat}, ${pos.lon}`; }

// -------------------------------------------------------------- static text
function txt() {
  const x = t();
  for (const k of ["sub","l1","l2","foot"]) $(k).textContent = x[k];
  Object.entries({ldes:"des", lann:"ann", run:"run", grid:"grid", demo:"demo", resT:"res", lagT:"lagT", lagRun:"lagRun", anoT:"anoT", anoRun:"anoRun",
    rankT:"rankT", rankRun:"rankRun", rankCmp:"cmp", upT:"upT", upHelp:"upHelp", upRun:"upRun", rankNote:"rankNote", demo2:"demo2", qT:"qT", scanT:"scanT", scanHelp:"scanHelp", scanRun:"scanRun", glossT:"glossT", sumT:"sumT", sumRun:"sumRun", sumCopy:"sumCopy", sumNote:"sumNote"}).forEach(([id, k]) => $(id).textContent = x[k]);
  $("lagALbl").textContent = x.lagA + " " + nameOf($("var").value);
  const rg = $("region").value || "all";
  $("region").innerHTML = [["all", x.rgAll], ["vn", x.rgVn], ["world", x.rgWorld]].map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join(""); $("region").value = rg;
  $("glossList").innerHTML = Object.values(G).map(g => `<dt>${esc(g[lang][0])}</dt><dd>${esc(g[lang][1])}</dd>`).join("");
  $("upName").placeholder = x.upName; $("upUnit").placeholder = x.upUnit; $("lang").textContent = lang === "vi" ? "EN" : "VI";
  document.documentElement.lang = lang; label();
  const tp = $("topic").value || "heat";
  $("topic").innerHTML = Object.keys(TOPICS).map(k => `<option value="${k}">${TOPICS[k][lang]}</option>`).join(""); $("topic").value = tp;
  fillVars();
  $("city").innerHTML = `<option value="">${esc(x.custom)}</option>` + CITIES.map(c => `<option value="${c.id}">${esc(cityName(c))}</option>`).join("");
  $("city").value = pos.city || "";
  drawCities(); renderAll(); EXTRA.forEach(f => f());
}
function fillVars() {
  const tp = $("topic").value, vs = $("var").value, list = allVars().filter(v => v.topic === tp);
  $("var").innerHTML = list.map(v => `<option value="${v.id}">${esc(v.name[lang])}</option>`).join("");
  if (vs && list.some(v => v.id === vs)) $("var").value = vs;
  $("desc").textContent = cur().desc ? cur().desc[lang] : "";
  const b = $("varB").value;
  $("varB").innerHTML = allVars().map(v => `<option value="${v.id}">${esc(v.name[lang])}</option>`).join("");
  if (b && allVars().some(v => v.id === b)) $("varB").value = b; else if (!b) $("varB").value = "RH2M";
  $("lagALbl").textContent = t().lagA + " " + nameOf($("var").value);
}

// ------------------------------------------------------- 1. trend + tiles
function renderAnalysis() {
  const a = S.a; if (!a) return; $("out").hidden = false;
  const x = t(), u = aMeta.unit, ub = u ? " " + u : "";
  $("srcTitle").textContent = `${x.src}: ${aMeta.label[lang]}`;
  const n = a.t.length, tb = a.t.reduce((s, q) => s + q, 0) / n, vb = a.v.reduce((s, q) => s + q, 0) / n, xs = [a.t[0], a.t[n - 1]];
  const line = s => xs.map(q => vb + s * (q - tb));      // trend lines through the centroid with the CI slopes -> confidence band
  plot("chart", [
    {x:xs, y:line(a.ci[0]), mode:"lines", line:{width:0}, hoverinfo:"skip", showlegend:false},
    {x:xs, y:line(a.ci[1]), mode:"lines", line:{width:0}, fill:"tonexty", fillcolor:"rgba(255,138,61,.2)", name:x.band, hoverinfo:"skip"},
    {x:a.t, y:a.v, mode:n > 60 ? "lines" : "lines+markers", name:x.data, line:{color:"#34D399", width:1.6}, marker:{size:6}, hovertemplate:`%{x:.2f}: %{y:.3g}${ub}<extra></extra>`},
    {x:xs, y:a.fit, mode:"lines", name:x.trend, line:{color:"#FF8A3D", dash:"dash", width:3}}],
    {yaxis:{title:u}, xaxis:{title:x.year}});
  const tile = (k, v, badge, tp) => `<div class="tile" title="${esc(tp ? tip(tp) : "")}"><small>${esc(k)}</small><b>${v}</b>${badge || ""}</div>`;
  const ok = (b, y, nn) => `<span class="badge ${b ? "ok" : ""}">${b ? y : nn}</span>`;
  $("tiles").innerHTML = [
    tile(x.slope, `${f3(a.slope)}${esc(ub)}${x.perYear}`, ok(a.sig, x.sig, x.nosig), "slope"),
    tile(x.ci, `[${f3(a.ci[0])}, ${f3(a.ci[1])}]`, "", "ci"), tile(x.pt_, fp(a.p_t), "", "p"), tile(x.mk, `${f3(a.tau)} / ${fp(a.p_mk)}`, "", "mk"),
    tile(x.sen, `${f3(a.sen)}${esc(ub)}${x.perYear}`, "", "sen"), tile(x.total, `${f3(a.total)}${esc(ub)}`, "", "total"),
    tile(x.r1, f3(a.r1), "", "r1"), tile(x.neff, `${f3(a.n_eff)} / ${a.n}`, "", "neff")].join("");
  $("verdict").textContent = a.verdict[lang]; $("verdict").style.borderColor = a.sig ? "#34D399" : "#8FA89B";
  renderQuality(); if (typeof renderEvidence === "function") renderEvidence();
}
const ym = tt => `${Math.floor(tt)}-${String(Math.floor((tt - Math.floor(tt)) * 12) + 1).padStart(2, "0")}`;
function renderQuality() {
  const a = S.a, q = a && a.quality; $("quality").hidden = !q; if (!q) return; const x = t();
  $("qT").textContent = x.qT; $("qT").title = tip("missing");
  const chip = (k, v, sub) => `<div class="tile"><small>${esc(k)}</small><b>${esc(v)}</b>${sub ? `<small>${esc(sub)}</small>` : ""}</div>`;
  $("qChips").innerHTML = [chip(x.qCov, `${(q.coverage * 100).toFixed(0)}%`, `${q.n_valid} / ${q.n_expected}`), chip(x.qMiss, String(q.n_missing)),
    chip(x.qGap, `${q.longest_gap} ${x.months}`), chip(x.qOutN, String(q.n_outliers))].join("");
  const IC = {ok:"✅", info:"ℹ️", warn:"⚠️"};
  $("qNotes").innerHTML = q.notes.map(n => `<li class="${esc(n.level)}">${IC[n.level] || "•"} ${esc(n[lang])}</li>`).join("");
  $("qOut").textContent = q.outliers.length ? x.qOutList + q.outliers.slice(0, 4).map(o => `${ym(o.t)} (${f3(o.v)})`).join(", ") : "";
  const mm = Object.keys(q.missing_by_month).map(Number).sort((u, v) => u - v);
  if (q.n_missing > 0) plot("qChart", [{type:"bar", x:mm.map(m => "T" + m), y:mm.map(m => q.missing_by_month[m]), marker:{color:"#FBBF24"}, hovertemplate:`%{x}: %{y}<extra></extra>`}],
    {height:170, margin:{t:24,r:8,b:28,l:34}, showlegend:false, title:{text:x.qMonth, font:{size:12}, x:0.02}, yaxis:{dtick:1, rangemode:"tozero"}});
  else $("qChart").hidden = true;
}
async function runAnalyze(over) {
  const v = over || $("var").value;
  const a = await api(`/api/analyze?${place()}&var=${encodeURIComponent(v)}&${range()}&deseason=${$("des").checked}&annual=${$("ann").checked}`);
  S.a = a; aMeta = {unit:(varOf(v) || {unit:""}).unit, label:(varOf(v) || {name:{vi:v, en:v}}).name};
  renderAnalysis();
}

// ---------------------------------------------------------- variable scan
function renderScan() {
  const r = S.scan; if (!r) return; const x = t();
  const nm = v => v.name[lang], fdr = r.filter(v => v.sig_fdr).length;
  $("scanNote").textContent = x.scanNote(fdr, r.length);
  const col = v => v.sig_fdr ? (v.effect_sd > 0 ? "#FF8A3D" : "#38BDF8") : v.sig ? (v.effect_sd > 0 ? "#8a5230" : "#2f6f8c") : "#46604f";
  const rows = [...r].sort((p, q) => q.effect_sd - p.effect_sd);
  plot("scanChart", [{type:"bar", orientation:"h", y:rows.map(nm), x:rows.map(v => v.effect_sd), marker:{color:rows.map(col)},
    customdata:rows.map(v => `${f3(v.slope)} ${v.unit}${x.perYear}; q=${fp(v.q)}`), hovertemplate:`%{y}: %{x:.2f} SD<br>%{customdata}<extra></extra>`}],
    {height:70 + 24 * rows.length, margin:{t:8,r:12,b:44,l:200}, showlegend:false, xaxis:{title:x.colEff, zeroline:true}, yaxis:{autorange:"reversed", automargin:true}});
  $("scanWrap").hidden = false;
  $("scanHead").innerHTML = `<th>${x.colVar}</th><th>${x.colTrend}</th><th title="${esc(tip("effect"))}">${x.colEff}</th><th title="${esc(tip("fdr"))}">${x.colQ}</th><th>${x.colRes}</th><th title="${esc(tip("evidence"))}">${x.colEv}</th>`;
  $("scanBody").innerHTML = r.map(v => `<tr><td><a class="city" data-v="${esc(v.var)}">${esc(nm(v))}</a><br><small class="note">${v.kind === "preset" ? x.src_g : x.src_p}</small></td>
    <td class="num">${f3(v.slope)} ${esc(v.unit)}${x.perYear}</td><td class="num">${v.effect_sd > 0 ? "+" : ""}${v.effect_sd.toFixed(2)}</td><td class="num">${fp(v.q)}</td>
    <td>${v.sig_fdr ? "✔ " + x.rFdr : v.sig ? "(✔) " + x.rSig : "– " + x.rNo}</td><td>${evChip(v.evidence)}</td></tr>`).join("");
}
async function runScan() { S.scan = await api(`/api/scan?${place()}&${range()}`); renderScan(); }
function selectVar(id) {
  const v = varOf(id); if (!v) return;
  $("topic").value = v.topic; fillVars(); $("var").value = id; $("desc").textContent = v.desc ? v.desc[lang] : ""; $("lagALbl").textContent = t().lagA + " " + nameOf(id);
}

// -------------------------------------------------------------- 2. lag
function renderLag() {
  const l = S.lag; if (!l) return; $("lagOut").hidden = false; const x = t();
  const bi = l.lags.indexOf(l.best_lag);
  plot("lagChart", [{type:"bar", x:l.lags.map(k => `${k} ${x.month}`), y:l.r, marker:{color:l.lags.map(k => k === l.best_lag ? "#FF8A3D" : "#34D399")},
    text:l.r.map(r => r.toFixed(2)), textposition:"outside", cliponaxis:false,
    customdata:l.p.map(fp), hovertemplate:`r = %{y:.3f}<br>p = %{customdata}<extra></extra>`}],
    {yaxis:{title:"r", range:[Math.min(-0.1, ...l.r) * 1.25 - .05, Math.max(0.1, ...l.r) * 1.25 + .05], zeroline:true}, xaxis:{title:x.lagAxis}, showlegend:false,
     annotations:[{x:bi, y:l.r[bi], text:"★ " + x.lagBest, showarrow:false, yshift:l.r[bi] >= 0 ? 28 : -28, font:{color:"#FF8A3D"}}]});
  $("lagBest").textContent = `★ ${x.lagBest}: ${l.best_lag} ${x.month}; r = ${f3(l.r[bi])}, p ${l.p[bi] < 0.001 ? "" : "= "}${fp(l.p[bi])} (${l.sig ? x.lagSig : x.lagNo}).  A: ${nameOf(l.a)} → B: ${nameOf(l.b)}`;
  $("lagCav").textContent = "⚠ " + l.caveat[lang];
}
async function runLag() {
  S.lag = await api(`/api/lag?${place()}&a=${encodeURIComponent($("var").value)}&b=${encodeURIComponent($("varB").value)}&${range()}`); renderLag();
}

// ------------------------------------------------------------ 3. anomaly
function renderAnomaly() {
  const d = S.ano; if (!d) return; const x = t(), m = d.months, u = d.unit, ub = u ? " " + u : "";
  const hi = m.filter(q => q.flag === "high"), lo = m.filter(q => q.flag === "low");
  const tr = (arr, name, color) => ({x:arr.map(q => q.t), y:arr.map(q => q.v), mode:"markers", name:`${name} (${arr.length})`, marker:{color, size:9, line:{color:"#fff", width:1}}, hovertemplate:`%{x:.2f}: %{y:.3g}${ub}<extra>${name}</extra>`});
  plot("anoChart", [
    {x:m.map(q => q.t), y:m.map(q => q.p05), mode:"lines", line:{width:0}, hoverinfo:"skip", showlegend:false},
    {x:m.map(q => q.t), y:m.map(q => q.p95), mode:"lines", line:{width:0}, fill:"tonexty", fillcolor:"rgba(52,211,153,.16)", name:x.anoBand, hoverinfo:"skip"},
    {x:m.map(q => q.t), y:m.map(q => q.v), mode:"lines", line:{color:"#8FA89B", width:1.2}, name:x.data, hovertemplate:`%{x:.2f}: %{y:.3g}${ub}<extra></extra>`},
    tr(hi, x.anoHigh, "#FF8A3D"), tr(lo, x.anoLow, "#38BDF8")], {yaxis:{title:u}, xaxis:{title:x.year}});
  $("anoNote").textContent = x.anoFlag(d.n_flagged);
}
async function runAnomaly() { S.ano = await api(`/api/anomaly?${place()}&var=${encodeURIComponent($("var").value)}&${range()}`); renderAnomaly(); }

// ------------------------------------------------------ ranking + compare
const picked = () => [...document.querySelectorAll("#rankBody input:checked")].map(i => i.value);
function renderRank(fit) {
  const r = S.rank; if (!r) return; const x = t(), u = cur().unit;
  $("rankWrap").hidden = false;
  $("rankHead").innerHTML = `<th></th><th>#</th><th>${x.colCity}</th><th>${x.colSlope} (${esc(u)}${x.perYear})</th><th>${x.colP}</th><th title="${esc(tip("fdr"))}">${x.colQ}</th><th>${x.colSig}</th>`;
  const keep = new Set(window.__picked || []), mark = c => c.sig_fdr ? "✔" : c.sig ? "(✔)" : "–";
  $("rankBody").innerHTML = r.map((c, i) => `<tr><td><input type="checkbox" value="${c.city}" aria-label="${esc(c.name[lang])}" ${keep.has(c.city) ? "checked" : ""}></td><td>${i + 1}</td>
   <td><a class="city" data-c="${c.city}">${esc(c.name[lang])}</a></td><td class="num">${f3(c.slope)}</td><td class="num">${fp(c.p)}</td><td class="num">${fp(c.q)}</td><td>${mark(c)}</td></tr>`).join("");
  $("rankCmp").disabled = false;
  layer.clearLayers(); const mx = Math.max(...r.map(c => Math.abs(c.slope))) || 1;
  r.forEach(c => L.circleMarker([c.lat, c.lon], {radius:11, color:c.slope > 0 ? "#FF8A3D" : "#38BDF8", weight:c.sig_fdr ? 4 : 1, fillOpacity:.2 + .6 * Math.abs(c.slope) / mx})
    .bindTooltip(`${c.name[lang]}: ${f3(c.slope)} ${u}${x.perYear}, p=${fp(c.p)}, q=${fp(c.q)} ${mark(c)}`).addTo(layer));
  if (fit && r.length) map.fitBounds(L.latLngBounds(r.map(c => [c.lat, c.lon])), {padding:[30, 30], maxZoom: 8});
  const up = r.filter(c => c.sig_fdr && c.slope > 0).map(c => c.name[lang]), dn = r.filter(c => c.sig_fdr && c.slope < 0).map(c => c.name[lang]);
  $("oppNote").hidden = false;
  $("oppNote").textContent = (up.length && dn.length) ? x.oppBoth(up.join(", "), dn.join(", ")) : (up.length || dn.length) ? x.oppOne(up.length ? x.oppUp : x.oppDown, (up.length ? up : dn).join(", ")) : x.oppNone;
  $("oppNote").textContent += "  " + x.rankFdr;
}
async function runRank() {
  if (!VARS.some(v => v.id === $("var").value)) throw new Error(t().notPower);
  S.rank = await api(`/api/ranking?var=${encodeURIComponent($("var").value)}&region=${$("region").value}&${range()}`); window.__picked = []; renderRank(true);
}
async function runOpposite() {                           // same variable, opposite directions in different places
  selectVar("CLOUD_AMT"); $("region").value = "all"; $("y0").value = 2000; $("y1").value = 2024;
  await runRank(); $("rankCard").scrollIntoView({behavior:"smooth", block:"start"});
}
function renderCompare() {
  const c = S.cmp; if (!c) return; const x = t(), u = cur().unit;
  plot("cmpChart", c.flatMap((e, i) => [
    {x:e.a.t, y:e.a.v, mode:"lines+markers", name:e.name[lang], line:{color:COLORS[i % 5], width:2}, marker:{size:5}},
    {x:[e.a.t[0], e.a.t[e.a.t.length - 1]], y:e.a.fit, mode:"lines", line:{color:COLORS[i % 5], dash:"dash", width:1.5}, showlegend:false, hoverinfo:"skip"}]),
    {yaxis:{title:u}, xaxis:{title:x.year}, title:{text:x.cmpTitle, font:{size:14}, x:0.02}, margin:{t:34,r:12,b:44,l:56}});
}
async function runCompare() {
  const ids = picked(); if (ids.length < 2 || ids.length > 5) throw new Error(t().cmpNeed);
  const v = encodeURIComponent($("var").value), rg = range();
  S.cmp = await Promise.all(ids.map(async (id, i) => {
    const a = await api(`/api/analyze?city=${id}&var=${v}&${rg}&deseason=true&annual=true`);
    if (MOCK) { a.v = a.v.map(q => q * (0.6 + 0.35 * i)); a.fit = a.fit.map(q => q * (0.6 + 0.35 * i)); }   // mock returns one file for every city
    return {name:CITIES.find(c => c.id === id).name, a};
  }));
  renderCompare();
}

// ------------------------------------------------------------------ upload
async function runUpload() {
  const file = $("file").files[0]; if (!file) throw new Error(t().nofile);
  const fd = new FormData(); fd.append("file", file);
  const q = new URLSearchParams({deseason:$("des").checked, annual:$("ann").checked, unit:$("upUnit").value});
  const nm = $("upName").value.trim(); if (nm) q.set("name", nm);
  S.a = await api("/api/upload?" + q, {method:"POST", body:fd});
  const label = nm || file.name.replace(/\.[^.]+$/, ""); aMeta = {unit:$("upUnit").value, label:{vi:label, en:label}};
  renderAnalysis(); $("out").scrollIntoView({behavior:"smooth", block:"start"});
}

// ------------------------------------------------------ automatic summary
const ICON = {trend:"📈", change:"↕️", extreme:"🏔️", season:"🗓️", anomaly:"⚠️", lag:"🔗", rank:"🏅", quality:"ℹ️"};
function renderSummary() {
  const s = S.sum; if (!s) return; const x = t(), f = s.facts, u = s.unit, ub = u ? " " + u : "";
  $("sumOut").hidden = false; $("sumCopy").disabled = false; $("sumCopy").textContent = x.sumCopy;
  $("sumHead").textContent = s.headline[lang];
  const chip = (k, v, sub) => `<div class="tile"><small>${esc(k)}</small><b>${esc(v)}</b>${sub ? `<small>${esc(sub)}</small>` : ""}</div>`;
  const sign = q => (q > 0 ? "+" : "") + f3(q);
  const chips = [chip(x.cSlope, `${sign(f.slope)}${ub}${x.perYear}`, f.sig ? x.sig : x.nosig)];
  if (f.block_diff !== undefined) chips.push(chip(x.cDiff, `${sign(f.block_diff)}${ub}`, `${f3(f.last_mean)} vs ${f3(f.first_mean)}`));
  if (f.n_high !== undefined) chips.push(chip(x.cAno, `${f.n_high_recent} / ${f.n_high}`));
  if (f.lag_r !== undefined) chips.push(chip(x.cLag, `r = ${f.lag_r.toFixed(2)}`, `${f.best_lag} ${x.month}`));
  if (f.rank !== undefined) chips.push(chip(x.cRank, `${f.rank} / ${f.rank_total}`));
  $("sumChips").innerHTML = chips.join("");
  $("sumList").innerHTML = s.bullets.map(b => `<li class="${esc(b.tone)}"><span class="ic" aria-hidden="true">${ICON[b.kind] || "•"}</span><span>${esc(b[lang])}</span></li>`).join("");
  $("sumSrc").textContent = x.sumSrc(s.period[0], s.period[1]);
  const y = s.yearly.y, v = s.yearly.v, tr = [{x:y, y:v, mode:"lines+markers", name:x.sumYear, line:{color:"#34D399", width:2}, marker:{size:6}, hovertemplate:`%{x}: %{y:.3g}${ub}<extra></extra>`}];
  if (f.block_years) { const k = f.block_years;
    tr.push({x:[y[0], y[k - 1]], y:[f.first_mean, f.first_mean], mode:"lines", name:x.sumFirst(k), line:{color:"#38BDF8", width:4}, hoverinfo:"skip"},
            {x:[y[y.length - k], y[y.length - 1]], y:[f.last_mean, f.last_mean], mode:"lines", name:x.sumLast(k), line:{color:"#FF8A3D", width:4}, hoverinfo:"skip"}); }
  if (f.max_year !== undefined) { const i = y.indexOf(f.max_year), j = y.indexOf(f.min_year);
    tr.push({x:[y[i], y[j]], y:[v[i], v[j]], mode:"markers+text", text:[`${x.sumMax} ${y[i]}`, `${x.sumMin} ${y[j]}`], textposition:["top center", "bottom center"], cliponaxis:false,
             marker:{size:12, color:["#FF8A3D", "#38BDF8"], line:{color:"#fff", width:2}}, showlegend:false, hoverinfo:"skip"}); }
  const pad = (Math.max(...v) - Math.min(...v)) * .25 || 1;
  plot("sumChart", tr, {yaxis:{title:u, range:[Math.min(...v) - pad, Math.max(...v) + pad]}, xaxis:{title:x.year}});
}
async function runSummary() {
  const v = $("var").value, b = $("varB").value;
  S.sum = await api(`/api/summary?${place()}&var=${encodeURIComponent(v)}${b && b !== v ? "&b=" + encodeURIComponent(b) : ""}&${range()}`);
  renderSummary();
}
async function copySummary() {
  const s = S.sum; if (!s) return; const text = s.text[lang];
  try { await navigator.clipboard.writeText(text); }
  catch (e) { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
  $("sumCopy").textContent = t().sumCopied; setTimeout(() => { $("sumCopy").textContent = t().sumCopy; }, 1500);
}

function renderAll() { renderSummary(); renderScan(); renderAnalysis(); renderLag(); renderAnomaly(); renderRank(); renderCompare(); }

// -------------------------------------------------------------- demo (HCMC)
async function runDemo() {
  setCity("hcm"); map.setView([pos.lat, pos.lon], 9);
  const ok = new Set(PRESETS.filter(p => p.available).map(p => p.id));
  const air = !MOCK && ok.has("hcm_aod") && ok.has("hcm_no2");                       // the dust/NO2 case once the Giovanni files are in place
  const a = air ? "hcm_no2" : "T2M", b = air ? "hcm_aod" : "RH2M";
  $("topic").value = (varOf(a) || {}).topic || "heat"; fillVars(); $("var").value = a; $("varB").value = b; $("lagALbl").textContent = t().lagA + " " + nameOf(a);
  $("y0").value = air ? $("y0").value : 2000; $("des").checked = true; $("ann").checked = false;
  await runAnalyze(a); await Promise.all([runLag(), runAnomaly(), runSummary(), runScan()]);
  $("out").scrollIntoView({behavior:"smooth", block:"start"});
}

// ------------------------------------------------------------------ events
$("run").onclick = e => task(e.currentTarget, async () => { await runAnalyze(); await runSummary(); });   // the summary follows every analysis
$("sumRun").onclick = e => task(e.currentTarget, runSummary);
$("sumCopy").onclick = copySummary;
$("demo").onclick = e => task(e.currentTarget, runDemo);
$("demo2").onclick = e => task(e.currentTarget, runOpposite);
$("scanRun").onclick = e => task(e.currentTarget, runScan);
$("scanBody").addEventListener("click", e => { const v = e.target.dataset && e.target.dataset.v;
  if (v) task($("run"), async () => { selectVar(v); await runAnalyze(); await runSummary(); $("out").scrollIntoView({behavior:"smooth", block:"start"}); }); });
$("lagRun").onclick = e => task(e.currentTarget, runLag);
$("anoRun").onclick = e => task(e.currentTarget, runAnomaly);
$("rankRun").onclick = e => task(e.currentTarget, runRank);
$("rankCmp").onclick = e => task(e.currentTarget, runCompare);
$("upRun").onclick = e => task(e.currentTarget, runUpload);
$("grid").onclick = e => task(e.currentTarget, async () => {
  const g = await api(`/api/grid?lat=${pos.lat}&lon=${pos.lon}&var=${encodeURIComponent($("var").value)}&${range()}`);
  layer.clearLayers(); const m = Math.max(...g.map(c => Math.abs(c.slope))) || 1;
  g.forEach(c => L.circleMarker([c.lat, c.lon], {radius:14, color:c.slope > 0 ? "#FF8A3D" : "#38BDF8", weight:c.sig ? 4 : 1, fillOpacity:.2 + .6 * Math.abs(c.slope) / m})
    .bindTooltip(`${f3(c.slope)} ${cur().unit}${t().perYear}, p=${fp(c.p)}${c.sig ? " ✔" : ""}`).addTo(layer));
});
$("rankBody").addEventListener("click", e => { const c = e.target.dataset && e.target.dataset.c; if (c) { setCity(c); map.setView([pos.lat, pos.lon], 8); } });
$("rankBody").addEventListener("change", () => { window.__picked = picked(); });
$("city").onchange = () => { setCity($("city").value); if (pos.city) map.setView([pos.lat, pos.lon], 8); };
$("topic").onchange = () => { fillVars(); };
$("var").onchange = () => { $("desc").textContent = cur().desc ? cur().desc[lang] : ""; $("lagALbl").textContent = t().lagA + " " + nameOf($("var").value); };
$("lang").onclick = () => { lang = lang === "vi" ? "en" : "vi"; txt(); };
const drop = $("drop");
["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", e => { if (e.dataTransfer.files.length) $("file").files = e.dataTransfer.files; });

(async () => {
  txt();
  try { [VARS, CITIES, PRESETS] = await Promise.all([api("/api/variables"), api("/api/cities"), api("/api/presets")]); }
  catch (e) { showErr(e.message); return; }
  txt(); window.APP_READY = true; document.dispatchEvent(new Event("app-ready"));
})();

const $=id=>document.getElementById(id);
const T={vi:{sub:"Chọn biến, bấm một điểm trên bản đồ, rồi kiểm tra xu hướng có ý nghĩa thống kê hay không. Dữ liệu: NASA POWER.",l1:"1. Chọn biến",l2:"2. Chọn nơi (bấm lên bản đồ)",des:"Bỏ chu kỳ mùa",ann:"Trung bình năm",run:"Phân tích",grid:"Bản đồ xu hướng 3×3",pt:"Điểm",foot:"Chỉ xu hướng tuyến tính. p-value đã hiệu chỉnh tự tương quan bậc 1.",wait:"Đang lấy dữ liệu từ NASA…",err:"Lỗi: "},
en:{sub:"Pick a variable, click a point on the map, and test whether the trend is statistically significant. Data: NASA POWER.",l1:"1. Choose a variable",l2:"2. Choose a place (click the map)",des:"Remove seasonal cycle",ann:"Yearly averages",run:"Analyze",grid:"3×3 trend map",pt:"Point",foot:"Linear trends only. p-values are adjusted for lag-1 autocorrelation.",wait:"Fetching data from NASA…",err:"Error: "}};
const TOPICS={heat:{vi:"Nhiệt độ",en:"Heat"},water:{vi:"Nước & mưa",en:"Water & rain"},air:{vi:"Không khí",en:"Air"},land:{vi:"Năng lượng mặt trời",en:"Solar"}};
let lang="vi",VARS=[],last=null,pos={lat:10.3,lon:105.8},marker,layer;
const map=L.map("map").setView([pos.lat,pos.lon],6);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap"}).addTo(map);
marker=L.marker([pos.lat,pos.lon]).addTo(map);layer=L.layerGroup().addTo(map);
map.on("click",e=>{pos={lat:+e.latlng.lat.toFixed(2),lon:+e.latlng.lng.toFixed(2)};marker.setLatLng(e.latlng);txt()});
const cur=()=>VARS.find(v=>v.id===$("var").value);
function txt(){const t=T[lang];for(const k of["sub","l1","l2","foot"])$(k).textContent=t[k];
 $("ldes").textContent=t.des;$("lann").textContent=t.ann;$("run").textContent=t.run;$("grid").textContent=t.grid;
 $("pt").textContent=`${t.pt}: ${pos.lat}, ${pos.lon}`;$("lang").textContent=lang==="vi"?"EN":"VI";
 const tp=$("topic").value||"heat";$("topic").innerHTML=Object.keys(TOPICS).map(k=>`<option value="${k}">${TOPICS[k][lang]}</option>`).join("");$("topic").value=tp;
 const vs=$("var").value;$("var").innerHTML=VARS.filter(v=>v.topic===tp).map(v=>`<option value="${v.id}">${v.name[lang]}</option>`).join("");if(vs&&[...$("var").options].some(o=>o.value===vs))$("var").value=vs;
 if(cur())$("desc").textContent=cur().desc[lang];if(last)show(last)}
const qs=()=>new URLSearchParams({lat:pos.lat,lon:pos.lon,var:$("var").value,start:$("y0").value,end:$("y1").value,deseason:$("des").checked,annual:$("ann").checked});
async function api(p){$("desc").textContent=T[lang].wait;const r=await fetch(p);if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail||r.status)}return r.json()}
function show(a){last=a;$("out").hidden=false;const u=cur().unit;
 Plotly.newPlot("chart",[{x:a.t,y:a.v,mode:"lines",name:"data",line:{color:"#0f7c8a"}},
 {x:[a.t[0],a.t[a.t.length-1]],y:a.fit,mode:"lines",name:"trend",line:{color:"#c2410c",dash:"dash",width:3}}],
 {margin:{t:10,r:10,b:40,l:55},yaxis:{title:u},xaxis:{title:"year"},legend:{orientation:"h"}},{responsive:true});
 const f=x=>+x.toPrecision(3);
 $("stats").innerHTML=[["n / n_eff",`${a.n} / ${f(a.n_eff)}`],["Slope",`${f(a.slope)} ${u}/yr`],["95% CI",`[${f(a.ci[0])}, ${f(a.ci[1])}]`],["t-test p",f(a.p_t)],["Mann-Kendall τ / p",`${f(a.tau)} / ${f(a.p_mk)}`],["Sen",`${f(a.sen)} ${u}/yr`],["lag-1 r",f(a.r1)]].map(r=>`<tr><th>${r[0]}</th><td>${r[1]}</td></tr>`).join("");
 $("verdict").textContent=a.verdict[lang];$("verdict").style.borderColor=a.sig?"#0f7c8a":"#5a6b7b"}
$("run").onclick=async()=>{try{show(await api("/api/analyze?"+qs()));txt()}catch(e){alert(T[lang].err+e.message)}};
$("grid").onclick=async()=>{try{const g=await api("/api/grid?"+qs());layer.clearLayers();const m=Math.max(...g.map(c=>Math.abs(c.slope)))||1;
 g.forEach(c=>L.circleMarker([c.lat,c.lon],{radius:14,color:c.slope>0?"#c2410c":"#1d4ed8",weight:c.sig?4:1,fillOpacity:.2+.6*Math.abs(c.slope)/m})
 .bindTooltip(`${(+c.slope.toPrecision(3))} ${cur().unit}/yr, p=${(+c.p.toPrecision(2))}${c.sig?" ✔":""}`).addTo(layer));txt()}catch(e){alert(T[lang].err+e.message)}};
$("topic").onchange=txt;$("var").onchange=txt;$("lang").onclick=()=>{lang=lang==="vi"?"en":"vi";txt()};
fetch("/api/variables").then(r=>r.json()).then(v=>{VARS=v;txt()});

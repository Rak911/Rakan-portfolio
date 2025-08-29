
const TBL = document.getElementById('tbl');
const TBODY = document.getElementById('tbody');
const totalsCell = document.getElementById('totalsCell');
const refreshBtn = document.getElementById('refreshBtn');
const saveBtn = document.getElementById('saveBtn');
const exportBtn = document.getElementById('exportBtn');
const usdSarInput = document.getElementById('usdSar');
const sunbullahNavInput = document.getElementById('sunbullahNav');

const STORAGE_KEY = "rakan_web_holdings_v1";
const STORAGE_NAV = "rakan_web_sunbullah_nav";
const STORAGE_USD = "rakan_web_usd_sar";

function loadHoldings(){
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}
function saveHoldings(holdings){
  localStorage.setItem(STORAGE_KEY, JSON.stringify(holdings));
}
function defaultHoldings(){
  return null; // we let backend baseline
}

function fmt(n, digits=1){
  if (n===null || n===undefined || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString(undefined, {maximumFractionDigits: digits});
}

function fetchSummary(){
  const holdings = loadHoldings(); // if null -> backend baseline
  const payload = {
    holdings: holdings || undefined,
    sunbullah_nav: sunbullahNavInput.value ? Number(sunbullahNavInput.value) : null,
    usd_sar: usdSarInput.value ? Number(usdSarInput.value) : 3.75
  };
  return fetch("/api/summary", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  }).then(r => r.json());
}

function renderTable(data){
  TBODY.innerHTML = "";
  let totalZakat = 0;

  (data.rows || []).forEach(r => {
    const tr = document.createElement('tr');

    // Price formatting: SPUS row shows unit price without word "ريال"
    let priceCell = "—";
    if (r.price != null){
      if (r.name === "الصندوق الأمريكي الإسلامي"){
        priceCell = `${fmt(r.price, 1)}`; // no "ريال"
      } else {
        priceCell = `${fmt(r.price, 1)} ريال`;
      }
    }

    const mv = r.market_value != null ? `${fmt(r.market_value, 0)} ريال` : "—";
    const pl = r.pl != null ? `${fmt(r.pl, 0)} ريال` : "—";
    const plClass = r.pl == null ? "" : (r.pl >= 0 ? "pos" : "neg");

    const zakat = r.zakat != null ? r.zakat : 0;
    totalZakat += zakat || 0;
    const zk = r.zakat != null ? `${fmt(r.zakat, 0)} ريال` : "—";

    tr.innerHTML = `
      <td>${r.name}</td>
      <td class="mono">${r.qty ?? "—"}</td>
      <td class="mono">${r.avg != null ? fmt(r.avg, 1) : "—"}</td>
      <td class="mono">${priceCell}</td>
      <td class="mono">${mv}</td>
      <td class="mono ${plClass}">${pl}</td>
      <td class="mono">${zk}</td>
    `;
    TBODY.appendChild(tr);
  });

  const totalMkt = data.totals?.market_value ?? 0;
  const totalCost = data.totals?.total_cost ?? 0;
  const totalPL = data.totals?.pl ?? (totalMkt - totalCost);
  const pct = data.totals?.pl_pct != null ? data.totals.pl_pct : (totalCost ? (totalPL/totalCost*100) : null);

  const sign = totalPL >= 0 ? "+" : "";
  const pctText = pct != null ? ` (${sign}${fmt(pct,1)}%)` : "";
  totalsCell.innerHTML = `
    <div>الإجمالي السوقي: <strong>${fmt(totalMkt,0)} ريال</strong></div>
    <div>إجمالي الربح/الخسارة: <strong class="${totalPL>=0?"pos":"neg"}">${sign}${fmt(totalPL,0)} ريال</strong>${pctText}</div>
    <div>إجمالي الزكاة (الصناديق فقط): <strong>${fmt(totalZakat,0)} ريال</strong></div>
    <div style="margin-top:6px;">📌 إجمالي محفظتك اليوم ${fmt(totalMkt,0)} ريال.</div>
  `;
}

function refresh(){
  fetchSummary().then(renderTable).catch(()=>{
    totalsCell.textContent = "تعذر جلب الأسعار الآن.";
  });
}

refreshBtn.addEventListener('click', refresh);

saveBtn.addEventListener('click', () => {
  // For now, just save nav & usd/sar
  if (sunbullahNavInput.value) localStorage.setItem(STORAGE_NAV, sunbullahNavInput.value);
  if (usdSarInput.value) localStorage.setItem(STORAGE_USD, usdSarInput.value);
  alert("تم الحفظ ✅");
});

exportBtn.addEventListener('click', async () => {
  // Export current table as plain text
  const text = TBL.innerText;
  const blob = new Blob([text], {type: "text/plain"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "rakan_portfolio_summary.txt";
  a.click();
  URL.revokeObjectURL(url);
});

// Load saved settings
(function init(){
  const navSaved = localStorage.getItem(STORAGE_NAV);
  if (navSaved) sunbullahNavInput.value = navSaved;
  const usdSaved = localStorage.getItem(STORAGE_USD);
  if (usdSaved) usdSarInput.value = usdSaved;
  refresh();
  setInterval(refresh, 60_000);
})();

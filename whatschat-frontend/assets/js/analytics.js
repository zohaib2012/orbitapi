// analytics.js — Path: whatschat-frontend/assets/js/analytics.js

let perfChart=null, deviceChart=null;

document.addEventListener("DOMContentLoaded", async () => {
  Auth.requireAuth();
  fillSidebarUser();
  await loadAll("7days");
});

async function loadAll(period) {
  await Promise.all([loadOverview(period), loadPerfChart(period), loadDevices(), loadCampPerf()]);
}

async function loadOverview(period) {
  try {
    const d = await Analytics.getOverview(period);
    setVal("stat-total-sent",     d.total_sent?.toLocaleString());
    setVal("stat-delivery-rate",  d.delivery_rate + "%");
    setVal("stat-read-rate",      d.read_rate + "%");
    setVal("stat-click-rate",     d.click_rate + "%");
    setVal("stat-avg-response",   d.avg_response_time + "s");
    setVal("stat-delivered-sub",  d.total_delivered?.toLocaleString() + " delivered");
    setVal("stat-read-sub",       d.total_read?.toLocaleString() + " read");
    setVal("stat-click-sub",      d.total_clicked?.toLocaleString() + " clicks");
  } catch(e) { console.error(e); }
}

async function loadPerfChart(period) {
  try {
    const daily = await Analytics.getDaily(period);
    if (perfChart) perfChart.destroy();
    const ctx = document.getElementById("perfChart");
    if (!ctx || typeof Chart==="undefined") return;
    perfChart = new Chart(ctx.getContext("2d"), {
      type:"line",
      data:{
        labels: daily.map(d=>d.date),
        datasets:[
          {label:"Sent",      data:daily.map(d=>d.sent),      borderColor:"#25D366",tension:0.4,pointRadius:3,fill:false},
          {label:"Delivered", data:daily.map(d=>d.delivered), borderColor:"#3b82f6",tension:0.4,pointRadius:3,fill:false},
          {label:"Read",      data:daily.map(d=>d.read),      borderColor:"#f97316",tension:0.4,pointRadius:3,fill:false},
          {label:"Clicked",   data:daily.map(d=>d.clicked||0),borderColor:"#8b5cf6",tension:0.4,pointRadius:3,fill:false},
        ]
      },
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:"#f3f4f6"},ticks:{font:{family:"DM Sans",size:11},color:"#9ca3af"}},y:{grid:{color:"#f3f4f6"},ticks:{font:{family:"DM Sans",size:11},color:"#9ca3af"},beginAtZero:true}}}
    });
  } catch(e) { console.error(e); }
}

async function loadDevices() {
  try {
    const d = await Analytics.getDevices();
    if (deviceChart) deviceChart.destroy();
    const ctx = document.getElementById("deviceChart");
    if (ctx && typeof Chart!=="undefined") {
      deviceChart = new Chart(ctx.getContext("2d"), {
        type:"pie",
        data:{labels:["Android","iOS","Web"],datasets:[{data:[d.android,d.ios,d.web],backgroundColor:["#25D366","#3b82f6","#f97316"],borderWidth:2,borderColor:"#fff"}]},
        options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}
      });
    }
    setVal("dev-android", d.android?.toLocaleString());
    setVal("dev-ios",     d.ios?.toLocaleString());
    setVal("dev-web",     d.web?.toLocaleString());
  } catch(e) { console.error(e); }
}

async function loadCampPerf() {
  try {
    const data = await Analytics.getCampaigns();
    const tbody = document.getElementById("camp-perf-table");
    if (!tbody) return;
    if (!data.length) { tbody.innerHTML=`<tr><td colspan="3" style="text-align:center;padding:20px;color:#9ca3af">No data yet</td></tr>`; return; }
    tbody.innerHTML = data.map(c=>`
      <tr>
        <td style="padding:10px 16px">${c.name}</td>
        <td style="padding:10px 16px">${c.sent?.toLocaleString()}</td>
        <td style="padding:10px 16px">
          <div style="display:flex;align-items:center;gap:8px">
            <div style="flex:1;height:6px;background:#e5e7eb;border-radius:3px"><div style="width:${c.read_rate}%;height:100%;background:#25D366;border-radius:3px"></div></div>
            <span style="font-size:12px;font-weight:600;min-width:36px">${c.read_rate}%</span>
          </div>
        </td>
      </tr>`).join("");
  } catch(e) { console.error(e); }
}

function changePeriod(p) { loadAll(p); }